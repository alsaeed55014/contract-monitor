import arabic_reshaper as ar
from bidi.algorithm import get_display as gd
import re

_ar_rx = re.compile(r'[؀-ۿ]')
test_strings = ['مُحَمَّد', 'العربية', 'م', 'Hello', 'Male', '0570476258', 'PROGRAMMING PROG.', 'Alsaeed Alwazzan']

for t in test_strings:
    has_ar = bool(_ar_rx.search(t))
    result = gd(ar.reshape(t)) if has_ar else t
    print(repr(t), '-> ar?', has_ar, '->', repr(result))
