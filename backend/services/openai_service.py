import json
from typing import Any
from urllib import error, request


INTENT_SYSTEM_PROMPT = """
You are an intent classifier for an AI CI/CD assistant.

Classify the user's request into one of these intents:
- run_test
- deploy_project
- check_service_status
- summarize_monitoring
- unknown

Return strict JSON with the following keys:
- intent: one of the listed intents
- confidence: a float between 0 and 1
- reason: short explanation in Chinese
- suggested_action: short next step in Chinese
""".strip()


class IntentRecognitionError(Exception):
    """Raised when the OpenAI request fails or returns invalid data."""


def recognize_intent(
    user_input: str,
    api_key: str,
    model: str,
    base_url: str,
    timeout: int,
) -> dict[str, Any]:
    body = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": INTENT_SYSTEM_PROMPT}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_input}]},
        ],
        "text": {"format": {"type": "json_object"}},
    }

    response_data = _post_json(
        url=f"{base_url}/responses",
        api_key=api_key,
        body=body,
        timeout=timeout,
    )

    output_text = _extract_output_text(response_data)

    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise IntentRecognitionError("OpenAI returned invalid JSON content") from exc

    return {
        "user_input": user_input,
        "intent": parsed.get("intent", "unknown"),
        "confidence": parsed.get("confidence", 0),
        "reason": parsed.get("reason", ""),
        "suggested_action": parsed.get("suggested_action", ""),
        "model": response_data.get("model", model),
    }


def _post_json(url: str, api_key: str, body: dict[str, Any], timeout: int) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = request.Request(
        url=url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise IntentRecognitionError(f"OpenAI API request failed: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise IntentRecognitionError(f"Failed to connect to OpenAI API: {exc.reason}") from exc


def _extract_output_text(response_data: dict[str, Any]) -> str:
    output_text = response_data.get("output_text")
    if output_text:
        return output_text

    for output_item in response_data.get("output", []):
        for content in output_item.get("content", []):
            text_value = content.get("text")
            if text_value:
                return text_value

    raise IntentRecognitionError("OpenAI response does not contain output text")
