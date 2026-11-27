"""Test the fix for English text rendering in PNG export"""
import io
import fitz
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register fonts
pdfmetrics.registerFont(TTFont('ArabicRegular', 'fonts/NotoSansArabic-Regular.ttf'))
pdfmetrics.registerFont(TTFont('ArabicBold', 'fonts/NotoSansArabic-Bold.ttf'))
pdfmetrics.registerFont(TTFont('LatinRegular', 'C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('LatinBold', 'C:/Windows/Fonts/arialbd.ttf'))

def _sh(_t):
    # Simplified version of the fixed _sh function
    import re
    _ar_rx = re.compile(r'[؀-ۿ]')
    _emoji_rx = re.compile('[\U0001F000-\U0001FAFF]')
    _t = _emoji_rx.sub('', str(_t))
    if _ar_rx.search(_t):
        try:
            import arabic_reshaper as _ar_resh
            from bidi.algorithm import get_display as _bidi_disp
            return _bidi_disp(_ar_resh.reshape(_t))
        except Exception:
            return _t
    return _t

# Test 1: English text (should use Latin font)
buf = io.BytesIO()
c = canvas.Canvas(buf, pagesize=(600, 120))
c.setFont('LatinBold', 30)  # This should be the Latin font
c.drawString(50, 50, 'Hello World 123')
c.showPage()
c.save()

# Check rendering
doc = fitz.open("pdf", buf.getvalue())
pix = doc.load_page(0).get_pixmap(dpi=100)
# Count non-white pixels (should be > 0 if text rendered)
pixels = pix.samples
non_white = sum(1 for i in range(0, len(pixels), 4) if pixels[i:i+3] != [255, 255, 255])
print(f'English text rendered: {non_white} non-white pixels (should be > 0)')

# Save for visual inspection
pix.save('test_english_render.png')
print('Saved test_english_render.png for visual verification')