from pipeline.agents.document_parser import DocumentParser
from pipeline.agents.outline_agent import OutlineAgent
from pipeline.llm import BedrockClient, OpenAIClient
from utils.dynamo import get_job, update_job_status
from utils.s3 import put_json_document


def _build_llm_client(ai_engine: str | None):
    if (ai_engine or '').lower() == 'openai':
        return OpenAIClient()
    return BedrockClient()


def run_pipeline(job_id: str):
    print(f'Executing Agent Pipeline for {job_id}')

    try:
        job = get_job(job_id)
        if not job:
            raise ValueError(f'Job {job_id} not found in DynamoDB.')

        update_job_status(job_id, 'RUNNING', extra_updates={'pipelineStage': 'DOCUMENT_PARSING'})
        parser = DocumentParser()
        parsed_document = parser.parse(job)
        put_json_document(f'temp/{job_id}/parsed_document.json', parsed_document)

        update_job_status(job_id, 'RUNNING', extra_updates={'pipelineStage': 'OUTLINE_PROMPT_GENERATION'})
        outline_agent = OutlineAgent(_build_llm_client(job.get('options', {}).get('aiEngine')))
        outline_prompt = outline_agent.build_prompt_package(parsed_document)
        put_json_document(f'temp/{job_id}/outline_request.json', outline_prompt)

        update_job_status(job_id, 'RUNNING', extra_updates={'pipelineStage': 'OUTLINE_PROMPT_READY'})
        print(f'Prepared parsed document and outline prompt for {job_id}')
        return {
            'parsedDocument': parsed_document,
            'outlinePrompt': outline_prompt,
        }
    except Exception as error:
        try:
            update_job_status(job_id, 'FAILED', error_message=f'Pipeline bootstrap failed: {error}')
        except Exception:
            pass
        raise