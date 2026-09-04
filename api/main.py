"""
FastAPI REST API Service for Landslide Risk Prediction & Document Analysis.

Exposes the validated ML prediction engine and document-to-feature extraction
bridge without duplicating any ML or validation logic.
"""

from datetime import datetime, timezone
import json
import os
import sys
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import shared canonical modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.data_validation import (
    REQUIRED_FEATURES,
    validate_prediction_input,
)
from scripts.extract_features import (
    predict_from_document,
)
from scripts.predict import (
    FEATURE_INFO_PATH,
    load_model_artifacts,
    predict_risk,
)

# ==============================================================================
# 1. FASTAPI APP INITIALIZATION
# ==============================================================================

app = FastAPI(
    title="SIH Landslide Risk Early-Warning & Decision-Support API",
    description=(
        "REST API for landslide risk classification, probabilistic confidence scoring, "
        "transparent contributing factor reason codes, and PDF report feature extraction. "
        "Demonstration/MVP Decision Support Component."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for dashboard/frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# 2. PYDANTIC REQUEST & RESPONSE SCHEMAS
# ==============================================================================

class PredictRequest(BaseModel):
    """
    Schema for tabular 8-feature inference input.
    Pydantic enforces types; domain validation engine enforces physical sanity.
    """
    rainfall_24h: float = Field(..., description="24-hour cumulative rainfall in mm (>= 0)", example=182.0)
    rainfall_3d: float = Field(..., description="3-day cumulative rainfall in mm (>= 0)", example=420.0)
    rainfall_7d: float = Field(..., description="7-day cumulative rainfall in mm (>= 0)", example=650.0)
    slope: float = Field(..., description="Terrain slope angle in degrees (0 to 90)", example=38.0)
    elevation: float = Field(..., description="Elevation in metres (-500 to 9000)", example=850.0)
    historical_landslide: int = Field(..., description="Binary indicator of past landslide (0 or 1)", example=1)
    distance_to_landslide: float = Field(..., description="Distance to nearest historical landslide in km (>= 0)", example=0.8)
    soil_risk: float = Field(..., description="Soil susceptibility index (0.0 to 1.0)", example=0.7)


class ContributingFactor(BaseModel):
    code: str
    feature: str
    value: Any
    importance: float
    message: str


class PredictResponse(BaseModel):
    risk: str
    confidence: float
    probabilities: Dict[str, float]
    contributing_factors: List[ContributingFactor]
    model_version: str
    prediction_timestamp: str


class DocumentPredictResponse(BaseModel):
    prediction_ready: bool
    prediction_status: str
    features: Dict[str, Optional[float]]
    missing_features: List[str]
    warnings: List[str]
    sources: Dict[str, Any]
    prediction: Optional[PredictResponse] = None
    message: str


# ==============================================================================
# 3. REST ENDPOINTS
# ==============================================================================

@app.get("/", tags=["General"])
def root() -> Dict[str, Any]:
    """
    API identification and health probe endpoint.
    """
    return {
        "name": "SIH Landslide Risk Prediction API",
        "status": "running",
        "version": "1.0.0",
        "docs_url": "/docs",
        "architecture": "PyMuPDF + GLiNER2 -> Feature Bridge -> RandomForestClassifier -> Decision Support",
        "disclaimer": (
            "Demonstration/pipeline validation system trained on synthetic data. "
            "Not certified for operational real-world disaster management."
        )
    }


@app.get("/health", tags=["General"])
def health_check() -> Dict[str, Any]:
    """
    Health check endpoint verifying whether model artifacts are loadable and ready.
    """
    try:
        model, metadata, _ = load_model_artifacts()
        model_loaded = (model is not None and hasattr(model, "predict"))
        model_version = metadata.get("model_version", "unknown")
    except Exception as exc:
        return {
            "status": "degraded",
            "model_loaded": False,
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    return {
        "status": "healthy" if model_loaded else "degraded",
        "model_loaded": model_loaded,
        "model_version": model_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/model-info", tags=["Metadata"])
def get_model_info() -> Dict[str, Any]:
    """
    Returns verified model metadata, feature order, and validation limitations.
    """
    if not os.path.exists(FEATURE_INFO_PATH):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model metadata artifact 'model/feature_info.json' not found."
        )

    try:
        with open(FEATURE_INFO_PATH, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        return metadata
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read model metadata: {exc}"
        )


@app.post(
    "/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    tags=["Inference"]
)
def predict(payload: PredictRequest) -> Dict[str, Any]:
    """
    Executes real-time landslide risk classification with input sanity validation
    and transparent contributing factor reason generation.
    """
    data_dict = payload.model_dump()

    try:
        result = predict_risk(data_dict)
        return result
    except ValueError as val_err:
        # Schema or physical sanity validation error
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference execution failure: {exc}"
        )


@app.post(
    "/predict/pdf",
    response_model=DocumentPredictResponse,
    status_code=status.HTTP_200_OK,
    tags=["Inference"]
)
async def predict_pdf(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Ingests a geological/disaster PDF report, extracts text via PyMuPDF,
    bridges entities via GLiNER2 into the canonical 8-feature vector,
    and runs ML prediction ONLY IF all 8 required features are present.
    NEVER fabricates missing features.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file '{file.filename}' is not a valid PDF. Only .pdf files are supported."
        )

    try:
        pdf_bytes = await file.read()
        if len(pdf_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded PDF file is empty (0 bytes)."
            )

        # Extract text page by page using PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        extracted_text = ""
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text()
            extracted_text += f"\n--- PAGE {page_num} ---\n{page_text}"
        doc.close()

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to read/parse PDF document: {exc}"
        )

    # Bridge extracted text to structured ML features
    try:
        result = predict_from_document(extracted_text)
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document feature extraction bridge failure: {exc}"
        )


@app.get("/demo", tags=["Demonstration"])
def get_demo_scenarios() -> Dict[str, Any]:
    """
    Runs and returns predefined Low-risk, High/Critical-risk, and Incomplete-document
    demonstration scenarios through the live pipeline.
    """
    low_sample = {
        "rainfall_24h": 20.0,
        "rainfall_3d": 45.0,
        "rainfall_7d": 80.0,
        "slope": 12.0,
        "elevation": 400.0,
        "historical_landslide": 0,
        "distance_to_landslide": 8.5,
        "soil_risk": 0.1
    }

    high_sample = {
        "rainfall_24h": 182.0,
        "rainfall_3d": 420.0,
        "rainfall_7d": 650.0,
        "slope": 38.0,
        "elevation": 850.0,
        "historical_landslide": 1,
        "distance_to_landslide": 0.8,
        "soil_risk": 0.7
    }

    incomplete_entities = {
        "entities": {
            "rainfall": ["182 mm"],
            "slope angle": ["38 degrees"],
            "elevation": ["850 metres"],
            "landslide location": ["Cherrapunji"]
        }
    }

    low_result = predict_risk(low_sample)
    high_result = predict_risk(high_sample)
    incomplete_result = predict_from_document(incomplete_entities)

    return {
        "dataset_type": "DEMO / PIPELINE VALIDATION DATA",
        "demo_notice": (
            "These demonstration results validate that the software pipeline, "
            "validation rules, probabilistic output, and reason codes are functioning. "
            "The model was trained on an 18-row demonstration dataset."
        ),
        "scenarios": {
            "low_risk_scenario": {
                "input": low_sample,
                "output": low_result,
            },
            "high_critical_risk_scenario": {
                "input": high_sample,
                "output": high_result,
            },
            "incomplete_document_scenario": {
                "input": incomplete_entities,
                "output": incomplete_result,
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
