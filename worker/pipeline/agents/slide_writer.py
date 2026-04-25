from __future__ import annotations

from typing import Any


VALID_SLIDE_TYPES = {'summary', 'text', 'chart', 'table', 'section-header'}


class SlideWriter:
    def build_slide_draft(
        self,
        parsed_document: dict[str, Any],
        outline_prompt: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        content = parsed_document.get('contentSummary', {})
        user_options = parsed_document.get('userOptions', {})
        sections = list(content.get('sections') or [])
        target_length = self._target_length(user_options.get('length'), sections)
        llm_outline = (outline_prompt or {}).get('llmOutline') or {}
        llm_slides = self._normalize_llm_slides(llm_outline.get('slides') or [], sections)
        if llm_slides:
            return {
                'jobId': parsed_document.get('jobId'),
                'slides': llm_slides[:target_length],
                'sourceDocumentType': content.get('documentType', 'unknown'),
                'outlinePromptProvider': (outline_prompt or {}).get('provider'),
                'outlineSource': 'llm',
            }

        slides: list[dict[str, Any]] = []

        slides.append(
            {
                'index': 1,
                'title': str(content.get('title') or 'Generated Presentation'),
                'type': 'summary',
                'purpose': 'Introduce the generated deck.',
                'bullets': self._overview_bullets(content, user_options),
                'sourceSections': [section.get('title', 'Overview') for section in sections[:3]],
            }
        )

        available_slots = max(target_length - 1, 1)
        for section in sections[:available_slots]:
            slides.append(self._section_to_slide(len(slides) + 1, section))

        while len(slides) < target_length:
            slides.append(self._filler_slide(len(slides) + 1, content, user_options))

        return {
            'jobId': parsed_document.get('jobId'),
            'slides': slides[:target_length],
            'sourceDocumentType': content.get('documentType', 'unknown'),
            'outlinePromptProvider': (outline_prompt or {}).get('provider'),
            'outlineSource': 'deterministic',
        }

    def _normalize_llm_slides(self, llm_slides: list[dict[str, Any]], sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        section_by_title = {str(section.get('title', '')).lower(): section for section in sections}
        normalized: list[dict[str, Any]] = []
        for index, slide in enumerate(llm_slides, start=1):
            title = str(slide.get('title') or f'Slide {index}')
            slide_type = slide.get('type') if slide.get('type') in VALID_SLIDE_TYPES else 'text'
            source_sections = [str(item) for item in slide.get('sourceSections') or [] if str(item).strip()]
            matched_section = self._match_section(source_sections, section_by_title)
            normalized_slide = {
                'index': index,
                'title': title,
                'type': slide_type,
                'purpose': str(slide.get('purpose') or f'Present {title}.'),
                'bullets': self._section_bullets(matched_section or {}),
                'sourceSections': source_sections,
            }
            if slide_type == 'table' and matched_section:
                normalized_slide['table'] = {
                    'columns': matched_section.get('columns') or [],
                    'rows': matched_section.get('sampleRows') or matched_section.get('tablePreview') or [],
                }
            if slide_type == 'chart' and matched_section:
                normalized_slide['chart'] = {
                    'columns': matched_section.get('columns') or [],
                    'rows': matched_section.get('sampleRows') or [],
                    'numericColumns': matched_section.get('numericColumns') or [],
                }
            normalized.append(normalized_slide)
        return normalized

    def _match_section(self, source_sections: list[str], section_by_title: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
        for source_section in source_sections:
            exact = section_by_title.get(source_section.lower())
            if exact:
                return exact
        for source_section in source_sections:
            lowered_source = source_section.lower()
            for title, section in section_by_title.items():
                if lowered_source in title or title in lowered_source:
                    return section
        return None

    def _target_length(self, raw_length: Any, sections: list[dict[str, Any]]) -> int:
        try:
            requested = int(raw_length)
        except (TypeError, ValueError):
            requested = max(len(sections) + 1, 5)
        return min(max(requested, 3), 15)

    def _overview_bullets(self, content: dict[str, Any], user_options: dict[str, Any]) -> list[str]:
        tone = user_options.get('tone') or 'Executive'
        target = user_options.get('target') or 'Management'
        sections = content.get('sections') or []
        bullets = [
            f'Prepared for {target} with a {tone} tone.',
            f'Built from {len(sections)} extracted source section(s).',
        ]
        if sections:
            bullets.append(f'Primary focus: {sections[0].get("title", "Overview")}.')
        return bullets

    def _section_to_slide(self, index: int, section: dict[str, Any]) -> dict[str, Any]:
        data_type = section.get('dataType') if section.get('dataType') in VALID_SLIDE_TYPES else 'text'
        title = str(section.get('title') or f'Section {index}')
        slide = {
            'index': index,
            'title': title,
            'type': data_type,
            'purpose': str(section.get('summary') or f'Summarize {title}.'),
            'bullets': self._section_bullets(section),
            'sourceSections': [title],
        }
        if data_type == 'table':
            slide['table'] = {
                'columns': section.get('columns') or [],
                'rows': section.get('sampleRows') or section.get('tablePreview') or [],
            }
        if data_type == 'chart':
            slide['chart'] = {
                'columns': section.get('columns') or [],
                'rows': section.get('sampleRows') or [],
                'numericColumns': section.get('numericColumns') or [],
            }
        return slide

    def _section_bullets(self, section: dict[str, Any]) -> list[str]:
        bullets = [str(item) for item in section.get('bullets') or [] if str(item).strip()]
        if bullets:
            return bullets[:5]
        summary = str(section.get('summary') or '').strip()
        if summary:
            return [summary]
        columns = section.get('columns') or []
        if columns:
            return [f'Columns include {", ".join(str(column) for column in columns[:4])}.']
        return ['Source content was extracted and prepared for presentation.']

    def _filler_slide(self, index: int, content: dict[str, Any], user_options: dict[str, Any]) -> dict[str, Any]:
        if index == 2:
            title = 'Executive Overview'
            bullets = [section.get('summary') or section.get('title') or 'Key source section' for section in (content.get('sections') or [])[:3]]
        else:
            title = 'Next Steps'
            bullets = [
                'Validate the generated narrative with source owners.',
                'Adjust slide emphasis for the intended audience.',
                'Use the output deck as a first editable draft.',
            ]
        return {
            'index': index,
            'title': title,
            'type': 'text',
            'purpose': str(user_options.get('notes') or 'Provide a useful supporting slide.'),
            'bullets': bullets or ['Review the source material and refine the story.'],
            'sourceSections': [],
        }
