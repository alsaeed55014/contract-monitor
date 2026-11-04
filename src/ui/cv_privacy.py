import io
import os
import re
import json
import base64
import streamlit as st
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import pdfplumber

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
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    span_text = span.get("text", "")
                    emails_in_span = re.findall(EMAIL_PATTERN, span_text)
                    for email in emails_in_span:
                        instances = page.search_for(email)
                        for inst in instances:
                            rect = fitz_module.Rect(inst)
                            page.add_redact_annot(rect, fill=(1, 1, 1))
                            total_emails += 1

                    phones_in_span = []
                    for pattern in PHONE_PATTERNS:
                        phones_in_span.extend(re.findall(pattern, span_text))
                    for phone in sorted(set(phones_in_span), key=len, reverse=True):
                        instances = page.search_for(phone)
                        for inst in instances:
                            rect = fitz_module.Rect(inst)
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

        # Clear old session state when a new file is uploaded
        if st.session_state.get('cv_last_file_name') != uploaded_file.name:
            for k in [
                'cv_original_text', 'cv_cleaned_text', 'cv_phones_count', 'cv_emails_count',
                'cv_labels_count', 'cv_file_ext', 'cv_file_name', 'cv_last_file_name',
                'cv_pdf_bytes', 'cv_cleaned_pdf_bytes', 'cv_image_bytes',
                'cv_cleaned_image_bytes', 'cv_image_boxes', 'cv_detected_phones',
                'cv_detected_emails', 'cv_ocr_done'
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
                    'cv_detected_emails', 'cv_ocr_done'
                ]:
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

                c_stats1, c_stats2 = st.columns(2)
                with c_stats1:
                    st.metric(t("cv_phones_removed", lang), st.session_state.get('cv_phones_count', 0))
                with c_stats2:
                    st.metric(t("cv_emails_removed", lang), st.session_state.get('cv_emails_count', 0))

                if st.session_state.get('cv_original_text'):
                    st.text_area("Cleaned Text Preview", st.session_state.get('cv_cleaned_text', st.session_state.cv_original_text), height=200, key="cv_cleaned_preview", disabled=True)

            elif 'cv_cleaned_text' in st.session_state:
                cleaned_text = st.session_state.cv_cleaned_text
                st.text_area("Cleaned Content", cleaned_text, height=400, key="cv_cleaned_display")

                c_stats1, c_stats2, c_stats3 = st.columns(3)
                with c_stats1:
                    st.metric(t("cv_phones_removed", lang), st.session_state.get('cv_phones_count', 0))
                with c_stats2:
                    st.metric(t("cv_emails_removed", lang), st.session_state.get('cv_emails_count', 0))
                with c_stats3:
                    st.metric("التسميات المحذوفة" if is_ar else "Labels removed", st.session_state.get('cv_labels_count', 0))

                base_name = "cleaned_" + st.session_state.get('cv_file_name', 'cv')
                clean_filename = base_name + ".txt"
                st.download_button(
                    label="⬇️ " + t("cv_download_btn", lang),
                    data=cleaned_text.encode('utf-8'),
                    file_name=clean_filename,
                    mime="text/plain",
                    width='stretch',
                    key="cv_download_cleaned_txt"
                )
                st.info("ℹ️ " + ("تم حفظ النص المنظف كملف نصي." if is_ar else "Cleaned text saved as text file."))
            elif 'cv_original_text' in st.session_state and not is_image:
                st.info(t("cv_no_sensitive", lang))
