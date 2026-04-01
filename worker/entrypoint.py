import os
import sys

from pipeline.orchestrator import run_pipeline


def main() -> int:
    job_id = os.environ.get("JOB_ID")
    if not job_id:
        print("JOB_ID environment variable not set.")
        return 1

    print(f"Starting pipeline for job: {job_id}")
    run_pipeline(job_id)
    print(f"Pipeline finished for job: {job_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
