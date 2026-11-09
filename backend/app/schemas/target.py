from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnalysisTargetBase(BaseModel):
    name: str


class AnalysisTargetCreate(AnalysisTargetBase):
    pass


class AnalysisTargetRead(AnalysisTargetBase):
    id: int
    owner_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
