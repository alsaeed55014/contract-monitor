from fontTools.ttLib import TTFont
import os, glob

candidates = ['arial.ttf', 'arialbd.ttf', 'tahoma.ttf', 'tahomabd.ttf',
              'segoeui.ttf', 'segoeuib.ttf', 'calibri.ttf', 'calibrib.ttf',
              'times.ttf', 'timesbd.ttf', 'verdana.ttf', 'verdanab.ttf']

for name in candidates:
    path = 'C:/Windows/Fonts/' + name
    if not os.path.exists(path):
        continue
    try:
        font = TTFont(path)
        cmap = font.getBestCmap()
        latin_ok = all(ord(c) in cmap for c in 'HelloWorld')
        digits_ok = all(ord(c) in cmap for c in '0123456789')
        arabic_ok = all(ord(c) in cmap for c in 'مرحبا')
        print(f'{name:16} latin={latin_ok} digits={digits_ok} arabic={arabic_ok}')
    except Exception as e:
        print(f'{name:16} ERR {e}')
