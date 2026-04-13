"""PDF 보고서 생성."""

from __future__ import annotations

import datetime as dt
import os

from fpdf import FPDF


class KoreanPDF(FPDF):
    def __init__(self) -> None:
        super().__init__()
        self.font_family_name = "Helvetica"
        regular = "C:/Windows/Fonts/malgun.ttf"
        bold = "C:/Windows/Fonts/malgunbd.ttf"

        try:
            if os.path.exists(regular):
                self.add_font("Malgun", "", regular)
                self.font_family_name = "Malgun"
            if os.path.exists(bold):
                self.add_font("MalgunB", "", bold)
        except Exception:
            self.font_family_name = "Helvetica"

    def kfont(self, size: int = 11, bold: bool = False) -> None:
        if bold and self.font_family_name == "Malgun":
            try:
                self.set_font("MalgunB", "", size)
                return
            except Exception:
                pass
        self.set_font(self.font_family_name, "", size)


def _safe_text(value: str) -> str:
    return value.replace("\n", " ").replace("⛔", "불가").strip()


def generate_report_pdf(payload: dict) -> bytes:
    pdf = KoreanPDF()
    pdf.add_page()
    pdf.set_auto_page_break(True, 14)

    pdf.kfont(18, bold=True)
    pdf.cell(0, 12, "상표등록 가능성 검토 서비스", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    pdf.cell(0, 8, f"작성일: {dt.date.today().isoformat()}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    summary_rows = [
        ("상표명", payload["trademark_name"]),
        ("상표 유형", payload["trademark_type"]),
        ("상품군", ", ".join(payload["selected_classes"]) or "-"),
        ("유사군 코드", ", ".join(payload["selected_codes"]) or "-"),
        ("등록 가능성", f'{payload["score"]}% - {payload["score_label"]}'),
        ("식별력", payload["distinctiveness"]),
        ("선행상표", f'{payload["prior_count"]}건'),
    ]

    pdf.kfont(12, bold=True)
    pdf.cell(0, 8, "검토 요약", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    for label, value in summary_rows:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 7, _safe_text(f"{label}: {value}"))
    pdf.ln(2)

    pdf.kfont(12, bold=True)
    pdf.cell(0, 8, "주요 선행상표", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    if not payload["top_prior"]:
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 7, "확인된 주요 선행상표가 없습니다.", new_x="LMARGIN", new_y="NEXT")
    else:
        for idx, item in enumerate(payload["top_prior"], start=1):
            line = (
                f"{idx}. {item.get('trademarkName', '-')}"
                f" | {item.get('registerStatus', '-')}"
                f" | {item.get('classificationCode', '-')}"
                f" | 유사도 {item.get('similarity', 0)}%"
            )
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 7, _safe_text(line))
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 7, _safe_text(f"출원인: {item.get('applicantName', '-')}"))
            pdf.ln(1)

    pdf.kfont(12, bold=True)
    pdf.cell(0, 8, "개선 방안", new_x="LMARGIN", new_y="NEXT")
    pdf.kfont(10)
    for option in payload["name_options"]:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 7, _safe_text(f"상표명 대안: {option['name']} -> 예상 {option['expected_score']}%"))
    for option in payload["scope_options"]:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            0,
            7,
            _safe_text(f"{option['title']}: {option['description']} (예상 {option['expected_score']}%)"),
        )

    pdf.ln(4)
    pdf.kfont(8)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, "본 결과는 참고용 AI 분석입니다. 최종 출원 판단은 변리사와 상담해 주세요.")
    return bytes(pdf.output())
