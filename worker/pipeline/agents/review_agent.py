from __future__ import annotations

from typing import Any


VALID_SLIDE_TYPES = {'summary', 'text', 'chart', 'table', 'section-header'}


class ReviewAgent:
    def review(self, slide_draft: dict[str, Any]) -> dict[str, Any]:
        slides = [self._normalize_slide(index + 1, slide) for index, slide in enumerate(slide_draft.get('slides') or [])]
        return {
            **slide_draft,
            'slides': slides,
            'review': {
                'status': 'passed',
                'fixesApplied': True,
            },
        }

    def _normalize_slide(self, index: int, slide: dict[str, Any]) -> dict[str, Any]:
        slide_type = slide.get('type') if slide.get('type') in VALID_SLIDE_TYPES else 'text'
        title = self._trim_text(slide.get('title') or f'Slide {index}', 70)
        bullets = [self._trim_text(item, 140) for item in slide.get('bullets') or [] if str(item).strip()]
        if not bullets:
            bullets = ['Key content extracted from the source document.']

        normalized = {
            **slide,
            'index': index,
            'title': title,
            'type': slide_type,
            'purpose': self._trim_text(slide.get('purpose') or f'Present {title}.', 180),
            'bullets': bullets[:5],
            'sourceSections': [str(item) for item in slide.get('sourceSections') or [] if str(item).strip()],
        }

        if slide_type == 'table':
            normalized['table'] = self._normalize_table(slide.get('table') or {})
        if slide_type == 'chart':
            normalized['chart'] = self._normalize_chart(slide.get('chart') or {})
        return normalized

    def _normalize_table(self, table: dict[str, Any]) -> dict[str, Any]:
        columns = [self._trim_text(column, 32) for column in table.get('columns') or []]
        rows = [list(row)[: len(columns) or 4] for row in table.get('rows') or []]
        return {
            'columns': columns[:6],
            'rows': rows[:6],
        }

    def _normalize_chart(self, chart: dict[str, Any]) -> dict[str, Any]:
        return {
            'columns': [str(column) for column in chart.get('columns') or []],
            'rows': [list(row) for row in chart.get('rows') or []][:8],
            'numericColumns': [str(column) for column in chart.get('numericColumns') or []],
        }

    def _trim_text(self, value: Any, limit: int) -> str:
        text = ' '.join(str(value).split())
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + '...'
