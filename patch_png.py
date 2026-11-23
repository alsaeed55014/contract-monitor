import io, os

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "            # ── Server-side PNG image (ReportLab + PyMuPDF for Arabic support) ──"
end_marker = "                return pix.tobytes(\"png\")"
start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)
end_idx = content.find('\n', end_idx) + 1

new_func = '''            # ── Server-side PNG image (ReportLab + PyMuPDF, two-column layout) ──
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

                def _sw(_t, _font, _size):
                    try:
                        return pdfmetrics.stringWidth(_sh(_t), _font, _size)
                    except Exception:
                        return len(str(_t)) * (_size * 0.55)

                def _wrap(_t, _font, _size, _maxw):
                    _out, _cur = [], ''
                    for _w in str(_t).split():
                        _cand = (_cur + ' ' + _w).strip()
                        if _sw(_cand, _font, _size) <= _maxw or not _cur:
                            _cur = _cand
                        else:
                            _out.append(_cur)
                            _cur = _w
                    if _cur:
                        _out.append(_cur)
                    return _out or ['']

                def _is_nat(_lbl):
                    _c = str(_lbl).lower()
                    return 'nationality' in _c or '\\u0627\\u0644\\u062c\\u0646\\u0633\\u064a\\u0629' in _c or '\\u062c\\u0646\\u0633\\u064a\\u0629' in _c

                def _is_gen(_lbl):
                    _c = str(_lbl).lower()
                    if 'nationality' in _c or '\\u0627\\u0644\\u062c\\u0646\\u0633\\u064a\\u0629' in _c or '\\u062c\\u0646\\u0633\\u064a\\u0629' in _c:
                        return False
                    return ('gender' in _c or '\\u0627\\u0644\\u0646\\u0648\\u0639' in _c or 'sex' in _c
                            or _c.strip() in ['\\u0627\\u0644\\u062c\\u0646\\u0633', 'gender'] or '\\u0627\\u0644\\u062c\\u0646\\u0633' in _c)

                def _gen_kind(_v):
                    _l = str(_v).lower().strip()
                    if any(w in _l for w in ['female', '\\u0623\\u0646\\u062b\\u0649', '\\u0627\\u0646\\u062b\\u0649', '\\u0627\\u0646\\u0627\\u062b', '\\u0623\\u0646\\u0627\\u062b', '\\u0627\\u0645\\u0631\\u0623\\u0629', '\\u0627\\u0645\\u0631\\u0627\\u0629']) or _l in ['f', '\\u0623\\u0646\\u062b\\u0649', '\\u0627\\u0646\\u062b\\u0649']:
                        return 'F'
                    if any(w in _l for w in ['male', '\\u0620\\u0643\\u0631', '\\u0631\\u062c\\u0644']) or _l in ['m', '\\u0620\\u0643\\u0631']:
                        return 'M'
                    return ''

                def _flag_img(_code):
                    if not _has_rq:
                        return None
                    _ck = f'_flg2_{str(_code).lower()}'
                    if _ck in st.session_state:
                        return st.session_state[_ck]
                    _d = None
                    try:
                        _r = _rq.get(f'https://flagcdn.com/w160/{str(_code).lower()}.png', timeout=8)
                        if _r.status_code == 200 and _r.content:
                            _d = _io.BytesIO(_r.content)
                    except Exception:
                        _d = None
                    st.session_state[_ck] = _d
                    return _d

                def _entry_text(_it):
                    if _it['is_empty']:
                        return ('\\u063a\\u064a\\u0631 \\u0645\\u0633\\u062c\\u0644' if is_ar else 'Not recorded')
                    _v = str(_it['value'])
                    if is_ar:
                        try:
                            _v = t_val(_v, 'ar', _it['orig_label'])
                        except Exception:
                            pass
                    return _v

                _rows = []
                for _sk, _stitle in sections_def:
                    _items = [it for it in visible_fields if classify_field(it) == _sk]
                    if not _items:
                        continue
                    _rows.append({'t': 'sec', 'title': _stitle, 'n': len(_items)})
                    for _it in _items:
                        _vt = _entry_text(_it)
                        _fk, _gk, _fl = '', '', None
                        if not _it['is_empty']:
                            if _is_nat(_it['label']):
                                try:
                                    _nc = _get_nationality_code(_it['value'])
                                except Exception:
                                    _nc = None
                                if _nc:
                                    _nc = str(_nc).strip().lower()
                                    try:
                                        _vt = get_country_display_name(_nc, 'ar' if is_ar else 'en') or _vt
                                    except Exception:
                                        pass
                                    _fl = _flag_img(_nc)
                            elif _is_gen(_it['label']):
                                _gk = _gen_kind(_vt)
                        _rows.append({'t': 'row', 'label': str(_it['label']), 'val': _vt,
                                      'gen': _gk, 'flag': _fl, 'empty': bool(_it['is_empty'])})

                def _reserve(_en):
                    if _en['gen'] in ('M', 'F'):
                        return 112
                    if _en['flag'] is not None:
                        return 50
                    return 0

                def _plan(_en, _textw):
                    _avail = max(120, _textw - _reserve(_en))
                    _lab = _sh(str(_en['label']).rstrip(':\\uff1a').strip() + ':')
                    _labw = pdfmetrics.stringWidth(_lab, _T_LAB, _S_LAB)
                    _vlines = _wrap(_en['val'], _T_VAL, _S_VAL, _avail)
                    if _labw + _sw(_vlines[0], _T_VAL, _S_VAL) <= _avail:
                        return (True, _lab, _labw, _vlines)
                    return (False, _lab, _labw, _vlines)

                def _row_h(_en, _textw):
                    _comb, _lab, _labw, _vlines = _plan(_en, _textw)
                    if _comb:
                        _n = len(_vlines)
                    else:
                        _n = len(_vlines) + 1
                    return max(56, _n * _LH + _VPAD * 2)

                _layout, _i = [], 0
                while _i < len(_rows):
                    _e = _rows[_i]
                    if _e['t'] == 'sec':
                        _layout.append(_e)
                        _i += 1
                        continue
                    _tw = _CELLW - _TXTPAD * 2
                    if _i + 1 < len(_rows) and _rows[_i + 1]['t'] == 'row':
                        _e2 = _rows[_i + 1]
                        _layout.append({'t': 'pair', 'a': _e, 'b': _e2,
                                        'h': max(_row_h(_e, _tw), _row_h(_e2, _tw))})
                        _i += 2
                    else:
                        _layout.append({'t': 'single', 'a': _e, 'h': _row_h(_e, _CW - _TXTPAD * 2)})
                        _i += 1

                _title = '\\u0627\\u0644\\u0628\\u064a\\u0627\\u0646\\u0627\\u062a \\u0627\\u0644\\u0643\\u0627\\u0645\\u0644\\u0629 \\u0627\\u0644\\u0645\\u0633\\u062c\\u0644\\u0629 \\u0644\\u0644\\u0639\\u0627\\u0645\\u0644' if is_ar else 'Complete Registered Worker Data'
                _meta = (f"{'\\u0625\\u062c\\u0645\\u0627\\u0644\\u064a \\u0627\\u0644\\u062d\\u0642\\u0648\\u0644' if is_ar else 'Total'}: {total_fields_count} | "
                         f"{'\\u0627\\u0644\\u0645\\u0633\\u062c\\u0644\\u0629' if is_ar else 'Filled'}: {filled_count} | {_now_str}")
                _t_lines = _wrap(_title, _f_bold, 34, _CW - 90)
                _n_lines = _wrap(str(worker_name), _f_bold, 30, _CW - 90)
                _m_lines = _wrap(_meta, _f_reg, 21, _CW - 90)

                _head_h = len(_t_lines) * 44 + len(_n_lines) * 40 + len(_m_lines) * 26 + 52
                _H = 30 + _head_h + 22
                for _e in _layout:
                    _H += (54 if _e['t'] == 'sec' else _e['h']) + 8
                _H += 24 + 30 + 66 + 30

                _buf = _io.BytesIO()
                c = canvas.Canvas(_buf, pagesize=(_W, _H))
                _y = _H - 30

                c.setStrokeColor(Color(0, 0, 0))
                c.setLineWidth(3)
                c.roundRect(_M - 8, _y - _head_h, _CW + 16, _head_h, 16, stroke=1, fill=0)
                _ty = _y - 34
                c.setFillColor(Color(0, 0, 0))
                for _ln in _t_lines:
                    c.setFont(_f_bold, 34)
                    c.drawCentredString(_W // 2, _ty, _sh(_ln))
                    _ty -= 44
                for _ln in _n_lines:
                    c.setFont(_f_bold, 30)
                    c.drawCentredString(_W // 2, _ty, _sh(_ln))
                    _ty -= 40
                c.setFillColor(Color(0.36, 0.36, 0.36))
                for _ln in _m_lines:
                    c.setFont(_f_reg, 21)
                    c.drawCentredString(_W // 2, _ty, _sh(_ln))
                    _ty -= 26

                _y -= _head_h + 22

                def _draw_cell(_en, _x0, _x1, _rh, _yy):
                    _x1 = _x1 - _TXTPAD
                    _x0 = _x0 + _TXTPAD
                    _comb, _lab, _labw, _vlines = _plan(_en, (_x1 - _x0) - _reserve(_en))
                    _n = len(_vlines) if _comb else len(_vlines) + 1
                    _cy = _yy + (_rh - _n * _LH) // 2

                    _ix = _x1
                    if _rtl:
                        if _en['gen'] in ('M', 'F'):
                            _col = Color(0.129, 0.588, 0.953) if _en['gen'] == 'M' else Color(0.925, 0.251, 0.478)
                            _g = '\\u062\\u0630\\u0643\\u0631' if _en['gen'] == 'M' else '\\u0623\\u0646\\u062b\\u0649'
                            c.setFillColor(_col)
                            c.roundRect(_ix - 100, _cy + 2, 100, 28, 14, stroke=0, fill=1)
                            c.setFillColor(Color(1, 1, 1))
                            c.setFont(_f_bold, 18)
                            c.drawCentredString(_ix - 50, _cy + 10, _sh(_g))
                            _ix -= 112
                        elif _en['flag'] is not None:
                            try:
                                c.drawImage(ImageReader(_en['flag']), _ix - 44, _cy + 1, width=44, height=29,
                                            preserveAspectRatio=True, anchor='c', mask='auto')
                                _ix -= 54
                            except Exception:
                                pass
                        c.setFillColor(Color(0.51, 0.51, 0.51) if _en['empty'] else Color(0, 0, 0))
                        c.setFont(_T_LAB, _S_LAB)
                        c.drawRightString(_ix, _cy + 4, _lab)
                        c.setFillColor(Color(0.51, 0.51, 0.51) if _en['empty'] else Color(0, 0, 0))
                        if _comb:
                            c.setFont(_T_VAL, _S_VAL)
                            c.drawRightString(_ix - _labw, _cy + 4, _sh(_vlines[0]))
                            _vy = _cy - _LH + 4
                            for _ln in _vlines[1:]:
                                c.drawRightString(_ix, _vy, _sh(_ln))
                                _vy -= _LH
                        else:
                            _vy = _cy - _LH + 4
                            for _ln in _vlines:
                                c.setFont(_T_VAL, _S_VAL)
                                c.drawRightString(_ix, _vy, _sh(_ln))
                                _vy -= _LH
                    else:
                        if _en['gen'] in ('M', 'F'):
                            _col = Color(0.129, 0.588, 0.953) if _en['gen'] == 'M' else Color(0.925, 0.251, 0.478)
                            _g = 'Male' if _en['gen'] == 'M' else 'Female'
                            c.setFillColor(_col)
                            c.roundRect(_x0, _cy + 2, 100, 28, 14, stroke=0, fill=1)
                            c.setFillColor(Color(1, 1, 1))
                            c.setFont(_f_bold, 18)
                            c.drawCentredString(_x0 + 50, _cy + 10, _g)
                            _x0 += 112
                        elif _en['flag'] is not None:
                            try:
                                c.drawImage(ImageReader(_en['flag']), _x0, _cy + 1, width=44, height=29,
                                            preserveAspectRatio=True, anchor='c', mask='auto')
                                _x0 += 54
                            except Exception:
                                pass
                        c.setFillColor(Color(0.51, 0.51, 0.51) if _en['empty'] else Color(0, 0, 0))
                        c.setFont(_T_LAB, _S_LAB)
                        c.drawString(_x0, _cy + 4, _lab)
                        c.setFillColor(Color(0.51, 0.51, 0.51) if _en['empty'] else Color(0, 0, 0))
                        if _comb:
                            c.setFont(_T_VAL, _S_VAL)
                            c.drawString(_x0 + _labw, _cy + 4, _sh(_vlines[0]))
                            _vy = _cy - _LH + 4
                            for _ln in _vlines[1:]:
                                c.drawString(_x0, _vy, _sh(_ln))
                                _vy -= _LH
                        else:
                            _vy = _cy - _LH + 4
                            for _ln in _vlines:
                                c.setFont(_T_VAL, _S_VAL)
                                c.drawString(_x0, _vy, _sh(_ln))
                                _vy -= _LH

                for _e in _layout:
                    if _e['t'] == 'sec':
                        c.setFillColor(Color(0, 0, 0))
                        c.roundRect(_M, _y - 44, _CW, 44, 9, stroke=0, fill=1)
                        c.setFillColor(Color(1, 1, 1))
                        c.setFont(_f_bold, 25)
                        c.drawCentredString(_W // 2, _y - 34, _sh(f"{_e['title']} ({_e['n']})"))
                        _y -= 54
                        continue

                    _rh = _e['h']
                    c.setStrokeColor(Color(0, 0, 0))
                    c.setLineWidth(1.6)
                    c.rect(_M, _y - _rh, _CW, _rh, stroke=1, fill=0)
                    if _e['t'] == 'pair':
                        _mid = _M + _CELLW + _CELLGAP // 2
                        c.setLineWidth(1)
                        c.setStrokeColor(Color(0.55, 0.55, 0.55))
                        c.line(_mid, _y - _rh, _mid, _y)
                        c.setLineWidth(1.6)
                        if _rtl:
                            _draw_cell(_e['a'], _mid, _M + _CW, _rh, _y - _rh)
                            _draw_cell(_e['b'], _M, _mid, _rh, _y - _rh)
                        else:
                            _draw_cell(_e['a'], _M, _mid, _rh, _y - _rh)
                            _draw_cell(_e['b'], _mid, _M + _CW, _rh, _y - _rh)
                    else:
                        _draw_cell(_e['a'], _M, _M + _CW, _rh, _y - _rh)
                    _y -= _rh + 8

                _y -= 16
                c.setStrokeColor(Color(0.63, 0.63, 0.63))
                c.setLineWidth(1.4)
                c.line(_M + 60, _y, _W - _M - 60, _y)
                _y -= 26
                c.setFillColor(Color(0.60, 0.49, 0.12))
                c.setFont(_f_reg, 19)
                c.drawCentredString(_W // 2, _y, 'PROGRAMMING  \\u2022  PROG.')
                _y -= 44
                c.setFillColor(Color(0.54, 0.40, 0.03))
                c.setFont(_f_reg, 26)
                c.drawCentredString(_W // 2, _y, 'Alsaeed Alwazzan')

                c.showPage()
                c.save()

                doc = fitz.open("pdf", _buf.getvalue())
                pix = doc.load_page(0).get_pixmap(dpi=150)
                return pix.tobytes("png")
'''

content = content[:start_idx] + new_func + content[end_idx:]
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Replaced OK")
