import json
from typing import Any


DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Session-Token",
    "Access-Control-Allow-Methods": "OPTIONS,GET,POST",
}


def build_response(status_code: int, body: dict[str, Any] | None = None, headers: dict[str, str] | None = None):
    response_headers = dict(DEFAULT_HEADERS)
    if headers:
        response_headers.update(headers)

    return {
        "statusCode": status_code,
        "headers": response_headers,
        "body": "" if body is None else json.dumps(body),
    }


def build_error(status_code: int, message: str, details: dict[str, Any] | None = None):
    payload: dict[str, Any] = {"error": message}
    if details:
        payload["details"] = details
    return build_response(status_code, payload)


def parse_json_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body")
    if not body:
        return {}
    if isinstance(body, dict):
        return body
    return json.loads(body)


def get_header(event: dict[str, Any], header_name: str) -> str | None:
    headers = event.get("headers") or {}
    target = header_name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return None


def is_options_request(event: dict[str, Any]) -> bool:
    return (event.get("httpMethod") or "").upper() == "OPTIONS"
