from pipeline.agents.chart_renderer import ChartRenderer
from pipeline.agents.document_parser import DocumentParser
from pipeline.agents.outline_agent import OutlineAgent
from pipeline.agents.ppt_builder import PPTBuilder
from pipeline.agents.result_uploader import ResultUploader
from pipeline.agents.review_agent import ReviewAgent
from pipeline.agents.slide_writer import SlideWriter
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

        update_job_status(job_id, 'RUNNING', extra_updates={'pipelineStage': 'SLIDE_DRAFTING'})
        slide_writer = SlideWriter()
        slide_draft = slide_writer.build_slide_draft(parsed_document, outline_prompt)
        put_json_document(f'temp/{job_id}/slide_draft.json', slide_draft)

        update_job_status(job_id, 'RUNNING', extra_updates={'pipelineStage': 'REVIEWING'})
        reviewed_slides = ReviewAgent().review(slide_draft)
        put_json_document(f'temp/{job_id}/reviewed_slides.json', reviewed_slides)

        update_job_status(job_id, 'RUNNING', extra_updates={'pipelineStage': 'CHART_RENDERING'})
        rendered_charts = ChartRenderer().render(job_id, reviewed_slides)

        update_job_status(job_id, 'RUNNING', extra_updates={'pipelineStage': 'PPT_BUILDING'})
        output_path = PPTBuilder().build(job, reviewed_slides, rendered_charts)

        update_job_status(job_id, 'RUNNING', extra_updates={'pipelineStage': 'RESULT_UPLOADING'})
        upload_result = ResultUploader().upload(job_id, output_path)

        print(f'Generated presentation for {job_id}: {upload_result["resultS3Key"]}')
        return {
            'parsedDocument': parsed_document,
            'outlinePrompt': outline_prompt,
            'slideDraft': slide_draft,
            'reviewedSlides': reviewed_slides,
            'renderedCharts': rendered_charts,
            'outputPath': output_path,
            'uploadResult': upload_result,
        }
    except Exception as error:
        try:
            update_job_status(job_id, 'FAILED', error_message=f'Pipeline bootstrap failed: {error}')
        except Exception:
            pass
        raise
