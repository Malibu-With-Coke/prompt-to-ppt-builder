import json
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from shared.db import init_job, update_job_status  # noqa: E402
from shared.response import build_error, build_response, get_header, is_options_request, parse_json_body  # noqa: E402


stepfunctions = boto3.client("stepfunctions")


def _state_machine_arn() -> str:
    state_machine_arn = os.environ.get("STEP_FUNCTIONS_ARN") or os.environ.get("STATE_MACHINE_ARN")
    if not state_machine_arn:
        raise RuntimeError("Step Functions ARN is not configured.")
    return state_machine_arn


def handler(event, context):
    if is_options_request(event):
        return build_response(200)

    session_token = get_header(event, "X-Session-Token")
    if not session_token:
        return build_error(401, "Missing X-Session-Token header.")

    try:
        body = parse_json_body(event)
    except json.JSONDecodeError:
        return build_error(400, "Request body must be valid JSON.")

    job_id = body.get("jobId")
    template_s3_key = body.get("templateS3Key")
    content_s3_key = body.get("contentS3Key")
    options = body.get("options") or {}

    missing_fields = [
        field_name
        for field_name, value in {
            "jobId": job_id,
            "templateS3Key": template_s3_key,
            "contentS3Key": content_s3_key,
        }.items()
        if not value
    ]
    if missing_fields:
        return build_error(400, "Missing required fields.", {"fields": missing_fields})

    try:
        item = init_job(
            job_id=job_id,
            session_token=session_token,
            template_s3_key=template_s3_key,
            content_s3_key=content_s3_key,
            options=options,
        )
        stepfunctions.start_execution(
            stateMachineArn=_state_machine_arn(),
            name=job_id,
            input=json.dumps(
                {
                    "jobId": job_id,
                    "templateS3Key": template_s3_key,
                    "contentS3Key": content_s3_key,
                    "options": options,
                    "sessionToken": session_token,
                }
            ),
        )
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")
        if error_code == "ConditionalCheckFailedException":
            return build_error(409, "A job with this jobId already exists.")

        try:
            update_job_status(job_id, "FAILED", error_message=str(error))
        except Exception:
            pass
        return build_error(500, "Failed to create job.", {"reason": str(error)})
    except Exception as error:
        try:
            update_job_status(job_id, "FAILED", error_message=str(error))
        except Exception:
            pass
        return build_error(500, "Failed to create job.", {"reason": str(error)})

    return build_response(
        202,
        {
            "jobId": item["jobId"],
            "status": item["status"],
            "createdAt": item["createdAt"],
        },
    )