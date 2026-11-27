from reportlab.pdfbase.ttfonts import TTFont

for name in ['NotoSansArabic-Regular.ttf', 'NotoSansArabic-Bold.ttf', 'DejaVuSans.ttf']:
    try:
        f = TTFont('x', 'fonts/' + name)
        cmap = f.face.charToGlyph
        missing = [c for c in 'HelloWorldabcXYZ' if ord(c) not in cmap]
        missing_digits = [c for c in '0123456789' if ord(c) not in cmap]
        missing_ar = [c for c in 'مرحبا' if ord(c) not in cmap]
        print(name, 'glyphs=', len(cmap), 'missing_latin=', missing, 'missing_digits=', missing_digits, 'missing_arabic=', missing_ar)
    except Exception as e:
        print(name, 'ERR', e)
