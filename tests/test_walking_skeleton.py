import importlib
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / 'backend'
WORKER_ROOT = ROOT / 'worker'
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))


class FakeClientError(Exception):
    def __init__(self, error_response, operation_name):
        super().__init__(error_response.get('Error', {}).get('Message', operation_name))
        self.response = error_response
        self.operation_name = operation_name


def install_fake_aws_modules():
    fake_boto3 = types.ModuleType('boto3')
    fake_boto3.client = lambda service_name, *args, **kwargs: mock.Mock(name=f'{service_name}_client')
    fake_boto3.resource = lambda service_name, *args, **kwargs: mock.Mock(name=f'{service_name}_resource')
    fake_boto3_dynamodb = types.ModuleType('boto3.dynamodb')
    fake_boto3_conditions = types.ModuleType('boto3.dynamodb.conditions')

    class FakeAttr:
        def __init__(self, name):
            self.name = name

        def eq(self, value):
            return ('eq', self.name, value)

    fake_boto3_conditions.Attr = FakeAttr
    fake_boto3_dynamodb.conditions = fake_boto3_conditions

    fake_botocore = types.ModuleType('botocore')
    fake_botocore_exceptions = types.ModuleType('botocore.exceptions')
    fake_botocore_exceptions.ClientError = FakeClientError
    fake_botocore.exceptions = fake_botocore_exceptions

    sys.modules['boto3'] = fake_boto3
    sys.modules['boto3.dynamodb'] = fake_boto3_dynamodb
    sys.modules['boto3.dynamodb.conditions'] = fake_boto3_conditions
    sys.modules['botocore'] = fake_botocore
    sys.modules['botocore.exceptions'] = fake_botocore_exceptions


def import_fresh(module_name: str):
    install_fake_aws_modules()
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


class WalkingSkeletonTests(unittest.TestCase):
    def setUp(self):
        os.environ['S3_BUCKET_NAME'] = 'test-bucket'
        os.environ['STEP_FUNCTIONS_ARN'] = 'arn:aws:states:ap-northeast-2:123456789012:stateMachine:test'
        os.environ['DYNAMODB_TABLE_NAME'] = 'ppt-jobs'
        os.environ['DYNAMODB_TABLE'] = 'ppt-jobs'
        os.environ['S3_BUCKET'] = 'test-bucket'

    def test_backend_api_walking_skeleton(self):
        upload_url_api = import_fresh('lambdas.upload_url_api')
        create_job_api = import_fresh('lambdas.create_job_api')
        get_job_api = import_fresh('lambdas.get_job_api')

        upload_event = {
            'httpMethod': 'POST',
            'body': json.dumps(
                {
                    'jobId': 'job-123',
                    'fileType': 'template',
                    'fileName': 'master-template.pptx',
                    'contentType': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                }
            ),
        }

        with mock.patch.object(upload_url_api, 'resolve_bucket_name', return_value='test-bucket'), mock.patch.object(
            upload_url_api,
            'generate_presigned_url',
            return_value='https://signed-upload.example/template',
        ):
            upload_response = upload_url_api.handler(upload_event, None)

        self.assertEqual(upload_response['statusCode'], 200)
        upload_payload = json.loads(upload_response['body'])
        self.assertEqual(upload_payload['s3Key'], 'uploads/job-123/template.pptx')
        self.assertTrue(upload_payload['uploadUrl'].startswith('https://signed-upload.example'))

        created_job = {
            'jobId': 'job-123',
            'status': 'PENDING',
            'createdAt': '2026-04-01T00:00:00Z',
        }
        create_event = {
            'httpMethod': 'POST',
            'headers': {'X-Session-Token': 'session-abc'},
            'body': json.dumps(
                {
                    'jobId': 'job-123',
                    'templateS3Key': upload_payload['s3Key'],
                    'contentS3Key': 'uploads/job-123/content.docx',
                    'options': {
                        'tone': 'Executive',
                        'target': 'Management',
                        'length': 10,
                        'aiEngine': 'bedrock',
                    },
                }
            ),
        }

        with mock.patch.object(create_job_api, 'init_job', return_value=created_job) as init_job_mock:
            create_job_api.stepfunctions = mock.Mock()
            create_response = create_job_api.handler(create_event, None)

        self.assertEqual(create_response['statusCode'], 202)
        create_payload = json.loads(create_response['body'])
        self.assertEqual(create_payload['jobId'], 'job-123')
        init_job_mock.assert_called_once()
        create_job_api.stepfunctions.start_execution.assert_called_once()

        stored_job = {
            'jobId': 'job-123',
            'sessionToken': 'session-abc',
            'status': 'SUCCEEDED',
            'createdAt': '2026-04-01T00:00:00Z',
            'updatedAt': '2026-04-01T00:02:00Z',
            'resultS3Key': 'results/job-123/output.pptx',
        }
        get_event = {
            'httpMethod': 'GET',
            'headers': {'X-Session-Token': 'session-abc'},
            'pathParameters': {'jobId': 'job-123'},
        }

        with mock.patch.object(get_job_api, 'get_job', return_value=stored_job), mock.patch.object(
            get_job_api,
            'generate_download_url',
            return_value='https://signed-download.example/output',
        ), mock.patch.object(get_job_api, 'resolve_bucket_name', return_value='test-bucket'):
            get_response = get_job_api.handler(get_event, None)

        self.assertEqual(get_response['statusCode'], 200)
        get_payload = json.loads(get_response['body'])
        self.assertEqual(get_payload['status'], 'SUCCEEDED')
        self.assertEqual(get_payload['resultUrl'], 'https://signed-download.example/output')

    def test_demo_job_fast_path_returns_succeeded_without_worker_execution(self):
        create_job_api = import_fresh('lambdas.create_job_api')

        create_event = {
            'httpMethod': 'POST',
            'headers': {'X-Session-Token': 'session-demo'},
            'body': json.dumps(
                {
                    'jobId': 'job-demo-123',
                    'demoPreset': 'excel',
                    'options': {
                        'tone': 'Executive',
                        'target': 'Management',
                        'length': 8,
                        'aiEngine': 'bedrock',
                    },
                }
            ),
        }

        prepared_assets = {
            'templateS3Key': 'uploads/job-demo-123/template.pptx',
            'contentS3Key': 'uploads/job-demo-123/content.xlsx',
            'resultS3Key': 'results/job-demo-123/output.pptx',
            'pipelineStage': 'DEMO_RESULT_READY',
        }
        created_job = {
            'jobId': 'job-demo-123',
            'status': 'PENDING',
            'createdAt': '2026-04-01T00:00:00Z',
        }

        with mock.patch.object(create_job_api, 'prepare_demo_job_assets', return_value=prepared_assets), mock.patch.object(
            create_job_api, 'init_job', return_value=created_job
        ) as init_job_mock, mock.patch.object(create_job_api, 'update_job_status') as update_status_mock:
            create_job_api.stepfunctions = mock.Mock()
            create_response = create_job_api.handler(create_event, None)

        self.assertEqual(create_response['statusCode'], 202)
        create_payload = json.loads(create_response['body'])
        self.assertEqual(create_payload['status'], 'SUCCEEDED')
        self.assertEqual(create_payload['demoPreset'], 'excel')
        init_job_mock.assert_called_once()
        update_status_mock.assert_called_once_with(
            'job-demo-123',
            'SUCCEEDED',
            result_s3_key='results/job-demo-123/output.pptx',
            extra_updates={'pipelineStage': 'DEMO_RESULT_READY', 'demoPreset': 'excel'},
        )
        create_job_api.stepfunctions.start_execution.assert_not_called()

    def test_worker_bootstrap_walking_skeleton(self):
        document_parser_module = import_fresh('pipeline.agents.document_parser')
        orchestrator_module = import_fresh('pipeline.orchestrator')

        job_record = {
            'jobId': 'job-456',
            'templateS3Key': 'uploads/job-456/template.pptx',
            'contentS3Key': 'uploads/job-456/content.docx',
            'options': {
                'aiEngine': 'bedrock',
                'length': 10,
            },
        }

        with mock.patch.object(document_parser_module, 'get_object_bytes', side_effect=[b'template-bytes', b'content-bytes']) as get_bytes_mock, mock.patch.object(
            document_parser_module.DocumentParser,
            '_parse_template',
            return_value={'layouts': [{'name': 'Title and Content'}], 'maxBullets': 4},
        ), mock.patch.object(
            document_parser_module.DocumentParser,
            '_parse_content',
            return_value={'title': 'Q1 Review', 'sections': [{'title': 'Revenue', 'dataType': 'text'}]},
        ):
            parsed_document = document_parser_module.DocumentParser().parse(job_record)

        self.assertEqual(get_bytes_mock.call_count, 2)
        self.assertEqual(parsed_document['jobId'], 'job-456')
        self.assertIn('templateRules', parsed_document)
        self.assertIn('contentSummary', parsed_document)

        outline_prompt = {
            'provider': 'bedrock',
            'systemPrompt': 'system',
            'userPrompt': 'user',
            'responseSchema': {'type': 'object'},
        }
        slide_draft = {'slides': [{'index': 1, 'title': 'Q1 Review', 'type': 'text', 'bullets': ['Revenue improved.']}]}
        reviewed_slides = {'slides': [{'index': 1, 'title': 'Q1 Review', 'type': 'text', 'bullets': ['Revenue improved.']}]}
        rendered_charts = {'charts': []}
        upload_result = {'resultS3Key': 'results/job-456/output.pptx', 'pipelineStage': 'RESULT_READY'}

        with mock.patch.object(orchestrator_module, 'get_job', return_value=job_record), mock.patch.object(
            orchestrator_module, 'update_job_status'
        ) as update_status_mock, mock.patch.object(
            orchestrator_module.DocumentParser,
            'parse',
            return_value=parsed_document,
        ) as parse_mock, mock.patch.object(
            orchestrator_module.OutlineAgent,
            'build_prompt_package',
            return_value=outline_prompt,
        ) as outline_mock, mock.patch.object(
            orchestrator_module, 'put_json_document'
        ) as put_json_mock, mock.patch.object(
            orchestrator_module.SlideWriter,
            'build_slide_draft',
            return_value=slide_draft,
        ) as slide_writer_mock, mock.patch.object(
            orchestrator_module.ReviewAgent,
            'review',
            return_value=reviewed_slides,
        ) as review_mock, mock.patch.object(
            orchestrator_module.ChartRenderer,
            'render',
            return_value=rendered_charts,
        ) as chart_mock, mock.patch.object(
            orchestrator_module.PPTBuilder,
            'build',
            return_value='/tmp/job-456-output.pptx',
        ) as ppt_builder_mock, mock.patch.object(
            orchestrator_module.ResultUploader,
            'upload',
            return_value=upload_result,
        ) as uploader_mock:
            result = orchestrator_module.run_pipeline('job-456')

        self.assertEqual(result['parsedDocument'], parsed_document)
        self.assertEqual(result['outlinePrompt'], outline_prompt)
        self.assertEqual(result['uploadResult'], upload_result)
        parse_mock.assert_called_once_with(job_record)
        outline_mock.assert_called_once_with(parsed_document)
        slide_writer_mock.assert_called_once_with(parsed_document, outline_prompt)
        review_mock.assert_called_once_with(slide_draft)
        chart_mock.assert_called_once_with('job-456', reviewed_slides)
        ppt_builder_mock.assert_called_once_with(job_record, reviewed_slides, rendered_charts)
        uploader_mock.assert_called_once_with('job-456', '/tmp/job-456-output.pptx')
        self.assertEqual(put_json_mock.call_count, 4)
        put_paths = [call.args[0] for call in put_json_mock.call_args_list]
        self.assertEqual(
            put_paths,
            [
                'temp/job-456/parsed_document.json',
                'temp/job-456/outline_request.json',
                'temp/job-456/slide_draft.json',
                'temp/job-456/reviewed_slides.json',
            ],
        )
        update_status_mock.assert_any_call('job-456', 'RUNNING', extra_updates={'pipelineStage': 'DOCUMENT_PARSING'})
        update_status_mock.assert_any_call('job-456', 'RUNNING', extra_updates={'pipelineStage': 'OUTLINE_PROMPT_GENERATION'})
        update_status_mock.assert_any_call('job-456', 'RUNNING', extra_updates={'pipelineStage': 'SLIDE_DRAFTING'})
        update_status_mock.assert_any_call('job-456', 'RUNNING', extra_updates={'pipelineStage': 'REVIEWING'})
        update_status_mock.assert_any_call('job-456', 'RUNNING', extra_updates={'pipelineStage': 'CHART_RENDERING'})
        update_status_mock.assert_any_call('job-456', 'RUNNING', extra_updates={'pipelineStage': 'PPT_BUILDING'})
        update_status_mock.assert_any_call('job-456', 'RUNNING', extra_updates={'pipelineStage': 'RESULT_UPLOADING'})

    def test_worker_agents_create_chart_and_ppt_artifacts(self):
        slide_writer_module = import_fresh('pipeline.agents.slide_writer')
        review_agent_module = import_fresh('pipeline.agents.review_agent')
        chart_renderer_module = import_fresh('pipeline.agents.chart_renderer')
        ppt_builder_module = import_fresh('pipeline.agents.ppt_builder')

        parsed_document = {
            'jobId': 'job-xlsx',
            'templateRules': {'layouts': [{'name': 'Title and Content'}], 'maxBullets': 4},
            'contentSummary': {
                'title': 'Sales Workbook',
                'documentType': 'xlsx',
                'sections': [
                    {
                        'title': 'Revenue',
                        'summary': 'Revenue by segment.',
                        'dataType': 'chart',
                        'columns': ['Segment', 'Revenue'],
                        'sampleRows': [['A', 10], ['B', 15], ['C', 12]],
                        'numericColumns': ['Revenue'],
                    }
                ],
            },
            'userOptions': {'length': 3, 'tone': 'Executive', 'target': 'Management'},
        }

        slide_draft = slide_writer_module.SlideWriter().build_slide_draft(parsed_document)
        reviewed_slides = review_agent_module.ReviewAgent().review(slide_draft)

        with mock.patch.object(chart_renderer_module, 'put_file') as put_file_mock:
            rendered_charts = chart_renderer_module.ChartRenderer().render('job-xlsx', reviewed_slides)

        self.assertEqual(len(rendered_charts['charts']), 1)
        self.assertTrue(Path(rendered_charts['charts'][0]['localPath']).exists())
        put_file_mock.assert_called_once()

        from pptx import Presentation

        template_path = Path(tempfile.gettempdir()) / 'unit-template.pptx'
        Presentation().save(template_path)

        job_record = {
            'jobId': 'job-xlsx',
            'templateS3Key': 'uploads/job-xlsx/template.pptx',
        }
        with mock.patch.object(ppt_builder_module, 'get_object_bytes', return_value=template_path.read_bytes()):
            output_path = ppt_builder_module.PPTBuilder().build(job_record, reviewed_slides, rendered_charts)

        self.assertTrue(Path(output_path).exists())
        self.assertGreater(Path(output_path).stat().st_size, 0)

    def test_outline_agent_invokes_llm_and_slide_writer_uses_outline(self):
        outline_agent_module = import_fresh('pipeline.agents.outline_agent')
        slide_writer_module = import_fresh('pipeline.agents.slide_writer')

        class FakeLLMClient:
            provider_name = 'fake-llm'

            def __init__(self):
                self.invoked = False

            def build_json_request(self, *, system_prompt, user_prompt, schema):
                return {'model': 'fake', 'schema': schema}

            def invoke_json(self, *, system_prompt, user_prompt, schema):
                self.invoked = True
                return {
                    'slides': [
                        {
                            'index': 1,
                            'title': 'LLM Revenue Story',
                            'type': 'chart',
                            'purpose': 'Show the revenue trend.',
                            'sourceSections': ['Revenue'],
                        }
                    ]
                }

        parsed_document = {
            'jobId': 'job-llm',
            'templateRules': {'layouts': [{'name': 'Title and Content'}]},
            'contentSummary': {
                'title': 'Revenue Workbook',
                'documentType': 'xlsx',
                'sections': [
                    {
                        'title': 'Revenue',
                        'summary': 'Revenue trend by segment.',
                        'dataType': 'chart',
                        'columns': ['Segment', 'Revenue'],
                        'sampleRows': [['A', 10], ['B', 20]],
                        'numericColumns': ['Revenue'],
                    }
                ],
            },
            'userOptions': {'length': 3},
        }

        fake_client = FakeLLMClient()
        prompt_package = outline_agent_module.OutlineAgent(fake_client).build_prompt_package(parsed_document)
        slide_draft = slide_writer_module.SlideWriter().build_slide_draft(parsed_document, prompt_package)

        self.assertTrue(fake_client.invoked)
        self.assertEqual(prompt_package['llmStatus'], 'SUCCEEDED')
        self.assertEqual(slide_draft['outlineSource'], 'llm')
        self.assertEqual(slide_draft['slides'][0]['title'], 'LLM Revenue Story')
        self.assertEqual(slide_draft['slides'][0]['type'], 'chart')
        self.assertIn('chart', slide_draft['slides'][0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
