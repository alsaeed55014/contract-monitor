import io, re
import fitz
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper as ar
from bidi.algorithm import get_display as gd

pdfmetrics.registerFont(TTFont('ArabicRegular', 'fonts/NotoSansArabic-Regular.ttf'))
pdfmetrics.registerFont(TTFont('ArabicBold', 'fonts/NotoSansArabic-Bold.ttf'))

_ar_rx = re.compile(r'[؀-ۿ]')
_emoji_rx = re.compile('[\U0001F000-\U0001FAFF]')

def _sh(_t):
    _t = _emoji_rx.sub('', str(_t))
    if _ar_rx.search(_t):
        try:
            return gd(ar.reshape(_t))
        except Exception:
            return _t
    return _t

# Test 1: English text with Arabic font (should be empty - no glyphs)
buf = io.BytesIO()
c = canvas.Canvas(buf, pagesize=(600, 200))
c.setFont('ArabicBold', 30)
c.drawString(50, 100, _sh('Hello World'))
c.showPage()
c.save()

doc = fitz.open("pdf", buf.getvalue())
pix = doc.load_page(0).get_pixmap(dpi=72)
# Check if pixels are all white (text invisible)
import numpy as np
arr = np.frombuffer(pix.tobytes(), dtype=np.uint8).reshape(pix.height, pix.width, 4)
non_white = (arr[:, :, 0] < 250).sum()
print(f'Test 1 (English with Arabic font): non-white pixels = {non_white} (should be > 0)')

# Test 2: Arabic text with Arabic font (should render)
buf2 = io.BytesIO()
c2 = canvas.Canvas(buf2, pagesize=(600, 200))
c2.setFont('ArabicBold', 30)
c2.drawString(50, 100, _sh('مرحبا'))
c2.showPage()
c2.save()

doc2 = fitz.open("pdf", buf2.getvalue())
pix2 = doc2.load_page(0).get_pixmap(dpi=72)
arr2 = np.frombuffer(pix2.tobytes(), dtype=np.uint8).reshape(pix2.height, pix2.width, 4)
non_white2 = (arr2[:, :, 0] < 250).sum()
print(f'Test 2 (Arabic with Arabic font): non-white pixels = {non_white2} (should be > 0)')