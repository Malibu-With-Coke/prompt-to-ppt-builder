from __future__ import annotations

from typing import Any


VALID_SLIDE_TYPES = {'summary', 'text', 'chart', 'table', 'section-header'}


class ReviewAgent:
    def review_output(
        self,
        parsed_document: dict[str, Any],
        deck_transform: dict[str, Any],
        ppt_validation: dict[str, Any],
    ) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        transform_plan = deck_transform.get('transformPlan') or {}
        content = parsed_document.get('contentSummary') or {}

        findings.extend(self._review_transform_coverage(parsed_document, transform_plan))
        findings.extend(self._review_excel_update_intent(content, transform_plan))
        findings.extend(self._review_ppt_validation(ppt_validation))

        blocking_findings = [finding for finding in findings if finding.get('severity') == 'error']
        warning_findings = [finding for finding in findings if finding.get('severity') == 'warning']
        if blocking_findings:
            status = 'needs_retry'
        elif warning_findings:
            status = 'warning'
        else:
            status = 'passed'

        return {
            'status': status,
            'findings': findings,
            'summary': {
                'findingCount': len(findings),
                'blockingFindingCount': len(blocking_findings),
                'warningFindingCount': len(warning_findings),
            },
        }

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

    def _review_transform_coverage(self, parsed_document: dict[str, Any], transform_plan: dict[str, Any]) -> list[dict[str, Any]]:
        template_slides = (parsed_document.get('templateRules') or {}).get('templateSlides') or []
        expected_shape_ids = {
            int(shape['shapeId'])
            for slide in template_slides
            for shape in slide.get('textShapes') or []
            if shape.get('shapeId') is not None and str(shape.get('text') or '').strip()
        }
        replacement_shape_ids = {
            int(replacement['shapeId'])
            for slide in transform_plan.get('slides') or []
            for replacement in slide.get('replacements') or []
            if replacement.get('shapeId') is not None
        }
        missing = sorted(expected_shape_ids - replacement_shape_ids)
        if not missing:
            return []
        return [
            {
                'severity': 'error',
                'type': 'missing_text_replacements',
                'message': f'Transform plan omitted replacement text for shape IDs: {missing}',
                'shapeIds': missing,
            }
        ]

    def _review_excel_update_intent(self, content: dict[str, Any], transform_plan: dict[str, Any]) -> list[dict[str, Any]]:
        if content.get('documentType') not in {'xlsx', 'multi'}:
            return []
        has_chart_ready_data = any(section.get('numericColumns') for section in content.get('sections') or [])
        if not has_chart_ready_data:
            return []
        chart_intent_count = sum(len(slide.get('chartUpdates') or []) for slide in transform_plan.get('slides') or [])
        table_intent_count = sum(len(slide.get('tableUpdates') or []) for slide in transform_plan.get('slides') or [])
        if chart_intent_count or table_intent_count:
            return []
        return [
            {
                'severity': 'warning',
                'type': 'missing_excel_update_intent',
                'message': 'Workbook has chart-friendly numeric data, but the transform plan did not include chartUpdates or tableUpdates intent.',
            }
        ]

    def _review_ppt_validation(self, ppt_validation: dict[str, Any]) -> list[dict[str, Any]]:
        findings = []
        render_status = (ppt_validation.get('render') or {}).get('status')
        if render_status == 'failed':
            findings.append(
                {
                    'severity': 'error',
                    'type': 'render_failed',
                    'message': (ppt_validation.get('render') or {}).get('reason') or 'PPTX render smoke test failed.',
                }
            )
        elif render_status == 'skipped':
            findings.append(
                {
                    'severity': 'warning',
                    'type': 'render_skipped',
                    'message': (ppt_validation.get('render') or {}).get('reason') or 'PPTX render smoke test was skipped.',
                }
            )

        for warning in (ppt_validation.get('audit') or {}).get('warnings') or []:
            warning_type = warning.get('type') or 'ppt_warning'
            findings.append(
                {
                    'severity': 'error' if warning_type == 'high_text_density' else 'warning',
                    'type': warning_type,
                    'message': warning.get('message') or 'PPTX structural audit warning.',
                    'slideIndex': warning.get('slideIndex'),
                    'shapeId': warning.get('shapeId'),
                }
            )
        return findings
