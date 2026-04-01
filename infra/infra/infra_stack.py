import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_s3_assets as s3assets,
    aws_secretsmanager as secretsmanager,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct


class InfraStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ai_engine = os.getenv('AI_ENGINE', 'bedrock')
        bedrock_model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
        openai_secret_name = os.getenv('OPENAI_SECRET_NAME', '')

        self.bucket = s3.Bucket(
            self,
            'PromptToPPTBucket',
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
                    allowed_origins=['*'],
                    allowed_headers=['*'],
                    max_age=3000,
                )
            ],
        )

        self.table = dynamodb.Table(
            self,
            'PPTJobsTable',
            partition_key=dynamodb.Attribute(name='jobId', type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute='ttl',
        )

        vpc = ec2.Vpc(
            self,
            'PptVpc',
            max_azs=2,
            nat_gateways=1,
        )

        cluster = ecs.Cluster(
            self,
            'PptCluster',
            vpc=vpc,
        )

        task_def = ecs.FargateTaskDefinition(
            self,
            'PptWorkerTaskDef',
            cpu=512,
            memory_limit_mib=1024,
        )

        worker_source_asset = s3assets.Asset(
            self,
            'WorkerSourceAsset',
            path='../worker',
        )

        worker_bootstrap_command = " && ".join(
            [
                "python -m pip install --no-cache-dir boto3",
                "python -c \"import boto3, os, zipfile; from pathlib import Path; archive = Path('/tmp/worker.zip'); workspace = Path('/opt/runtime-worker'); workspace.mkdir(parents=True, exist_ok=True); boto3.client('s3').download_file(os.environ['WORKER_ASSET_BUCKET'], os.environ['WORKER_ASSET_KEY'], str(archive)); zipfile.ZipFile(archive).extractall(workspace)\"",
                "python -m pip install --no-cache-dir -r /opt/runtime-worker/requirements.txt",
                "python /opt/runtime-worker/entrypoint.py",
            ]
        )

        worker_container = task_def.add_container(
            'PptWorkerContainer',
            image=ecs.ContainerImage.from_registry('public.ecr.aws/docker/library/python:3.11-slim'),
            logging=ecs.LogDrivers.aws_logs(stream_prefix='PptWorker'),
            environment={
                'S3_BUCKET': self.bucket.bucket_name,
                'DYNAMODB_TABLE': self.table.table_name,
                'AI_ENGINE': ai_engine,
                'BEDROCK_MODEL_ID': bedrock_model_id,
                'OPENAI_SECRET_NAME': openai_secret_name,
                'WORKER_ASSET_BUCKET': worker_source_asset.s3_bucket_name,
                'WORKER_ASSET_KEY': worker_source_asset.s3_object_key,
                'AWS_DEFAULT_REGION': Stack.of(self).region,
            },
            command=['sh', '-lc', worker_bootstrap_command],
        )

        self.table.grant_read_write_data(task_def.task_role)
        self.bucket.grant_read_write(task_def.task_role)
        worker_source_asset.grant_read(task_def.task_role)
        task_def.task_role.add_to_principal_policy(
            iam.PolicyStatement(
                actions=['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
                resources=['*'],
            )
        )
        if openai_secret_name:
            openai_secret = secretsmanager.Secret.from_secret_name_v2(
                self,
                'OpenAISecret',
                openai_secret_name,
            )
            openai_secret.grant_read(task_def.task_role)

        run_task = tasks.EcsRunTask(
            self,
            'RunFargateWorker',
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,
            cluster=cluster,
            task_definition=task_def,
            launch_target=tasks.EcsFargateLaunchTarget(platform_version=ecs.FargatePlatformVersion.LATEST),
            assign_public_ip=False,
            container_overrides=[
                tasks.ContainerOverride(
                    container_definition=worker_container,
                    environment=[
                        tasks.TaskEnvironmentVariable(name='JOB_ID', value=sfn.JsonPath.string_at('$.jobId'))
                    ],
                )
            ],
        )

        state_machine = sfn.StateMachine(
            self,
            'PptStateMachine',
            definition_body=sfn.DefinitionBody.from_chainable(run_task),
            timeout=Duration.minutes(15),
        )

        lambda_code = _lambda.Code.from_asset('../backend')
        common_env = {
            'DYNAMODB_TABLE_NAME': self.table.table_name,
            'S3_BUCKET_NAME': self.bucket.bucket_name,
            'STEP_FUNCTIONS_ARN': state_machine.state_machine_arn,
        }

        upload_url_lambda = _lambda.Function(
            self,
            'UploadUrlLambda',
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=lambda_code,
            handler='lambdas.upload_url_api.handler',
            environment=common_env,
        )
        self.bucket.grant_put(upload_url_lambda)

        create_job_lambda = _lambda.Function(
            self,
            'CreateJobLambda',
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=lambda_code,
            handler='lambdas.create_job_api.handler',
            environment=common_env,
        )
        self.table.grant_read_write_data(create_job_lambda)
        self.bucket.grant_read_write(create_job_lambda)
        state_machine.grant_start_execution(create_job_lambda)

        get_job_lambda = _lambda.Function(
            self,
            'GetJobLambda',
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=lambda_code,
            handler='lambdas.get_job_api.handler',
            environment=common_env,
        )
        self.table.grant_read_data(get_job_lambda)
        self.bucket.grant_read(get_job_lambda)

        list_jobs_lambda = _lambda.Function(
            self,
            'ListJobsLambda',
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=lambda_code,
            handler='lambdas.list_jobs_api.handler',
            environment=common_env,
        )
        self.table.grant_read_data(list_jobs_lambda)

        api = apigw.RestApi(
            self,
            'PptApi',
            rest_api_name='Prompt-to-PPT API',
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    'Content-Type',
                    'X-Amz-Date',
                    'Authorization',
                    'X-Api-Key',
                    'X-Amz-Security-Token',
                    'X-Amz-User-Agent',
                    'X-Session-Token',
                ],
            ),
        )

        jobs_api = api.root.add_resource('jobs')
        jobs_api.add_method('POST', apigw.LambdaIntegration(create_job_lambda))
        jobs_api.add_method('GET', apigw.LambdaIntegration(list_jobs_lambda))

        single_job_api = jobs_api.add_resource('{jobId}')
        single_job_api.add_method('GET', apigw.LambdaIntegration(get_job_lambda))

        upload_url_api = jobs_api.add_resource('upload-url')
        upload_url_api.add_method('POST', apigw.LambdaIntegration(upload_url_lambda))

        CfnOutput(self, 'ApiBaseUrl', value=api.url)
        CfnOutput(self, 'BucketName', value=self.bucket.bucket_name)
        CfnOutput(self, 'JobsTableName', value=self.table.table_name)
        CfnOutput(self, 'StateMachineArn', value=state_machine.state_machine_arn)
        CfnOutput(self, 'ClusterName', value=cluster.cluster_name)
