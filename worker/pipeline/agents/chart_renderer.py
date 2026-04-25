from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Any

from utils.s3 import put_file


class ChartRenderer:
    def render(self, job_id: str, reviewed_slides: dict[str, Any]) -> dict[str, Any]:
        rendered_charts: list[dict[str, Any]] = []
        for slide in reviewed_slides.get('slides') or []:
            if slide.get('type') != 'chart':
                continue
            chart = slide.get('chart') or {}
            chart_path = self._render_chart_file(job_id, slide, chart)
            if not chart_path:
                continue
            s3_key = f'temp/{job_id}/charts/slide-{slide["index"]}.png'
            put_file(s3_key, str(chart_path), 'image/png')
            rendered_charts.append(
                {
                    'slideIndex': slide['index'],
                    'title': slide.get('title'),
                    'localPath': str(chart_path),
                    's3Key': s3_key,
                }
            )
        return {'charts': rendered_charts}

    def _render_chart_file(self, job_id: str, slide: dict[str, Any], chart: dict[str, Any]) -> Path | None:
        columns = chart.get('columns') or []
        rows = chart.get('rows') or []
        numeric_columns = chart.get('numericColumns') or []
        if not columns or not rows or not numeric_columns:
            return None

        numeric_header = numeric_columns[0]
        try:
            value_index = columns.index(numeric_header)
        except ValueError:
            return None
        label_index = 0 if value_index != 0 else 1 if len(columns) > 1 else 0

        labels: list[str] = []
        values: list[float] = []
        for row in rows:
            if value_index >= len(row):
                continue
            value = row[value_index]
            if not isinstance(value, (int, float)):
                continue
            label = row[label_index] if label_index < len(row) else f'Item {len(labels) + 1}'
            labels.append(str(label)[:24])
            values.append(float(value))

        if not labels or not values:
            return None

        output_path = Path(tempfile.gettempdir()) / f'{job_id}-slide-{slide["index"]}.png'
        try:
            import matplotlib

            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
        except ModuleNotFoundError:
            output_path.write_bytes(
                base64.b64decode(
                    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII='
                )
            )
            return output_path

        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.bar(labels, values, color='#014986')
        ax.set_title(str(slide.get('title') or 'Chart'))
        ax.set_ylabel(str(numeric_header))
        ax.tick_params(axis='x', labelrotation=25)
        fig.tight_layout()
        fig.savefig(output_path, dpi=160)
        plt.close(fig)
        return output_path
