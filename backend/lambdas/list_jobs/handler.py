import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from shared.db import list_jobs  # noqa: E402
from shared.response import build_error, build_response, get_header, is_options_request  # noqa: E402


def lambda_handler(event, context):
    if is_options_request(event):
        return build_response(200)

    session_token = get_header(event, "X-Session-Token")
    if not session_token:
        return build_error(401, "Missing X-Session-Token header.")

    try:
        jobs = list_jobs(session_token)
        summaries = [
            {
                "jobId": item["jobId"],
                "status": item["status"],
                "createdAt": item["createdAt"],
                "updatedAt": item.get("updatedAt", item["createdAt"]),
            }
            for item in jobs
        ]
    except Exception as error:
        return build_error(500, "Failed to list jobs.", {"reason": str(error)})

    return build_response(200, {"jobs": summaries})
