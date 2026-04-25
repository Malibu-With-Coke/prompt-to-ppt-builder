from pathlib import Path

from shared.s3 import put_object_bytes, resolve_bucket_name


ASSET_DIR = Path(__file__).resolve().parents[1] / "demo_assets"

DEMO_PRESETS = {
    "excel": {
        "templateFile": "demo_template.pptx",
        "templateContentType": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "contentFile": "demo_content.xlsx",
        "contentContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "resultFile": "demo_result.pptx",
        "resultContentType": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pipelineStage": "DEMO_RESULT_READY",
    }
}


def _read_asset_bytes(file_name: str) -> bytes:
    asset_path = ASSET_DIR / file_name
    if not asset_path.exists():
        raise FileNotFoundError(f"Demo asset not found: {asset_path}")
    return asset_path.read_bytes()


def prepare_demo_job_assets(job_id: str, preset: str = "excel") -> dict[str, str]:
    asset_config = DEMO_PRESETS.get(preset)
    if not asset_config:
        allowed = ", ".join(sorted(DEMO_PRESETS))
        raise ValueError(f"Unsupported demo preset. Allowed values: {allowed}")

    bucket = resolve_bucket_name()

    template_key = f"uploads/{job_id}/template.pptx"
    content_key = f"uploads/{job_id}/content.xlsx"
    result_key = f"results/{job_id}/output.pptx"

    put_object_bytes(
        bucket,
        template_key,
        _read_asset_bytes(asset_config["templateFile"]),
        asset_config["templateContentType"],
    )
    put_object_bytes(
        bucket,
        content_key,
        _read_asset_bytes(asset_config["contentFile"]),
        asset_config["contentContentType"],
    )
    put_object_bytes(
        bucket,
        result_key,
        _read_asset_bytes(asset_config["resultFile"]),
        asset_config["resultContentType"],
    )

    return {
        "templateS3Key": template_key,
        "contentS3Key": content_key,
        "resultS3Key": result_key,
        "pipelineStage": asset_config["pipelineStage"],
    }
