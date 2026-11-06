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

# PyMuPDF (fitz) is optional: guard the import
try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    fitz = None
    FITZ_AVAILABLE = False

# Application Base Directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Persistent storage directory for CV background (survives app restarts)
BG_STORAGE_DIR = os.path.join(BASE_DIR, "cv_background_storage")
BG_STORAGE_FILE = os.path.join(BG_STORAGE_DIR, "background.bin")
BG_SETTINGS_FILE = os.path.join(BG_STORAGE_DIR, "settings.json")

# ── Background Template Keys ─────────────────────────────────────────────────
BG_KEYS = [
    'cv_bg_bytes', 'cv_bg_ext', 'cv_bg_name',
    'cv_bg_header_px', 'cv_bg_footer_px',
    'cv_bg_left_cm', 'cv_bg_right_cm',
    'cv_bg_cv_scale', 'cv_bg_cv_align',
]

# ── Persistent storage helpers ────────────────────────────────────────────────

def _save_background_to_disk(bg_bytes, bg_ext, bg_name,
                             header_px, footer_px,
                             left_cm, right_cm, cv_scale, cv_align):
    """Save background image and settings to disk for persistence across app restarts."""
    try:
        os.makedirs(BG_STORAGE_DIR, exist_ok=True)
        with open(BG_STORAGE_FILE, "wb") as f:
            f.write(bg_bytes)
        settings = {
            "ext": bg_ext,
            "name": bg_name,
            "header_px": int(header_px),
            "footer_px": int(footer_px),
            "left_cm": float(left_cm),
            "right_cm": float(right_cm),
            "cv_scale": float(cv_scale),
            "cv_align": cv_align,
        }
        with open(BG_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving background to disk: {e}")


def _load_background_from_disk():
    """Load background image and settings from disk. Returns dict or None."""
    try:
        if not os.path.exists(BG_STORAGE_FILE) or not os.path.exists(BG_SETTINGS_FILE):
            return None
        with open(BG_STORAGE_FILE, "rb") as f:
            bg_bytes = f.read()
        with open(BG_SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
        return {
            "bytes": bg_bytes,
            "ext": settings.get("ext", ""),
            "name": settings.get("name", ""),
            "header_px": int(settings.get("header_px", 195)),
            "footer_px": int(settings.get("footer_px", 225)),
            "left_cm": float(settings.get("left_cm", 1.0)),
            "right_cm": float(settings.get("right_cm", 1.0)),
            "cv_scale": float(settings.get("cv_scale", 1.0)),
            "cv_align": settings.get("cv_align", "center"),
        }
    except Exception as e:
        print(f"Error loading background from disk: {e}")
        return None


def _delete_background_from_disk():
    """Delete background files from disk."""
    try:
        if os.path.exists(BG_STORAGE_FILE):
            os.remove(BG_STORAGE_FILE)
        if os.path.exists(BG_SETTINGS_FILE):
            os.remove(BG_SETTINGS_FILE)
    except Exception as e:
        print(f"Error deleting background from disk: {e}")


# Supported Image Extensions
IMAGE_EXTS = ["jpg", "jpeg", "png", "webp", "bmp", "tiff", "jfif"]

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
    h, w = bg_img.shape[:2]

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

    # ── Load persisted background from disk if not already in session ──
    if "cv_bg_bytes" not in st.session_state:
        persisted = _load_background_from_disk()
        if persisted is not None:
            st.session_state.cv_bg_bytes = persisted["bytes"]
            st.session_state.cv_bg_ext = persisted["ext"]
            st.session_state.cv_bg_name = persisted["name"]
            st.session_state.cv_bg_header_px = persisted["header_px"]
            st.session_state.cv_bg_footer_px = persisted["footer_px"]
            st.session_state.cv_bg_left_cm = persisted["left_cm"]
            st.session_state.cv_bg_right_cm = persisted["right_cm"]
            st.session_state.cv_bg_cv_scale = persisted["cv_scale"]
            st.session_state.cv_bg_cv_align = persisted["cv_align"]

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

                # Save to disk for persistence across app restarts
                _save_background_to_disk(
                    st.session_state.cv_bg_bytes, st.session_state.cv_bg_ext, st.session_state.cv_bg_name,
                    st.session_state.cv_bg_header_px, st.session_state.cv_bg_footer_px,
                    st.session_state.cv_bg_left_cm, st.session_state.cv_bg_right_cm,
                    st.session_state.get("cv_bg_cv_scale", 1.0),
                    st.session_state.get("cv_bg_cv_align", "center"),
                )

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

                # Persist updated settings to disk immediately
                _save_background_to_disk(
                    st.session_state.cv_bg_bytes, st.session_state.cv_bg_ext, st.session_state.cv_bg_name,
                    st.session_state.cv_bg_header_px, st.session_state.cv_bg_footer_px,
                    st.session_state.cv_bg_left_cm, st.session_state.cv_bg_right_cm,
                    st.session_state.cv_bg_cv_scale, st.session_state.cv_bg_cv_align,
                )

            # Show auto-detection info
            st.caption("ℹ️ " + ("سيتم كشف الخط الأفقي تلقائياً وتحديد المنطقة المحجوزة (5 سم قبل الذيل)" if is_ar else "Horizontal line will be auto-detected with 5cm margin before footer"))

            if st.button(
                "🗑️ " + ("حذف الخلفية" if is_ar else "Remove background"),
                key="cv_bg_remove_btn"
            ):
                # Delete from disk
                _delete_background_from_disk()
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


def _extract_profile_image(img_bytes):
    """
    Extract profile picture from CV image.
    Looks for a square-ish image in the top-left or top-right area.
    Returns profile image bytes or None.
    """
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        w, h = img.size

        # Define search areas (top 40% of page)
        search_h = int(h * 0.4)

        # Try to find profile-like regions (square-ish, reasonable size)
        # Search for typical profile photo locations (top-left or top-right quadrant)
        profile_quadrants = [
            (0, 0, int(w * 0.3), int(search_h * 0.5)),  # Top-left
            (int(w * 0.7), 0, w, int(search_h * 0.5)),  # Top-right
        ]

        for x1, y1, x2, y2 in profile_quadrants:
            if x2 <= x1 or y2 <= y1:
                continue

            quadrant = img.crop((x1, y1, x2, y2))
            if quadrant.size == 0:
                continue

            # Simple heuristic: check if region has image-like properties
            # by analyzing color variation
            pixels = list(quadrant.getdata())
            if len(pixels) > 0:
                # Calculate standard deviation of RGB values
                r_vals = [p[0] for p in pixels]
                g_vals = [p[1] for p in pixels]
                b_vals = [p[2] for p in pixels]

                r_std = (sum((x - sum(r_vals)/len(r_vals))**2 for x in r_vals) / len(r_vals))**0.5
                g_std = (sum((x - sum(g_vals)/len(g_vals))**2 for x in g_vals) / len(g_vals))**0.5
                b_std = (sum((x - sum(b_vals)/len(b_vals))**2 for x in b_vals) / len(b_vals))**0.5

                avg_std = (r_std + g_std + b_std) / 3

                if avg_std > 30:  # Likely contains an image/photo
                    # Extract this region as potential profile
                    profile_img = quadrant.resize((150, 150), Image.LANCZOS)

                    out = io.BytesIO()
                    profile_img.save(out, format="PNG")
                    return out.getvalue()

        return None
    except Exception as e:
        print(f"Error extracting profile: {e}")
        return None


def _render_text_on_background(text_lines, bg_bytes, bg_ext, header_px, footer_px, profile_img_bytes=None, left_cm=1.0, right_cm=1.0):
    """
    Render extracted text lines on background with optional profile image.
    Returns merged image bytes and PDF bytes.
    """
    # Load background
    if bg_ext == 'pdf':
        bg_img = _pdf_page_to_image(bg_bytes, dpi=150)
    else:
        bg_img = Image.open(io.BytesIO(bg_bytes)).convert("RGB")

    bg_w, bg_h = bg_img.size

    # Detect horizontal line for better content area calculation
    line_y = _detect_horizontal_line_position(bg_img)

    # Get side margins from session state
    left_cm_val = st.session_state.get("cv_bg_left_cm", left_cm)
    right_cm_val = st.session_state.get("cv_bg_right_cm", right_cm)

    # Calculate optimal content area
    content_top, content_bottom, content_width, margin_sides = _calculate_content_area(
        bg_img, header_px, footer_px, line_y, left_cm_val, right_cm_val
    )

    # Create drawing context
    draw = ImageDraw.Draw(bg_img)

    # Load multiple fonts for different sizes
    try:
        from PIL import ImageFont
        # Try to use common fonts
        font_paths = [
            os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arial.ttf"),
            os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "tahoma.ttf"),
            os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "calibri.ttf"),
        ]
        font_path = None
        for fp in font_paths:
            if os.path.exists(fp):
                font_path = fp
                break

        if font_path:
            title_font = ImageFont.truetype(font_path, 28)
            header_font = ImageFont.truetype(font_path, 20)
            body_font = ImageFont.truetype(font_path, 14)
            small_font = ImageFont.truetype(font_path, 12)
        else:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
    except Exception:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Draw profile image if available (top-left of content area)
    if profile_img_bytes:
        try:
            profile_img = Image.open(io.BytesIO(profile_img_bytes)).convert("RGBA")
            profile_img = profile_img.resize((120, 120), Image.LANCZOS)
            paste_x = margin_sides + 20
            paste_y = content_top + 20
            bg_img.paste(profile_img, (paste_x, paste_y), profile_img)
            # Adjust text start position
            text_start_x = paste_x + 140
        except Exception:
            text_start_x = margin_sides + 20
    else:
        text_start_x = margin_sides + 20

    # Draw text lines with better formatting
    y_pos = content_top + 20
    line_height = 25

    for line in text_lines:
        if y_pos + line_height > content_bottom:
            break

        # Skip empty lines
        if not line.strip():
            y_pos += 10
            continue

        # Determine if this is a header (CAPS or short line)
        is_header = len(line) < 50 and line.isupper() or any(keyword in line.upper() for keyword in ['OBJECTIVE', 'EXPERIENCE', 'EDUCATION', 'SKILLS', 'CERTIFICATE', 'INFORMATION', 'BACKGROUND'])

        try:
            # Choose font based on line type
            if is_header:
                draw.text((text_start_x, y_pos), line, fill=(0, 0, 0), font=header_font)
                y_pos += line_height + 5  # Extra space after headers
            else:
                draw.text((text_start_x, y_pos), line, fill=(0, 0, 0), font=body_font)
                y_pos += line_height
        except Exception:
            # Fallback for unsupported characters
            draw.text((text_start_x, y_pos), line, fill=(0, 0, 0), font=body_font)
            y_pos += line_height

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

            with st.spinner("⏳ " + ("جارٍ استخراج النص والصورة..." if is_ar else "Extracting text and profile...")):
                # Extract text using OCR with position info
                ocr_data = extract_text_and_boxes_from_image(cv_bytes, "cv_img.jpg")
                words = ocr_data.get('words', [])

                # Sort words by position (top to bottom, left to right)
                words_sorted = sorted(words, key=lambda w: (w.get('top', 0), w.get('left', 0)))

                # Group words into lines based on y-position
                lines = []
                current_line = []
                current_y = None
                y_threshold = 15  # Pixels to consider same line

                for word in words_sorted:
                    text = word.get('text', '').strip()
                    if not text:
                        continue

                    word_y = word.get('top', 0)
                    if current_y is None:
                        current_y = word_y
                        current_line = [text]
                    elif abs(word_y - current_y) < y_threshold:
                        current_line.append(text)
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [text]
                        current_y = word_y

                if current_line:
                    lines.append(' '.join(current_line))

                # Clean text: remove all phone numbers and emails from each line
                cleaned_lines = []
                for line in lines:
                    cleaned_line, _, _, _ = remove_emails_and_phones_from_text(line)
                    if cleaned_line.strip():
                        cleaned_lines.append(cleaned_line)

                # Extract profile image
                profile_img = _extract_profile_image(cv_bytes)

                # Render on background
                merged_img_bytes, merged_pdf_bytes = _render_text_on_background(
                    cleaned_lines, bg_bytes, bg_ext, header_px, footer_px, profile_img,
                    left_cm=left_cm, right_cm=right_cm
                )
                st.session_state.cv_extracted_img_bytes = merged_img_bytes
                st.session_state.cv_extracted_pdf_bytes = merged_pdf_bytes

                # Show stats
                total_phones = 0
                total_emails = 0
                for line in lines:
                    _, p, e, _ = remove_emails_and_phones_from_text(line)
                    total_phones += len(p)
                    total_emails += len(e)

                if total_phones > 0 or total_emails > 0:
                    stats = []
                    if total_phones > 0:
                        stats.append(f"📞 {total_phones} " + ("رقم" if is_ar else "number(s)"))
                    if total_emails > 0:
                        stats.append(f"✉️ {total_emails} " + ("إيميل" if is_ar else "email(s)"))
                    st.info("✅ " + ("تم حذف: " if is_ar else "Removed: ") + " | ".join(stats))

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
        for i in range(len(data.get('text', []))):
            t_word = data['text'][i].strip()
            if t_word:
                words.append({
                    'text': t_word,
                    'left': int(data['left'][i]),
                    'top': int(data['top'][i]),
                    'width': int(data['width'][i]),
                    'height': int(data['height'][i]),
                    'line': t_word
                })
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

    st.info("ℹ️ " + ("هذا القسم يدعم تنظيف ملفات PDF وجميع أنواع الصور (JPG, PNG, JPEG, WEBP, BMP). يتم حذف أرقام الهواتف والإيميلات مع الحفاظ على التنسيق الأصلي والتصميم بالكامل." if is_ar else "This tool supports PDF files and all image formats (JPG, PNG, JPEG, WEBP, BMP). Phone numbers and email addresses are cleanly removed while preserving original format and design."))
    if not FITZ_AVAILABLE:
        st.warning("⚠️ " + ("PyMuPDF (fitz) غير مثبت في هذه البيئة، لذا تنظيف PDF الذي يحافظ على التنسيق غير متوفر. يرجى استخدام تنظيف الصور أو تنظيف النص فقط." if is_ar else "PyMuPDF (fitz) is not installed in this environment."))

    # Background uploader section
    has_background = _render_background_uploader(is_ar)

    st.divider()

    # File uploader supporting PDF and ALL image formats
    uploaded_file = st.file_uploader(
        t("cv_upload_label", lang),
        type=["pdf"] + IMAGE_EXTS,
        help=t("cv_upload_help", lang)
    )

    if uploaded_file is not None:
        file_ext = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ''
        is_pdf = file_ext == "pdf"
        is_image = file_ext in IMAGE_EXTS

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
        if is_pdf:
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

                        # Match word boxes
                        for w in boxes:
                            txt = w.get('text', '').strip()
                            line = w.get('line', '').strip()

                            # Check email
                            em = re.findall(EMAIL_PATTERN, txt) or re.findall(EMAIL_PATTERN, line)
                            if em:
                                sensitive_boxes.append(w)
                                emails_found.extend(em)
                                continue

                            # Check phone regex
                            is_p = False
                            for pat in PHONE_PATTERNS:
                                pm = re.findall(pat, txt) or re.findall(pat, line)
                                if pm:
                                    sensitive_boxes.append(w)
                                    phones_found.extend(pm)
                                    is_p = True
                                    break
                            if is_p:
                                continue

                            # Check phone by digit sequence
                            txt_digits = re.sub(r'\D', '', txt)
                            if len(txt_digits) >= 6:
                                for kp in known_phones:
                                    kp_digits = re.sub(r'\D', '', kp)
                                    if kp_digits and (kp_digits in txt_digits or txt_digits in kp_digits):
                                        sensitive_boxes.append(w)
                                        is_p = True
                                        break
                            if is_p:
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

        # Show merge section if both cleaned CV and background exist
        if has_background and ('cv_cleaned_image_bytes' in st.session_state or 'cv_cleaned_pdf_bytes' in st.session_state):
            _render_merge_section(is_ar)
