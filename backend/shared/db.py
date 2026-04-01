import os
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr


dynamodb = boto3.resource("dynamodb")


def _table_name() -> str:
    table_name = (
        os.environ.get("DYNAMODB_TABLE_NAME")
        or os.environ.get("TABLE_NAME")
        or os.environ.get("DYNAMODB_TABLE")
    )
    if not table_name:
        raise RuntimeError("DynamoDB table name is not configured.")
    return table_name


def _table():
    return dynamodb.Table(_table_name())


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _ttl_epoch(days: int = 30) -> int:
    return int((datetime.now(timezone.utc) + timedelta(days=days)).timestamp())


def init_job(
    job_id: str,
    session_token: str,
    template_s3_key: str,
    content_s3_key: str,
    options: dict[str, Any],
) -> dict[str, Any]:
    now = utcnow_iso()
    item = {
        "jobId": job_id,
        "sessionToken": session_token,
        "status": "PENDING",
        "templateS3Key": template_s3_key,
        "contentS3Key": content_s3_key,
        "options": options,
        "createdAt": now,
        "updatedAt": now,
        "ttl": _ttl_epoch(),
    }
    _table().put_item(
        Item=item,
        ConditionExpression="attribute_not_exists(jobId)",
    )
    return item


def get_job(job_id: str) -> dict[str, Any] | None:
    response = _table().get_item(Key={"jobId": job_id})
    return response.get("Item")


def list_jobs(session_token: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    scan_kwargs = {"FilterExpression": Attr("sessionToken").eq(session_token)}

    while True:
        response = _table().scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

    return sorted(items, key=lambda item: item.get("createdAt", ""), reverse=True)


def update_job_status(
    job_id: str,
    status: str,
    *,
    error_message: str | None = None,
    result_s3_key: str | None = None,
    extra_updates: dict[str, Any] | None = None,
) -> None:
    expression_names = {"#status": "status"}
    expression_values: dict[str, Any] = {
        ":status": status,
        ":updatedAt": utcnow_iso(),
    }
    assignments = ["#status = :status", "updatedAt = :updatedAt"]
    removals: list[str] = []

    if error_message is not None:
        expression_values[":errorMessage"] = error_message
        assignments.append("errorMessage = :errorMessage")
    else:
        removals.append("errorMessage")

    if result_s3_key is not None:
        expression_values[":resultS3Key"] = result_s3_key
        assignments.append("resultS3Key = :resultS3Key")

    if extra_updates:
        for index, (key, value) in enumerate(extra_updates.items()):
            name_token = f"#extra{index}"
            value_token = f":extra{index}"
            expression_names[name_token] = key
            expression_values[value_token] = value
            assignments.append(f"{name_token} = {value_token}")

    update_expression = f"SET {', '.join(assignments)}"
    if removals:
        update_expression += f" REMOVE {', '.join(removals)}"

    _table().update_item(
        Key={"jobId": job_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_names,
        ExpressionAttributeValues=expression_values,
    )
