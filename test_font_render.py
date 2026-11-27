"""Render English text with Arabic font vs Arial font to PNG files for visual check."""
import io
import fitz
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('ArabicRegular', 'fonts/NotoSansArabic-Regular.ttf'))
pdfmetrics.registerFont(TTFont('ArabicBold', 'fonts/NotoSansArabic-Bold.ttf'))
pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))

# English with Arabic font
buf = io.BytesIO()
c = canvas.Canvas(buf, pagesize=(600, 100))
c.setFont('ArabicBold', 30)
c.drawString(50, 50, 'Hello World')
c.showPage()
c.save()
doc = fitz.open("pdf", buf.getvalue())
doc.load_page(0).get_pixmap(dpi=72).save('test_arabic_font_english.png')

# English with Arial font
buf2 = io.BytesIO()
c2 = canvas.Canvas(buf2, pagesize=(600, 100))
c2.setFont('Arial', 30)
c2.drawString(50, 50, 'Hello World')
c2.showPage()
c2.save()
doc2 = fitz.open("pdf", buf2.getvalue())
doc2.load_page(0).get_pixmap(dpi=72).save('test_arial_font_english.png')

print('Saved test_arabic_font_english.png and test_arial_font_english.png')

# Check if text rendered by measuring ink coverage
from PIL import Image
import numpy as np

for fname in ['test_arabic_font_english.png', 'test_arial_font_english.png']:
    img = Image.open(fname).convert('L')
    arr = np.array(img)
    ink = (arr < 128).sum()
    print(f'{fname}: {ink} dark pixels')
