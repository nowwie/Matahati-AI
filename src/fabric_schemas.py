from typing import Literal

from pydantic import BaseModel, Field


# INPUT SCHEMA

class FabricMeasurements(BaseModel):
    chest: float = Field(gt=0, le=400)
    waist: float = Field(gt=0, le=400)
    shoulder: float = Field(gt=0, le=400)
    length: float = Field(gt=0, le=400)
    sleeve: float = Field(gt=0, le=400)

    # Optional measurements
    hip: float | None = Field(default=None, gt=0, le=400)
    thigh: float | None = Field(default=None, gt=0, le=400)


class FabricAllowances(BaseModel):
    patternMatching: bool
    oneWay: bool
    details: bool


class FabricEstimateRequest(BaseModel):
    garmentType: Literal[
        "shirt", "blouse", "skirt",
        "pants", "dress", "outer"
    ]

    fit: Literal["slim", "regular", "oversized"]
    sleeve: Literal["short", "long", "none"]

    measurementsCm: FabricMeasurements | None
    fabricWidthCm: float | None = Field(gt=0, le=400)

    allowances: FabricAllowances


# OUTPUT SCHEMA

class FabricEstimateSuccess(BaseModel):
    status: Literal["ok"]
    ruleId: str
    layoutM: float
    extraM: float
    totalM: float


class FabricEstimateUnavailable(BaseModel):
    status: Literal["unavailable"]
    ruleId: str
    reason: Literal["measurements", "width"]
