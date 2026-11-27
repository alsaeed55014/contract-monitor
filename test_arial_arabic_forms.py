"""Check if Arial's cmap covers the Arabic presentation forms arabic_reshaper emits."""
import arabic_reshaper as ar
from fontTools.ttLib import TTFont

reshaped = ar.reshape('مرحبا بكم في النظام')
codes = sorted({ord(ch) for ch in reshaped})
print('reshaped chars:', [hex(c) for c in codes[:12]], '... total', len(codes))

for name, path in [('NotoArabic', 'fonts/NotoSansArabic-Regular.ttf'),
                   ('Arial', 'C:/Windows/Fonts/arial.ttf'),
                   ('Tahoma', 'C:/Windows/Fonts/tahoma.ttf'),
                   ('SegoeUI', 'C:/Windows/Fonts/segoeui.ttf')]:
    cmap = TTFont(path).getBestCmap()
    missing = [hex(c) for c in codes if c not in cmap and c != 0x20]
    latin = all(ord(c) in cmap for c in 'HelloWorld')
    print(f'{name:11} latin={latin} missing_reshaped={missing if missing else "NONE"}')
