import json
import os
from typing import Any, Mapping

import boto3

from pipeline.llm.base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    provider_name = 'openai'

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or os.environ.get('OPENAI_MODEL', 'gpt-4.1')
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY') or self._load_api_key_from_secret()

    def build_json_request(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            'model': self.model,
            'input': [
                {'role': 'system', 'content': [{'type': 'input_text', 'text': system_prompt}]},
                {'role': 'user', 'content': [{'type': 'input_text', 'text': user_prompt}]},
            ],
            'text': {
                'format': {
                    'type': 'json_schema',
                    'name': 'slide_outline',
                    'schema': dict(schema),
                }
            },
        }

    def invoke_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError('OpenAI API key is not configured.')

        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.responses.create(**self.build_json_request(system_prompt=system_prompt, user_prompt=user_prompt, schema=schema))
        text = getattr(response, 'output_text', None)
        if not text:
            text = self._extract_text_from_response(response)
        return json.loads(text)

    def _load_api_key_from_secret(self) -> str | None:
        secret_name = os.environ.get('OPENAI_SECRET_NAME')
        if not secret_name:
            return None
        secret_value = boto3.client('secretsmanager').get_secret_value(SecretId=secret_name)
        raw_secret = secret_value.get('SecretString')
        if not raw_secret:
            return None
        try:
            parsed_secret = json.loads(raw_secret)
        except json.JSONDecodeError:
            return raw_secret
        return parsed_secret.get('OPENAI_API_KEY') or parsed_secret.get('api_key') or parsed_secret.get('key')

    def _extract_text_from_response(self, response: Any) -> str:
        output = getattr(response, 'output', None) or []
        text_parts: list[str] = []
        for item in output:
            for content in getattr(item, 'content', []) or []:
                text = getattr(content, 'text', None)
                if text:
                    text_parts.append(text)
        return ''.join(text_parts).strip()
