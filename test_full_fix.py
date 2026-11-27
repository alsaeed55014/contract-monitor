"""Test the complete fix: English AND Arabic rendering in both interface modes"""
import io
import re
import fitz
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper as ar
from bidi.algorithm import get_display as gd

# Register fonts
pdfmetrics.registerFont(TTFont('ArabicRegular', 'fonts/NotoSansArabic-Regular.ttf'))
pdfmetrics.registerFont(TTFont('ArabicBold', 'fonts/NotoSansArabic-Bold.ttf'))
pdfmetrics.registerFont(TTFont('LatinRegular', 'C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('LatinBold', 'C:/Windows/Fonts/arialbd.ttf'))

_ar_rx = re.compile(r'[\u0600-\u06FF]')
_emoji_rx = re.compile('[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]')

def _sh(_t):
    _t = _emoji_rx.sub('', str(_t))
    if _ar_rx.search(_t):
        try:
            return gd(ar.reshape(_t))
        except Exception:
            return _t
    return _t

def render_test(is_ar_mode, desc):
    """Render a worker card simulating English or Arabic interface mode."""
    _rtl = bool(is_ar_mode)
    _f_reg, _f_bold = ('ArabicRegular', 'ArabicBold') if _rtl else ('LatinRegular', 'LatinBold')
    _l_reg, _l_bold = ('LatinRegular', 'LatinBold') if not _rtl else ('LatinRegular', 'LatinBold')

    _T_LAB, _S_LAB = (_f_bold, 23) if _rtl else (_l_bold, 23)
    _T_VAL, _S_VAL = (_f_reg, 24) if _rtl else (_l_reg, 24)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(600, 400))

    # Title (should be Arabic font in Arabic mode, Latin font in English mode)
    title = 'بيانات العامل' if is_ar_mode else 'Worker Data'
    c.setFont(_l_bold if not _rtl else _f_bold, 30)
    c.drawCentredString(300, 350, _sh(title))

    # Name
    name = 'أحمد محمد' if is_ar_mode else 'Ahmed Mohammed'
    c.setFont(_l_bold if not _rtl else _f_bold, 24)
    c.drawCentredString(300, 310, _sh(name))

    # Label + value (two columns)
    # English interface: labels in Latin font, values in Latin font
    # Arabic interface: labels in Arabic font, values in Arabic font
    c.setFont(_T_LAB, _S_LAB)
    c.drawString(50, 260, _sh('الاسم:' if is_ar_mode else 'Name:'))

    val = _sh('أحمد' if is_ar_mode else 'Ahmed')
    c.setFont(_T_VAL, _S_VAL)
    c.drawString(200, 260, val)

    # Phone number (English digits)
    c.setFont(_T_LAB, _S_LAB)
    c.drawString(50, 230, _sh('الهاتف:' if is_ar_mode else 'Phone:'))
    c.setFont(_T_VAL, _S_VAL)
    c.drawString(200, 230, _sh('+966 50 123 4567'))

    c.showPage()
    c.save()

    # Save for visual inspection
    doc = fitz.open("pdf", buf.getvalue())
    pix = doc.load_page(0).get_pixmap(dpi=100)
    filename = f'test_{"ar" if is_ar_mode else "en"}_mode.png'
    pix.save(filename)

    # Count ink pixels
    pixels = pix.samples
    non_white = sum(1 for i in range(0, len(pixels), 4) if pixels[i:i+3] != [255, 255, 255])
    print(f'{desc}: {non_white} non-white pixels, saved as {filename}')

render_test(False, 'English interface mode')
render_test(True, 'Arabic interface mode')
print('\nBoth tests completed.')