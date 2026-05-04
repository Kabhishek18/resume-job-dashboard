"""Map HTTP statuses and transport errors to fallback policy."""

from enum import Enum


class LLMFailureClass(str, Enum):
    """Used by the gateway to decide whether to try the next model."""

    LOCAL_CONFIG_AUTH = "local_config_auth"
    RETRYABLE_UPSTREAM = "retryable_upstream"
    INVALID_MODEL_OUTPUT = "invalid_model_output"


def classify_http_status(status_code: int) -> LLMFailureClass:
    """401 = bad API key / account auth (operator fix); do not rotate models."""
    if status_code == 401:
        return LLMFailureClass.LOCAL_CONFIG_AUTH
    return LLMFailureClass.RETRYABLE_UPSTREAM
