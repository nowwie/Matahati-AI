
from fabric_schemas import FabricEstimateRequest
from fabric_estimator import estimate_fabric


# Data pengujian
base_measurements = {
    "chest": 90,
    "waist": 75,
    "shoulder": 40,
    "length": 100,
    "sleeve": 55,
}

allowances = {
    "patternMatching": True,
    "oneWay": True,
    "details": False,
}


# Test 1: Semua jenis pakaian
garments = ["shirt", "blouse", "skirt", "pants", "dress", "outer"]

for garment in garments:
    request = FabricEstimateRequest(
        garmentType=garment,
        fit="regular",
        sleeve="long",
        measurementsCm=base_measurements,
        fabricWidthCm=115,
        allowances=allowances,
    )

    print(f"\nJenis pakaian: {garment}")
    print(estimate_fabric(request))


# Test 2: Pants dengan hip dan thigh
request_with_optional = FabricEstimateRequest(
    garmentType="pants",
    fit="regular",
    sleeve="long",
    measurementsCm={
        **base_measurements,
        "hip": 95,
        "thigh": 55,
    },
    fabricWidthCm=115,
    allowances=allowances,
)

print("\nTest pants dengan hip dan thigh:")
print(estimate_fabric(request_with_optional))


# Test 3: Pants tanpa hip dan thigh
request_without_optional = FabricEstimateRequest(
    garmentType="pants",
    fit="regular",
    sleeve="long",
    measurementsCm=base_measurements,
    fabricWidthCm=115,
    allowances=allowances,
)

print("\nTest pants tanpa hip dan thigh:")
print(estimate_fabric(request_without_optional))
