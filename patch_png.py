'''            # ── Server-side PNG image (ReportLab + PyMuPDF, two-column layout) ──
            def _build_worker_png_bytes():
                import io as _io
                import os as _os
                import fitz
                from reportlab.pdfgen import canvas
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                from reportlab.lib.colors import Color
                from reportlab.lib.utils import ImageReader
                import arabic_reshaper as _ar_resh
                from bidi.algorithm import get_display as _bidi_disp
                import re as _rx2
                try:
                    import requests as _rq
                    _has_rq = True
                except Exception:
                    _has_rq = False

                _ar_rx = _rx2.compile(r'[\\u0600-\\u06FF]')
                _emoji_rx = _rx2.compile('[\\U0001F000-\\U0001FAFF\\u2600-\\u27BF\\u2B00-\\u2BFF\\uFE0F\\u200D]')
                _proj = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
                _ar = os.path.join(_proj, 'NotoSansArabic-Regular.ttf')
                _ar_b = os.path.join(_proj, 'NotoSansArabic-Bold.ttf')
                try:
                    pdfmetrics.registerFont(TTFont('ArabicRegular', _ar))
                    pdfmetrics.registerFont(TTFont('ArabicBold', _ar_b))
                    _f_reg, _f_bold = 'ArabicRegular', 'ArabicBold'
                except Exception:
                    _f_reg, _f_bold = 'Helvetica', 'Helvetica-Bold'

                # Register Latin fonts for English text
                _lat = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arial.ttf')
                _lat_b = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arialbd.ttf')
                try:
                    pdfmetrics.registerFont(TTFont('LatinRegular', _lat))
                    pdfmetrics.registerFont(TTFont('LatinBold', _lat_b))
                    _l_reg, _l_bold = 'LatinRegular', 'LatinBold'
                except Exception:
                    _l_reg, _l_bold = 'Helvetica', 'Helvetica-Bold'

                def _sh(_t):
                    _t = _emoji_rx.sub('', str(_t))
                    if _ar_rx.search(_t):
                        try:
                            return _bidi_disp(_ar_resh.reshape(_t))
                        except Exception:
                            return _t
                    return _t

                _rtl = bool(is_ar)
                _W, _M = 1440, 40
                _CW = _W - 2 * _M
                _TXTPAD, _VPAD, _CELLGAP = 14, 8, 14
                _CELLW = (_CW - _CELLGAP) // 2
                _LH = 32
                _T_LAB, _S_LAB = _f_bold, 23
                _T_VAL, _S_VAL = _f_reg, 24