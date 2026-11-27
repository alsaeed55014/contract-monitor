from fontTools.ttLib import TTFont

for name in ['DejaVuSans.ttf', 'Amiri-Regular.ttf']:
    try:
        font = TTFont('fonts/' + name)
        cmap = font.getBestCmap()
        latin_chars = [c for c in 'HelloWorldabcXYZ' if ord(c) in cmap]
        digit_chars = [c for c in '0123456789' if ord(c) in cmap]
        arabic_chars = [c for c in 'مرحبا' if ord(c) in cmap]
        punct_chars = [c for c in ':,.-()[]{}' if ord(c) in cmap]
        print(name)
        print(f'  Latin chars found: {latin_chars}')
        print(f'  Digits found: {digit_chars}')
        print(f'  Arabic chars found: {arabic_chars}')
        print(f'  Punctuation found: {punct_chars}')
    except Exception as e:
        print(name, 'ERR', e)