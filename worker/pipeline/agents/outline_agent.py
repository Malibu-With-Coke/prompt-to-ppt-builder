import json
from typing import Any

from pipeline.llm.base import BaseLLMClient


OUTLINE_RESPONSE_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'properties': {
        'slides': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'index': {'type': 'integer'},
                    'title': {'type': 'string'},
                    'type': {'type': 'string', 'enum': ['summary', 'text', 'chart', 'table', 'section-header']},
                    'purpose': {'type': 'string'},
                    'sourceSections': {
                        'type': 'array',
                        'items': {'type': 'string'},
                    },
                },
                'required': ['index', 'title', 'type', 'purpose'],
                'additionalProperties': False,
            },
        }
    },
    'required': ['slides'],
    'additionalProperties': False,
}


class OutlineAgent:
    def __init__(self, llm_client: BaseLLMClient | None = None):
        self.llm_client = llm_client

    def build_prompt_package(self, parsed_document: dict[str, Any]) -> dict[str, Any]:
        prompt_input = {
            'templateRules': parsed_document['templateRules'],
            'contentSummary': parsed_document['contentSummary'],
            'userOptions': parsed_document.get('userOptions', {}),
        }
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(prompt_input)

        prompt_package = {
            'systemPrompt': system_prompt,
            'userPrompt': user_prompt,
            'responseSchema': OUTLINE_RESPONSE_SCHEMA,
            'input': prompt_input,
        }

        if self.llm_client is not None:
            prompt_package['provider'] = self.llm_client.provider_name
            prompt_package['providerRequest'] = self.llm_client.build_json_request(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=OUTLINE_RESPONSE_SCHEMA,
            )
            try:
                prompt_package['llmOutline'] = self.llm_client.invoke_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=OUTLINE_RESPONSE_SCHEMA,
                )
                prompt_package['llmStatus'] = 'SUCCEEDED'
            except Exception as error:
                prompt_package['llmStatus'] = 'FAILED'
                prompt_package['llmError'] = str(error)

        return prompt_package

    def _build_system_prompt(self) -> str:
        return (
            'You are the OutlineAgent for an enterprise Prompt-to-PPT builder. '
            'Create a slide outline that preserves the uploaded template style, '
            'matches the requested tone and audience, and only uses chart slides '
            'when the source document contains numeric chart-friendly data. '
            'Return valid JSON that strictly matches the provided schema.'
        )

    def _build_user_prompt(self, prompt_input: dict[str, Any]) -> str:
        return '\n'.join(
            [
                'Generate the presentation outline for the following parsed input.',
                'Requirements:',
                '- Keep the number of slides aligned with userOptions.length.',
                '- Reuse the template layouts and placeholder constraints.',
                '- Use concise executive phrasing suitable for PowerPoint slides.',
                '- Cite relevant source section titles in sourceSections whenever possible.',
                '',
                'Parsed input JSON:',
                json.dumps(prompt_input, indent=2, default=str),
            ]
        )
