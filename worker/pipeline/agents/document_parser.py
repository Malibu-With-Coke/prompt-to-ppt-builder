from __future__ import annotations

from io import BytesIO
from typing import Any

from utils.s3 import get_object_bytes


class DocumentParser:
    def __init__(self, bucket_name: str | None = None):
        self.bucket_name = bucket_name

    def parse(self, job: dict[str, Any]) -> dict[str, Any]:
        job_id = job['jobId']
        template_key = job['templateS3Key']
        content_key = job['contentS3Key']

        template_bytes = get_object_bytes(template_key, self.bucket_name)
        content_bytes = get_object_bytes(content_key, self.bucket_name)

        return {
            'jobId': job_id,
            'templateRules': self._parse_template(template_bytes),
            'contentSummary': self._parse_content(content_key, content_bytes),
            'userOptions': job.get('options', {}),
            'sources': {
                'templateS3Key': template_key,
                'contentS3Key': content_key,
            },
        }

    def _parse_content(self, content_key: str, payload: bytes) -> dict[str, Any]:
        lowered_key = content_key.lower()
        if lowered_key.endswith('.docx'):
            return self._parse_docx(payload)
        if lowered_key.endswith('.xlsx'):
            return self._parse_xlsx(payload)
        raise ValueError(f'Unsupported content file type: {content_key}')

    def _parse_template(self, payload: bytes) -> dict[str, Any]:
        from pptx import Presentation

        presentation = Presentation(BytesIO(payload))
        layout_summaries: list[dict[str, Any]] = []
        fonts: set[str] = set()
        colors: set[str] = set()
        max_bullets = 0

        for layout in presentation.slide_layouts:
            placeholders: list[str] = []
            for placeholder in layout.placeholders:
                placeholder_type = getattr(placeholder.placeholder_format, 'type', None)
                placeholders.append(str(placeholder_type) if placeholder_type is not None else 'UNKNOWN')
            layout_summaries.append(
                {
                    'name': layout.name or 'Unnamed Layout',
                    'placeholders': placeholders,
                }
            )

        for slide in presentation.slides:
            for shape in slide.shapes:
                if not getattr(shape, 'has_text_frame', False):
                    continue
                text_frame = shape.text_frame
                bullet_count = sum(1 for paragraph in text_frame.paragraphs if paragraph.text.strip())
                max_bullets = max(max_bullets, bullet_count)
                for paragraph in text_frame.paragraphs:
                    for run in paragraph.runs:
                        if run.font.name:
                            fonts.add(run.font.name)
                        color = getattr(getattr(run.font, 'color', None), 'rgb', None)
                        if color is not None:
                            colors.add(str(color))

        return {
            'slideCount': len(presentation.slides),
            'slideWidth': presentation.slide_width,
            'slideHeight': presentation.slide_height,
            'layouts': layout_summaries,
            'maxBullets': max_bullets or 4,
            'style': 'formal',
            'fonts': sorted(fonts),
            'colorTheme': sorted(colors)[:8],
        }

    def _parse_docx(self, payload: bytes) -> dict[str, Any]:
        from docx import Document

        document = Document(BytesIO(payload))
        title = 'Uploaded document'
        sections: list[dict[str, Any]] = []
        current_section: dict[str, Any] | None = None

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue

            style_name = paragraph.style.name if paragraph.style else ''
            if style_name.startswith('Title') and title == 'Uploaded document':
                title = text
                continue

            if style_name.startswith('Heading'):
                if current_section:
                    sections.append(self._finalize_text_section(current_section))
                current_section = {'title': text, 'chunks': []}
                continue

            if current_section is None:
                current_section = {'title': 'Overview', 'chunks': []}
                if title == 'Uploaded document':
                    title = text
            current_section['chunks'].append(text)

        if current_section:
            sections.append(self._finalize_text_section(current_section))

        for index, table in enumerate(document.tables, start=1):
            preview_rows = []
            for row in table.rows[:4]:
                preview_rows.append([cell.text.strip() for cell in row.cells])
            sections.append(
                {
                    'title': f'Table {index}',
                    'summary': 'Tabular content extracted from the document.',
                    'dataType': 'table',
                    'bullets': [],
                    'tablePreview': preview_rows,
                }
            )

        return {
            'title': title,
            'documentType': 'docx',
            'sections': sections
            or [
                {
                    'title': 'Overview',
                    'summary': 'The document did not contain extractable sections.',
                    'dataType': 'text',
                    'bullets': [],
                }
            ],
        }

    def _finalize_text_section(self, section: dict[str, Any]) -> dict[str, Any]:
        chunks = [chunk for chunk in section.get('chunks', []) if chunk]
        summary = ' '.join(chunks[:2])[:320]
        return {
            'title': section['title'],
            'summary': summary or 'No summary available.',
            'dataType': 'text',
            'bullets': chunks[:5],
        }

    def _parse_xlsx(self, payload: bytes) -> dict[str, Any]:
        from openpyxl import load_workbook

        workbook = load_workbook(BytesIO(payload), data_only=True, read_only=True)
        title = workbook.properties.title or workbook.sheetnames[0] or 'Workbook'
        sections: list[dict[str, Any]] = []

        for sheet in workbook.worksheets:
            rows: list[list[Any]] = []
            for raw_row in sheet.iter_rows(values_only=True):
                normalized_row = list(raw_row)
                if any(cell not in (None, '') for cell in normalized_row):
                    rows.append(normalized_row)
                if len(rows) >= 8:
                    break

            if not rows:
                continue

            header_row = rows[0]
            headers = [str(cell).strip() if cell not in (None, '') else f'Column {index + 1}' for index, cell in enumerate(header_row)]
            sample_rows = rows[1:6]
            numeric_columns = []
            for index, header in enumerate(headers):
                column_values = [row[index] for row in sample_rows if index < len(row) and isinstance(row[index], (int, float))]
                if len(column_values) >= 2:
                    numeric_columns.append(header)

            data_type = 'chart' if numeric_columns else 'table'
            sections.append(
                {
                    'title': sheet.title,
                    'summary': self._summarize_sheet(headers, sample_rows, numeric_columns),
                    'dataType': data_type,
                    'columns': headers,
                    'sampleRows': sample_rows,
                    'numericColumns': numeric_columns,
                }
            )

        return {
            'title': title,
            'documentType': 'xlsx',
            'sections': sections
            or [
                {
                    'title': 'Workbook Overview',
                    'summary': 'The workbook did not contain extractable rows.',
                    'dataType': 'table',
                    'columns': [],
                    'sampleRows': [],
                    'numericColumns': [],
                }
            ],
        }

    def _summarize_sheet(self, headers: list[str], sample_rows: list[list[Any]], numeric_columns: list[str]) -> str:
        header_preview = ', '.join(headers[:4]) if headers else 'no headers'
        row_count = len(sample_rows)
        if numeric_columns:
            numeric_preview = ', '.join(numeric_columns[:3])
            return f'Sheet contains {row_count} sampled data rows with chart-friendly numeric columns such as {numeric_preview}. Headers include {header_preview}.'
        return f'Sheet contains {row_count} sampled data rows. Headers include {header_preview}.'
