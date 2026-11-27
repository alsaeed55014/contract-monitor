# Comprehensive test of _sh function with edge cases
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

# Test cases including edge cases
test_cases = [
    # Pure English
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

    # Mixed Arabic-English (should preserve English parts)
    'Complete (العمال) Registered (العمال) Worker Data',
    'Name: (الاسم)',
    'Nationality: (الجنسية)',
    'Gender: (الجنس)',
    'Age: (العمر)',
    '0570476258 (رقم الهاتف)',

    # Pure Arabic (should be processed)
    'مُحَمَّد',
    'العربية',
    'م',
    'السلام عليكم',

    # Numbers and symbols (should remain unchanged)
    '1234567890',
    '057-047-6258',
    'PROGRAMMING@PROG',
    'Alsaeed_Alwazzan',
    '2026-11-23',
    '19:52',
]

print("Testing _sh function with comprehensive cases:")
for t in test_cases:
    out = _sh(t)
    status = 'OK' if out == t else 'DIFF'
    print(f'{status:4} in={t!r:40} out={out!r}')