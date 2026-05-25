import ast
import operator
from typing import Dict, Any, List, Set, Tuple

# Safe whitelist of mathematical operators
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

class SafeEvaluator(ast.NodeVisitor):
    def __init__(self, context: dict):
        self.context = context

    def visit_BinOp(self, node):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Operator {op_type.__name__} is not allowed.")
        return SAFE_OPERATORS[op_type](self.visit(node.left), self.visit(node.right))

    def visit_UnaryOp(self, node):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Operator {op_type.__name__} is not allowed.")
        return SAFE_OPERATORS[op_type](self.visit(node.operand))

    def visit_Num(self, node):
        return node.n

    def visit_Constant(self, node):
        # Support Python 3.8+ Constant node
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Constant type {type(node.value).__name__} is not allowed.")

    def visit_Name(self, node):
        if node.id in self.context:
            return self.context[node.id]
        raise NameError(f"Variable '{node.id}' is not defined in the parameter scope.")

    def visit_Attribute(self, node):
        # Safe attribute lookup: e.g. parent.radius or shaft.depth
        if isinstance(node.value, ast.Name):
            obj_name = node.value.id
            attr_name = node.attr
            if obj_name in self.context:
                obj_val = self.context[obj_name]
                if isinstance(obj_val, dict):
                    if attr_name in obj_val:
                        return obj_val[attr_name]
                    # Also support size array indices or size mapping
                    if attr_name == "size" and "size" in obj_val:
                        return obj_val["size"]
                    raise AttributeError(f"Object '{obj_name}' has no attribute '{attr_name}'")
                raise TypeError(f"Object '{obj_name}' is not a structure or component.")
            raise NameError(f"Object '{obj_name}' is not defined in the hierarchy scope.")
        raise ValueError("Complex attribute chaining is not allowed.")

    def generic_visit(self, node):
        raise ValueError(f"Expression node type {type(node).__name__} is not allowed.")

def safe_eval(expr: Any, context: dict) -> Any:
    """Evaluates an expression string using a secure AST whitelist."""
    if not isinstance(expr, str):
        return expr
    # Try parsing as float first for speed
    try:
        return float(expr)
    except ValueError:
        pass

    try:
        tree = ast.parse(expr, mode='eval')
        evaluator = SafeEvaluator(context)
        return evaluator.visit(tree.body)
    except Exception as e:
        raise ValueError(f"Expression evaluation error for '{expr}': {e}")

class DependencyExtractor(ast.NodeVisitor):
    def __init__(self):
        self.dependencies = set()

    def visit_Name(self, node):
        self.dependencies.add(node.id)

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name):
            self.dependencies.add(node.value.id)
        else:
            self.generic_visit(node)

    def generic_visit(self, node):
        for child in ast.iter_child_nodes(node):
            self.visit(child)

def extract_dependencies(expr: Any) -> Set[str]:
    """Extracts variable or component references from an expression string."""
    if not isinstance(expr, str):
        return set()
    try:
        tree = ast.parse(expr, mode='eval')
        extractor = DependencyExtractor()
        extractor.visit(tree)
        return extractor.dependencies
    except Exception:
        return set()

def resolve_parametric_object(components: List[Dict[str, Any]], parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Sorts components topologically based on expression dependencies and evaluates
    all relative dimensions and coordinates securely.
    """
    # 1. Build dependency graph of components
    comp_dict = {c["id"]: c for c in components if "id" in c}
    adj_list: Dict[str, Set[str]] = {cid: set() for cid in comp_dict}
    
    for comp in components:
        cid = comp["id"]
        parentId = comp.get("parentId")
        
        # Traverse all expression fields to find references
        fields_to_check = []
        # Position expressions
        if "position" in comp:
            fields_to_check.extend(comp["position"])
        # Geometry expressions
        if "geometry" in comp:
            for val in comp["geometry"].values():
                if isinstance(val, list):
                    fields_to_check.extend(val)
                else:
                    fields_to_check.append(val)
                    
        for field in fields_to_check:
            deps = extract_dependencies(field)
            for dep in deps:
                if dep == "parent" and parentId:
                    adj_list[cid].add(parentId)
                elif dep in comp_dict:
                    adj_list[cid].add(dep)
                    
    # 2. Cycle Detection & Topological Sort (Kahn's or DFS)
    visited = {} # status: 0=unvisited, 1=visiting, 2=visited
    sorted_cids = []
    
    def dfs(node):
        visited[node] = 1 # visiting
        for neighbor in adj_list[node]:
            if visited.get(neighbor, 0) == 1:
                raise ValueError(f"Cyclic dependency detected in parametric formulas containing node '{node}' and '{neighbor}'.")
            if visited.get(neighbor, 0) == 0:
                dfs(neighbor)
        visited[node] = 2 # visited
        sorted_cids.append(node)
        
    for cid in comp_dict:
        if visited.get(cid, 0) == 0:
            dfs(cid)
            
    # 3. Evaluate expressions in topological order
    resolved_context = {**parameters}
    resolved_components = []
    
    for cid in sorted_cids:
        comp = comp_dict[cid]
        parentId = comp.get("parentId")
        
        # Add parent convenience reference to evaluation context
        eval_context = {**resolved_context}
        if parentId and parentId in resolved_context:
            eval_context["parent"] = resolved_context[parentId]
            
        # Resolve position coordinates
        resolved_pos = []
        for coord in comp.get("position", [0.0, 0.0, 0.0]):
            resolved_pos.append(float(safe_eval(coord, eval_context)))
            
        # Resolve geometry dimensions
        geometry = comp.get("geometry", {})
        resolved_geom = {}
        for geom_key, geom_val in geometry.items():
            if geom_key == "type":
                resolved_geom[geom_key] = geom_val
            elif isinstance(geom_val, list):
                resolved_geom[geom_key] = [float(safe_eval(v, eval_context)) for v in geom_val]
            elif isinstance(geom_val, (int, float, str)):
                # Keep string urls, resolve math parameters
                if geom_key == "url":
                    resolved_geom[geom_key] = geom_val
                else:
                    resolved_geom[geom_key] = safe_eval(geom_val, eval_context)
            else:
                resolved_geom[geom_key] = geom_val
                
        # Shallow copy component and update resolved properties
        resolved_comp = {**comp}
        resolved_comp["position"] = resolved_pos
        resolved_comp["geometry"] = resolved_geom
        
        resolved_components.append(resolved_comp)
        
        # Store resolved properties in context for other components to reference
        resolved_context[cid] = {
            "position": resolved_pos,
            **resolved_geom
        }
        
    # Re-order resolved components to preserve original array order (optional but cleaner)
    original_order = {c["id"]: idx for idx, c in enumerate(components)}
    resolved_components.sort(key=lambda c: original_order.get(c["id"], 999))
    
    return resolved_components
