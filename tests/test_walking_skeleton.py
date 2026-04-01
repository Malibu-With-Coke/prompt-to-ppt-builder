import importlib
import json
import os
import sys
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
        ) as put_json_mock:
            result = orchestrator_module.run_pipeline('job-456')

        self.assertEqual(result['parsedDocument'], parsed_document)
        self.assertEqual(result['outlinePrompt'], outline_prompt)
        parse_mock.assert_called_once_with(job_record)
        outline_mock.assert_called_once_with(parsed_document)
        self.assertEqual(put_json_mock.call_count, 2)
        put_paths = [call.args[0] for call in put_json_mock.call_args_list]
        self.assertEqual(
            put_paths,
            ['temp/job-456/parsed_document.json', 'temp/job-456/outline_request.json'],
        )
        update_status_mock.assert_any_call('job-456', 'RUNNING', extra_updates={'pipelineStage': 'DOCUMENT_PARSING'})
        update_status_mock.assert_any_call('job-456', 'RUNNING', extra_updates={'pipelineStage': 'OUTLINE_PROMPT_GENERATION'})
        update_status_mock.assert_any_call('job-456', 'RUNNING', extra_updates={'pipelineStage': 'OUTLINE_PROMPT_READY'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
