from __future__ import annotations

from utils.dynamo import update_job_status
from utils.s3 import put_file


class ResultUploader:
    def upload(self, job_id: str, output_path: str) -> dict[str, str]:
        result_key = f'results/{job_id}/output.pptx'
        put_file(
            result_key,
            output_path,
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        )
        update_job_status(
            job_id,
            'SUCCEEDED',
            result_s3_key=result_key,
            extra_updates={'pipelineStage': 'RESULT_READY'},
        )
        return {
            'resultS3Key': result_key,
            'pipelineStage': 'RESULT_READY',
        }
