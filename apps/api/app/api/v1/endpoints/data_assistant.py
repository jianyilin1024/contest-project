"""数据助手（F6）接口。

POST /data/assist  识别段落的数据缺口，联网检索并给出带来源的补充建议
"""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.data_assistant import (
    DataAssistRequest,
    DataAssistResponse,
    GapOut,
    SuggestionOut,
)
from app.services.documents.data_assistant import assist
from app.services.llm import LLMError, get_llm_provider

router = APIRouter(prefix="/data", tags=["data"])
logger = logging.getLogger(__name__)


@router.post("/assist", response_model=DataAssistResponse, summary="数据缺口检索")
async def data_assist(payload: DataAssistRequest) -> DataAssistResponse:
    try:
        outcome = await assist(payload.text.strip(), get_llm_provider())
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc

    logger.info(
        "数据助手完成 gaps=%d suggestions=%d searched=%d",
        len(outcome["gaps"]),
        len(outcome["suggestions"]),
        outcome["searched"],
    )
    return DataAssistResponse(
        gaps=[GapOut(**item) for item in outcome["gaps"]],
        suggestions=[SuggestionOut(**item) for item in outcome["suggestions"]],
        searched=outcome["searched"],
    )
