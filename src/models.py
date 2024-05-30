import os
import time
from typing import Any, Dict, List, Tuple
from pydantic import BaseModel, validator
import arrow
from config import config
from utils import gen_random

sep = config.PATH_SEPERATOR


class ValidationErrorLength(Exception):
    pass


class Base0(BaseModel):
    id: str = ""
    created: str = ""
    modified: str = ""
    model_name: str = ""

    @classmethod
    def _utc_now(cls):
        return str(arrow.utcnow()).replace("-", "").replace(":", "").split(".")[0]

    @classmethod
    def create_unique_string(cls):
        return str(gen_random(32))

    @validator("id", always=True)
    def set_id(cls, val):
        if val:
            return val
        return cls.create_unique_string()

    @validator("created", always=True)
    def set_created(cls, val):
        return cls._utc_now()

    @validator("modified", always=True)
    def set_modified(cls, val):
        return cls._utc_now()

    def dict(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        result = super().dict(*args, **kwargs)
        result["model_name"] = self.__class__.__name__
        self.model_name = result["model_name"]
        return result

    def get_filename(self):
        return "data.json"

    @classmethod
    def build_parent_path(cls, oid: str) -> str:
        if len(oid) < 3:
            raise ValidationErrorLength(f"The id {oid} must be > 2 characters")
        return sep.join([cls.__name__, oid[-2:], oid[-3:], oid])

    @classmethod
    def build_path(cls, oid: str) -> str:
        return sep.join(
            [
                cls.build_parent_path(oid),
                "data.json",
            ]
        )

    def get_parent_path(self):
        return type(self).build_parent_path(self.id)

    def get_relative_path(self):
        # builds the full relative path including filename
        return sep.join([self.get_parent_path(), self.get_filename()])

    def get_ttl(self):
        return ""

    def get_foriegn_keys(self):
        return []

    def update_modified(self):
        self.modified = type(self)._utc_now()

    def __repr__(self):
        return self.__class__.__name__


class User(Base0):
    first_name: str
    last_name: str
    password_hash: str
    email: str


class Campaign(Base0):
    title: str
    description: str
    user_id: str
    contributions: List[Dict[str, Any]] = []
    goal: int
    user_id: str
    category_id: str
    country_id: int
    currency_code: str
    currency_symbol: str
    campaign_type_id: int
    image_path: str = ""
    recipient: str = ""
    amount_reached: int = 0
    last_contribution_datetime: str = ""
    sentiment: str = ""
    contribution_count: int = 0


# used soley for display purposes, does not get persisted
class MiniCampaign(BaseModel):
    id: str
    title: str
    currency_symbol: str
    created: str
    progress: int
    amount_reached: int

    def __init__(self, campaign: Campaign):
        target_data = {
            k: v for k, v in campaign.dict().items() if k in self.__annotations__
        }
        target_data["progress"] = min(
            1, campaign.amount_reached / max(1, campaign.goal)
        )
        super().__init__(**target_data)
