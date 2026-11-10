"""Review request and response schemas."""

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    text: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_id: int
    text: str
    rating: int
