"""Test: which system font renders BOTH reshaped Arabic AND Latin correctly?"""
import io
import fitz
import arabic_reshaper as ar
from bidi.algorithm import get_display as gd
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image
import numpy as np

FONTS = {
    'Noto': 'fonts/NotoSansArabic-Regular.ttf',
    'Arial': 'C:/Windows/Fonts/arial.ttf',
    'Tahoma': 'C:/Windows/Fonts/tahoma.ttf',
    'SegoeUI': 'C:/Windows/Fonts/segoeui.ttf',
    'Calibri': 'C:/Windows/Fonts/calibri.ttf',
    'Times': 'C:/Windows/Fonts/times.ttf',
}
for name, path in FONTS.items():
    try:
        pdfmetrics.registerFont(TTFont(name, path))
    except Exception as e:
        print(name, 'REGISTER ERR', e)

def ink_of(fontname, text):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(600, 120))
    c.setFont(fontname, 32)
    c.drawString(40, 40, text)
    c.showPage()
    c.save()
    doc = fitz.open("pdf", buf.getvalue())
    pix = doc.load_page(0).get_pixmap(dpi=100)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    arr = np.array(img.convert('L'))
    return int((arr < 128).sum())

ar_reshaped = gd(ar.reshape('مرحبا بكم'))
for name in FONTS:
    try:
        lat = ink_of(name, 'Hello World 123')
        arb = ink_of(name, ar_reshaped)
        print(f'{name:9} latin_ink={lat:5}  arabic_ink={arb:5}  '
              f'{"BOTH OK" if lat > 50 and arb > 50 else "MISSING"}')
    except Exception as e:
        print(name, 'ERR', e)
