from typing import Any, Literal

from pydantic import BaseModel, Field


ScaleLevel = Literal["object", "component", "subcomponent", "material", "molecule", "atom"]


class ObjectModelRef(BaseModel):
    kind: Literal["procedural", "gltf"] = "procedural"
    asset_url: str | None = Field(default=None, alias="assetUrl")


class MicroLevel(BaseModel):
    level: ScaleLevel
    name: str
    description: str
    next: str | None = None


class SimulationProperties(BaseModel):
    mass: float = Field(default=1.0)
    heat_generation: float = Field(default=0.0, alias="heatGeneration")
    energy_consumption: float = Field(default=0.0, alias="energyConsumption")


class ObjectComponent(BaseModel):
    id: str
    name: str
    parent_id: str | None = Field(default=None, alias="parentId")
    scale_level: ScaleLevel = Field(default="component", alias="scaleLevel")
    function: str
    material: str | None = None
    risk_if_removed: str | None = Field(default=None, alias="riskIfRemoved")
    position: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    color: str = "#5ec8d8"
    geometry: dict[str, Any] = Field(default_factory=dict)
    layout: dict[str, Any] | None = None
    children: list[str] = Field(default_factory=list)
    micro_levels: list[MicroLevel] = Field(default_factory=list, alias="microLevels")
    simulation_properties: SimulationProperties | None = Field(default=None, alias="simulationProperties")


class ExplorableObject(BaseModel):
    id: str
    name: str
    type: str
    summary: str
    default_view: str = Field(default="assembled", alias="defaultView")
    model: ObjectModelRef = Field(default_factory=ObjectModelRef)
    components: list[ObjectComponent]


class ObjectSearchResult(BaseModel):
    id: str
    name: str
    type: str
    summary: str
    component_count: int = Field(alias="componentCount")

