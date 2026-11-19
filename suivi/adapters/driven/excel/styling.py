"""Mise en forme commune des feuilles Excel produites par l'application."""
from openpyxl.styles import Font


def style_sheet(ws) -> None:
    for cell in ws[1]:
        cell.font = Font(name="Arial", bold=True)
    for column in ws.columns:
        width = max(len(str(c.value)) if c.value is not None else 0 for c in column)
        ws.column_dimensions[column[0].column_letter].width = min(width + 3, 45)
        for c in column[1:]:
            c.font = Font(name="Arial")
            if isinstance(c.value, bool):
                continue
            if isinstance(c.value, int):
                c.number_format = "#,##0"
            elif isinstance(c.value, float):
                c.number_format = "0.0"
    ws.freeze_panes = "A2"
