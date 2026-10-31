from functools import lru_cache
import html
import io
import json
from pathlib import Path
from typing import Any

from PIL import Image
import pymupdf
import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
     Image as RLImage,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

import config
import core

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
WATERMARK_PATH = ASSETS_DIR / "opacidade2.png"
SEAL_PATH = ASSETS_DIR / "selo.png"
SIG_FONT_PATH = ASSETS_DIR / "fonts" / "MrsSaintDelafield-Regular.ttf"

NAVY = colors.HexColor("#111E38")
GOLD = colors.HexColor("#A8842A")
INK = colors.HexColor("#141619")
MUTED = colors.HexColor("#4A5260")
PEN_BLUE = colors.HexColor("#0E2954")
PAPER_BG = colors.HexColor("#FCFBF7")
RULE_GRAY = colors.HexColor("#C8CDD6")
STAMP_RED = colors.HexColor("#9E1B1B")
STAMP_GREEN = colors.HexColor("#145A32")

_FONT_REGISTERED = False


def _ensure_fonts() -> str:
    global _FONT_REGISTERED
    if not _FONT_REGISTERED and SIG_FONT_PATH.exists():
        pdfmetrics.registerFont(TTFont("OfficerSignature", str(SIG_FONT_PATH)))
        _FONT_REGISTERED = True
    return "OfficerSignature" if _FONT_REGISTERED else "Times-Italic"


@lru_cache(maxsize=2)
def _watermark_bytes(opacity: float = 0.075) -> bytes:
    """Pre-multiplies alpha of opacidade2.png onto paper background so every PDF/PNG viewer renders exact low opacity."""
    img = Image.open(WATERMARK_PATH).convert("RGBA").resize((720, 720), Image.Resampling.LANCZOS)
    r, g, b, a = img.split()
    a = a.point(lambda px: int(px * opacity))
    overlay = Image.merge("RGBA", (r, g, b, a))
    bg = Image.new("RGBA", img.size, (252, 251, 247, 255))
    combined = Image.alpha_composite(bg, overlay).convert("RGB")
    buf = io.BytesIO()
    combined.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


@lru_cache(maxsize=1)
def _header_crest_bytes() -> bytes:
    img = Image.open(WATERMARK_PATH).convert("RGBA").resize((240, 240), Image.Resampling.LANCZOS)
    bg = Image.new("RGBA", img.size, (252, 251, 247, 255))
    combined = Image.alpha_composite(bg, img).convert("RGB")
    buf = io.BytesIO()
    combined.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


@lru_cache(maxsize=1)
def _seal_bytes() -> bytes:
    img = Image.open(SEAL_PATH).convert("RGBA").resize((360, 360), Image.Resampling.LANCZOS)
    bg = Image.new("RGBA", img.size, (250, 248, 241, 255))
    combined = Image.alpha_composite(bg, img).convert("RGB")
    buf = io.BytesIO()
    combined.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _qr_reader(url: str) -> ImageReader:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#111E38", back_color="#FCFBF7").convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


class _NumberedOfficialCanvas(canvas.Canvas):
    """Two-pass canvas that draws page borders, watermark, header banner, and footer with Page X of Y."""

    def __init__(self, *args, doc_meta: dict[str, Any] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []
        self._meta = doc_meta or {}

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_chrome(total)
            super().showPage()
        super().save()

    def _draw_page_chrome(self, total_pages: int):
        w, h = letter
        m = 0.42 * inch

        # Outer & inner formal border rules
        self.saveState()
        self.setStrokeColor(NAVY)
        self.setLineWidth(1.4)
        self.rect(m, m, w - 2 * m, h - 2 * m)
        self.setStrokeColor(GOLD)
        self.setLineWidth(0.55)
        self.rect(m + 3.5, m + 3.5, w - 2 * (m + 3.5), h - 2 * (m + 3.5))

        # Status stamp in center if DRAFT or REVOKED
        status = self._meta.get("status", "PENDING")
        if status != "APPROVED":
            stamp_txt = "DRAFT — PENDING COMMAND APPROVAL" if status == "PENDING" else f"{status} — NOT VALID"
            self.saveState()
            self.translate(w / 2, h / 2)
            self.rotate(34)
            self.setFillColor(colors.Color(0.65, 0.12, 0.12, alpha=0.11))
            self.setFont("Helvetica-Bold", 36)
            self.drawCentredString(0, 0, stamp_txt)
            self.restoreState()

        # Footer block inside frame
        fy = m + 8
        self.setStrokeColor(NAVY)
        self.setLineWidth(0.75)
        self.line(0.66 * inch, fy + 43, w - 0.66 * inch, fy + 43)

        ctrl = self._meta.get("control_no") or "DRAFT-UNASSIGNED"
        verify_url = f"{config.SITE_URL}/verify.html?n={ctrl}"
        qr = _qr_reader(verify_url)
        self.drawImage(qr, 0.66 * inch, fy + 3, width=36, height=36, mask="auto")

        self.setFillColor(NAVY)
        self.setFont("Helvetica-Bold", 7.2)
        self.drawString(0.66 * inch + 42, fy + 29, f"OFFICIAL RECORD · CONTROL NO. {ctrl}")
        self.setFillColor(MUTED)
        self.setFont("Helvetica", 6.5)
        self.drawString(
            0.66 * inch + 42,
            fy + 19,
            "AUTHENTICITY VERIFICATION: Scan QR or verify control number at official UPD Registry:",
        )
        self.setFillColor(NAVY)
        self.setFont("Helvetica-Bold", 6.5)
        self.drawString(0.66 * inch + 42, fy + 9, verify_url[:95])

        self.setFillColor(NAVY)
        self.setFont("Helvetica-Bold", 7.2)
        self.drawRightString(w - 0.66 * inch, fy + 28, "LAW ENFORCEMENT SENSITIVE")
        self.setFillColor(MUTED)
        self.setFont("Times-Italic", 7.4)
        self.drawRightString(w - 0.66 * inch, fy + 18, "Unified Police Department · County of Los Santos")
        self.setFillColor(INK)
        self.setFont("Helvetica-Bold", 7.4)
        self.drawRightString(w - 0.66 * inch, fy + 8, f"Page {self._pageNumber} of {total_pages}")
        self.restoreState()


def _draw_background_and_watermark(c: canvas.Canvas, _doc):
    """Drawn BEFORE flowables on each page so paper tone and watermark sit behind all text."""
    w, h = letter
    c.saveState()
    c.setFillColor(PAPER_BG)
    c.rect(0, 0, w, h, stroke=0, fill=1)

    if WATERMARK_PATH.exists():
        wm_size = 4.05 * inch
        c.drawImage(
            ImageReader(io.BytesIO(_watermark_bytes(0.075))),
            (w - wm_size) / 2,
            (h - wm_size) / 2 - 0.10 * inch,
            width=wm_size,
            height=wm_size,
            mask="auto",
        )
    c.restoreState()


def render_pdf(doc_record: dict[str, Any]) -> bytes:
    """Renders a full document dictionary into a US-Letter PDF byte stream."""
    sig_font = _ensure_fonts()
    snap = (
        json.loads(doc_record["template_snapshot"])
        if isinstance(doc_record["template_snapshot"], str)
        else doc_record["template_snapshot"]
    )
    data = (
        json.loads(doc_record["data_json"])
        if isinstance(doc_record["data_json"], str)
        else doc_record["data_json"]
    )

    ctrl = doc_record.get("control_no") or f"DRAFT-{doc_record.get('id', 'PREVIEW')}"
    status = doc_record.get("status", "PENDING")
    created_date = (doc_record.get("approved_at") or doc_record.get("created_at") or "")[:10] or "2026-10-31"
    category_label = (
        "JUDICIAL FILING · DOJ / SUPERIOR COURT"
        if snap.get("category") == "doj"
        else "INTERNAL DEPARTMENTAL RECORD"
    )

    variables = {
        **data,
        "control_no": ctrl,
        "date": created_date,
        "issuer_name": doc_record.get("issuer_name", "Officer"),
        "issuer_badge": doc_record.get("issuer_badge", "0000"),
        "issuer_rank": doc_record.get("issuer_rank", "Officer"),
        "issuer_division": doc_record.get("issuer_division", "Patrol Division"),
        "approver_name": doc_record.get("approver_name") or "Pending Command Review",
        "approver_badge": doc_record.get("approver_badge") or "—",
        "approver_rank": doc_record.get("approver_rank") or "Command Staff",
    }

    buf = io.BytesIO()
    pdf_doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.66 * inch,
        rightMargin=0.66 * inch,
        topMargin=0.56 * inch,
        bottomMargin=1.02 * inch,
        title=f"{ctrl} - {snap.get('name', 'UPD Document')}",
        author="Unified Police Department Records System",
    )

    # Styles
    s_dept = ParagraphStyle("Dept", fontName="Helvetica-Bold", fontSize=12.2, leading=14, textColor=NAVY)
    s_subdept = ParagraphStyle("SubDept", fontName="Helvetica-Bold", fontSize=7.4, leading=9.5, textColor=GOLD)
    s_juris = ParagraphStyle("Juris", fontName="Times-Roman", fontSize=8.4, leading=10, textColor=MUTED)
    s_meta_lbl = ParagraphStyle("MetaL", fontName="Helvetica-Bold", fontSize=6.8, leading=9, textColor=MUTED, alignment=TA_RIGHT)
    s_meta_val = ParagraphStyle("MetaV", fontName="Helvetica-Bold", fontSize=8.4, leading=10, textColor=NAVY, alignment=TA_RIGHT)
    s_court = ParagraphStyle("Court", fontName="Times-Bold", fontSize=9.2, leading=11.5, textColor=NAVY, alignment=TA_CENTER)
    s_title = ParagraphStyle("DocTitle", fontName="Helvetica-Bold", fontSize=11.4, leading=14, textColor=NAVY, alignment=TA_CENTER)
    s_sec_hdr = ParagraphStyle(
        "SecHdr",
        fontName="Helvetica-Bold",
        fontSize=9.2,
        leading=12,
        textColor=NAVY,
        spaceBefore=5,
        spaceAfter=2,
        keepWithNext=True,
    )
    s_body = ParagraphStyle(
        "Body",
        fontName="Times-Roman",
        fontSize=9.9,
        leading=13.5,
        textColor=INK,
        alignment=TA_JUSTIFY,
        spaceAfter=4,
    )
    s_meta_line = ParagraphStyle(
        "MetaLine",
        fontName="Times-Roman",
        fontSize=9.4,
        leading=12.5,
        textColor=INK,
        alignment=TA_LEFT,
        spaceAfter=1.5,
    )

    story: list[Any] = []

    # 1. Institutional Masthead Table
    left_masthead = [
        Paragraph("UNIFIED POLICE DEPARTMENT", s_dept),
        Paragraph("OFFICE OF THE CHIEF OF POLICE · HEADQUARTERS", s_subdept),
        Paragraph("State of San Andreas · County of Los Santos", s_juris),
    ]
    status_color = "#145A32" if status == "APPROVED" else "#9E1B1B"
    right_masthead = [
        Paragraph(f"CONTROL NO.: <font color='#111E38'><b>{ctrl}</b></font>", s_meta_val),
        Paragraph(f"DATE OF RECORD: <b>{created_date}</b>", s_meta_lbl),
        Paragraph(f"SERIES: <b>{category_label}</b>", s_meta_lbl),
        Paragraph(f"STATUS: <font color='{status_color}'><b>{status}</b></font>", s_meta_lbl),
    ]

    if WATERMARK_PATH.exists():
        crest_flow = RLImage(io.BytesIO(_header_crest_bytes()), width=0.58 * inch, height=0.58 * inch)
        hdr_tbl = Table(
            [[crest_flow, left_masthead, right_masthead]],
            colWidths=[0.68 * inch, 3.52 * inch, 2.98 * inch],
        )
    else:
        hdr_tbl = Table([[left_masthead, right_masthead]], colWidths=[4.20 * inch, 2.98 * inch])

    hdr_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(hdr_tbl)
    story.append(HRFlowable(width="100%", thickness=1.4, color=NAVY, spaceBefore=1, spaceAfter=1.5))
    story.append(HRFlowable(width="100%", thickness=0.6, color=GOLD, spaceBefore=0, spaceAfter=5))

    # 2. Court / Division Caption Banner + Document Title
    court_hdr = (snap.get("court_header") or "UNIFIED POLICE DEPARTMENT").replace("\n", "<br/>")
    title_html = (snap.get("title") or snap.get("name") or "OFFICIAL DOCUMENT").replace("\n", "<br/>")
    banner_tbl = Table(
        [
            [Paragraph(court_hdr, s_court)],
            [Paragraph(title_html, s_title)],
        ],
        colWidths=[7.18 * inch],
    )
    banner_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F0E6")),
                ("BOX", (0, 0), (-1, -1), 0.8, NAVY),
                ("LINEBELOW", (0, 0), (-1, 0), 0.4, RULE_GRAY),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(banner_tbl)
    story.append(Spacer(1, 7))

    # 3. Body paragraphs
    filled_body = core.fill_template_body(snap.get("body", ""), variables)
    blocks = filled_body.split("\n\n")
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        if all(ln.startswith("<b>") and ":" in ln[:45] for ln in lines) and len(lines) >= 2:
            rows = [[Paragraph(ln, s_meta_line)] for ln in lines]
            kv_tbl = Table(rows, colWidths=[7.18 * inch])
            kv_tbl.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.5, RULE_GRAY),
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F7F2")),
                        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(kv_tbl)
            story.append(Spacer(1, 6))
            continue

        first = lines[0]
        if first.startswith("<b>") and first.endswith("</b>") and len(lines) > 1:
            story.append(Paragraph(first, s_sec_hdr))
            rest = "<br/>".join(lines[1:])
            story.append(Paragraph(rest, s_body))
        else:
            joined = "<br/>".join(lines)
            story.append(Paragraph(joined, s_body))

    story.append(Spacer(1, 8))

    # 4. Authentication & Signatures Block
    s_sig_role = ParagraphStyle("SigRole", fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=MUTED, alignment=TA_CENTER)
    s_sig_script = ParagraphStyle("SigScript", fontName=sig_font, fontSize=23, leading=24, textColor=PEN_BLUE, alignment=TA_CENTER)
    s_sig_pending = ParagraphStyle("SigPend", fontName="Helvetica-Bold", fontSize=7.8, leading=11, textColor=STAMP_RED, alignment=TA_CENTER)
    s_sig_name = ParagraphStyle("SigName", fontName="Helvetica-Bold", fontSize=8.2, leading=10, textColor=NAVY, alignment=TA_CENTER)
    s_sig_sub = ParagraphStyle("SigSub", fontName="Times-Roman", fontSize=7.8, leading=9.5, textColor=INK, alignment=TA_CENTER)
    s_seal_cap = ParagraphStyle("SealCap", fontName="Helvetica-Bold", fontSize=6, leading=7.5, textColor=GOLD, alignment=TA_CENTER)

    issuer_col = [
        Paragraph("SUBMITTING / AFFIANT OFFICER", s_sig_role),
        Spacer(1, 3),
        Paragraph(html.escape(variables["issuer_name"]), s_sig_script),
        HRFlowable(width="88%", thickness=0.75, color=NAVY, spaceBefore=1.5, spaceAfter=2.5),
        Paragraph(html.escape(variables["issuer_name"].upper()), s_sig_name),
        Paragraph(
            f"{html.escape(variables['issuer_rank'])} · Badge #{html.escape(str(variables['issuer_badge']))}",
            s_sig_sub,
        ),
        Paragraph("Unified Police Department", s_sig_sub),
    ]

    if status == "APPROVED" and doc_record.get("approver_name"):
        approver_col = [
            Paragraph("APPROVING COMMAND AUTHORITY", s_sig_role),
            Spacer(1, 3),
            Paragraph(html.escape(variables["approver_name"]), s_sig_script),
            HRFlowable(width="88%", thickness=0.75, color=NAVY, spaceBefore=1.5, spaceAfter=2.5),
            Paragraph(html.escape(variables["approver_name"].upper()), s_sig_name),
            Paragraph(
                f"{html.escape(variables['approver_rank'])} · Badge #{html.escape(str(variables['approver_badge']))}",
                s_sig_sub,
            ),
            Paragraph(f"Counter-Signed: {created_date}", s_sig_sub),
        ]
    else:
        approver_col = [
            Paragraph("APPROVING COMMAND AUTHORITY", s_sig_role),
            Spacer(1, 10),
            Paragraph("[ AWAITING COMMAND COUNTER-SIGNATURE ]", s_sig_pending),
            Spacer(1, 5),
            HRFlowable(width="88%", thickness=0.75, color=RULE_GRAY, spaceBefore=1.5, spaceAfter=2.5),
            Paragraph("REQUIRED RANK LEVEL: " + ("COMMANDER+" if snap.get("category") == "doj" else "CORPORAL+"), s_sig_name),
            Paragraph("Unified Police Department", s_sig_sub),
        ]

    seal_col: list[Any] = []
    if SEAL_PATH.exists():
        seal_col.append(RLImage(io.BytesIO(_seal_bytes()), width=1.12 * inch, height=1.12 * inch))
        seal_col.append(Spacer(1, 1.5))
        seal_col.append(Paragraph("OFFICIAL SEAL · AUTHENTICATED", s_seal_cap))

    sig_tbl = Table(
        [[issuer_col, seal_col, approver_col]],
        colWidths=[2.74 * inch, 1.70 * inch, 2.74 * inch],
    )
    sig_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 0.6, RULE_GRAY),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAF8F1")),
            ]
        )
    )
    story.append(KeepTogether([sig_tbl]))

    meta = {"control_no": ctrl, "status": status}
    pdf_doc.build(
        story,
        onFirstPage=_draw_background_and_watermark,
        onLaterPages=_draw_background_and_watermark,
        canvasmaker=lambda *a, **kw: _NumberedOfficialCanvas(*a, doc_meta=meta, **kw),
    )
    return buf.getvalue()


def pdf_to_png(pdf_bytes: bytes, dpi: int = 180) -> bytes:
    """Rasterizes a PDF byte stream into a crisp single PNG image (stacks multi-page documents vertically)."""
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    zoom = dpi / 72.0
    mat = pymupdf.Matrix(zoom, zoom)
    pil_pages: list[Image.Image] = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        pil_pages.append(img)
    doc.close()

    if len(pil_pages) == 1:
        out_img = pil_pages[0]
    else:
        gap = 18
        total_w = max(p.width for p in pil_pages)
        total_h = sum(p.height for p in pil_pages) + gap * (len(pil_pages) - 1)
        out_img = Image.new("RGB", (total_w, total_h), (30, 35, 45))
        y = 0
        for p in pil_pages:
            out_img.paste(p, ((total_w - p.width) // 2, y))
            y += p.height + gap

    out = io.BytesIO()
    out_img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def render_document_bundle(doc_record: dict[str, Any], dpi: int = 180) -> tuple[bytes, bytes]:
    """Returns (pdf_bytes, png_bytes) for the given document record."""
    pdf_bytes = render_pdf(doc_record)
    png_bytes = pdf_to_png(pdf_bytes, dpi=dpi)
    return pdf_bytes, png_bytes
