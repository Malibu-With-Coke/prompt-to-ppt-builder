import os

import aws_cdk as core
import aws_cdk.assertions as assertions

from infra.infra_stack import InfraStack


def test_core_e2e_resources_created():
    os.environ['AI_ENGINE'] = 'bedrock'
    os.environ['BEDROCK_MODEL_ID'] = 'anthropic.claude-3-5-sonnet-20241022-v2:0'

    app = core.App()
    stack = InfraStack(app, "infra")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::ECS::TaskDefinition", 1)
    template.resource_count_is("AWS::StepFunctions::StateMachine", 1)
    template.resource_count_is("AWS::ApiGateway::RestApi", 1)
    template.resource_count_is("AWS::Lambda::Function", 4)
    template.has_output("ApiBaseUrl", {})
    template.has_output("StateMachineArn", {})
