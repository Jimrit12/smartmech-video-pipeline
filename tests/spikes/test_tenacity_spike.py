"""Spike test proving tenacity retry strategy for transient errors vs non-transient refusals."""

import pytest
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed


class TransientError(Exception):
    """Simulates rate limit, 5xx, or network timeout."""


class ContentPolicyRefusal(Exception):
    """Content moderation or safety refusal; must never be retried."""


class FlakyService:
    def __init__(self) -> None:
        self.attempts = 0

    @retry(
        retry=retry_if_exception_type(TransientError),
        stop=stop_after_attempt(3),
        wait=wait_fixed(0.01),
        reraise=True,
    )
    def flaky_transient_call(self) -> str:
        self.attempts += 1
        if self.attempts < 3:
            raise TransientError("Temporary 503 Service Unavailable")
        return "success"

    @retry(
        retry=retry_if_exception_type(TransientError),
        stop=stop_after_attempt(3),
        wait=wait_fixed(0.01),
        reraise=True,
    )
    def policy_refusal_call(self) -> str:
        self.attempts += 1
        raise ContentPolicyRefusal("Content flagged by safety policy")


def test_tenacity_retries_transient_error() -> None:
    service = FlakyService()
    result = service.flaky_transient_call()
    assert result == "success"
    assert service.attempts == 3


def test_tenacity_does_not_retry_policy_refusal() -> None:
    service = FlakyService()
    with pytest.raises(ContentPolicyRefusal):
        service.policy_refusal_call()
    assert service.attempts == 1
