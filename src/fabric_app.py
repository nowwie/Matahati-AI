
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from fabric_schemas import FabricEstimateRequest
from fabric_estimator import estimate_fabric

app = FastAPI(
    title="MATAHATI Fabric Estimation API",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "service": "MATAHATI Fabric Estimation",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/fabric-estimate")
def fabric_estimate(request: FabricEstimateRequest):
    try:
        return estimate_fabric(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fabric estimation failed: {str(e)}"
        )
