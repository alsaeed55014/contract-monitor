import io
import re
import fitz
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register fonts
pdfmetrics.registerFont(TTFont('ArabicRegular', 'fonts/NotoSansArabic-Regular.ttf'))
pdfmetrics.registerFont(TTFont('ArabicBold', 'fonts/NotoSansArabic-Bold.ttf'))

# Test function
_ar_rx = re.compile(r'[؀-ۿ]')
_emoji_rx = re.compile('[\U0001F000-\U0001FAFF]')

def _sh(_t):
    _t = _emoji_rx.sub('', str(_t))
    if _ar_rx.search(_t):
        try:
            import arabic_reshaper as _ar_resh
            from bidi.algorithm import get_display as _bidi_disp
            return _bidi_disp(_ar_resh.reshape(_t))
        except Exception:
            return _t
    return _t

# Test 1: Check if English text renders with Arabic font
buf = io.BytesIO()
c = canvas.Canvas(buf, pagesize=(600, 200))
c.setFont('ArabicBold', 30)
c.drawString(50, 100, _sh('Hello World'))  # Should be invisible
c.showPage()
c.save()

# Check if we have any non-white pixels (text should be invisible)
doc = fitz.open("pdf", buf.getvalue())
pix = doc.load_page(0).get_pixmap(dpi=150)
# Count non-white pixels
pixels = pix.samples
non_white = sum(1 for i in range(0, len(pixels), 4) if pixels[i:i+3] != [255, 255, 255])
print(f'English text rendered with Arabic font: {non_white} non-white pixels (0 = invisible)')

# Test 2: Arabic text with Arabic font (should be visible)
buf2 = io.BytesIO()
c2 = canvas.Canvas(buf2, pagesize=(600, 200))
c2.setFont('ArabicBold', 30)
c2.drawString(50, 100, _sh('مرحبا'))  # Should be visible
c2.showPage()
c2.save()

doc2 = fitz.open("pdf", buf2.getvalue())
pix2 = doc2.load_page(0).get_pixmap(dpi=150)
pixels2 = pix2.samples
non_white2 = sum(1 for i in range(0, len(pixels2), 4) if pixels2[i:i+3] != [255, 255, 255])
print(f'Arabic text rendered with Arabic font: {non_white2} non-white pixels (0 = invisible)')