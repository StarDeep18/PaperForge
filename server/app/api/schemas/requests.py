"""
API Request Models.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any


class ChatRequest(BaseModel):
    """
    Structured chat request payload for performing grounded question answering.
    """
    query: str = Field(..., description="The user's query/question.")
    workspace_id: Optional[str] = Field(None, description="Optional workspace ID scoping.")
    conversation_history: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of previous messages: [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]"
    )
    retrieval_options: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom parameters for retrieval service (e.g. top_k, similarity_threshold)."
    )
    generation_options: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom parameters for generation service (e.g. temperature, template_name)."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "What is quantum superposition?",
                "workspace_id": "workspace-123",
                "conversation_history": [
                    {"role": "user", "content": "Explain quantum states."},
                    {"role": "assistant", "content": "Sure! I can explain concepts like superposition or entanglement."}
                ],
                "retrieval_options": {
                    "top_k": 3,
                    "score_threshold": 0.5
                },
                "generation_options": {
                    "temperature": 0.3
                }
            }
        }
    }

    @field_validator("query")
    @classmethod
    def validate_query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or contain only whitespace.")
        return v

    @field_validator("conversation_history")
    @classmethod
    def validate_conversation_history(cls, history: list[dict[str, str]]) -> list[dict[str, str]]:
        for msg in history:
            if "role" not in msg or "content" not in msg:
                raise ValueError("Each conversation history message must contain 'role' and 'content' keys.")
            if msg["role"] not in ("user", "assistant", "system"):
                raise ValueError("Role must be one of: 'user', 'assistant', 'system'.")
        return history
