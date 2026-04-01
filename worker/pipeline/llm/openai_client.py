import os
from typing import Any, Mapping

from pipeline.llm.base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    provider_name = 'openai'

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get('OPENAI_MODEL', 'gpt-4.1')

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