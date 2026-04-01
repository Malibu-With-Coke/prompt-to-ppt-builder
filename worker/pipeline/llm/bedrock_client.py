import os
from typing import Any, Mapping

from pipeline.llm.base import BaseLLMClient


class BedrockClient(BaseLLMClient):
    provider_name = 'bedrock'

    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')

    def build_json_request(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            'modelId': self.model_id,
            'system': [{'text': system_prompt}],
            'messages': [
                {
                    'role': 'user',
                    'content': [{'text': user_prompt}],
                }
            ],
            'inferenceConfig': {
                'temperature': 0.2,
                'maxTokens': 2000,
            },
            'additionalModelRequestFields': {
                'response_format': {
                    'type': 'json_schema',
                    'json_schema': {
                        'name': 'slide_outline',
                        'schema': dict(schema),
                    },
                }
            },
        }