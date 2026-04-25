import json
import os
from typing import Any, Mapping

import boto3

from pipeline.llm.base import BaseLLMClient


class BedrockClient(BaseLLMClient):
    provider_name = 'bedrock'

    def __init__(self, model_id: str | None = None, runtime_client: Any | None = None):
        self.model_id = model_id or os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
        self.runtime_client = runtime_client or boto3.client('bedrock-runtime')

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
        }

    def invoke_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: Mapping[str, Any],
    ) -> dict[str, Any]:
        request = self.build_json_request(
            system_prompt=system_prompt,
            user_prompt=self._json_only_prompt(user_prompt, schema),
            schema=schema,
        )
        response = self.runtime_client.converse(**request)
        text = self._extract_text(response)
        return json.loads(text)

    def _json_only_prompt(self, user_prompt: str, schema: Mapping[str, Any]) -> str:
        return '\n'.join(
            [
                user_prompt,
                '',
                'Return only a valid JSON object. Do not wrap it in Markdown.',
                'The JSON must satisfy this schema:',
                json.dumps(schema, indent=2),
            ]
        )

    def _extract_text(self, response: Mapping[str, Any]) -> str:
        message = response.get('output', {}).get('message', {})
        content_blocks = message.get('content') or []
        parts = [block.get('text', '') for block in content_blocks if isinstance(block, Mapping)]
        text = ''.join(parts).strip()
        if text.startswith('```'):
            text = text.strip('`').strip()
            if text.lower().startswith('json'):
                text = text[4:].strip()
        return text
