"""Generate Office documents as in-memory bytes."""

from io import BytesIO

from docx import Document
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor as DocxRGBColor
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt as PptPt

NAVY = RGBColor(15, 23, 42)
GOLD = RGBColor(212, 160, 23)
WHITE = RGBColor(255, 255, 255)
SLATE = RGBColor(30, 41, 59)


def create_document(doc_type: str, template: str | None, title: str) -> bytes:
    """Create a DOCX, XLSX, or PPTX document as bytes."""
    normalized_template = template or "blank"
    if doc_type == "docx":
        return _create_docx(normalized_template, title)
    if doc_type == "xlsx":
        return _create_xlsx(normalized_template, title)
    if doc_type == "pptx":
        return _create_pptx(normalized_template, title)
    raise ValueError(f"Unsupported office document type: {doc_type}")


def _create_docx(template: str, title: str) -> bytes:
    doc = Document()
    _apply_docx_defaults(doc)

    doc.add_heading(title, level=0)
    doc.add_paragraph()

    if template == "blank":
        doc.add_paragraph("Start drafting here.")
    elif template == "legal_memo":
        _add_labeled_paragraph(doc, "To", "[Recipient]")
        _add_labeled_paragraph(doc, "From", "[Author]")
        _add_labeled_paragraph(doc, "Date", "[Date]")
        _add_labeled_paragraph(doc, "Re", title)
        doc.add_paragraph()
        doc.add_heading("Executive Summary", level=1)
        doc.add_paragraph("[Summarize the issue, recommendation, and key risks.]")
        doc.add_heading("Facts", level=1)
        doc.add_paragraph("[Insert relevant factual background.]")
        doc.add_heading("Analysis", level=1)
        doc.add_paragraph("[Insert legal analysis with authorities and reasoning.]")
        doc.add_heading("Recommendation", level=1)
        doc.add_paragraph("[Insert recommended next steps.]")
    elif template == "contract":
        doc.add_heading("Parties", level=1)
        doc.add_paragraph("This Agreement is entered into between [Party A] and [Party B].")
        doc.add_heading("Recitals", level=1)
        doc.add_paragraph("WHEREAS, [background recital one].")
        doc.add_paragraph("WHEREAS, [background recital two].")
        for heading in [
            "Definitions",
            "Services and Deliverables",
            "Fees and Payment",
            "Confidentiality",
            "Representations and Warranties",
            "Indemnities",
            "Limitation of Liability",
            "Term and Termination",
            "Governing Law and Dispute Resolution",
        ]:
            doc.add_heading(heading, level=1)
            doc.add_paragraph("[Draft clause text here.]")
    elif template == "nda":
        doc.add_heading("Confidentiality and Non-Disclosure Agreement", level=1)
        doc.add_paragraph("This NDA is made between [Disclosing Party] and [Receiving Party].")
        for heading in [
            "Purpose",
            "Definition of Confidential Information",
            "Permitted Use",
            "Non-Disclosure Obligations",
            "Required Disclosures",
            "Return or Destruction of Materials",
            "Term",
            "Governing Law",
        ]:
            doc.add_heading(heading, level=1)
            doc.add_paragraph("[Insert GCC-appropriate NDA language.]")
    elif template == "court_brief":
        doc.add_heading("Before the Competent Court", level=1)
        _add_labeled_paragraph(doc, "Matter", title)
        _add_labeled_paragraph(doc, "Claimant", "[Claimant Name]")
        _add_labeled_paragraph(doc, "Respondent", "[Respondent Name]")
        doc.add_heading("Relief Sought", level=1)
        doc.add_paragraph("[State the orders requested from the court.]")
        doc.add_heading("Statement of Facts", level=1)
        doc.add_paragraph("[Set out facts in chronological order.]")
        doc.add_heading("Legal Grounds", level=1)
        doc.add_paragraph("[Insert statutory and procedural grounds for relief.]")
        doc.add_heading("Attachments", level=1)
        doc.add_paragraph("[List exhibits and supporting materials.]")
    else:
        doc.add_paragraph("Unsupported template selected; a blank document was created.")

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _apply_docx_defaults(doc: Document) -> None:
    for style_name in ("Normal", "Body Text", "Default Paragraph Font"):
        try:
            style = doc.styles[style_name]
        except KeyError:
            continue
        style.font.name = "Calibri"
        style.font.size = Pt(11)
        if style._element.rPr is None:
            style._element.get_or_add_rPr()
        r_fonts = style._element.rPr.rFonts
        if r_fonts is None:
            r_fonts = OxmlElement("w:rFonts")
            style._element.rPr.append(r_fonts)
        r_fonts.set(qn("w:ascii"), "Calibri")
        r_fonts.set(qn("w:hAnsi"), "Calibri")
        r_fonts.set(qn("w:eastAsia"), "Calibri")

    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    _add_heyamin_header(doc)
    doc.core_properties.language = "en-US"


def _add_heyamin_header(doc: Document) -> None:
    """Add a subtle 'Created with HeyAmin' header to all sections."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    for section in doc.sections:
        header = section.header
        header.is_linked_to_previous = False
        para = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        para.text = ""
        run = para.add_run("Created with HeyAmin")
        run.font.size = Pt(8)
        run.font.color.rgb = DocxRGBColor(180, 180, 180)
        run.font.name = "Calibri"
        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT


def _add_labeled_paragraph(doc: Document, label: str, value: str) -> None:
    paragraph = doc.add_paragraph()
    label_run = paragraph.add_run(f"{label}: ")
    label_run.bold = True
    paragraph.add_run(value)


def _create_xlsx(template: str, title: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Overview"

    if template == "blank":
        ws["A1"] = title
        ws["A2"] = "Start working in this sheet."
    elif template == "budget":
        headers = ["Category", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Total"]
        rows = [
            ["Revenue", 0, 0, 0, 0, 0, 0, "=SUM(B2:G2)"],
            ["Payroll", 0, 0, 0, 0, 0, 0, "=SUM(B3:G3)"],
            ["External Counsel", 0, 0, 0, 0, 0, 0, "=SUM(B4:G4)"],
            ["Operations", 0, 0, 0, 0, 0, 0, "=SUM(B5:G5)"],
        ]
        _write_sheet(ws, headers, rows)
    elif template == "tracker":
        headers = ["Title", "Status", "Owner", "Due Date", "Notes"]
        rows = [
            ["Prepare filing", "In Progress", "[Owner]", "[YYYY-MM-DD]", ""],
            ["Collect exhibits", "Open", "[Owner]", "[YYYY-MM-DD]", ""],
            ["Client approval", "Pending", "[Owner]", "[YYYY-MM-DD]", ""],
        ]
        _write_sheet(ws, headers, rows)
    elif template == "legal_matrix":
        headers = ["Jurisdiction", "Law", "Article", "Summary", "Status"]
        rows = [
            ["UAE", "[Law Name]", "[Article]", "[Summary]", "Monitor"],
            ["DIFC", "[Law Name]", "[Article]", "[Summary]", "Review"],
            ["KSA", "[Law Name]", "[Article]", "[Summary]", "Action"],
        ]
        _write_sheet(ws, headers, rows)
    else:
        ws["A1"] = title
        ws["A2"] = "Unsupported template selected; a blank workbook was created."

    _style_workbook(wb)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _write_sheet(ws, headers: list[str], rows: list[list[object]]) -> None:
    ws.append(headers)
    for row in rows:
        ws.append(row)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def _style_workbook(wb: Workbook) -> None:
    header_fill = PatternFill(fill_type="solid", fgColor="1E293B")
    header_font = Font(color="FFFFFF", bold=True)
    bold_font = Font(bold=True)

    for ws in wb.worksheets:
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font

        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            for cell in row:
                if cell.row > 1 and cell.column == 1:
                    cell.font = bold_font

        for idx in range(1, ws.max_column + 1):
            max_length = 0
            for cell in ws[get_column_letter(idx)]:
                max_length = max(max_length, len(str(cell.value or "")))
            ws.column_dimensions[get_column_letter(idx)].width = min(max(max_length + 2, 12), 32)


def _create_pptx(template: str, title: str) -> bytes:
    prs = Presentation()

    if template == "blank":
        _add_title_slide(prs, title, "Prepared with Amin")
    elif template == "pitch":
        _add_title_slide(prs, title, "Executive pitch")
        for heading in ["Problem", "Solution", "Market", "Team", "Ask"]:
            _add_content_slide(prs, heading, ["[Insert content]", "[Key takeaway]"])
    elif template == "status_update":
        _add_title_slide(prs, title, "Status update")
        for heading in ["Summary", "Progress", "Risks", "Next Steps"]:
            _add_content_slide(prs, heading, ["[Insert update]", "[Owner / timeline]"])
    elif template == "legal_overview":
        _add_title_slide(prs, title, "Legal overview")
        for heading in ["Jurisdiction", "Key Laws", "Obligations", "Recommendations"]:
            _add_content_slide(prs, heading, ["[Insert legal point]", "[Commercial implication]"])
    else:
        _add_title_slide(prs, title, "Blank presentation")

    buffer = BytesIO()
    prs.save(buffer)
    return buffer.getvalue()


def _add_title_slide(prs: Presentation, title: str, subtitle: str) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = NAVY

    slide.shapes.title.text = title
    title_frame = slide.shapes.title.text_frame
    title_frame.paragraphs[0].font.color.rgb = WHITE
    title_frame.paragraphs[0].font.size = PptPt(28)
    title_frame.paragraphs[0].font.bold = True

    subtitle_box = slide.placeholders[1]
    subtitle_box.text = subtitle
    subtitle_para = subtitle_box.text_frame.paragraphs[0]
    subtitle_para.font.color.rgb = GOLD
    subtitle_para.font.size = PptPt(16)
    subtitle_para.alignment = PP_ALIGN.LEFT


def _add_content_slide(prs: Presentation, title: str, bullets: list[str]) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = WHITE

    slide.shapes.title.text = title
    title_para = slide.shapes.title.text_frame.paragraphs[0]
    title_para.font.color.rgb = NAVY
    title_para.font.bold = True
    title_para.font.size = PptPt(22)

    body = slide.placeholders[1].text_frame
    body.clear()
    for idx, bullet in enumerate(bullets):
        paragraph = body.paragraphs[0] if idx == 0 else body.add_paragraph()
        paragraph.text = bullet
        paragraph.font.color.rgb = SLATE
        paragraph.font.size = PptPt(16)
        paragraph.level = 0

    accent = slide.shapes.add_shape(
        1,
        Inches(0.5),
        Inches(1.3),
        Inches(1.5),
        Inches(0.08),
    )
    accent.fill.solid()
    accent.fill.fore_color.rgb = GOLD
    accent.line.fill.background()
