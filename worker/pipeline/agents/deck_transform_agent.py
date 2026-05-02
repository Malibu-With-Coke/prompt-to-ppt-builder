from __future__ import annotations

import json
from typing import Any

from pipeline.llm.base import BaseLLMClient


EMU_PER_INCH = 914400


DECK_TRANSFORM_RESPONSE_SCHEMA: dict[str, Any] = {
    'type': 'object',
    'properties': {
        'deckTitle': {'type': 'string'},
        'strategy': {'type': 'string'},
        'slides': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'slideIndex': {'type': 'integer'},
                    'sourceFocus': {
                        'type': 'array',
                        'items': {'type': 'string'},
                    },
                    'speakerNotes': {'type': 'string'},
                    'chartUpdates': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'targetShapeId': {'type': 'integer'},
                                'sourceSheet': {'type': 'string'},
                                'chartType': {'type': 'string'},
                                'categoryColumn': {'type': 'string'},
                                'valueColumns': {
                                    'type': 'array',
                                    'items': {'type': 'string'},
                                },
                                'intent': {'type': 'string'},
                            },
                            'required': ['sourceSheet', 'chartType', 'categoryColumn', 'valueColumns', 'intent'],
                            'additionalProperties': False,
                        },
                    },
                    'tableUpdates': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'targetShapeId': {'type': 'integer'},
                                'sourceSheet': {'type': 'string'},
                                'columns': {
                                    'type': 'array',
                                    'items': {'type': 'string'},
                                },
                                'rowLimit': {'type': 'integer'},
                                'intent': {'type': 'string'},
                            },
                            'required': ['sourceSheet', 'columns', 'rowLimit', 'intent'],
                            'additionalProperties': False,
                        },
                    },
                    'replacements': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'shapeId': {'type': 'integer'},
                                'text': {'type': 'string'},
                            },
                            'required': ['shapeId', 'text'],
                            'additionalProperties': False,
                        },
                    },
                },
                'required': ['slideIndex', 'sourceFocus', 'speakerNotes', 'replacements'],
                'additionalProperties': False,
            },
        },
    },
    'required': ['deckTitle', 'strategy', 'slides'],
    'additionalProperties': False,
}


class DeckTransformAgent:
    """Ask the LLM to transform source content into the uploaded PPT template."""

    def __init__(self, llm_client: BaseLLMClient | None = None):
        if llm_client is None:
            raise ValueError('DeckTransformAgent requires an LLM client.')
        self.llm_client = llm_client

    def build_transform_plan(self, parsed_document: dict[str, Any]) -> dict[str, Any]:
        prompt_input = self._build_prompt_input(parsed_document)
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(prompt_input)

        transform_plan = self.llm_client.invoke_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=DECK_TRANSFORM_RESPONSE_SCHEMA,
        )
        self._validate_plan(prompt_input, transform_plan)

        return {
            'provider': self.llm_client.provider_name,
            'providerRequest': self.llm_client.build_json_request(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=DECK_TRANSFORM_RESPONSE_SCHEMA,
            ),
            'llmStatus': 'SUCCEEDED',
            'input': prompt_input,
            'responseSchema': DECK_TRANSFORM_RESPONSE_SCHEMA,
            'transformPlan': transform_plan,
        }

    def _build_prompt_input(self, parsed_document: dict[str, Any]) -> dict[str, Any]:
        template_rules = parsed_document.get('templateRules') or {}
        return {
            'jobId': parsed_document.get('jobId'),
            'template': {
                'slideCount': template_rules.get('slideCount'),
                'slideWidth': template_rules.get('slideWidth'),
                'slideHeight': template_rules.get('slideHeight'),
                'fonts': template_rules.get('fonts', []),
                'colorTheme': template_rules.get('colorTheme', []),
                'slides': self._slides_with_fit_hints(template_rules.get('templateSlides') or []),
            },
            'content': parsed_document.get('contentSummary') or {},
            'userOptions': parsed_document.get('userOptions') or {},
        }

    def _slides_with_fit_hints(self, template_slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
        enriched_slides = []
        for slide in template_slides:
            text_shapes = []
            for shape in slide.get('textShapes') or []:
                text_shapes.append(
                    {
                        **shape,
                        'fit': self._shape_fit_hint(shape),
                    }
                )
            enriched_slides.append({**slide, 'textShapes': text_shapes})
        return enriched_slides

    def _shape_fit_hint(self, shape: dict[str, Any]) -> dict[str, Any]:
        position = shape.get('position') or {}
        width_in = self._emu_to_inches(position.get('width'))
        height_in = self._emu_to_inches(position.get('height'))
        area = width_in * height_in
        text = str(shape.get('text') or '')

        if area < 0.35:
            role = 'decorative-or-micro-label'
            max_chars = 20
        elif area < 0.75:
            role = 'label-or-kpi'
            max_chars = 40
        elif area < 1.5:
            role = 'short-callout'
            max_chars = 80
        elif area < 3.0:
            role = 'compact-body'
            max_chars = 140
        else:
            role = 'body'
            max_chars = 220

        if len(text) <= 35 and area >= 0.75:
            role = 'title-or-label'
            max_chars = min(max_chars, 70)

        return {
            'role': role,
            'maxChars': max_chars,
            'maxLines': self._max_lines_for_role(role),
            'areaIn2': round(area, 2),
            'guidance': 'Keep replacement text at or below maxChars. Move detail to speakerNotes instead of overfilling the shape.',
        }

    def _max_lines_for_role(self, role: str) -> int:
        if role in {'decorative-or-micro-label', 'label-or-kpi', 'title-or-label'}:
            return 1
        if role == 'short-callout':
            return 2
        return 3

    def _emu_to_inches(self, value: Any) -> float:
        try:
            return max(int(value), 0) / EMU_PER_INCH
        except Exception:
            return 0.0

    def _build_system_prompt(self) -> str:
        return (
            'You are the core generation engine for a Prompt-to-PPT product. '
            'Your job is not to create a generic new presentation. Your job is to transform '
            'the uploaded template deck into a new deck that keeps the same slide count, '
            'visual layout, tone, and business-report structure while replacing stale template '
            'content with facts from the uploaded Word or Excel source. Return strict JSON only.'
        )

    def _build_user_prompt(self, prompt_input: dict[str, Any]) -> str:
        return '\n'.join(
            [
                'Transform the template PPT into a new presentation using the source content.',
                '',
                'Rules:',
                '- Keep every template slide in the same order. Do not add, remove, or reorder slides.',
                '- For each template slide, rewrite each meaningful text shape listed in template.slides[].textShapes.',
                '- Use the shapeId values exactly so the builder can replace text in-place.',
                '- Obey every shape fit hint in template.slides[].textShapes[].fit. Replacement text must stay at or below fit.maxChars and should not exceed fit.maxLines.',
                '- Put supporting detail in speakerNotes when fit.maxChars is too small for the full source nuance.',
                '- Use content.sections, content.documentProfile, content.workbookProfile, and per-source documents as the source of truth. Do not assume any hidden Markdown conversion layer.',
                '- Preserve the template intent. Example: if the template is a Q1 business report and the source is Q2, produce a Q2 business report.',
                '- If content.documentType is multi, synthesize across all content.documents and use sourceFocus to name the most relevant source file or section.',
                '- Do not keep stale quarter, year, metric, customer, or status claims from the template unless the source supports them.',
                '- Fit replacement copy into the original shape. Prefer concise title, label, KPI, and bullet phrasing.',
                '- Use the language of the template/source. If either is Korean, produce Korean business presentation copy.',
                '- For Excel content, summarize trends and metrics directly in the text replacements.',
                '- If Excel tables, formulas, charts, or chart-friendly numeric columns are present, also return chartUpdates or tableUpdates intent for the relevant slide.',
                '- chartUpdates and tableUpdates describe desired data updates only. Text replacements must still be complete because the current builder may not update native charts yet.',
                '- Prefer sourceSheet values from content.sections[].title and columns from content.sections[].columns or numericColumns. For multi-file input, include the source file context in intent text when useful.',
                '- If a text shape is decorative or should be intentionally blank, return an empty string for that shapeId.',
                '',
                'Input JSON:',
                json.dumps(prompt_input, indent=2, ensure_ascii=False, default=str),
            ]
        )

    def _validate_plan(self, prompt_input: dict[str, Any], transform_plan: dict[str, Any]) -> None:
        template_slides = prompt_input.get('template', {}).get('slides') or []
        expected_slide_count = len(template_slides)
        slides = transform_plan.get('slides') or []
        if expected_slide_count and len(slides) != expected_slide_count:
            raise ValueError(f'LLM returned {len(slides)} slide plans for {expected_slide_count} template slides.')

        text_shape_ids = {
            int(shape['shapeId'])
            for slide in template_slides
            for shape in slide.get('textShapes') or []
            if shape.get('shapeId') is not None
        }
        replacement_shape_ids = {
            int(replacement['shapeId'])
            for slide in slides
            for replacement in slide.get('replacements') or []
            if replacement.get('shapeId') is not None
        }
        if text_shape_ids and not replacement_shape_ids:
            raise ValueError('LLM returned no text replacements for the template.')
        missing_shape_ids = sorted(text_shape_ids - replacement_shape_ids)
        if missing_shape_ids:
            raise ValueError(f'LLM did not return replacements for template shape IDs: {missing_shape_ids}')
