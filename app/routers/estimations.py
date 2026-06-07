from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ..services.llm_service import get_estimation, stream_estimation

router = APIRouter(prefix="/api/v1")


class EstimationRequest(BaseModel):
    translation: str


class EstimationResponse(BaseModel):
    estimation: str
    model: str
    input_tokens: int
    output_tokens: int
    system_prompt: str


@router.post("/estimate", response_model=EstimationResponse)
def estimate(body: EstimationRequest) -> EstimationResponse:
    result = get_estimation(body.translation)
    return EstimationResponse(**result)


@router.post("/estimate/stream")
def estimate_stream(body: EstimationRequest) -> StreamingResponse:
    return StreamingResponse(stream_estimation(body.translation), media_type="text/plain")
