from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Intent = Literal[
    "greeting",
    "order_tracking",
    "payment_issue",
    "current_time",
    "general_question",
    "unknown",
]
RiskProfile = Literal["low", "medium", "high", "unknown"]
Priority = Literal["low", "medium", "high"]

class IngestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        min_length=1,
        max_length=5000,
        description="The user original message",
        examples=["where is my order?"]
    )

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank")
        return value


class TokenMetadata(BaseModel):
    estimated_input_tokens: int = Field(default=0, ge=0)
    note: str = "Estimated input token count for the message"


class IngestionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    risk_profile: RiskProfile
    priority: Priority
    requires_action: bool
    summary: str = Field(min_length=1, max_length=1000)
    token_metadata: TokenMetadata = Field(default_factory=TokenMetadata)
