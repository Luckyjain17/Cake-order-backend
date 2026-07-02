from pydantic import BaseModel
from typing import Optional


class SettingSchema(BaseModel):
    key: str
    value: Optional[str] = None

    class Config:
        from_attributes = True
