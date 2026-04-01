import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from shared.db import get_job  # noqa: E402
from shared.response import build_error, build_response, get_header, is_options_request  # noqa: E402
from shared.s3 import generate_download_url, resolve_bucket_name  # noqa: E402


def handler(event, context):
    if is_options_request(event):
        return build_response(200)

    session_token = get_header(event, "X-Session-Token")
    if not session_token:
        return build_error(401, "Missing X-Session-Token header.")

    job_id = (event.get("pathParameters") or {}).get("jobId")
    if not job_id:
        return build_error(400, "Missing jobId path parameter.")

    try:
        item = get_job(job_id)
        if not item or item.get("sessionToken") != session_token:
            return build_error(404, "Job not found.")

        response_body = {
            "jobId": item["jobId"],
            "status": item["status"],
            "createdAt": item["createdAt"],
            "updatedAt": item.get("updatedAt", item["createdAt"]),
        }

        if item.get("pipelineStage"):
            response_body["pipelineStage"] = item["pipelineStage"]

        if item.get("errorMessage"):
            response_body["errorMessage"] = item["errorMessage"]

        if item.get("status") == "SUCCEEDED" and item.get("resultS3Key"):
            response_body["resultUrl"] = generate_download_url(
                resolve_bucket_name(),
                item["resultS3Key"],
            )
    except Exception as error:
        return build_error(500, "Failed to fetch job.", {"reason": str(error)})

    return build_response(200, response_body)
