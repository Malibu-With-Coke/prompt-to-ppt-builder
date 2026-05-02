import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from shared.response import build_error, build_response, is_options_request, parse_json_body  # noqa: E402
from shared.s3 import generate_presigned_url, resolve_bucket_name  # noqa: E402


ALLOWED_EXTENSIONS = {
    "template": {".pptx"},
    "content": {".docx", ".xlsx"},
}


def _build_s3_key(job_id: str, file_type: str, file_name: str) -> str:
    extension = Path(file_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS[file_type]:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS[file_type]))
        raise ValueError(f"Unsupported {file_type} extension. Allowed: {allowed}")

    canonical_name = f"{file_type}{extension}"
    return f"uploads/{job_id}/{canonical_name}"


def _build_content_s3_key(job_id: str, file_name: str, file_index: int | None) -> str:
    extension = Path(file_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS["content"]:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS["content"]))
        raise ValueError(f"Unsupported content extension. Allowed: {allowed}")

    if file_index is None:
        return f"uploads/{job_id}/content{extension}"
    if file_index < 0 or file_index > 99:
        raise ValueError("fileIndex must be between 0 and 99.")
    return f"uploads/{job_id}/content-{file_index + 1:02d}{extension}"


def _normalize_file_index(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError("fileIndex must be an integer.")


def handler(event, context):
    if is_options_request(event):
        return build_response(200)

    try:
        body = parse_json_body(event)
    except json.JSONDecodeError:
        return build_error(400, "Request body must be valid JSON.")

    job_id = body.get("jobId")
    file_type = body.get("fileType")
    file_name = body.get("fileName")
    content_type = body.get("contentType")
    file_index = body.get("fileIndex")

    if not job_id or not file_type or not file_name:
        return build_error(400, "jobId, fileType, and fileName are required.")

    if file_type not in ALLOWED_EXTENSIONS:
        return build_error(400, "fileType must be either 'template' or 'content'.")

    try:
        normalized_file_index = _normalize_file_index(file_index)
        s3_key = _build_content_s3_key(job_id, file_name, normalized_file_index) if file_type == "content" else _build_s3_key(job_id, file_type, file_name)
        upload_url = generate_presigned_url(
            bucket=resolve_bucket_name(),
            key=s3_key,
            content_type=content_type,
        )
    except ValueError as error:
        return build_error(400, str(error))
    except Exception as error:
        return build_error(500, "Failed to generate upload URL.", {"reason": str(error)})

    return build_response(
        200,
        {
            "uploadUrl": upload_url,
            "s3Key": s3_key,
        },
    )
