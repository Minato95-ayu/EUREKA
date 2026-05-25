import pytest
from app.services.parameter_resolver import safe_eval, resolve_parametric_object, extract_dependencies

def test_safe_eval_math():
    """Verify that safe_eval executes arithmetic whitelisted operations correctly."""
    context = {"x": 10, "y": 2.5}
    assert safe_eval("x + y * 2", context) == 15.0
    assert safe_eval("(x - 2) / 2", context) == 4.0
    assert safe_eval("-x", context) == -10
    
def test_safe_eval_attributes():
    """Verify that safe_eval resolves attributes on component descriptors securely."""
    context = {
        "parent": {"radius": 0.5, "depth": 1.2},
        "shaft": {"size": [1.0, 2.0, 3.0]}
    }
    assert safe_eval("parent.radius * 2", context) == 1.0
    assert safe_eval("parent.depth + 0.8", context) == 2.0
    assert safe_eval("shaft.size", context) == [1.0, 2.0, 3.0]

def test_safe_eval_sandbox_violation():
    """Verify that non-whitelisted actions raise errors instead of executing code."""
    context = {"x": 10}
    # Function calls disallowed
    with pytest.raises(ValueError, match="not allowed"):
        safe_eval("abs(x)", context)
        
    # Import attempts disallowed
    with pytest.raises(ValueError, match="not allowed"):
        safe_eval("__import__('os').system('ls')", context)

def test_extract_dependencies():
    """Verify extract_dependencies retrieves referenced variable and component names."""
    assert extract_dependencies("parent.radius * 2") == {"parent"}
    assert extract_dependencies("shaft.depth + block.depth") == {"shaft", "block"}
    assert extract_dependencies("1.5") == set()

def test_resolve_parametric_object():
    """Verify end-to-end topological evaluation of a parametric component list."""
    components = [
        {
            "id": "blade",
            "parentId": "shaft",
            "position": ["parent.radius + 0.05", 0.0, 0.0],
            "geometry": {"type": "box", "size": [0.4, 0.05, 0.1]}
        },
        {
            "id": "shaft",
            "parentId": None,
            "position": [0.0, 0.0, 0.0],
            "geometry": {"type": "cylinder", "radius": "shaft_radius", "depth": 2.0}
        }
    ]
    parameters = {"shaft_radius": 0.12}
    
    resolved = resolve_parametric_object(components, parameters)
    
    # Verify topological order was resolved correctly (shaft before blade)
    shaft_res = next(c for c in resolved if c["id"] == "shaft")
    blade_res = next(c for c in resolved if c["id"] == "blade")
    
    assert shaft_res["geometry"]["radius"] == 0.12
    assert blade_res["position"][0] == 0.12 + 0.05

def test_cyclic_dependency_raises():
    """Verify that cyclic dependencies are caught and raise value errors."""
    components = [
        {
            "id": "part_A",
            "position": ["part_B.position[0]", 0, 0],
            "geometry": {"type": "box"}
        },
        {
            "id": "part_B",
            "position": ["part_A.position[0]", 0, 0],
            "geometry": {"type": "box"}
        }
    ]
    
    with pytest.raises(ValueError, match="Cyclic dependency detected"):
        resolve_parametric_object(components, {})
