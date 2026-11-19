import io
import os
import re
import json
import base64
import streamlit as st
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import pdfplumber
import numpy as np

try:
    from src.core.i18n import t
except ImportError:
    from core.i18n import t

# python-docx (Word) support — optional, falls back gracefully
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DocxDocument = None
    DOCX_AVAILABLE = False

# reportlab is available in this environment and used to render extracted
# docx text into a PDF so it can be cleaned & merged like a normal CV PDF.
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# PyMuPDF (fitz) is optional: guard the import
try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    fitz = None
    FITZ_AVAILABLE = False

# Arabic text shaping & RTL support
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    BIDI_AVAILABLE = True
except ImportError:
    BIDI_AVAILABLE = False

try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False

# Application Base Directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Background Template Keys ─────────────────────────────────────────────────
BG_KEYS = [
    'cv_bg_bytes', 'cv_bg_ext', 'cv_bg_name',
    'cv_bg_header_px', 'cv_bg_footer_px',
    'cv_bg_left_cm', 'cv_bg_right_cm',
    'cv_bg_cv_scale', 'cv_bg_cv_align',
]

# Supported Image Extensions
IMAGE_EXTS = ["jpg", "jpeg", "png", "webp", "bmp", "tiff", "jfif"]

# Supported Word Document Extensions (.doc binary and .docx Office Open XML)
DOC_EXTS = ["doc", "docx"]

# --- Patterns for Sensitive Data Detection ---
EMAIL_PATTERN = r'[a-zA-Z0-9._%+\u200b-]+@[a-zA-Z0-9.\u200b-]+\.[a-zA-Z]{2,}'

PHONE_PATTERNS = [
    # International with country code: +966547125873, +966 54 712 5873, +63 9...
    r'\+\d{1,4}[\s\-.\u200b]?\(?\d{1,4}\)?[\s\-.\u200b]?\d{2,4}[\s\-.\u200b]?\d{2,4}[\s\-.\u200b]?\d{2,4}',
    r'\+\d{7,15}',
    # Saudi mobile: 056 036 2968 / 0560362968 / 056-036-2968 / 05...
    r'05\d{2}[\s\-.\u200b]?\d{3}[\s\-.\u200b]?\d{3}',
    r'05\d{8}',
    # General continuous 9 to 15 digit numbers (handles international without +)
    r'(?:\+|00)?\d{9,14}',
    # Parentheses format: (+966) 56 036 2968
    r'\(\+?\d{1,4}\)[\s\-.\u200b]?\d{2,4}[\s\-.\u200b]?\d{2,4}[\s\-.\u200b]?\d{2,4}',
    # General spaced format: 56 036 2968
    r'\d{2,3}[\s\-.\u200b]\d{3}[\s\-.\u200b]\d{4}',
    # OCR-friendly spaced format with 3-digit groups: 554 978 543
    r'\d{3}[\s\-.\u200b]\d{3}[\s\-.\u200b]\d{3}',
    # International without +: 966 554 978 543
    r'\d{3}[\s\-.\u200b]\d{3}[\s\-.\u200b]\d{3}[\s\-.\u200b]\d{3}',
]

LABEL_PATTERNS = [
    r'Email\s*:', r'Email', r'E-mail\s*:', r'E-mail',
    r'Mobile No\s*\.\s*', r'Mobile No\s*', r'Mobile\s*:', r'Mobile',
    r'Phone\s*:', r'Phone', r'Tel\s*:', r'Tel',
    r'Contact\s*:', r'Contact No\s*:',
]


# ── Background Template Helpers ───────────────────────────────────────────────

def _pdf_page_to_image(pdf_bytes, dpi=150):
    """Render first page of a PDF to a PIL Image at the given DPI."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()
    return img


def _detect_header_footer_height(bg_img: Image.Image):
    """
    Auto-detect header & footer heights (in pixels) from a letterhead image
    by scanning for the last 'non-white' row from the top/bottom.
    Uses a whiteness threshold to find where the design ends.
    Returns (header_px, footer_px).
    """
    arr = np.array(bg_img.convert("RGB"))
    h, w = arr.shape[:2]

    def row_is_content(row):
        """True if the row has at least one pixel darker than threshold."""
        return bool(np.any(row < 220))

    # Scan from top → find last 'content' row in top 35% of page
    header_px = 0
    for y in range(int(h * 0.35)):
        if row_is_content(arr[y]):
            header_px = y + 1

    # Scan from bottom → find last 'content' row in bottom 25% of page
    footer_px = 0
    for y in range(h - 1, int(h * 0.75), -1):
        if row_is_content(arr[y]):
            footer_px = (h - y)

    # Add a comfortable safety margin
    header_px = int(header_px * 1.05) + 10
    footer_px = int(footer_px * 1.05) + 10

    return max(header_px, 20), max(footer_px, 20)


def _detect_horizontal_line_position(bg_img: Image.Image):
    """
    Detect the horizontal line below the header in the letterhead.
    Returns the y-position (pixels) of the line, or None if not found.
    """
    import numpy as np
    arr = np.array(bg_img.convert("RGB"))
    h, w = arr.shape[:2]

    # Scan top 40% of the page for horizontal lines
    search_h = int(h * 0.4)

    for y in range(search_h):
        row = arr[y]
        # Check if this row has a horizontal line (dark pixels spanning most of width)
        dark_pixels = np.sum(row < 200, axis=1)
        if len(dark_pixels) > 0 and np.max(dark_pixels) > w * 0.6:
            # Found a potential horizontal line
            # Verify it's continuous (not just scattered pixels)
            line_pixels = np.where(row < 200)[0]
            if len(line_pixels) > 0:
                max_gap = np.max(np.diff(line_pixels)) if len(line_pixels) > 1 else 0
                if max_gap < 50:  # Maximum gap of 50 pixels
                    return y + 1  # Return position below the line

    return None


def _calculate_content_area(bg_img: Image.Image, header_px, footer_px, line_y=None, left_cm=1.0, right_cm=1.0):
    """
    Calculate the optimal content area for placing the CV.
    If a horizontal line is detected, use it to determine margins.
    Returns (content_top, content_bottom, content_width, margin_sides_px).
    """
    w, h = bg_img.size  # PIL Image.size = (width, height); no .shape attribute

    # If line is detected, use it as the starting point
    if line_y is not None:
        content_top = line_y + int(h * 0.05)  # 5% of page height below the line
    else:
        content_top = header_px

    content_bottom = h - footer_px

    # Calculate 5 cm in pixels (assuming 150 DPI, 1 cm ≈ 59 pixels)
    cm_to_px = 59
    margin_bottom = 5 * cm_to_px  # 5 cm

    # Adjust content_bottom to leave 5 cm margin before footer
    content_bottom = min(content_bottom, h - footer_px - margin_bottom)

    # Convert cm to pixels for side margins
    left_margin_px = int(left_cm * cm_to_px)
    right_margin_px = int(right_cm * cm_to_px)

    # Content width (full width minus margins)
    content_width = w - (left_margin_px + right_margin_px)

    return content_top, content_bottom, content_width, left_margin_px


def merge_cv_on_background(cv_bytes, bg_bytes, bg_ext,
                            header_px, footer_px,
                            cv_is_pdf=False,
                            left_cm=1.0, right_cm=1.0,
                            cv_scale=1.0, cv_align='center'):
    """
    Overlay a CV (image or PDF page) onto a background letterhead image,
    respecting header_px and footer_px safe zones.

    cv_scale: multiplier applied to the fitted scale (1.0 = fit to content area,
              >1.0 = enlarge, <1.0 = shrink). Width is the primary driver.
    cv_align: horizontal placement of the scaled CV ('left', 'center', 'right').

    Returns: merged_image_bytes (PNG), merged_pdf_bytes
    """
    # ── Load background ──────────────────────────────────────────────────────
    if bg_ext == 'pdf':
        bg_img = _pdf_page_to_image(bg_bytes, dpi=150)
    else:
        bg_img = Image.open(io.BytesIO(bg_bytes)).convert("RGB")

    bg_w, bg_h = bg_img.size

    # ── Load CV page ─────────────────────────────────────────────────────────
    if cv_is_pdf and FITZ_AVAILABLE:
        cv_img = _pdf_page_to_image(cv_bytes, dpi=150)
    else:
        cv_img = Image.open(io.BytesIO(cv_bytes)).convert("RGBA")

    # ── Define safe content area on the background ───────────────────────────
    content_top = header_px
    content_bottom = bg_h - footer_px
    content_h = content_bottom - content_top

    # Apply side margins from cm to pixels
    cm_to_px = 59
    left_margin_px = int(left_cm * cm_to_px)
    right_margin_px = int(right_cm * cm_to_px)
    content_w = bg_w - (left_margin_px + right_margin_px)

    if content_h <= 0:
        content_h = max(bg_h // 2, 100)
        content_top = header_px

    # ── Scale CV to fit inside safe content area ──────────────────────────────
    cv_w, cv_h = cv_img.size
    fit_scale = min(content_w / cv_w, content_h / cv_h)
    scale = fit_scale * cv_scale
    new_w = int(cv_w * scale)
    new_h = int(cv_h * scale)

    # When aligning RIGHT and user asked to enlarge (cv_scale > 1.0),
    # let the CV expand to fill more of the available width so it is not
    # left small/narrow on the left side. Cap at content_w so it stays
    # inside the safe area, but keep the right-edge anchor.
    if cv_align == 'right' and cv_scale > 1.0 and new_w < content_w:
        # Try to grow width to fill content area while respecting height
        max_w_by_height = int(cv_w * (content_h / cv_h))
        new_w = min(max_w_by_height, content_w)
        new_h = int(cv_h * (new_w / cv_w))

    # Clamp so the CV never overflows the safe content area horizontally/vertically
    if new_w > content_w:
        new_w = content_w
        new_h = int(cv_h * (new_w / cv_w))
    if new_h > content_h:
        new_h = content_h
        new_w = int(cv_w * (new_h / cv_h))

    cv_scaled = cv_img.resize((new_w, new_h), Image.LANCZOS)

    # Position the CV horizontally according to cv_align.
    # RIGHT: anchor at right edge of content area (leaves gap on left if smaller).
    # LEFT:  anchor at left edge.
    # CENTER: centre in content area.
    if cv_align == 'right':
        paste_x = left_margin_px + content_w - new_w
    elif cv_align == 'left':
        paste_x = left_margin_px
    else:  # center
        paste_x = left_margin_px + (content_w - new_w) // 2
    paste_y = content_top

    # ── Compose ──────────────────────────────────────────────────────────────
    merged = bg_img.copy()
    if cv_scaled.mode == "RGBA":
        merged.paste(cv_scaled, (paste_x, paste_y), cv_scaled)
    else:
        merged.paste(cv_scaled.convert("RGBA"), (paste_x, paste_y))

    # Output as PNG bytes
    img_out = io.BytesIO()
    merged.save(img_out, format="PNG")
    merged_img_bytes = img_out.getvalue()

    # Output as PDF bytes
    pdf_out = io.BytesIO()
    merged.convert("RGB").save(pdf_out, format="PDF")
    merged_pdf_bytes = pdf_out.getvalue()

    return merged_img_bytes, merged_pdf_bytes


def _render_background_uploader(is_ar: bool):
    """
    Renders the background template upload section.
    Returns True when a valid background has been stored in session_state.
    """
    st.markdown("---")
    st.subheader("🖼️ " + ("رفع خلفية الورقة المؤسسية" if is_ar else "Upload Letterhead Background"))
    st.caption(
        "ارفع ورقة الشركة (PDF أو صورة) لتظهر السيرة الذاتية المنظفة فوقها مع مراعاة الترويسة والذيل." if is_ar else
        "Upload a company letterhead (PDF or image) to overlay the cleaned CV on it, respecting header & footer."
    )

    bg_uploader_col, bg_preview_col = st.columns([1, 1])

    with bg_uploader_col:
        bg_file = st.file_uploader(
            "📂 " + ("اختر ورقة الخلفية (PDF / صورة)" if is_ar else "Choose letterhead file (PDF / image)"),
            type=["pdf"] + IMAGE_EXTS,
            key="cv_bg_uploader",
            help="PDF أو JPG أو PNG..." if is_ar else "PDF or JPG or PNG..."
        )

        if bg_file is not None:
            new_name = bg_file.name
            if st.session_state.get("cv_bg_name") != new_name:
                for k in BG_KEYS + ['cv_bg_header_px', 'cv_bg_footer_px', 'cv_merged_img_bytes', 'cv_merged_pdf_bytes', 'cv_extracted_img_bytes', 'cv_extracted_pdf_bytes']:
                    st.session_state.pop(k, None)
            if "cv_bg_bytes" not in st.session_state:
                raw = bg_file.getvalue()
                ext = new_name.split(".")[-1].lower()
                st.session_state.cv_bg_bytes = raw
                st.session_state.cv_bg_ext = ext
                st.session_state.cv_bg_name = new_name

                # Auto-detect margins
                try:
                    if ext == "pdf" and FITZ_AVAILABLE:
                        bg_pil = _pdf_page_to_image(raw, dpi=72)
                    else:
                        bg_pil = Image.open(io.BytesIO(raw)).convert("RGB")
                    h_px, f_px = _detect_header_footer_height(bg_pil)
                    # Convert from 72-DPI preview to 150-DPI render coords
                    scale_factor = 150 / 72 if ext == "pdf" else 1.0
                    header_val = min(int(h_px * scale_factor), 1000)
                    footer_val = min(int(f_px * scale_factor), 1000)
                    st.session_state.cv_bg_header_px = header_val
                    st.session_state.cv_bg_footer_px = footer_val
                    # Set default side margins to 1 cm
                    st.session_state.cv_bg_left_cm = 1.0
                    st.session_state.cv_bg_right_cm = 1.0
                except Exception:
                    st.session_state.cv_bg_header_px = 195
                    st.session_state.cv_bg_footer_px = 225
                    st.session_state.cv_bg_left_cm = 1.0
                    st.session_state.cv_bg_right_cm = 1.0

        # Manual margin controls (shown when a background is loaded)
        if "cv_bg_bytes" in st.session_state:
            st.markdown("**⚙️ " + ("ضبط الهوامش" if is_ar else "Adjust margins") + "**")

            # Vertical margins (Header & Footer)
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                header_val = int(st.session_state.get("cv_bg_header_px", 195))
                header_val = min(header_val, 1000)  # Clamp to max
                st.session_state.cv_bg_header_px = st.number_input(
                    "↕️ " + ("الترويسة (بالبكسل)" if is_ar else "Header (px)"),
                    min_value=0, max_value=1000,
                    value=header_val,
                    step=5, key="cv_bg_header_input"
                )
            with m_col2:
                footer_val = int(st.session_state.get("cv_bg_footer_px", 225))
                footer_val = min(footer_val, 1000)  # Clamp to max
                st.session_state.cv_bg_footer_px = st.number_input(
                    "↕️ " + ("الذيل (بالبكسل)" if is_ar else "Footer (px)"),
                    min_value=0, max_value=1000,
                    value=footer_val,
                    step=5, key="cv_bg_footer_input"
                )

            # Horizontal margins (Left & Right in cm)
            st.markdown("**" + ("الهوامش الجانبية" if is_ar else "Side margins") + "**")
            h_col1, h_col2 = st.columns(2)
            with h_col1:
                left_cm = st.session_state.get("cv_bg_left_cm", 1.0)
                st.session_state.cv_bg_left_cm = st.number_input(
                    "⬅️ " + ("يسار (سم)" if is_ar else "Left (cm)"),
                    min_value=0.0, max_value=10.0,
                    value=left_cm,
                    step=0.1, key="cv_bg_left_cm_input"
                )
            with h_col2:
                right_cm = st.session_state.get("cv_bg_right_cm", 1.0)
                st.session_state.cv_bg_right_cm = st.number_input(
                    "➡️ " + ("يمين (سم)" if is_ar else "Right (cm)"),
                    min_value=0.0, max_value=10.0,
                    value=right_cm,
                    step=0.1, key="cv_bg_right_cm_input"
                )
            st.caption(
                "ℹ️ " + ("القيمة الافتراضية لكل من اليمين واليسار: 1 سم" if is_ar else "Default for both Right and Left: 1 cm")
            )

            # CV display size & alignment on the background
            st.markdown("**" + ("حجم السيرة الذاتية على الخلفية" if is_ar else "CV display size on background") + "**")
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                cv_scale_val = st.session_state.get("cv_bg_cv_scale", 1.0)
                st.session_state.cv_bg_cv_scale = st.slider(
                    "📏 " + ("عرض السيرة (نسبة من عرض الورقة)" if is_ar else "CV width (% of sheet width)"),
                    min_value=0.5, max_value=2.0,
                    value=cv_scale_val,
                    step=0.05,
                    help="1.00 = تعبئة عرض المنطقة المخصصة. زِد القيمة لتكبير السيرة إذا ظهرت صغيرة." if is_ar else "1.00 = fill the reserved content width. Increase if the CV appears too small/narrow.",
                    key="cv_bg_cv_scale_input"
                )
            with s_col2:
                cv_align_val = st.session_state.get("cv_bg_cv_align", "center")
                st.session_state.cv_bg_cv_align = st.selectbox(
                    "📐 " + ("محاذاة السيرة أفقياً" if is_ar else "CV horizontal alignment"),
                    options=["center", "right", "left"],
                    index=["center", "right", "left"].index(cv_align_val) if cv_align_val in ["center", "right", "left"] else 0,
                    format_func=lambda x: ("وسط" if x == "center" else ("يمين" if x == "right" else "يسار")) if is_ar else ("Center" if x == "center" else ("Right" if x == "right" else "Left")),
                    key="cv_bg_cv_align_input"
                )

            # Show auto-detection info
            st.caption("ℹ️ " + ("سيتم كشف الخط الأفقي تلقائياً وتحديد المنطقة المحجوزة (5 سم قبل الذيل)" if is_ar else "Horizontal line will be auto-detected with 5cm margin before footer"))

            if st.button(
                "🗑️ " + ("حذف الخلفية" if is_ar else "Remove background"),
                key="cv_bg_remove_btn"
            ):
                for k in BG_KEYS + ['cv_bg_header_px', 'cv_bg_footer_px', 'cv_bg_left_cm', 'cv_bg_right_cm', 'cv_merged_img_bytes', 'cv_merged_pdf_bytes', 'cv_extracted_img_bytes', 'cv_extracted_pdf_bytes']:
                    st.session_state.pop(k, None)
                st.rerun()

    with bg_preview_col:
        if "cv_bg_bytes" in st.session_state:
            st.caption("🔍 " + ("معاينة الخلفية" if is_ar else "Background preview"))
            bg_bytes = st.session_state.cv_bg_bytes
            bg_ext = st.session_state.cv_bg_ext
            if bg_ext == "pdf" and FITZ_AVAILABLE:
                preview_img = _pdf_page_to_image(bg_bytes, dpi=72)
                preview_buf = io.BytesIO()
                preview_img.save(preview_buf, format="PNG")
                st.image(preview_buf.getvalue(), use_container_width=True)
            else:
                st.image(bg_bytes, use_container_width=True)

            # Show safe-area overlay indicators
            h_px = st.session_state.get("cv_bg_header_px", 160)
            f_px = st.session_state.get("cv_bg_footer_px", 80)
            st.caption(
                f"📐 " + ("منطقة الترويسة المحجوزة" if is_ar else "Reserved header zone") +
                f": {h_px}px  |  " +
                ("الذيل" if is_ar else "Footer") + f": {f_px}px"
            )

    return "cv_bg_bytes" in st.session_state


def prepare_arabic_text(text: str) -> str:
    """Reshape and reorder Arabic text for correct RTL display in Pillow."""
    if not text:
        return ""
    has_ar = any('\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F' for c in text)
    if has_ar and BIDI_AVAILABLE:
        try:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except Exception:
            return text
    return text


def wrap_arabic_text(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> list:
    """Break text into lines that fit within max_width when rendered in RTL."""
    if not text:
        return []
    words = text.split()
    lines = []
    curr = []
    for w in words:
        trial = " ".join(curr + [w])
        prep = prepare_arabic_text(trial)
        bbox = draw.textbbox((0, 0), prep, font=font)
        w_px = bbox[2] - bbox[0]
        if w_px <= max_width or not curr:
            curr.append(w)
        else:
            lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))
    return lines


def _get_arabic_fonts():
    """Load Arabic-compatible TrueType fonts across Windows and Linux environments."""
    font_paths = [
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "tahoma.ttf"),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "tahomabd.ttf"),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arial.ttf"),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arialbd.ttf"),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "segoeui.ttf"),
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    reg_path = None
    bold_path = None
    for p in font_paths:
        if os.path.exists(p):
            lp = p.lower()
            if not reg_path and "bd" not in lp and "bold" not in lp:
                reg_path = p
            elif not bold_path and ("bd" in lp or "bold" in lp):
                bold_path = p
    if not reg_path and bold_path:
        reg_path = bold_path
    if not bold_path and reg_path:
        bold_path = reg_path

    from PIL import ImageFont
    try:
        if bold_path:
            title_font = ImageFont.truetype(bold_path, 30)
            header_font = ImageFont.truetype(bold_path, 21)
        elif reg_path:
            title_font = ImageFont.truetype(reg_path, 30)
            header_font = ImageFont.truetype(reg_path, 21)
        else:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()

        if reg_path:
            body_font = ImageFont.truetype(reg_path, 17)
            small_font = ImageFont.truetype(reg_path, 14)
        else:
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
    except Exception:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    return title_font, header_font, body_font, small_font


def _extract_profile_image(cv_bytes, is_pdf=False):
    """
    Extract profile picture from CV (PDF or Image).
    Returns PNG bytes of cropped/extracted profile photo or None.
    """
    # 1. If PDF, inspect embedded image objects first
    if is_pdf and FITZ_AVAILABLE:
        try:
            doc = fitz.open(stream=cv_bytes, filetype="pdf")
            for page_idx in range(min(len(doc), 2)):
                page = doc[page_idx]
                for img_info in page.get_images(full=True):
                    xref = img_info[0]
                    base_img = doc.extract_image(xref)
                    raw_data = base_img.get("image")
                    if not raw_data:
                        continue
                    try:
                        cand = Image.open(io.BytesIO(raw_data)).convert("RGB")
                        cw, ch = cand.size
                        if 70 <= cw <= 1400 and 70 <= ch <= 1400:
                            aspect = cw / ch
                            if 0.55 <= aspect <= 1.8:
                                arr = np.array(cand)
                                if float(arr.std()) > 20:
                                    out = io.BytesIO()
                                    cand.save(out, format="PNG")
                                    return out.getvalue()
                    except Exception:
                        pass
        except Exception as e:
            print(f"Error in PDF profile extraction: {e}")

    # 2. Render PDF to image or load image directly
    try:
        if is_pdf and FITZ_AVAILABLE:
            pil_img = _pdf_page_to_image(cv_bytes, dpi=150)
        else:
            pil_img = Image.open(io.BytesIO(cv_bytes)).convert("RGB")

        w, h = pil_img.size
        arr = np.array(pil_img)
        search_h = int(h * 0.38)

        def detect_box(x_start, x_end):
            row_stds = [arr[y, x_start:x_end].std() for y in range(search_h)]
            in_photo = False
            best_run = (0, 0)
            cur_start = 0
            for y, s in enumerate(row_stds):
                if s > 30:
                    if not in_photo:
                        in_photo = True
                        cur_start = y
                else:
                    if in_photo:
                        in_photo = False
                        if (y - cur_start) > (best_run[1] - best_run[0]):
                            best_run = (cur_start, y)
            if in_photo and (search_h - cur_start) > (best_run[1] - best_run[0]):
                best_run = (cur_start, search_h)
            y1, y2 = best_run
            if y2 - y1 < 50:
                return None
            photo_slice = arr[y1:y2, x_start:x_end]
            col_stds = [photo_slice[:, x].std() for x in range(x_end - x_start)]
            x_in = False
            x_run = (0, 0)
            cx_start = 0
            for x, s in enumerate(col_stds):
                if s > 20:
                    if not x_in:
                        x_in = True
                        cx_start = x
                else:
                    if x_in:
                        x_in = False
                        if (x - cx_start) > (x_run[1] - x_run[0]):
                            x_run = (cx_start, x)
            if x_in and (len(col_stds) - cx_start) > (x_run[1] - x_run[0]):
                x_run = (cx_start, len(col_stds))
            return (x_start + x_run[0], y1, x_start + x_run[1], y2)

        # Check Top-Left (English CV), Top-Right (Arabic CV), and Top-Center
        candidate_boxes = [
            detect_box(0, int(w * 0.45)),
            detect_box(int(w * 0.55), w),
            detect_box(int(w * 0.3), int(w * 0.7)),
        ]
        best_crop = None
        best_area = 0
        for box in candidate_boxes:
            if box and (box[2] - box[0] >= 50) and (box[3] - box[1] >= 50):
                area = (box[2] - box[0]) * (box[3] - box[1])
                if area > best_area:
                    best_area = area
                    best_crop = pil_img.crop(box)

        if best_crop:
            out = io.BytesIO()
            best_crop.save(out, format="PNG")
            return out.getvalue()
    except Exception as e:
        print(f"Error in image profile extraction: {e}")

    return None


MANUAL_TRANSLATION_MAP = {
    # Headers
    'curriculum vitae': 'سيرة ذاتية', 'resume': 'سيرة ذاتية',
    'applicant': 'المتقدمة للعمل',
    'profile summary': 'النبذة التعريفية والملخص المهني',
    'core skills': 'المهارات والقدرات الأساسية',
    'work experience': 'الخبرات المهنية وسجل العمل',
    'education': 'المؤهلات العلمية والدراسية',
    'information': 'البيانات الشخصية',
    'personal information': 'البيانات الشخصية',
    'languages': 'اللغات المتقنة',
    'duties & responsibilities': 'المهام والمسؤوليات الرئيسية',
    'duties and responsibilities': 'المهام والمسؤوليات الرئيسية',

    # Job titles
    'domestic helper': 'عاملة منزلية',
    'quality assurance': 'ضمان ومراقبة الجودة',
    'service crew': 'طاقم خدمة عملاء ومطاعم',
    'factory worker': 'عاملة إنتاج ومصانع',
    'housemaid': 'عاملة منزلية',
    'housekeeper': 'مدبرة منزل',
    'caregiver': 'مقدمة رعاية',
    'nanny': 'جليسة أطفال',
    'waitress': 'نادلة',
    'waiter': 'نادل',
    'cashier': 'كاشير',
    'teagirl': 'مقدمة شاي ومساعدة مكتبية',
    'tea girl': 'مقدمة شاي ومساعدة مكتبية',
    'office teagirl': 'مقدمة شاي ومساعدة مكتبية',

    # Complete Sentences and duties
    'dedicated and hardworking professional with experience in quality assurance, food service, and factory production environments':
        'مهنية متميزة ومجتهدة تتمتع بخبرة عملية في مجالات ضمان الجودة، وخدمات الأغذية، وبيئات الإنتاج الصناعي.',
    'skilled in quality inspection, production procedures, food handling, workplace safety, teamwork, and maintaining cleanliness and productivity standards':
        'ماهرة في فحص ومراقبة الجودة، وإجراءات خطوط الإنتاج، والتعامل الآمن مع الأغذية، والسلامة المهنية، والعمل الجماعي، والحفاظ على أعلى معايير النظافة والإنتاجية.',
    'adaptable, detail-oriented, and capable of working efficiently in fast-paced environments while following company policies and operational procedures':
        'سريعة التكيف، دقيقة في التفاصيل، وقادرة على العمل بكفاءة عالية في بيئات العمل سريعة الوتيرة مع الالتزام التام بالتعليمات والسياسات التشغيلية.',
    'performed daily household cleaning, organizing, and general housekeeping tasks':
        'القيام بأعمال التنظيف اليومي الشامل للمنزل والترتيب والتنظيم والواجبات المنزلية العامة.',
    'maintained cleanliness and sanitation of bedrooms, bathrooms, kitchen, and living areas':
        'المحافظة على نظافة وتعقيم غرف النوم والحمامات والمطبخ وصالات المعيشة بأعلى درجات العناية.',
    'prepared daily meals and assisted with food preparation according to household preferences':
        'إعداد وتحضير الوجبات اليومية والمساعدة في الطهي وتجهيز الأطعمة وفقاً لتفضيلات ورغبات الأسرة.',
    'washed, dried, folded, and organized clothes and household linens':
        'غسيل وتجفيف وكي وطي وترتيب الملابس والمفروشات المنزلية بعناية ودقة.',
    'conducted quality checking and inspection of products according to established standards':
        'إجراء فحص واختبار جودة المنتجات والتأكد من مطابقتها للمعايير والمواصفات المعتمدة.',
    'monitored product quality and identified defects, inconsistencies, and production issues':
        'مراقبة جودة المنتجات على خطوط الإنتاج ورصد أي عيوب أو ملاحظات والعمل على معالجتها.',
    'ensured products met company specifications before distribution or release':
        'التأكد من مطابقة المنتجات لكافة مواصفات الجودة قبل التعبئة والتوزيع.',
    'assisted in maintaining accurate quality inspection records and reports':
        'المساعدة في توثيق وحفظ سجلات وتقارير الفحص المخبري وفحص الجودة بدقة.',
    'followed workplace safety, sanitation, and quality control procedures':
        'الالتزام الصارم بإجراءات السلامة والصحة المهنية وضوابط النظافة ومراقبة الجودة.',
    'provided courteous and efficient customer service during daily operations':
        'تقديم خدمة عملاء راقية وسريعة ومهذبة وتلبية طلبات الزبائن بكفاءة واحترافية.',
    'assisted customers with orders and ensured accurate food and beverage preparation':
        'مساعدة العملاء في تسجيل الطلبات وضمان تحضير الأطعمة والمشروبات بالدقة المطلوبة.',
    'handled food according to proper hygiene and sanitation procedures':
        'التعامل مع المنتجات الغذائية طبقاً لأعلى اشتراطات النظافة والتعقيم وسلامة الغذاء.',
    'maintained cleanliness of dining, service, and work areas':
        'المحافظة على نظافة صالات تناول الطعام وأماكن الخدمة ومحطات العمل باستمرار.',
    'assisted with cashiering, order taking, and payment transactions when assigned':
        'المساعدة في استقبال المدفوعات والتعامل مع الكاشير وتسجيل المعاملات المالية بدقة.',
    'replenished supplies and maintained proper organization of service areas':
        'تجديد وتعبئة المستلزمات والمواد الاستهلاكية والحفاظ على ترتيب مناطق العمل.',
    'performed assigned production tasks in a chicken dressing and food processing environment':
        'تنفيذ مهام الإنتاج والتجهيز المكلفة بها في بيئة معالجة وتعبئة الدواجن والصناعات الغذائية.',
    'assisted with food preparation, processing, packing, and product handling':
        'المساعدة في إعداد وتجهيز وتعبئة وتغليف المنتجات الغذائية والتعامل معها بحرص.',
    'followed proper food safety, hygiene, sanitation, and workplace safety procedures':
        'اتباع المعايير الصحية الصارمة لسلامة الأغذية والتعقيم وإجراءات السلامة في بيئة العمل.',
    'conducted visual checking of products to identify defects or quality concerns':
        'الفحص البصري الدقيق للمنتجات لرصد أي عيوب أو ملاحظات وضمان خروجها بأفضل جودة.',
    'maintained cleanliness and proper sanitation of workstations and equipment':
        'تنظيف وتعقيم محطات العمل والآلات والأدوات المستخدمة بانتظام لمنع أي تلوث.',
    'followed production schedules, work instructions, and company standards':
        'الالتزام بجداول العمل والإنتاج والتعليمات التشغيلية المعتمدة لدى المنشأة.',
    'worked efficiently with production team members to meet daily output requirements':
        'العمل بتعاون وانسجام مع فريق الإنتاج لتحقيق المستهدفات والإنتاجية اليومية المطلوبة.',

    # Skills
    'quality assurance': 'ضمان الجودة',
    'quality inspection': 'فحص ومراقبة الجودة',
    'production operations': 'عمليات وتشغيل خطوط الإنتاج',
    'food handling': 'التعامل الآمن مع الأغذية',
    'product checking': 'فحص المنتجات والمطابقة',
    'pralice checking': 'فحص المنتجات والمطابقة',
    'quality control': 'مراقبة الجودة والاشتراطات',
    'workplace safety': 'السلامة والصحة المهنية',
    'sanitation standards': 'معايير النظافة والتعقيم',
    'production support': 'دعم ومساندة الإنتاج',
    'inventory assistance': 'المساعدة في إدارة المخزون',
    'customer service': 'خدمة العملاء والضيافة',
    'team collaboration': 'العمل الجماعي والتعاون',
    'time management': 'إدارة وتنظيم الوقت',
    'workplace organization': 'ترتيب وتنظيم بيئة العمل',
    'safety compliance': 'الامتثال لمعايير السلامة',

    # Personal info
    'date of birth': 'تاريخ الميلاد',
    'address': 'العنوان والإقامة',
    'marital status': 'الحالة الاجتماعية',
    'single': 'عزباء',
    'married': 'متزوجة',
    'filipino': 'الفلبينية',
    'english': 'الإنجليزية',
    'arabic': 'العربية',
    'high school': 'المرحلة الثانوية',
    'secondary education': 'التعليم الثانوي',
    'educational level': 'المستوى التعليمي',
    'philippines': 'الفلبين',
    'riyadh, saudi arabia': 'الرياض، المملكة العربية السعودية',
    'mohammed aldohaish': 'محمد الدهيش',
    'january': 'يناير', 'february': 'فبراير', 'march': 'مارس',
    'april': 'أبريل', 'may': 'مايو', 'june': 'يونيو',
    'july': 'يوليو', 'august': 'أغسطس', 'september': 'سبتمبر',
    'october': 'أكتوبر', 'november': 'نوفمبر', 'december': 'ديسمبر',
    'present': 'حتى الآن',
    'years': 'سنوات', 'year': 'سنة', 'months': 'أشهر', 'month': 'شهر',

    # Prepositions, verbs, linking words
    'skilled in': 'ماهرة في',
    'capable of': 'قادرة على',
    'working efficiently': 'العمل بكفاءة',
    'fast-paced': 'سريعة الوتيرة',
    'following': 'اتباع',
    'operational': 'التشغيلية',
    'policies': 'السياسات',
    'procedures': 'الإجراءات',
    'environments': 'البيئات',
    'adaptable': 'سريعة التكيف',
    'detail-oriented': 'دقيقة في التفاصيل',
    'and': 'و',
    'with': 'مع',
    'in': 'في',
    'of': 'من',
    'for': 'لـ',
    'to': 'إلى',
    'while': 'مع',
    'during': 'خلال',
    'daily': 'يومياً',
    'general': 'عامة',
    'tasks': 'المهام',
    'cleanliness': 'النظافة',
    'sanitation': 'التعقيم',
    'bedrooms': 'غرف النوم',
    'bathrooms': 'الحمامات',
    'kitchen': 'المطبخ',
    'living areas': 'صالات المعيشة',
}


_LATIN_RE = re.compile(r'[A-Za-z]')
_ARABIC_RE = re.compile(r'[\u0600-\u06FF]')
_PLACEHOLDER_RE = re.compile(r'\[?\s*(PHONE|EMAIL)\s+REMOVED\s*\]?', re.IGNORECASE)
_NAME_TOKEN = '<<<CVNAME>>>'

_TRANSLATOR_SVC = None
_TRANSLATE_CACHE = {}

_FORBIDDEN_NAME_WORDS = {
    'QUALITY', 'ASSURANCE', 'CORE', 'SKILLS', 'HIGH', 'SCHOOL', 'WORK',
    'EXPERIENCE', 'EDUCATION', 'PROFILE', 'SUMMARY', 'INFORMATION', 'DUTIES',
    'RESPONSIBILITIES', 'APPLICANT', 'CONTACT', 'PHONE', 'EMAIL', 'MOBILE',
    'ADDRESS', 'CURRICULUM', 'VITAE', 'RESUME', 'OBJECTIVE', 'PERSONAL',
    'PROFESSIONAL', 'EMPLOYMENT', 'RECORD', 'REMOVED', 'GENDER', 'NATIONALITY',
}

_JOB_KEYWORDS = [
    'domestic helper', 'housekeeper', 'housemaid', 'caregiver', 'nanny',
    'quality assurance', 'service crew', 'factory worker', 'front of house',
    'tea girl', 'teagirl', 'waitress', 'waiter', 'cashier', 'barista',
    'cook', 'chef', 'driver', 'nurse', 'teacher', 'cleaner', 'sales clerk',
    'merchandiser', 'receptionist', 'secretary', 'supervisor', 'assistant',
    'office staff', 'sales', 'helper',
]

_SECTION_RULES = [
    (['profile summary', 'professional summary', 'career objective', 'career summary',
      'objective', 'summary'], 'summary'),
    (['work experience', 'employment history', 'employment record', 'work history',
      'professional experience', 'experience'], 'experience'),
    (['core skills', 'technical skills', 'core competencies', 'competencies',
      'skills / core', 'skills'], 'skills'),
    (['education', 'academic qualifications', 'educational background',
      'academic background'], 'education'),
    (['personal information', 'personal details', 'personal info', 'information',
      'contact'], 'info'),
]


def _get_translator_svc():
    global _TRANSLATOR_SVC
    if _TRANSLATOR_SVC is False:
        return None
    if _TRANSLATOR_SVC is not None:
        return _TRANSLATOR_SVC
    try:
        try:
            from src.core.file_translator import TranslationService
        except ImportError:
            from core.file_translator import TranslationService
        _TRANSLATOR_SVC = TranslationService(source_lang='auto', target_lang='ar')
        return _TRANSLATOR_SVC
    except Exception:
        _TRANSLATOR_SVC = False
        return None


def _has_latin(text: str) -> bool:
    return bool(_LATIN_RE.search(text or ''))


def _is_mostly_arabic(text: str) -> bool:
    ar = len(_ARABIC_RE.findall(text or ''))
    la = len(_LATIN_RE.findall(text or ''))
    return ar > 0 and ar >= max(la, 1)


def _protect_name(text: str, name: str) -> str:
    if not text or not name or len(name.strip()) < 2:
        return text
    return re.sub(re.escape(name.strip()), _NAME_TOKEN, text, flags=re.IGNORECASE)


def _restore_name(text: str, name: str) -> str:
    if not text:
        return text
    restored = text.replace(_NAME_TOKEN, name or '')
    restored = re.sub(r'<<<\s*CVNAME\s*>>>', name or '', restored, flags=re.IGNORECASE)
    return restored


def translate_sentence_to_arabic(text: str, keep_name: str = '') -> str:
    """Translate English text to Arabic. Keep the candidate name in its original form."""
    clean = (text or '').strip()
    if not clean:
        return ''
    if _PLACEHOLDER_RE.fullmatch(clean):
        return ''
    if keep_name and clean.strip().lower() == keep_name.strip().lower():
        return keep_name.strip()
    if not _has_latin(clean):
        return clean

    protected = _protect_name(clean, keep_name)
    cache_key = protected.lower()
    if cache_key in _TRANSLATE_CACHE:
        return _restore_name(_TRANSLATE_CACHE[cache_key], keep_name)

    lookup = re.sub(r'\s+', ' ', protected).strip().lower().rstrip('.:;,')
    if lookup in MANUAL_TRANSLATION_MAP:
        result = MANUAL_TRANSLATION_MAP[lookup]
        _TRANSLATE_CACHE[cache_key] = result
        return _restore_name(result, keep_name)

    translated = ''
    svc = _get_translator_svc()
    if svc:
        try:
            translated = (svc.translate_text(protected) or '').strip()
            if translated and hasattr(svc, '_is_error_response') and svc._is_error_response(translated):
                translated = ''
        except Exception:
            translated = ''

    if not translated and TRANSLATOR_AVAILABLE:
        try:
            translated = (GoogleTranslator(source='auto', target='ar').translate(protected) or '').strip()
        except Exception:
            translated = ''

    if translated and _has_latin(translated) and not _is_mostly_arabic(translated):
        # Second pass for leftover English fragments (never word-swap, full sentence again)
        leftover = translated
        if svc:
            try:
                again = (svc.translate_text(leftover) or '').strip()
                if again and not (hasattr(svc, '_is_error_response') and svc._is_error_response(again)):
                    translated = again
            except Exception:
                pass

    if not translated:
        translated = protected

    translated = _restore_name(translated.strip(), keep_name)
    _TRANSLATE_CACHE[cache_key] = _protect_name(translated, keep_name)
    return translated


def _is_contact_line(text: str) -> bool:
    s = (text or '').strip()
    if not s:
        return True
    if _PLACEHOLDER_RE.search(s):
        return True
    low = s.lower()
    if '@' in s or 'mailto:' in low:
        return True
    if re.search(r'(phone|mobile|email|e-mail|tel|whatsapp)\s*[:#]', low):
        return True
    digits = re.sub(r'\D', '', s)
    letters = _LATIN_RE.findall(s) + _ARABIC_RE.findall(s)
    if len(digits) >= 8 and len(letters) <= 6:
        return True
    return False


def _is_section_header(line: str, keywords) -> bool:
    compact = re.sub(r'[^a-zA-Z\u0600-\u06FF\s/]', ' ', (line or '').lower())
    compact = re.sub(r'\s+', ' ', compact).strip(' /')
    if not compact or len(compact.split()) > 6:
        return False
    for kw in keywords:
        if compact == kw or compact.startswith(kw + ' ') or compact.endswith(' ' + kw):
            return True
        if compact.replace('/', ' ').strip() == kw:
            return True
    return False


def _detect_line_section(line: str):
    for keywords, sec in _SECTION_RULES:
        if _is_section_header(line, keywords):
            return sec
    return None


def _detect_candidate_name(lines) -> str:
    """Pick the person's name from CV lines. Never use redaction placeholders."""
    candidates = []
    for i, raw in enumerate(lines):
        s = (raw or '').strip()
        if s.upper().strip(':') == 'APPLICANT' and i > 0:
            prev = (lines[i - 1] or '').strip()
            if prev and not _is_contact_line(prev) and not _PLACEHOLDER_RE.search(prev):
                return prev
        if not s or _is_contact_line(s) or _PLACEHOLDER_RE.search(s):
            continue
        if _detect_line_section(s):
            continue
        words = [w for w in re.split(r'\s+', s.replace('.', ' ').replace(',', ' ')) if w]
        if not (2 <= len(words) <= 5):
            continue
        if any(re.sub(r'[^A-Za-z]', '', w).upper() in _FORBIDDEN_NAME_WORDS for w in words):
            continue
        letters = ''.join(ch for ch in s if ch.isalpha() or ch.isspace() or ch in ".'-")
        if len(re.sub(r'\s', '', letters)) < 6:
            continue
        if sum(ch.isdigit() for ch in s) > 2:
            continue
        if not all(re.sub(r"[^A-Za-z\u0600-\u06FF]", '', w) for w in words):
            continue
        score = 0
        if i < 8:
            score += 4
        if s.isupper() or all(w[:1].isupper() for w in words if w):
            score += 3
        if 2 <= len(words) <= 4:
            score += 2
        candidates.append((score, -i, s))

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][2]
    return ''


def _detect_job_title(lines, experience_lines) -> str:
    """Find a job title from experience first, then the rest of the CV."""
    found = []
    src = list(experience_lines or []) + list(lines or [])
    for line in src:
        low = (line or '').lower()
        for kw in _JOB_KEYWORDS:
            if kw in low and kw not in found:
                found.append(kw)
        if len(found) >= 3:
            break
    if not found:
        return ''
    english_title = ' / '.join(found[:3])
    return translate_sentence_to_arabic(english_title)


def _extract_badge_fields(lines) -> str:
    """Build personal badges from the actual CV (translated), not hardcoded values."""
    nationality = dob = marital = languages = gender = ''

    def after_label(text, labels):
        for lab in labels:
            m = re.search(rf'{re.escape(lab)}\s*[:\-]\s*(.+)', text, flags=re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ''

    for raw in lines:
        s = (raw or '').strip()
        if not s or _is_contact_line(s):
            continue
        nationality = nationality or after_label(s, ['nationality', 'الجنسية'])
        dob = dob or after_label(s, ['date of birth', 'd.o.b', 'dob', 'born', 'تاريخ الميلاد'])
        marital = marital or after_label(s, ['marital status', 'الحالة الاجتماعية'])
        languages = languages or after_label(s, ['languages', 'اللغات'])
        gender = gender or after_label(s, ['gender', 'sex', 'الجنس'])
        low = s.lower()
        if not marital and re.fullmatch(r'(single|married|divorced|widowed|عزباء|أعزب|متزوجة|متزوج)', low):
            marital = s
        if not nationality and re.fullmatch(r'(filipino|filipina|indian|nepali|bangladeshi|indonesian|ethiopian|kenyan|egyptian|saudi)', low):
            nationality = s

    badges = []
    if nationality:
        badges.append('الجنسية: ' + translate_sentence_to_arabic(nationality))
    if dob:
        badges.append('تاريخ الميلاد: ' + translate_sentence_to_arabic(dob))
    if gender:
        badges.append('الجنس: ' + translate_sentence_to_arabic(gender))
    if marital:
        badges.append('الحالة: ' + translate_sentence_to_arabic(marital))
    if languages:
        badges.append('اللغات: ' + translate_sentence_to_arabic(languages))
    return '  |  '.join(badges)


def parse_and_structure_cv(raw_lines):
    """
    Parse extracted CV lines into clean, logically-ordered semantic sections.
    All content is translated to Arabic except the candidate's name.
    """
    junk_patterns = [
        r'ocr\.space', r'get your own.*api', r'testing only',
        r'not for production', r'freekey', r'^\s*https?://\S+\s*$',
        r'^\s*[-_]{3,}\s*$'
    ]
    cleaned = []
    for l in raw_lines or []:
        s = re.sub(r'\s+', ' ', (l or '').strip())
        s = _PLACEHOLDER_RE.sub('', s).strip(' -|:/')
        if not s:
            continue
        if any(re.search(p, s, re.IGNORECASE) for p in junk_patterns):
            continue
        cleaned.append(s)

    cand_name = _detect_candidate_name(cleaned)

    summary_lines = []
    experience_lines = []
    skills_lines = []
    education_lines = []
    info_lines = []
    leftover_lines = []
    cur_sec = None

    for line in cleaned:
        s = line.strip()
        if not s:
            continue
        if cand_name and s.lower() == cand_name.lower():
            continue
        if _is_contact_line(s):
            continue

        sec = _detect_line_section(s)
        if sec:
            cur_sec = sec
            continue

        s_low = s.lower()
        if any(k in s_low for k in ['date of birth', 'd.o.b', 'marital status', 'nationality', 'languages:', 'gender:', 'sex:']):
            info_lines.append(s)
            continue

        if cur_sec == 'info':
            info_lines.append(s)
        elif cur_sec == 'summary':
            summary_lines.append(s)
        elif cur_sec == 'experience':
            experience_lines.append(s)
        elif cur_sec == 'skills':
            skills_lines.append(s)
        elif cur_sec == 'education':
            education_lines.append(s)
        else:
            leftover_lines.append(s)

    if leftover_lines:
        if not summary_lines:
            summary_lines = leftover_lines
        elif not experience_lines:
            experience_lines = leftover_lines
        else:
            experience_lines.extend(leftover_lines)

    def merge_fragments(b_lines):
        merged = []
        year_re = re.compile(r'\b(?:19|20)\d{2}\b')
        for s in b_lines:
            if not merged:
                merged.append(s)
                continue
            prev = merged[-1]
            is_prev_header = prev.isupper() or prev.endswith(':') or 'Duties' in prev
            is_curr_header = s.isupper() or s.endswith(':') or 'Duties' in s
            is_curr_bullet = s.startswith(('•', '-', '*', '–', '—'))
            has_year = bool(year_re.search(prev) or year_re.search(s))

            if (
                not is_prev_header and not is_curr_header and not is_curr_bullet
                and not has_year and len(prev) < 95
                and not prev.endswith(('.', '!', '?', ':'))
            ):
                merged[-1] = prev + ' ' + s
            else:
                merged.append(s)
        return merged

    summary_merged = merge_fragments(summary_lines)
    exp_merged = merge_fragments(experience_lines)
    skills_merged = skills_lines
    edu_merged = merge_fragments(education_lines)

    def trans_list(items):
        out = []
        for l in items:
            t = translate_sentence_to_arabic(l, keep_name=cand_name)
            if not t or _PLACEHOLDER_RE.search(t):
                continue
            if 'مهام ومسؤوليات' in t or re.search(r'\bduties\b', l, re.I):
                continue
            out.append(t)
        return out

    doc_sections = []
    if summary_merged:
        doc_sections.append(('النبذة التعريفية والملخص المهني', trans_list(summary_merged)))
    if exp_merged:
        doc_sections.append(('الخبرات المهنية وسجل العمل', trans_list(exp_merged)))
    if skills_merged:
        trans_skills = [x for x in trans_list(skills_merged) if len(x.strip()) > 2]
        grouped_skills = []
        for i in range(0, len(trans_skills), 4):
            grouped_skills.append('  •  '.join(trans_skills[i:i + 4]))
        if grouped_skills:
            doc_sections.append(('المهارات والقدرات الأساسية', grouped_skills))
    if edu_merged:
        doc_sections.append(('المؤهلات العلمية والدراسية', trans_list(edu_merged)))

    if not doc_sections and cleaned:
        body = [s for s in cleaned if not cand_name or s.lower() != cand_name.lower()]
        body = [s for s in body if not _is_contact_line(s)]
        trans_body = trans_list(merge_fragments(body))
        if trans_body:
            doc_sections.append(('المحتوى المهني', trans_body))

    badge_str = _extract_badge_fields(cleaned + info_lines)
    job_ar = _detect_job_title(cleaned, exp_merged)
    display_title = ('المسمى الوظيفي: ' + job_ar) if job_ar else ''
    display_name = cand_name or ''

    return display_name, display_title, badge_str, doc_sections


def extract_cv_text_lines(cv_bytes, is_pdf=False):
    """Extract raw text lines from CV (PDF or Image) cleanly."""
    lines = []
    if is_pdf and FITZ_AVAILABLE:
        try:
            doc = fitz.open(stream=cv_bytes, filetype="pdf")
            for page in doc:
                t = page.get_text()
                if t:
                    for raw in t.splitlines():
                        s = raw.strip()
                        if s:
                            lines.append(s)
        except Exception as e:
            print(f"Error extracting PDF text: {e}")

    if len(lines) < 3:
        img_bytes = None
        if is_pdf and FITZ_AVAILABLE:
            try:
                pimg = _pdf_page_to_image(cv_bytes, dpi=150)
                buf = io.BytesIO()
                pimg.save(buf, format="PNG")
                img_bytes = buf.getvalue()
            except Exception:
                pass
        else:
            img_bytes = cv_bytes

        if img_bytes:
            res = extract_text_and_boxes_from_image(img_bytes, "cv.jpg")
            text = res.get("text", "")
            if text:
                for l in text.splitlines():
                    s = l.strip()
                    if s:
                        lines.append(s)

    return lines


def _render_text_on_background(text_lines, bg_bytes, bg_ext, header_px, footer_px, profile_img_bytes=None, left_cm=1.0, right_cm=1.0):
    """
    Render formatted Arabic text lines on background with candidate photo on the LEFT.
    Ensures clear font sizes, no overlapping with photo, and strict margin containment.
    Returns merged image bytes (PNG) and PDF bytes.
    """
    if bg_ext == 'pdf':
        bg_img = _pdf_page_to_image(bg_bytes, dpi=150)
    else:
        bg_img = Image.open(io.BytesIO(bg_bytes)).convert("RGB")

    bg_w, bg_h = bg_img.size

    # Detect horizontal line position
    line_y = _detect_horizontal_line_position(bg_img)

    # Calculate optimal content area (safe zone)
    content_top, content_bottom, content_width, left_margin_px = _calculate_content_area(
        bg_img, header_px, footer_px, line_y, left_cm, right_cm
    )

    draw = ImageDraw.Draw(bg_img)
    title_font, header_font, body_font, small_font = _get_arabic_fonts()

    cm_to_px = 59
    content_left = max(int(left_cm * cm_to_px), 45)
    content_right = bg_w - max(int(right_cm * cm_to_px), 45)
    right_x = content_right - 10

    # 1. Candidate Profile Photo on the LEFT
    photo_w = 145
    photo_h = 165
    photo_x = content_left + 15
    photo_y = content_top + 15
    photo_bottom = photo_y + photo_h

    if profile_img_bytes:
        try:
            pimg = Image.open(io.BytesIO(profile_img_bytes)).convert("RGB")
            pimg = pimg.resize((photo_w, photo_h), Image.LANCZOS)
            mask = Image.new("L", (photo_w, photo_h), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([(0, 0), (photo_w, photo_h)], radius=12, fill=255)
            bg_img.paste(pimg, (photo_x, photo_y), mask)
            draw.rounded_rectangle(
                [(photo_x - 2, photo_y - 2), (photo_x + photo_w + 2, photo_y + photo_h + 2)],
                radius=14, outline=(24, 52, 94), width=3
            )
        except Exception as e:
            print(f"Error drawing profile photo: {e}")
            profile_img_bytes = None

    # Parse and structure semantic sections
    cand_name, cand_title, badge_str, doc_sections = parse_and_structure_cv(text_lines)

    # 2. Candidate Header beside photo on the RIGHT (RTL zone)
    top_left_limit = photo_x + photo_w + 35
    top_available_w = right_x - top_left_limit
    cur_y = photo_y + 10

    # Candidate Name (Bold 30px, Dark Navy)
    name_prep = prepare_arabic_text(cand_name)
    bbox = draw.textbbox((0, 0), name_prep, font=title_font)
    nw = bbox[2] - bbox[0]
    draw.text((right_x - min(nw, top_available_w), cur_y), name_prep, fill=(24, 52, 94), font=title_font)
    cur_y += 42

    # Candidate Job Title (Bold 21px, Bronze Gold)
    title_prep = prepare_arabic_text(cand_title)
    bbox = draw.textbbox((0, 0), title_prep, font=header_font)
    tw = bbox[2] - bbox[0]
    draw.text((right_x - min(tw, top_available_w), cur_y), title_prep, fill=(180, 110, 25), font=header_font)
    cur_y += 36

    # Personal Badges (14px, Dark Grey)
    badge_prep = prepare_arabic_text(badge_str)
    bbox = draw.textbbox((0, 0), badge_prep, font=small_font)
    bw = bbox[2] - bbox[0]
    draw.text((right_x - min(bw, top_available_w), cur_y), badge_prep, fill=(80, 80, 80), font=small_font)
    cur_y += 30

    # 3. Main Body Sections start STRICTLY BELOW the photo
    if profile_img_bytes:
        cur_y = max(cur_y + 15, photo_bottom + 30)
    else:
        cur_y += 25

    full_w = right_x - (content_left + 15)

    line_height_body = 26
    line_height_header = 36

    for sec_title, items in doc_sections:
        if cur_y + line_height_header > content_bottom:
            break

        # Draw Section Header (NO MISSING GLYPH EMOJI BOXES!)
        prep_hdr = prepare_arabic_text(sec_title)
        bbox = draw.textbbox((0, 0), prep_hdr, font=header_font)
        hw = bbox[2] - bbox[0]
        draw.text((right_x - min(hw, full_w), cur_y), prep_hdr, fill=(24, 52, 94), font=header_font)
        draw.line([(content_left + 15, cur_y + 26), (right_x, cur_y + 26)], fill=(195, 215, 235), width=2)
        cur_y += line_height_header

        # Draw items
        for it in items:
            s_item = it.strip()
            if not s_item:
                continue

            # Format bullet points
            bullet_s = '• ' + s_item if not s_item.startswith(('•', '-', '*', '–', '—')) else s_item
            wrapped = wrap_arabic_text(bullet_s, body_font, full_w, draw)
            for wline in wrapped:
                if cur_y + line_height_body > content_bottom:
                    break
                prep_line = prepare_arabic_text(wline)
                bbox = draw.textbbox((0, 0), prep_line, font=body_font)
                lw = bbox[2] - bbox[0]
                draw.text((right_x - min(lw, full_w), cur_y), prep_line, fill=(35, 35, 35), font=body_font)
                cur_y += line_height_body
            cur_y += 3
        cur_y += 8

    # Output as PNG bytes
    img_out = io.BytesIO()
    bg_img.save(img_out, format="PNG")
    merged_img_bytes = img_out.getvalue()

    # Output as PDF bytes
    pdf_out = io.BytesIO()
    bg_img.convert("RGB").save(pdf_out, format="PDF")
    merged_pdf_bytes = pdf_out.getvalue()

    return merged_img_bytes, merged_pdf_bytes


def _render_merge_section(is_ar: bool):
    """
    Renders the 'Merge CV on Background' action button and result display.
    Should only be called when both a cleaned CV and a background exist.
    """
    st.markdown("---")
    st.subheader("🔗 " + ("دمج السيرة الذاتية مع الخلفية" if is_ar else "Merge CV with Letterhead"))

    if st.button(
        "🖨️ " + ("دمج وعرض السيرة على ورقة الشركة" if is_ar else "Overlay CV on Company Letterhead"),
        type="primary", width="stretch", key="cv_merge_btn"
    ):
        try:
            bg_bytes = st.session_state.cv_bg_bytes
            bg_ext = st.session_state.cv_bg_ext
            header_px = min(int(st.session_state.get("cv_bg_header_px", 160)), 1000)
            footer_px = min(int(st.session_state.get("cv_bg_footer_px", 80)), 1000)
            left_cm = st.session_state.get("cv_bg_left_cm", 1.0)
            right_cm = st.session_state.get("cv_bg_right_cm", 1.0)
            cv_scale = st.session_state.get("cv_bg_cv_scale", 1.0)
            cv_align = st.session_state.get("cv_bg_cv_align", "center")

            # Determine CV source bytes and type
            if "cv_cleaned_image_bytes" in st.session_state:
                cv_bytes = st.session_state.cv_cleaned_image_bytes
                cv_is_pdf = False
            elif "cv_cleaned_pdf_bytes" in st.session_state:
                cv_bytes = st.session_state.cv_cleaned_pdf_bytes
                cv_is_pdf = True
            else:
                st.warning("⚠️ " + ("يرجى تنظيف السيرة الذاتية أولاً." if is_ar else "Please clean the CV first."))
                return

            with st.spinner("⏳ " + ("جارٍ الدمج..." if is_ar else "Merging...")):
                merged_img_bytes, merged_pdf_bytes = merge_cv_on_background(
                    cv_bytes, bg_bytes, bg_ext, header_px, footer_px, cv_is_pdf=cv_is_pdf,
                    left_cm=left_cm, right_cm=right_cm,
                    cv_scale=cv_scale, cv_align=cv_align
                )
                st.session_state.cv_merged_img_bytes = merged_img_bytes
                st.session_state.cv_merged_pdf_bytes = merged_pdf_bytes

            st.success("✅ " + ("تم الدمج بنجاح!" if is_ar else "Merged successfully!"))
        except Exception as e:
            st.error(("خطأ أثناء الدمج: " if is_ar else "Merge error: ") + str(e))

    # Only show download buttons if merged result exists
    if "cv_merged_img_bytes" in st.session_state:
        st.image(
            st.session_state.cv_merged_img_bytes,
            caption="🖼️ " + ("السيرة الذاتية على الخلفية المؤسسية" if is_ar else "CV on Company Letterhead"),
            use_container_width=True
        )
        dl1, dl2 = st.columns(2)
        base_name = os.path.splitext(st.session_state.get("cv_file_name", "cv"))[0]
        with dl1:
            st.download_button(
                label="⬇️ " + ("تحميل كصورة PNG" if is_ar else "Download as PNG"),
                data=st.session_state.cv_merged_img_bytes,
                file_name=f"letterhead_{base_name}.png",
                mime="image/png",
                width="stretch",
                key="cv_dl_merged_png"
            )
        with dl2:
            st.download_button(
                label="⬇️ " + ("تحميل كـ PDF" if is_ar else "Download as PDF"),
                data=st.session_state.cv_merged_pdf_bytes,
                file_name=f"letterhead_{base_name}.pdf",
                mime="application/pdf",
                width="stretch",
                key="cv_dl_merged_pdf"
            )

    # New button: Extract text and profile, render on background
    st.markdown("---")
    st.subheader("📝 " + ("تفريغ النص والبروفيل على الخلفية" if is_ar else "Extract Text & Profile on Background"))
    st.caption(
        "استخراج النص وصورة البروفيل من السيرة الذاتية وعرضها على ورقة الخلفية بدون خلفية السيرة الأصلية." if is_ar else
        "Extract text and profile picture from CV and display on letterhead without original CV background."
    )

    if st.button(
        "✨ " + ("تفريغ الكلمات والصورة على ورقة الخلفية" if is_ar else "Extract Text & Profile on Letterhead"),
        type="primary", width="stretch", key="cv_extract_render_btn"
    ):
        try:
            if "cv_bg_bytes" not in st.session_state:
                st.warning("⚠️ " + ("يرجى رفع ورقة الخلفية أولاً." if is_ar else "Please upload background first."))
                return

            # Get CV bytes
            if "cv_image_bytes" in st.session_state:
                cv_bytes = st.session_state.cv_image_bytes
            elif "cv_pdf_bytes" in st.session_state:
                cv_bytes = st.session_state.cv_pdf_bytes
            else:
                st.warning("⚠️ " + ("يرجى رفع السيرة الذاتية أولاً." if is_ar else "Please upload CV first."))
                return

            bg_bytes = st.session_state.cv_bg_bytes
            bg_ext = st.session_state.cv_bg_ext
            header_px = min(int(st.session_state.get("cv_bg_header_px", 160)), 1000)
            footer_px = min(int(st.session_state.get("cv_bg_footer_px", 80)), 1000)
            left_cm = st.session_state.get("cv_bg_left_cm", 1.0)
            right_cm = st.session_state.get("cv_bg_right_cm", 1.0)

            cv_is_pdf = ('cv_pdf_bytes' in st.session_state and cv_bytes == st.session_state.get('cv_pdf_bytes'))
            with st.spinner("⏳ " + ("جارٍ استخراج وتنسيق النص وصورة البروفيل بالعربية..." if is_ar else "Extracting text and profile in Arabic...")):
                # 1. Extract text lines (handles both PDF direct extraction and OCR)
                raw_lines = extract_cv_text_lines(cv_bytes, is_pdf=cv_is_pdf)

                # 2. Privacy cleaning: strip phone numbers and emails
                cleaned_lines = []
                total_phones = 0
                total_emails = 0
                for line in raw_lines:
                    cl, p, e, _ = remove_emails_and_phones_from_text(line)
                    total_phones += len(p)
                    total_emails += len(e)
                    cl = _PLACEHOLDER_RE.sub(' ', cl)
                    cl = re.sub(r'\s+', ' ', cl).strip(' -|:/')
                    if cl:
                        cleaned_lines.append(cl)

                # 3. Extract candidate profile photo (from PDF objects or image crop)
                profile_img = _extract_profile_image(cv_bytes, is_pdf=cv_is_pdf)

                # 4. Render onto letterhead (parse_and_structure_cv translates/formats to Arabic)
                merged_img_bytes, merged_pdf_bytes = _render_text_on_background(
                    cleaned_lines, bg_bytes, bg_ext, header_px, footer_px, profile_img,
                    left_cm=left_cm, right_cm=right_cm
                )
                st.session_state.cv_extracted_img_bytes = merged_img_bytes
                st.session_state.cv_extracted_pdf_bytes = merged_pdf_bytes

                if total_phones > 0 or total_emails > 0:
                    stats = []
                    if total_phones > 0:
                        stats.append(f"📞 {total_phones} " + ("رقم" if is_ar else "number(s)"))
                    if total_emails > 0:
                        stats.append(f"✉️ {total_emails} " + ("إيميل" if is_ar else "email(s)"))
                    st.info("✅ " + ("تم حجب بيانات التواصل: " if is_ar else "Removed: ") + " | ".join(stats))

            st.success("✅ " + ("تم الاستخراج والعرض بنجاح!" if is_ar else "Extracted and rendered successfully!"))
        except Exception as e:
            st.error(("خطأ أثناء الاستخراج: " if is_ar else "Extraction error: ") + str(e))

    # Only show download buttons if extracted result exists
    if "cv_extracted_img_bytes" in st.session_state:
        st.image(
            st.session_state.cv_extracted_img_bytes,
            caption="📝 " + ("النص المستخرج على الخلفية" if is_ar else "Extracted Text on Background"),
            use_container_width=True
        )
        dl1, dl2 = st.columns(2)
        base_name = os.path.splitext(st.session_state.get("cv_file_name", "cv"))[0]
        with dl1:
            st.download_button(
                label="⬇️ " + ("تحميل كصورة PNG" if is_ar else "Download as PNG"),
                data=st.session_state.cv_extracted_img_bytes,
                file_name=f"extracted_{base_name}.png",
                mime="image/png",
                width="stretch",
                key="cv_dl_extracted_png"
            )
        with dl2:
            st.download_button(
                label="⬇️ " + ("تحميل كـ PDF" if is_ar else "Download as PDF"),
                data=st.session_state.cv_extracted_pdf_bytes,
                file_name=f"extracted_{base_name}.pdf",
                mime="application/pdf",
                width="stretch",
                key="cv_dl_extracted_pdf"
            )


def _load_image_clean(img_bytes):
    """Load image, correct EXIF orientation, and ensure standard color mode."""
    img = Image.open(io.BytesIO(img_bytes))
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')
    return img

def remove_emails_and_phones_from_text(text):
    """Remove emails, phone numbers, and their labels from text."""
    cleaned = text
    phones_found = []
    emails_found = []
    labels_found = []

    # Remove labels first
    for pattern in LABEL_PATTERNS:
        matches = re.findall(pattern, cleaned, flags=re.IGNORECASE)
        for match in sorted(set(matches), key=len, reverse=True):
            if match not in labels_found:
                labels_found.append(match)
            cleaned = cleaned.replace(match, "")

    # Find and remove emails
    emails_found = re.findall(EMAIL_PATTERN, cleaned)
    for email in sorted(set(emails_found), key=len, reverse=True):
        cleaned = cleaned.replace(email, "[EMAIL REMOVED]")

    # Find and remove phones (longest matches first)
    all_phones = []
    for pattern in PHONE_PATTERNS:
        matches = re.findall(pattern, cleaned)
        for match in matches:
            if match not in all_phones:
                all_phones.append(match)
    for phone in sorted(set(all_phones), key=len, reverse=True):
        if phone not in phones_found:
            phones_found.append(phone)
        cleaned = cleaned.replace(phone, "[PHONE REMOVED]")

    return cleaned, phones_found, emails_found, labels_found

def clean_pdf_preserve_format(pdf_bytes):
    """Remove emails and phone numbers from PDF while preserving images, fonts, layout, and formatting.
    Returns cleaned PDF bytes."""
    if not FITZ_AVAILABLE:
        raise RuntimeError("PyMuPDF (fitz) is not installed in this environment; PDF format-preserving cleaning is unavailable.")
    fitz_module = fitz
    doc = fitz_module.open(stream=pdf_bytes, filetype="pdf")
    total_emails = 0
    total_phones = 0

    for page_num in range(len(doc)):
        page = doc[page_num]

        # ── Also redact link annotations (clickable hyperlinks like mailto:) ──
        try:
            for link in page.get_links() or []:
                link_uri = link.get("uri", "") or ""
                if "@" in link_uri or "mailto:" in link_uri.lower():
                    rect = fitz_module.Rect(link.get("from", link.get("rect", [0, 0, 0, 0])))
                    page.add_redact_annot(rect, fill=(1, 1, 1))
                    total_emails += 1
        except Exception:
            pass

        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                line_has_email = False
                line_bbox = line.get("bbox", None)
                for span in line.get("spans", []):
                    span_text = span.get("text", "")
                    span_bbox = span.get("bbox", None)

                    # ── Emails: aggressive — if ANY span in the line has '@', redact the whole line ──
                    has_email = ("@" in span_text) or bool(re.findall(EMAIL_PATTERN, span_text))
                    if has_email and line_bbox:
                        rect = fitz_module.Rect(line_bbox)
                        page.add_redact_annot(rect, fill=(1, 1, 1))
                        total_emails += 1
                        line_has_email = True
                        break  # line redacted; move to next line

                    # ── Phones ── (only if this span/line is not an email line)
                    if not line_has_email:
                        phones_in_span = []
                        for pattern in PHONE_PATTERNS:
                            phones_in_span.extend(re.findall(pattern, span_text))
                        for phone in sorted(set(phones_in_span), key=len, reverse=True):
                            instances = page.search_for(phone)
                            if instances:
                                for inst in instances:
                                    rect = fitz_module.Rect(inst)
                                    page.add_redact_annot(rect, fill=(1, 1, 1))
                                    total_phones += 1
                            elif span_bbox:
                                rect = fitz_module.Rect(span_bbox)
                                page.add_redact_annot(rect, fill=(1, 1, 1))
                                total_phones += 1

    if total_emails > 0 or total_phones > 0:
        for page_num in range(len(doc)):
            page = doc[page_num]
            page.apply_redactions()

    output = io.BytesIO()
    doc.save(output, garbage=4, deflate=True)
    doc.close()
    output.seek(0)
    return output.read(), total_emails, total_phones

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF using pdfplumber."""
    text_parts = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


# --- Word (.doc / .docx) → Text / PDF helpers ---

def _docx_to_text(docx_bytes):
    """Extract all text from a .docx file using python-docx (paragraphs + tables)."""
    if not DOCX_AVAILABLE:
        return ""
    try:
        doc = DocxDocument(io.BytesIO(docx_bytes))
        parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n".join(parts)
    except Exception:
        return ""


def _is_doc_binary(data):
    """Quick check whether bytes look like a legacy .doc (OLE Compound File) header."""
    return data[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'


def text_to_pdf_bytes(text, title="CV"):
    """Render plain text into a clean A4 PDF using reportlab."""
    try:
        buffer = io.BytesIO()
        styles = getSampleStyleSheet()
        style = styles["Normal"]
        style.fontName = "Helvetica"
        style.fontSize = 11
        style.leading = 16
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
            title=title,
        )
        story = []
        for line in text.split("\n"):
            if line.strip():
                story.append(Paragraph(line, style))
            story.append(Spacer(1, 6))
        doc.build(story)
        buffer.seek(0)
        return buffer.read()
    except Exception:
        return b""


def doc_to_pdf(file_bytes, filename="cv.doc"):
    """
    Convert a Word file (.doc or .docx) to PDF bytes.
    - .docx: extracted via python-docx then rendered to PDF.
    - .doc (legacy binary): requires LibreOffice/antiword which are not
      available in this environment — returns empty bytes and a flag so the UI
      can show a helpful message asking the user to re-save as .docx.
    Returns (pdf_bytes, extracted_text, is_convertible).
    """
    name_lower = filename.lower()

    if name_lower.endswith(".docx"):
        if not DOCX_AVAILABLE:
            return b"", "", False
        text = _docx_to_text(file_bytes)
        if not text or not text.strip():
            return b"", "", False
        pdf_bytes = text_to_pdf_bytes(text, title=os.path.splitext(filename)[0])
        return pdf_bytes, text, True

    if name_lower.endswith(".doc"):
        # Legacy binary .doc — python-docx cannot read it.
        if _is_doc_binary(file_bytes):
            return b"", "", False  # not convertible without LibreOffice
        # Not a real .doc binary; try treating as docx anyway
        text = _docx_to_text(file_bytes)
        if text and text.strip():
            pdf_bytes = text_to_pdf_bytes(text, title=os.path.splitext(filename)[0])
            return pdf_bytes, text, True
        return b"", "", False

    return b"", "", False


# --- Multi-Tier Image OCR Extraction ---

def _get_pytesseract():
    """Detect and configure PyTesseract with standard Windows paths."""
    try:
        import pytesseract
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
            os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
        ]
        for c in candidates:
            if os.path.exists(c):
                pytesseract.pytesseract.tesseract_cmd = c
                break
        return pytesseract
    except Exception:
        return None

def _ocr_pytesseract(img_bytes):
    """Tier 1: Local PyTesseract OCR."""
    pyt = _get_pytesseract()
    if not pyt:
        return None
    try:
        img = _load_image_clean(img_bytes)
        data = pyt.image_to_data(img, output_type=pyt.Output.DICT)
        text = pyt.image_to_string(img)
        words = []
        # Group words by (block, par, line) so we can reconstruct full line text
        line_groups = {}
        for i in range(len(data.get('text', []))):
            t_word = data['text'][i].strip()
            if not t_word:
                continue
            block = data['block_num'][i]
            par = data['par_num'][i]
            line_num = data['line_num'][i]
            key = (block, par, line_num)
            if key not in line_groups:
                line_groups[key] = []
            line_groups[key].append({
                'text': t_word,
                'left': int(data['left'][i]),
                'top': int(data['top'][i]),
                'width': int(data['width'][i]),
                'height': int(data['height'][i]),
            })
        # Flatten with full line text attached to each word
        for key, wlist in line_groups.items():
            line_text = ' '.join(w['text'] for w in wlist)
            for w in wlist:
                w['line'] = line_text
                words.append(w)
        return {'text': text, 'words': words}
    except Exception:
        return None

def _ocr_space(img_bytes, filename="cv_img.jpg"):
    """Tier 2: OCR.space Free High-Accuracy API with Word Bounding Boxes."""
    import requests
    keys = ["K87899142388957", "helloworld"]
    for key in keys:
        try:
            payload = {
                'apikey': key,
                'language': 'eng',
                'isOverlayRequired': True,
                'detectOrientation': True,
                'scale': True,
                'OCREngine': 2
            }
            files = {'file': (filename, img_bytes, 'image/jpeg')}
            res = requests.post('https://api.ocr.space/parse/image', files=files, data=payload, timeout=12)
            if res.status_code == 200:
                d = res.json()
                if not d.get('IsErroredOnProcessing') and d.get('ParsedResults'):
                    p0 = d['ParsedResults'][0]
                    full_text = p0.get('ParsedText', '')
                    overlay = p0.get('TextOverlay', {})
                    lines = overlay.get('Lines', [])
                    words = []
                    for l in lines:
                        l_txt = l.get('LineText', '')
                        for w in l.get('Words', []):
                            words.append({
                                'text': w.get('WordText', ''),
                                'left': int(w.get('Left', 0)),
                                'top': int(w.get('Top', 0)),
                                'width': int(w.get('Width', 0)),
                                'height': int(w.get('Height', 0)),
                                'line': l_txt
                            })
                    if full_text.strip():
                        return {'text': full_text, 'words': words}
        except Exception:
            continue
    return None

def _ocr_google_vision(img_bytes):
    """Tier 3: Google Cloud Vision API using local credentials.json if enabled."""
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests
        import requests
        creds_path = os.path.join(BASE_DIR, "credentials.json")
        if not os.path.exists(creds_path):
            return None
        scopes = ['https://www.googleapis.com/auth/cloud-vision']
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
        req = google.auth.transport.requests.Request()
        creds.refresh(req)
        b64 = base64.b64encode(img_bytes).decode('utf-8')
        res = requests.post(
            "https://vision.googleapis.com/v1/images:annotate",
            headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
            json={"requests": [{"image": {"content": b64}, "features": [{"type": "TEXT_DETECTION"}]}]},
            timeout=10
        )
        if res.status_code == 200:
            data = res.json()
            ann = data.get('responses', [{}])[0].get('textAnnotations', [])
            if ann:
                full_text = ann[0].get('description', '')
                words = []
                for a in ann[1:]:
                    verts = a.get('boundingPoly', {}).get('vertices', [])
                    if len(verts) >= 4:
                        xs = [v.get('x', 0) for v in verts]
                        ys = [v.get('y', 0) for v in verts]
                        l = min(xs); t = min(ys)
                        w = max(xs) - l; h = max(ys) - t
                        words.append({
                            'text': a.get('description', ''),
                            'left': int(l), 'top': int(t), 'width': int(w), 'height': int(h),
                            'line': a.get('description', '')
                        })
                return {'text': full_text, 'words': words}
    except Exception:
        pass
    return None

def extract_text_and_boxes_from_image(img_bytes, filename="cv.jpg"):
    """Multi-tier OCR pipeline for images."""
    res = _ocr_pytesseract(img_bytes)
    if res and res.get('text', '').strip():
        return res
    res = _ocr_space(img_bytes, filename)
    if res and res.get('text', '').strip():
        return res
    res = _ocr_google_vision(img_bytes)
    if res and res.get('text', '').strip():
        return res
    return {'text': '', 'words': []}

def redact_image_sensitive_data(img_bytes, sensitive_boxes, file_ext="jpg"):
    """
    Mask sensitive bounding boxes on image cleanly with matching background color.
    Returns: (cleaned_image_bytes, cleaned_pdf_bytes)
    """
    img = _load_image_clean(img_bytes)
    draw = ImageDraw.Draw(img)
    img_w, img_h = img.size

    for box in sensitive_boxes:
        left = max(0, int(box.get('left', 0)) - 4)
        top = max(0, int(box.get('top', 0)) - 3)
        right = min(img_w, int(box.get('left', 0) + box.get('width', 0)) + 4)
        bottom = min(img_h, int(box.get('top', 0) + box.get('height', 0)) + 3)

        if right <= left or bottom <= top:
            continue

        bg_color = (255, 255, 255)
        try:
            # Sample color from the edge to blend with original background
            sample_x = max(0, left - 6)
            sample_y = max(0, min(img_h - 1, top + (bottom - top) // 2))
            c = img.getpixel((sample_x, sample_y))
            if isinstance(c, tuple):
                bg_color = c[:3]
            elif isinstance(c, int):
                bg_color = (c, c, c)
        except Exception:
            bg_color = (255, 255, 255)

        draw.rectangle([left, top, right, bottom], fill=bg_color)

    # Output as Image bytes
    img_out = io.BytesIO()
    if file_ext.lower() in ['png', 'webp']:
        img.save(img_out, format='PNG')
    else:
        img.convert('RGB').save(img_out, format='JPEG', quality=95)
    cleaned_img_bytes = img_out.getvalue()

    # Output as PDF bytes (wraps clean image inside crisp PDF document)
    pdf_out = io.BytesIO()
    img.convert('RGB').save(pdf_out, format='PDF', quality=95)
    cleaned_pdf_bytes = pdf_out.getvalue()

    return cleaned_img_bytes, cleaned_pdf_bytes

# --- Main UI Function ---

def render_cv_privacy_cleaner_content():
    """CV Privacy Cleaner: Fully handles both PDF documents and all image files."""
    lang = st.session_state.lang
    is_ar = lang == 'ar'

    st.title("🔒 " + t("cv_privacy_title", lang))
    st.markdown(t("cv_privacy_desc", lang))
    st.divider()

    st.info("ℹ️ " + ("هذا القسم يدعم تنظيف ملفات PDF وجميع أنواع الصور (JPG, PNG, JPEG, WEBP, BMP) بالإضافة إلى ملفات وورد (DOCX) التي يتم تحويلها إلى PDF. يتم حذف أرقام الهواتف والإيميلات مع الحفاظ على التنسيق الأصلي والتصميم بالكامل، ويمكن عرض السيرة على ورقة الشركة (الخلفية المؤسسية)." if is_ar else "This tool supports PDF files and all image formats (JPG, PNG, JPEG, WEBP, BMP) plus Word files (DOCX) which are converted to PDF. Phone numbers and email addresses are cleanly removed while preserving original format and design, and the CV can be displayed on the company letterhead background."))
    if not FITZ_AVAILABLE:
        st.warning("⚠️ " + ("PyMuPDF (fitz) غير مثبت في هذه البيئة، لذا تنظيف PDF الذي يحافظ على التنسيق غير متوفر. يرجى استخدام تنظيف الصور أو تنظيف النص فقط." if is_ar else "PyMuPDF (fitz) is not installed in this environment."))

    # Background uploader section
    has_background = _render_background_uploader(is_ar)

    st.divider()

    # File uploader supporting PDF and ALL image formats
    uploaded_file = st.file_uploader(
        t("cv_upload_label", lang),
        type=["pdf"] + IMAGE_EXTS + DOC_EXTS,
        help=t("cv_upload_help", lang)
    )

    if uploaded_file is not None:
        file_ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ''
        is_pdf = file_ext == "pdf"
        is_image = file_ext in IMAGE_EXTS
        is_doc = file_ext in DOC_EXTS

        # Clear old session state when a new CV file is uploaded.
        # IMPORTANT: do NOT clear anything in BG_KEYS so the uploaded
        # letterhead background and its margin/scale/align settings are kept.
        if st.session_state.get('cv_last_file_name') != uploaded_file.name:
            for k in [
                'cv_original_text', 'cv_cleaned_text', 'cv_phones_count', 'cv_emails_count',
                'cv_labels_count', 'cv_file_ext', 'cv_file_name', 'cv_last_file_name',
                'cv_pdf_bytes', 'cv_cleaned_pdf_bytes', 'cv_image_bytes',
                'cv_cleaned_image_bytes', 'cv_image_boxes', 'cv_detected_phones',
                'cv_detected_emails', 'cv_ocr_done',
                'cv_merged_img_bytes', 'cv_merged_pdf_bytes',
                'cv_extracted_img_bytes', 'cv_extracted_pdf_bytes',
            ]:
                st.session_state.pop(k, None)

            st.session_state.cv_last_file_name = uploaded_file.name
            st.session_state.cv_file_ext = file_ext
            st.session_state.cv_file_name = uploaded_file.name

        raw_bytes = uploaded_file.getvalue()

        # Convert Word (.doc / .docx) to PDF so it can be cleaned & merged like a normal CV PDF
        if is_doc and DOCX_AVAILABLE and 'cv_pdf_bytes' not in st.session_state:
            with st.spinner("جاري تحويل ملف وورد إلى PDF..." if is_ar else "Converting Word file to PDF..."):
                conv_pdf_bytes, conv_text, convertible = doc_to_pdf(raw_bytes, uploaded_file.name)
                if convertible and conv_pdf_bytes:
                    st.session_state.cv_pdf_bytes = conv_pdf_bytes
                    st.session_state.cv_original_text = conv_text
                    is_pdf = True  # treat as PDF for the cleaning & merge flow below
                else:
                    if uploaded_file.name.lower().endswith(".doc"):
                        st.error(
                            "ملفات وورد القديمة (.doc) تتطلب تحويلها إلى صيغة .docx أولاً لوجود برنامج LibreOffice غير متوفر في هذا السيرفر. "
                            "يرجى فتح الملف في وورد وحفظه كملف Word (.docx) ثم إعادة رفعه." if is_ar else
                            "Legacy Word (.doc) files require saving as .docx first (LibreOffice is not available on this server). "
                            "Please open the file in Word and save it as Word (.docx), then re-upload."
                        )
                    else:
                        st.error("فشل تحويل ملف وورد إلى PDF" if is_ar else "Failed to convert Word file to PDF")

        if is_pdf and 'cv_pdf_bytes' not in st.session_state:
            st.session_state.cv_pdf_bytes = raw_bytes
        elif is_image:
            st.session_state.cv_image_bytes = raw_bytes

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📄 " + (t("cv_original_text", lang)))

            if is_pdf:
                try:
                    if 'cv_original_text' not in st.session_state:
                        pdf_text = extract_text_from_pdf(io.BytesIO(raw_bytes))
                        st.session_state.cv_original_text = pdf_text
                    st.text_area("PDF Content", st.session_state.get('cv_original_text', ''), height=400, key="cv_original_pdf")

                    # Visual preview of first page (works for PDF uploads and docx→PDF conversions)
                    if FITZ_AVAILABLE and 'cv_pdf_bytes' in st.session_state:
                        preview_img = _pdf_page_to_image(st.session_state.cv_pdf_bytes, dpi=100)
                        preview_buf = io.BytesIO()
                        preview_img.save(preview_buf, format="PNG")
                        st.image(
                            preview_buf.getvalue(),
                            caption=("معاينة الصفحة الأولى من السيرة الذاتية" if is_ar else "First page preview of the CV"),
                            use_container_width=True,
                        )
                except Exception as e:
                    st.error(t("cv_error", lang) + ": " + str(e))
            elif is_image:
                st.image(raw_bytes, caption=uploaded_file.name, use_container_width=True)

                # Run OCR extraction once per image
                if 'cv_ocr_done' not in st.session_state:
                    with st.spinner("جارٍ تحليل الصورة واستخراج النص... " if is_ar else "Analyzing image and extracting text..."):
                        ocr_data = extract_text_and_boxes_from_image(raw_bytes, uploaded_file.name)
                        st.session_state.cv_original_text = ocr_data.get('text', '')
                        st.session_state.cv_image_boxes = ocr_data.get('words', [])
                        st.session_state.cv_ocr_done = True

                # Pre-detect sensitive items in extracted text
                extracted_txt = st.session_state.get('cv_original_text', '')
                if extracted_txt.strip():
                    with st.expander("📝 " + ("النص المستخرج من الصورة" if is_ar else "Extracted Image Text"), expanded=False):
                        st.text_area("OCR Text", extracted_txt, height=220, key="cv_original_ocr", disabled=True)

                    _, pre_phones, pre_emails, _ = remove_emails_and_phones_from_text(extracted_txt)
                    st.session_state.cv_detected_phones = pre_phones
                    st.session_state.cv_detected_emails = pre_emails

                    if pre_phones or pre_emails:
                        details = []
                        if pre_phones:
                            details.append(f"📞 {len(pre_phones)} " + ("هاتف" if is_ar else "phones"))
                        if pre_emails:
                            details.append(f"✉️ {len(pre_emails)} " + ("إيميل" if is_ar else "emails"))
                        st.warning("⚠️ " + ("تم رصد بيانات حساسة بالصورة: " if is_ar else "Sensitive data detected: ") + " | ".join(details))
                    else:
                        st.info("ℹ️ " + ("تم استخراج النص من الصورة بنجاح." if is_ar else "Text extracted successfully."))
                else:
                    st.info("ℹ️ " + ("الصورة جاهزة للتنظيف. اضغط على زر 'تنظيف الملف' باليسار لتنظيفها وتحميلها بصيغة صورة أو PDF." if is_ar else "Image ready for cleaning. Click Clean File to process."))

                # Optional custom keyword mask
                with st.expander("🛠️ " + ("حذف كلمات أو أرقام إضافية يدوياً (اختياري)" if is_ar else "Manual removal options (optional)"), expanded=False):
                    st.text_input(
                        "أدخل أي رقم هاتف أو إيميل إضافي ترغب بحذفه من الصورة" if is_ar else "Enter phone or email to redact",
                        key="cv_manual_custom_input",
                        placeholder="+9665... أو user@gmail.com"
                    )

        with col2:
            st.subheader("✨ " + (t("cv_cleaned_text", lang)))

            # Clear / Reset button
            if st.button("🗑️ " + ("مسح البيانات وبدء جديد" if is_ar else "Clear & Start Fresh"), width='stretch', key="cv_clear_btn"):
                for k in [
                    'cv_original_text', 'cv_cleaned_text', 'cv_phones_count', 'cv_emails_count',
                    'cv_labels_count', 'cv_file_ext', 'cv_file_name', 'cv_last_file_name',
                    'cv_pdf_bytes', 'cv_cleaned_pdf_bytes', 'cv_image_bytes',
                    'cv_cleaned_image_bytes', 'cv_image_boxes', 'cv_detected_phones',
                    'cv_detected_emails', 'cv_ocr_done',
                    'cv_merged_img_bytes', 'cv_merged_pdf_bytes',
                    'cv_extracted_img_bytes', 'cv_extracted_pdf_bytes',
                    'cv_bg_header_px', 'cv_bg_footer_px', 'cv_bg_left_cm', 'cv_bg_right_cm',
                ] + BG_KEYS:
                    st.session_state.pop(k, None)
                st.rerun()

            # Clean File Button
            if st.button(t("cv_clean_btn", lang), type="primary", width='stretch', key="cv_clean_btn"):
                if is_pdf and 'cv_pdf_bytes' in st.session_state:
                    if not FITZ_AVAILABLE:
                        st.error("مكتبة PyMuPDF (fitz) غير مثبتة في هذه البيئة، لذا التنظيف الذي يحفظ تنسيق PDF غير متاح." if is_ar else "PyMuPDF (fitz) is not installed in this environment.")
                    else:
                        try:
                            cleaned_pdf_bytes, email_count, phone_count = clean_pdf_preserve_format(st.session_state.cv_pdf_bytes)
                            st.session_state.cv_cleaned_pdf_bytes = cleaned_pdf_bytes
                            st.session_state.cv_emails_count = email_count
                            st.session_state.cv_phones_count = phone_count
                            if st.session_state.get('cv_original_text'):
                                c_txt, _, _, l_found = remove_emails_and_phones_from_text(st.session_state.cv_original_text)
                                st.session_state.cv_cleaned_text = c_txt
                                st.session_state.cv_labels_count = len(l_found)
                            st.success(t("cv_cleaned_success", lang))
                        except Exception as e:
                            st.error("خطأ في تنظيف PDF: " + str(e) if is_ar else "Error cleaning PDF: " + str(e))

                elif is_image and 'cv_image_bytes' in st.session_state:
                    try:
                        img_bytes = st.session_state.cv_image_bytes
                        boxes = st.session_state.get('cv_image_boxes', [])
                        orig_text = st.session_state.get('cv_original_text', '')
                        known_phones = st.session_state.get('cv_detected_phones', [])
                        known_emails = st.session_state.get('cv_detected_emails', [])

                        sensitive_boxes = []
                        phones_found = list(known_phones)
                        emails_found = list(known_emails)
                        labels_found = []

                        # ── Pass 1: Line-level detection ──
                        # Phone numbers and emails are often split across multiple OCR words
                        # (e.g. "+966 554 978 543" → separate words). Group by line and redact
                        # ALL words on any line that contains a phone/email pattern.
                        line_to_words = {}
                        for w in boxes:
                            line_key = w.get('line', '').strip()
                            if line_key:
                                line_to_words.setdefault(line_key, []).append(w)

                        line_has_sensitive = set()
                        for line_text, line_words in line_to_words.items():
                            # Email on line
                            if re.findall(EMAIL_PATTERN, line_text):
                                line_has_sensitive.add(line_text)
                                for em in re.findall(EMAIL_PATTERN, line_text):
                                    if em not in emails_found:
                                        emails_found.append(em)
                                continue
                            # Phone on line
                            for pat in PHONE_PATTERNS:
                                if re.findall(pat, line_text):
                                    line_has_sensitive.add(line_text)
                                    for ph in re.findall(pat, line_text):
                                        if ph not in phones_found:
                                            phones_found.append(ph)
                                    break

                        # Mark ALL words on sensitive lines for redaction
                        for w in boxes:
                            if w.get('line', '').strip() in line_has_sensitive:
                                if w not in sensitive_boxes:
                                    sensitive_boxes.append(w)

                        # ── Pass 2: Per-word checks (labels, digit fallback, remaining) ──
                        for w in boxes:
                            if w in sensitive_boxes:
                                continue
                            txt = w.get('text', '').strip()

                            # Check phone by digit sequence (fallback for fragmented OCR)
                            txt_digits = re.sub(r'\D', '', txt)
                            if len(txt_digits) >= 6:
                                for kp in known_phones:
                                    kp_digits = re.sub(r'\D', '', kp)
                                    if kp_digits and (kp_digits in txt_digits or txt_digits in kp_digits):
                                        sensitive_boxes.append(w)
                                        break
                            if w in sensitive_boxes:
                                continue

                            # Check labels
                            for lab_pat in LABEL_PATTERNS:
                                if re.search(lab_pat, txt, re.IGNORECASE):
                                    sensitive_boxes.append(w)
                                    labels_found.append(txt)
                                    break

                        # Check manual user input
                        manual_kw = st.session_state.get('cv_manual_custom_input', '').strip()
                        if manual_kw:
                            for kw in [k.strip() for k in re.split(r'[,\s]+', manual_kw) if k.strip()]:
                                for w in boxes:
                                    if kw.lower() in w.get('text', '').lower() or kw.lower() in w.get('line', '').lower():
                                        if w not in sensitive_boxes:
                                            sensitive_boxes.append(w)
                                        if any(ch.isdigit() for ch in kw) and kw not in phones_found:
                                            phones_found.append(kw)
                                        elif '@' in kw and kw not in emails_found:
                                            emails_found.append(kw)

                        # Clean image and generate both Image and PDF outputs
                        cleaned_img, cleaned_pdf = redact_image_sensitive_data(
                            img_bytes, sensitive_boxes, file_ext=file_ext
                        )

                        st.session_state.cv_cleaned_image_bytes = cleaned_img
                        st.session_state.cv_cleaned_pdf_bytes = cleaned_pdf

                        if orig_text:
                            c_txt, p_l, e_l, l_l = remove_emails_and_phones_from_text(orig_text)
                            st.session_state.cv_cleaned_text = c_txt
                            phones_found.extend(p_l)
                            emails_found.extend(e_l)
                            labels_found.extend(l_l)

                        st.session_state.cv_phones_count = len(set(phones_found))
                        st.session_state.cv_emails_count = len(set(emails_found))
                        st.session_state.cv_labels_count = len(set(labels_found))

                        st.success(t("cv_cleaned_success", lang))
                    except Exception as e:
                        st.error(f"خطأ أثناء تنظيف الصورة: {str(e)}" if is_ar else f"Error cleaning image: {str(e)}")

                elif st.session_state.get('cv_original_text'):
                    cleaned_text, phones, emails, labels = remove_emails_and_phones_from_text(st.session_state.cv_original_text)
                    st.session_state.cv_cleaned_text = cleaned_text
                    st.session_state.cv_phones_count = len(phones)
                    st.session_state.cv_emails_count = len(emails)
                    st.session_state.cv_labels_count = len(labels)
                    st.success(t("cv_cleaned_success", lang))
                else:
                    st.warning("الرجاء رفع ملف أولاً" if is_ar else "Please upload a file first")

            # --- Display Results & Download Options ---
            if 'cv_cleaned_image_bytes' in st.session_state:
                st.image(st.session_state.cv_cleaned_image_bytes, caption="معاينة الصورة بعد التنظيف" if is_ar else "Cleaned Image Preview", use_container_width=True)

                # Stats metrics
                c_stats1, c_stats2, c_stats3 = st.columns(3)
                with c_stats1:
                    st.metric(t("cv_phones_removed", lang), st.session_state.get('cv_phones_count', 0))
                with c_stats2:
                    st.metric(t("cv_emails_removed", lang), st.session_state.get('cv_emails_count', 0))
                with c_stats3:
                    st.metric("التسميات المحذوفة" if is_ar else "Labels removed", st.session_state.get('cv_labels_count', 0))

                # Download Buttons
                d_col1, d_col2 = st.columns(2)
                with d_col1:
                    clean_img_fn = "cleaned_" + st.session_state.get('cv_file_name', 'cv.jpg')
                    mime_typ = f"image/{file_ext if file_ext in ['png', 'webp', 'bmp'] else 'jpeg'}"
                    st.download_button(
                        label="⬇️ " + ("تحميل الصورة بعد التنظيف" if is_ar else "Download Cleaned Image"),
                        data=st.session_state.cv_cleaned_image_bytes,
                        file_name=clean_img_fn,
                        mime=mime_typ,
                        width='stretch',
                        key="cv_dl_clean_img"
                    )
                with d_col2:
                    base_raw = os.path.splitext(st.session_state.get('cv_file_name', 'cv'))[0]
                    clean_pdf_fn = f"cleaned_{base_raw}.pdf"
                    st.download_button(
                        label="⬇️ " + ("تحميل كملف PDF" if is_ar else "Download as PDF"),
                        data=st.session_state.cv_cleaned_pdf_bytes,
                        file_name=clean_pdf_fn,
                        mime="application/pdf",
                        width='stretch',
                        key="cv_dl_clean_img_pdf"
                    )

                if st.session_state.get('cv_cleaned_text'):
                    with st.expander("📄 " + ("النص بعد التنظيف" if is_ar else "Cleaned Text Preview")):
                        st.text_area("Cleaned Text", st.session_state.cv_cleaned_text, height=200, key="cv_clean_txt_prev", disabled=True)
                        st.download_button(
                            label="⬇️ " + ("تحميل النص المنظف (.txt)" if is_ar else "Download Text (.txt)"),
                            data=st.session_state.cv_cleaned_text.encode('utf-8'),
                            file_name=f"cleaned_{base_raw}.txt",
                            mime="text/plain",
                            width='stretch',
                            key="cv_dl_clean_txt_from_img"
                        )

            elif 'cv_cleaned_pdf_bytes' in st.session_state and is_pdf:
                clean_filename = "cleaned_" + st.session_state.get('cv_file_name', 'cv.pdf')
                st.download_button(
                    label="⬇️ " + t("cv_download_btn", lang),
                    data=st.session_state.cv_cleaned_pdf_bytes,
                    file_name=clean_filename,
                    mime="application/pdf",
                    width='stretch',
                    key="cv_download_cleaned_pdf"
                )
                st.info("ℹ️ " + ("تم حفظ PDF مع الحفاظ على الصور والتنسيق الأصلي. الإيميلات وأرقام الهواتف محذوفة." if is_ar else "PDF saved preserving images and original format. Emails and phone numbers removed."))

                # Visual preview of cleaned PDF first page
                if FITZ_AVAILABLE:
                    try:
                        clean_preview_img = _pdf_page_to_image(st.session_state.cv_cleaned_pdf_bytes, dpi=100)
                        clean_preview_buf = io.BytesIO()
                        clean_preview_img.save(clean_preview_buf, format="PNG")
                        st.image(
                            clean_preview_buf.getvalue(),
                            caption=("معاينة الصفحة الأولى بعد التنظيف" if is_ar else "Cleaned first page preview"),
                            use_container_width=True,
                        )
                    except Exception:
                        pass

        # Show merge section if both cleaned CV and background exist
        if has_background and ('cv_cleaned_image_bytes' in st.session_state or 'cv_cleaned_pdf_bytes' in st.session_state):
            _render_merge_section(is_ar)
