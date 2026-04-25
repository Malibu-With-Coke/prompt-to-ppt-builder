from pipeline.agents.deck_transform_agent import DeckTransformAgent
from pipeline.agents.document_parser import DocumentParser
from pipeline.agents.ppt_builder import PPTBuilder
from pipeline.agents.result_uploader import ResultUploader
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

        update_job_status(job_id, 'RUNNING', extra_updates={'pipelineStage': 'LLM_TEMPLATE_TRANSFORMATION'})
        transform_agent = DeckTransformAgent(_build_llm_client(job.get('options', {}).get('aiEngine')))
        deck_transform = transform_agent.build_transform_plan(parsed_document)
        put_json_document(f'temp/{job_id}/deck_transform_plan.json', deck_transform)

        update_job_status(job_id, 'RUNNING', extra_updates={'pipelineStage': 'PPT_BUILDING'})
        output_path = PPTBuilder().build(job, deck_transform)

        update_job_status(job_id, 'RUNNING', extra_updates={'pipelineStage': 'RESULT_UPLOADING'})
        upload_result = ResultUploader().upload(job_id, output_path)

        print(f'Generated presentation for {job_id}: {upload_result["resultS3Key"]}')
        return {
            'parsedDocument': parsed_document,
            'deckTransform': deck_transform,
            'outputPath': output_path,
            'uploadResult': upload_result,
        }
    except Exception as error:
        try:
            update_job_status(job_id, 'FAILED', error_message=f'Pipeline bootstrap failed: {error}')
        except Exception:
            pass
        raise
