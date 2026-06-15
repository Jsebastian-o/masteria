from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ..schemas import EstimationRequest, EstimationResponse
from ..services.llm_service import stream_estimation

router = APIRouter(prefix="/api/v1")


@router.post("/estimate/stream")
def estimate_stream(body: EstimationRequest) -> StreamingResponse:
    return StreamingResponse(stream_estimation(body), media_type="text/plain")
