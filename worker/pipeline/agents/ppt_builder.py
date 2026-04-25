from __future__ import annotations

import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any

from utils.s3 import get_object_bytes


class PPTBuilder:
    def build(
        self,
        job: dict[str, Any],
        reviewed_slides: dict[str, Any],
        rendered_charts: dict[str, Any],
    ) -> str:
        from pptx import Presentation
        from pptx.enum.text import PP_ALIGN
        from pptx.util import Inches, Pt

        template_bytes = get_object_bytes(job['templateS3Key'])
        presentation = Presentation(BytesIO(template_bytes))
        chart_by_slide = {chart['slideIndex']: chart for chart in rendered_charts.get('charts') or []}

        for slide_data in reviewed_slides.get('slides') or []:
            layout = self._select_layout(presentation, slide_data.get('type'))
            slide = presentation.slides.add_slide(layout)
            title_shape = slide.shapes.title
            if title_shape is not None:
                title_shape.text = slide_data.get('title') or f"Slide {slide_data.get('index')}"

            if slide_data.get('type') == 'table':
                self._add_table(slide, slide_data, presentation)
            elif slide_data.get('type') == 'chart' and slide_data.get('index') in chart_by_slide:
                self._add_chart(slide, slide_data, chart_by_slide[slide_data['index']], presentation)
            else:
                self._add_bullets(slide, slide_data, presentation)

            notes = slide.notes_slide.notes_text_frame
            notes.text = slide_data.get('purpose') or ''

            for shape in slide.shapes:
                if not getattr(shape, 'has_text_frame', False):
                    continue
                for paragraph in shape.text_frame.paragraphs:
                    paragraph.alignment = PP_ALIGN.LEFT
                    for run in paragraph.runs:
                        run.font.size = run.font.size or Pt(18)

        output_path = Path(tempfile.gettempdir()) / f'{job["jobId"]}-output.pptx'
        presentation.save(output_path)
        return str(output_path)

    def _select_layout(self, presentation: Any, slide_type: str | None) -> Any:
        preferred_names = {
            'summary': ('Title and Content', 'Title Slide'),
            'text': ('Title and Content',),
            'table': ('Title and Content', 'Blank'),
            'chart': ('Title and Content', 'Blank'),
        }.get(slide_type or 'text', ('Title and Content',))

        for preferred_name in preferred_names:
            for layout in presentation.slide_layouts:
                if preferred_name.lower() in (layout.name or '').lower():
                    return layout
        return presentation.slide_layouts[1] if len(presentation.slide_layouts) > 1 else presentation.slide_layouts[0]

    def _add_bullets(self, slide: Any, slide_data: dict[str, Any], presentation: Any) -> None:
        from pptx.util import Inches, Pt

        body = self._body_placeholder(slide)
        if body is None:
            body = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), presentation.slide_width - Inches(1.6), Inches(4.6))
        text_frame = body.text_frame
        text_frame.clear()
        for index, bullet in enumerate(slide_data.get('bullets') or []):
            paragraph = text_frame.paragraphs[0] if index == 0 else text_frame.add_paragraph()
            paragraph.text = str(bullet)
            paragraph.level = 0
            for run in paragraph.runs:
                run.font.size = Pt(20)

    def _add_table(self, slide: Any, slide_data: dict[str, Any], presentation: Any) -> None:
        from pptx.util import Inches, Pt

        table_data = slide_data.get('table') or {}
        columns = table_data.get('columns') or ['Column 1']
        rows = table_data.get('rows') or [['No tabular rows extracted']]
        row_count = min(len(rows) + 1, 7)
        col_count = min(len(columns), 6)
        table_shape = slide.shapes.add_table(row_count, col_count, Inches(0.7), Inches(1.7), presentation.slide_width - Inches(1.4), Inches(4.6))
        table = table_shape.table
        for col_index in range(col_count):
            table.cell(0, col_index).text = str(columns[col_index])
        for row_index, row in enumerate(rows[: row_count - 1], start=1):
            for col_index in range(col_count):
                table.cell(row_index, col_index).text = str(row[col_index]) if col_index < len(row) else ''
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.text_frame.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(10)

    def _add_chart(self, slide: Any, slide_data: dict[str, Any], chart: dict[str, Any], presentation: Any) -> None:
        from pptx.util import Inches

        slide.shapes.add_picture(chart['localPath'], Inches(0.7), Inches(1.6), width=presentation.slide_width - Inches(1.4))
        if slide_data.get('bullets'):
            textbox = slide.shapes.add_textbox(Inches(0.8), Inches(6.2), presentation.slide_width - Inches(1.6), Inches(0.8))
            textbox.text_frame.text = str(slide_data['bullets'][0])

    def _body_placeholder(self, slide: Any) -> Any | None:
        for shape in slide.placeholders:
            if shape == slide.shapes.title:
                continue
            if getattr(shape, 'has_text_frame', False):
                return shape
        return None
