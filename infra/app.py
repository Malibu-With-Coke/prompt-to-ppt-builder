#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infra.infra_stack import InfraStack


region = os.getenv('CDK_DEFAULT_REGION') or os.getenv('AWS_REGION') or 'ap-northeast-2'
account = os.getenv('CDK_DEFAULT_ACCOUNT')

app = cdk.App()
InfraStack(
    app,
    "InfraStack",
    env=cdk.Environment(account=account, region=region),
)

app.synth()
