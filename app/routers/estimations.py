from fastapi import APIRouter
from pydantic import BaseModel
from ..services.llm_service import get_estimation

router = APIRouter(prefix="/api/v1")


class EstimationRequest(BaseModel):
    translation: str


class EstimationResponse(BaseModel):
    estimation: str


@router.post("/estimate", response_model=EstimationResponse)
def estimate(body: EstimationRequest) -> EstimationResponse:
    result = get_estimation(body.translation)
    return EstimationResponse(estimation=result)
