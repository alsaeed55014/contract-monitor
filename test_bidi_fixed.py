import arabic_reshaper as ar
from bidi.algorithm import get_display as gd
import re

_ar_rx = re.compile(r'[؀-ۿ]')
test_strings = ['م', 'Hello', '0570476258', 'PROGRAMMING PROG.']

for t in test_strings:
    has_ar = bool(_ar_rx.search(t))
    result = gd(ar.reshape(t)) if has_ar else t
    print('ar?' + str(has_ar), 'applied' if has_ar else 'original')