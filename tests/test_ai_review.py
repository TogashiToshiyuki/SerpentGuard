"""Mocked tests for the explicit optional OpenAI explanation service."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import httpx
import openai
import pytest
from pydantic import ValidationError

from serpentguard.ai_payload import build_ai_review_payload
from serpentguard.ai_review import (
    AI_REVIEW_SYSTEM_INSTRUCTION,
    AIExplanationResponse,
    AIPrioritizedFinding,
    AIReviewServiceError,
    OpenAIReviewConfig,
    generate_ai_explanation,
    load_openai_review_config,
)
from serpentguard.analysis import analyze_model
from serpentguard.parser import parse_text


class FakeResponses:
    def __init__(self, *, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[dict[str, object]] = []

    def parse(self, **kwargs):  # noqa: ANN003, ANN201
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result


class FakeClient:
    def __init__(self, responses: FakeResponses) -> None:
        self.responses = responses


def _payload():
    parsed = parse_text("surf unused cyl 0 0 1\n", file_name="model.inp")
    report = analyze_model(parsed)
    return build_ai_review_payload(
        analysis_purpose="Explain the selected deterministic finding.",
        report=report,
        parsed_model=parsed,
    )


def _explanation(*, rule_id: str = "SG006") -> AIExplanationResponse:
    return AIExplanationResponse(
        summary="One deterministic finding needs review.",
        prioritized_findings=[
            AIPrioritizedFinding(
                rule_id=rule_id,
                priority="medium",
                rationale="The surface is currently unused by parsed cells.",
            )
        ],
        explanation="This explains the local finding without changing its severity.",
        suggested_checks=["Confirm whether the surface is intentionally reserved."],
        confidence="high",
        limitations=["Only the structured payload was available."],
    )


def _config() -> OpenAIReviewConfig:
    return OpenAIReviewConfig(
        model="configured-structured-model",
        api_key="sk-test-private-value",
        timeout_seconds=12.5,
    )


def test_config_requires_api_key_and_model_without_exposing_key() -> None:
    with pytest.raises(AIReviewServiceError) as missing_key:
        load_openai_review_config({})
    assert missing_key.value.code == "missing_api_key"

    with pytest.raises(AIReviewServiceError) as missing_model:
        load_openai_review_config({"OPENAI_API_KEY": "private"})
    assert missing_model.value.code == "missing_model"

    config = load_openai_review_config(
        {
            "OPENAI_API_KEY": "private-key-value",
            "SERPENTGUARD_OPENAI_MODEL": "configured-model",
            "SERPENTGUARD_OPENAI_TIMEOUT_SECONDS": "25",
        }
    )
    assert config.model == "configured-model"
    assert config.timeout_seconds == 25
    assert "private-key-value" not in repr(config)


@pytest.mark.parametrize(
    "environment",
    [
        {
            "OPENAI_API_KEY": "key",
            "SERPENTGUARD_OPENAI_MODEL": "contains spaces",
        },
        {
            "OPENAI_API_KEY": "key",
            "SERPENTGUARD_OPENAI_MODEL": "model",
            "SERPENTGUARD_OPENAI_TIMEOUT_SECONDS": "not-a-number",
        },
        {
            "OPENAI_API_KEY": "key",
            "SERPENTGUARD_OPENAI_MODEL": "model",
            "SERPENTGUARD_OPENAI_TIMEOUT_SECONDS": "0",
        },
    ],
)
def test_invalid_runtime_configuration_is_rejected(environment) -> None:
    with pytest.raises(AIReviewServiceError) as captured:
        load_openai_review_config(environment)
    assert captured.value.code == "invalid_configuration"


def test_explicit_request_sends_exact_payload_json_as_input() -> None:
    payload = _payload()
    expected = _explanation()
    responses = FakeResponses(
        result=SimpleNamespace(
            status="completed",
            output_parsed=expected,
            output=[],
        )
    )

    actual = generate_ai_explanation(
        payload,
        config=_config(),
        client=FakeClient(responses),
    )

    assert actual == expected
    assert len(responses.calls) == 1
    call = responses.calls[0]
    assert call["input"] == payload.model_dump_json(exclude_none=False)
    assert call["instructions"] == AI_REVIEW_SYSTEM_INSTRUCTION
    assert call["text_format"] is AIExplanationResponse
    assert call["model"] == "configured-structured-model"
    assert call["timeout"] == 12.5
    assert call["store"] is False
    assert "raw_text" not in str(call["input"])


def test_sdk_client_disables_automatic_retries() -> None:
    responses = FakeResponses(
        result=SimpleNamespace(
            status="completed",
            output_parsed=_explanation(),
            output=[],
        )
    )
    fake_client = FakeClient(responses)

    with patch("openai.OpenAI", return_value=fake_client) as client_factory:
        generate_ai_explanation(_payload(), config=_config())

    client_factory.assert_called_once_with(
        api_key="sk-test-private-value",
        timeout=12.5,
        max_retries=0,
    )
    assert len(responses.calls) == 1


def test_system_instruction_contains_required_safety_constraints() -> None:
    instruction = AI_REVIEW_SYSTEM_INSTRUCTION.lower()

    assert "never invent line numbers" in instruction
    assert "never invent serpent syntax" in instruction
    assert "never claim complete" in instruction
    assert "never override" in instruction
    assert "purpose-dependent statements as recommendations" in instruction
    assert "do not provide a full corrected serpent input file" in instruction


def _http_response(status_code: int) -> httpx.Response:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    return httpx.Response(status_code, request=request)


@pytest.mark.parametrize(
    ("sdk_error", "expected_code"),
    [
        (
            openai.AuthenticationError(
                "invalid key",
                response=_http_response(401),
                body=None,
            ),
            "authentication",
        ),
        (
            openai.APITimeoutError(
                httpx.Request("POST", "https://api.openai.com/v1/responses")
            ),
            "timeout",
        ),
        (
            openai.RateLimitError(
                "limited",
                response=_http_response(429),
                body=None,
            ),
            "rate_limit",
        ),
        (
            openai.APIConnectionError(
                request=httpx.Request(
                    "POST",
                    "https://api.openai.com/v1/responses",
                )
            ),
            "network",
        ),
    ],
)
def test_openai_sdk_errors_are_mapped_without_live_calls(
    sdk_error: Exception,
    expected_code: str,
) -> None:
    responses = FakeResponses(error=sdk_error)

    with pytest.raises(AIReviewServiceError) as captured:
        generate_ai_explanation(
            _payload(),
            config=_config(),
            client=FakeClient(responses),
        )

    assert captured.value.code == expected_code
    assert len(responses.calls) == 1


def test_incomplete_response_is_not_displayed_as_valid() -> None:
    responses = FakeResponses(
        result=SimpleNamespace(
            status="incomplete",
            output_parsed=None,
            output=[],
        )
    )

    with pytest.raises(AIReviewServiceError) as captured:
        generate_ai_explanation(
            _payload(),
            config=_config(),
            client=FakeClient(responses),
        )

    assert captured.value.code == "partial_response"


def test_invalid_structured_response_is_rejected() -> None:
    responses = FakeResponses(
        result=SimpleNamespace(
            status="completed",
            output_parsed={"summary": "Only one field"},
            output=[],
        )
    )

    with pytest.raises(AIReviewServiceError) as captured:
        generate_ai_explanation(
            _payload(),
            config=_config(),
            client=FakeClient(responses),
        )

    assert captured.value.code == "invalid_structured_response"


def test_sdk_side_pydantic_parse_error_is_mapped() -> None:
    with pytest.raises(ValidationError) as validation:
        AIExplanationResponse.model_validate({"summary": "partial"})
    responses = FakeResponses(error=validation.value)

    with pytest.raises(AIReviewServiceError) as captured:
        generate_ai_explanation(
            _payload(),
            config=_config(),
            client=FakeClient(responses),
        )

    assert captured.value.code == "invalid_structured_response"


def test_invented_prioritized_rule_id_is_rejected() -> None:
    responses = FakeResponses(
        result=SimpleNamespace(
            status="completed",
            output_parsed=_explanation(rule_id="SG999"),
            output=[],
        )
    )

    with pytest.raises(AIReviewServiceError) as captured:
        generate_ai_explanation(
            _payload(),
            config=_config(),
            client=FakeClient(responses),
        )

    assert captured.value.code == "invalid_structured_response"


def test_refusal_is_reported_without_attempting_to_parse_content() -> None:
    refusal = SimpleNamespace(type="refusal", refusal="Unable to comply")
    message = SimpleNamespace(content=[refusal])
    responses = FakeResponses(
        result=SimpleNamespace(
            status="completed",
            output_parsed=None,
            output=[message],
        )
    )

    with pytest.raises(AIReviewServiceError) as captured:
        generate_ai_explanation(
            _payload(),
            config=_config(),
            client=FakeClient(responses),
        )

    assert captured.value.code == "refusal"


def test_privacy_audit_blocks_request_before_client_call() -> None:
    unsafe = _payload().model_copy(update={"analysis_purpose": r"C:\private\model.inp"})
    responses = FakeResponses()

    with pytest.raises(AIReviewServiceError) as captured:
        generate_ai_explanation(
            unsafe,
            config=_config(),
            client=FakeClient(responses),
        )

    assert captured.value.code == "payload_rejected"
    assert responses.calls == []
