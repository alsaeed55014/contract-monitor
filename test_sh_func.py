# Test the current _sh behavior on various strings
import re

_ar_rx = re.compile(r'[؀-ۿ]')
_emoji_rx = re.compile('[\U0001F000-\U0001FAFF]')

def _sh(_t):
    _t = _emoji_rx.sub('', str(_t))
    if _ar_rx.search(_t):
        try:
            import arabic_reshaper as _ar_resh
            from bidi.algorithm import get_display as _bidi_disp
            return _bidi_disp(_ar_resh.reshape(_t))
        except Exception:
            return _t
    return _t

# English strings used in the PNG
tests = [
    'Complete Registered Worker Data',
    'Total: 6 | Filled: 6 | 2026-11-23 19:52',
    'Name:',
    'Nationality:',
    'Gender:',
    'Age:',
    'Male',
    'Female',
    '0570476258',
    'PROGRAMMING  •  PROG.',
    'Alsaeed Alwazzan',
    'Not recorded',
    '20261124',
    'Personal Info (6)',
    'Job Details (16)',
    '259',
    '41',
]
for t in tests:
    out = _sh(t)
    status = 'OK ' if out == t else 'DIFF'
    print(f'{status} in={t!r} out={out!r}')
