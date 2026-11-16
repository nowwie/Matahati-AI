
import math

from fabric_schemas import FabricEstimateRequest


# FABRIC ESTIMATION CONSTANTS

EASE_CM = {
    "slim": 6,
    "regular": 10,
    "oversized": 20,
}

SEAM_CM = 1.5
HEM_CM = 3

OUTER_EXTRA_EASE_CM = 6
DRESS_FLARE = 1.2
HIP_FROM_WAIST = 1.25
CROTCH_EXT_CM = 5
SLEEVE_WIDTH_RATIO = 0.35
LAYOUT_WASTE = 1.15
NECK_FACING_CM = 15

PATTERN_MATCHING_RATIO = 0.15
ONE_WAY_RATIO = 0.10

DETAILS_CM = {
    "upper": 25,
    "lower": 15,
}

PURCHASE_STEP_M = 0.25


# HELPER FUNCTIONS

def round2(value: float) -> float:
    return math.floor(value * 100 + 0.5) / 100


def to_purchase_m(value: float) -> float:
    return math.ceil(round2(value) / PURCHASE_STEP_M) * PURCHASE_STEP_M


def calculate_rows(
    piece_width: float,
    pieces: int,
    fabric_width: float
) -> int:
    per_row = max(1, math.floor(fabric_width / piece_width))
    return math.ceil(pieces / per_row)


# MAIN ESTIMATOR

def estimate_fabric(data: FabricEstimateRequest) -> dict:
    measurements = data.measurementsCm
    garment = data.garmentType

    rule_id = f"prototype-{garment}-v1"

    if measurements is None:
        return {
            "status": "unavailable",
            "ruleId": rule_id,
            "reason": "measurements",
        }

    if data.fabricWidthCm is None:
        return {
            "status": "unavailable",
            "ruleId": rule_id,
            "reason": "width",
        }

    width = data.fabricWidthCm
    ease = EASE_CM[data.fit]

    piece_length = measurements.length + HEM_CM + SEAM_CM

    is_lower = garment in ("skirt", "pants")

    if is_lower:
        hip = (
            measurements.hip
            if measurements.hip is not None
            else measurements.waist * HIP_FROM_WAIST
        ) + ease

        pieces = 2 if garment == "skirt" else 4

        piece_width = (
            hip / pieces
            + 2 * SEAM_CM
            + (CROTCH_EXT_CM if garment == "pants" else 0)
        )

        layout_cm = (
            calculate_rows(piece_width, pieces, width)
            * piece_length
        )

    else:
        circumference = (
            max(measurements.chest, measurements.waist)
            + ease
            + (
                OUTER_EXTRA_EASE_CM
                if garment == "outer"
                else 0
            )
        )

        flare = DRESS_FLARE if garment == "dress" else 1

        panel_width = (
            (circumference / 2) * flare
            + 2 * SEAM_CM
        )

        layout_cm = (
            calculate_rows(panel_width, 2, width)
            * piece_length
        )

        if data.sleeve != "none":
            sleeve_width = (
                circumference * SLEEVE_WIDTH_RATIO
                + 2 * SEAM_CM
            )

            sleeve_length = (
                measurements.sleeve
                + HEM_CM
                + SEAM_CM
            )

            layout_cm += (
                calculate_rows(sleeve_width, 2, width)
                * sleeve_length
            )

        layout_cm += NECK_FACING_CM

    layout_cm *= LAYOUT_WASTE

    extra_cm = 0

    if data.allowances.patternMatching:
        extra_cm += layout_cm * PATTERN_MATCHING_RATIO

    if data.allowances.oneWay:
        extra_cm += layout_cm * ONE_WAY_RATIO

    if data.allowances.details:
        extra_cm += (
            DETAILS_CM["lower"]
            if is_lower
            else DETAILS_CM["upper"]
        )

    layout_m = round2(layout_cm / 100)
    extra_m = round2(extra_cm / 100)

    total_m = to_purchase_m(layout_m + extra_m)

    return {
        "status": "ok",
        "ruleId": rule_id,
        "layoutM": layout_m,
        "extraM": extra_m,
        "totalM": total_m,
    }