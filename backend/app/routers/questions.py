import logging
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.adapters.llm import ClaudeClient, LLMError
from app.auth import get_current_user
from app.config import get_settings
from app.db import get_session
from app.errors import ApiError
from app.models import User
from app.services.qa import LLMClient, TargetNotFoundError, answer_question

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/targets")

MAX_QUESTION_LENGTH = 1000
QUESTION_REQUIRED = "Type a question about this target's reviews."

NOT_CONFIGURED = ApiError(
    status.HTTP_503_SERVICE_UNAVAILABLE,
    "qa_unavailable",
    "Asking questions isn't available right now. Please try again later.",
)

# Each failure keeps its own code so the logs and UI can tell them apart.
LLM_ERRORS: dict[str, tuple[int, str, str]] = {
    "timeout": (
        504,
        "qa_timeout",
        "ReviewLens took too long to answer. Please try again.",
    ),
    "rate_limited": (
        429,
        "qa_busy",
        "ReviewLens is answering too many questions right now. "
        "Please try again in a minute.",
    ),
    "unavailable": (
        503,
        "qa_unavailable",
        "ReviewLens can't reach its AI service right now. Please try again shortly.",
    ),
    "misconfigured": (
        503,
        "qa_unavailable",
        "Asking questions isn't available right now. Please try again later.",
    ),
}
LLM_UNEXPECTED = (
    502,
    "qa_failed",
    "ReviewLens couldn't answer that right now. Please try again.",
)


class QuestionCreate(BaseModel):
    """Request body. Ownership and target come from the token and the URL."""

    model_config = ConfigDict(extra="ignore")

    question: str

    @field_validator("question")
    @classmethod
    def check_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError(QUESTION_REQUIRED)
        if len(value) > MAX_QUESTION_LENGTH:
            raise ValueError(f"Use {MAX_QUESTION_LENGTH} characters or fewer.")
        return value


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rating: float
    text: str
    reviewer_name: str | None
    review_date: str | None
    reviewer_avatar_url: str | None = None
    image_urls: list[str] = []

    @field_validator("image_urls", mode="before")
    @classmethod
    def no_images_as_empty_list(cls, value: object) -> object:
        return [] if value is None else value


class AnswerRead(BaseModel):
    target_id: int
    target_name: str
    status: str
    answer: str
    reviews_used: int
    reviews_total: int
    evidence: list[EvidenceRead]


@lru_cache
def _claude_client(api_key: str, model: str) -> ClaudeClient:
    return ClaudeClient(api_key=api_key, model=model)


def get_llm_client() -> LLMClient:
    """Return the live model client. Tests override this dependency."""
    settings = get_settings()
    if settings.anthropic_api_key is None:
        logger.error("ANTHROPIC_API_KEY is not set, so Q&A is unavailable")
        raise NOT_CONFIGURED
    return _claude_client(
        settings.anthropic_api_key.get_secret_value(), settings.llm_model
    )


@router.post("/{target_id}/questions", response_model=AnswerRead)
def ask_question(
    target_id: int,
    payload: QuestionCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    llm: Annotated[LLMClient, Depends(get_llm_client)],
) -> AnswerRead:
    """Answer a question from the reviews of a target the caller owns."""
    try:
        result = answer_question(
            session,
            owner_id=user.id,
            target_id=target_id,
            question=payload.question,
            llm=llm,
        )
    except TargetNotFoundError:
        raise ApiError(
            status.HTTP_404_NOT_FOUND,
            "target_not_found",
            "We couldn't find that target. It may not exist or you may not have "
            "access.",
        ) from None
    except LLMError as exc:
        code_status, code, message = LLM_ERRORS.get(exc.category, LLM_UNEXPECTED)
        logger.warning(
            "Q&A failed for target %s and user %s: %s",
            target_id,
            user.id,
            exc.category,
        )
        raise ApiError(code_status, code, message) from None
    except SQLAlchemyError:
        logger.exception("Could not load reviews for Q&A on target %s", target_id)
        raise ApiError(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "unexpected",
            "Something went wrong on our side. Please try again.",
        ) from None

    return AnswerRead(
        target_id=result.target_id,
        target_name=result.target_name,
        status=result.status,
        answer=result.answer,
        reviews_used=result.reviews_used,
        reviews_total=result.reviews_total,
        evidence=[EvidenceRead.model_validate(review) for review in result.evidence],
    )
