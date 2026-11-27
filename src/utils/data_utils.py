import pandas as pd
import re
import streamlit as st

def build_auto_column_config(df_or_styler, cfg=None):
    """Auto-fit every column to its header + content (exact width, no truncation).

    Shared helper for tables that don't use pinning (WhatsApp results, modals,
    previews). Headers render centered, body cells far-left. Existing entries
    (ImageColumn/LinkColumn/NumberColumn) keep their type and only gain an
    exact pixel width. Returns the cfg dict ready for st.dataframe.
    """
    if cfg is None:
        cfg = {}

    if hasattr(df_or_styler, 'data'):
        df_temp = df_or_styler.data
        cols = list(df_temp.columns)
    elif hasattr(df_or_styler, 'columns'):
        df_temp = df_or_styler
        cols = list(df_temp.columns)
    else:
        return cfg

    def estimate_px(text):
        s = str(text).replace("\xA0", "").strip()
        if s in ("", "nan", "None", "NaT", "-"):
            return 0
        px = 0
        for char in s:
            o = ord(char)
            if 0x1F300 <= o <= 0x1FAFF or 0x2600 <= o <= 0x27BF or 0xFE00 <= o <= 0xFE0F or char in ("✅", "❌", "⚠️", "🚹", "🚺"):
                px += 14
            elif '\u0600' <= char <= '\u06FF':
                px += 8
            elif char.isupper():
                px += 8.5
            elif char.isdigit():
                px += 7.5
            elif char.islower():
                px += 6.5
            else:
                px += 5
        return px

    for col in cols:
        col_str = str(col).replace("\xA0", "").strip()
        if col_str.startswith("__"):
            continue
        if col_str.startswith("🚩") or "🏳️" in col_str:
            if col in cfg:
                try:
                    cfg[col]["width"] = 52
                except Exception:
                    pass
            else:
                cfg[col] = st.column_config.ImageColumn(label=col_str, width=52)
            continue
        header_px = estimate_px(col_str)
        max_px = header_px
        try:
            _cfg_tc = (cfg.get(col, {}) or {}).get("type_config") or {}
        except Exception:
            _cfg_tc = {}
        _is_link_cfg = isinstance(_cfg_tc, dict) and _cfg_tc.get("type") == "link"
        _is_img_cfg = isinstance(_cfg_tc, dict) and _cfg_tc.get("type") == "image"
        if _is_link_cfg:
            max_px = max(max_px, 40.0)
        elif _is_img_cfg:
            max_px = header_px
        else:
            try:
                vals = df_temp[col].astype(str)
                vals = vals[~vals.isin(["", "nan", "None", "NaT", "None ", "nan "])]
                if not vals.empty:
                    data_px = vals.apply(estimate_px).max()
                    if pd.notna(data_px):
                        max_px = max(max_px, float(data_px))
            except Exception:
                pass
        fit_px = max(50, min(int(max_px + 14), 460))
        try:
            _tc = (cfg.get(col, {}) or {}).get("type_config") or {}
        except Exception:
            _tc = {}
        _is_link = isinstance(_tc, dict) and _tc.get("type") == "link"
        _cl = col_str.lower().strip()
        _is_cv = _is_link or ("سيرة" in col_str) or ("download cv" in _cl) or (_cl == "cv")
        if _is_cv:
            _align = "center"
        else:
            _align = "left"
            try:
                _rtl_hit = any('\u0600' <= ch <= 'ۿ' for ch in col_str)
                if not _rtl_hit and col in df_temp.columns:
                    _svals = df_temp[col].astype(str)
                    _samp = _svals.head(60) if len(_svals) > 60 else _svals
                    for _v in _samp:
                        _s = str(_v)
                        if any('\u0600' <= ch <= 'ۿ' for ch in _s):
                            _rtl_hit = True
                            break
                        for _ch in _s:
                            _o = ord(_ch)
                            if 0x1F300 <= _o <= 0x1FAFF or 0x2600 <= _o <= 0x27BF or 0xFE00 <= _o <= 0xFE0F:
                                _rtl_hit = True
                                break
                        if _rtl_hit:
                            break
                if _rtl_hit:
                    _align = "right"
            except Exception:
                pass
        _is_flag = col_str.startswith("🚩") or "🏳️" in col_str or (isinstance(_tc, dict) and _tc.get("type") == "image")
        if col in cfg:
            try:
                cfg[col]["width"] = fit_px
                try:
                    lbl = cfg[col].get("label")
                    if isinstance(lbl, str) and "\xA0" in lbl:
                        cfg[col]["label"] = col_str
                except Exception:
                    pass
                if not _is_flag:
                    try:
                        cfg[col]["alignment"] = _align
                    except Exception:
                        pass
            except Exception:
                pass
        else:
            try:
                is_num = pd.api.types.is_numeric_dtype(df_temp[col])
            except Exception:
                is_num = False
            if is_num:
                cfg[col] = st.column_config.TextColumn(label=col_str, width=fit_px)
            else:
                cfg[col] = st.column_config.Column(label=col_str, width=fit_px)
            if not _is_flag:
                try:
                    cfg[col]["alignment"] = _align
                except Exception:
                    pass
    return cfg
def sort_by_reg_date_desc(df):
    """Sort any data table newest-first by registration date (الأحدث أولاً).

    Finds the registration/timestamp column (original or translated names),
    parses dates robustly (Arabic-Indic digits, ص/م markers), sorts newest
    first with undated rows last. Returns the frame unchanged when there is
    no date column or nothing to sort — safe to call on every table.
    Index labels are preserved, so row-selection mappings keep working.
    """
    try:
        if df is None or getattr(df, "empty", True):
            return df
        cols = [c for c in df.columns if not str(c).startswith("__")]
        keys = ["طابع زمني", "تاريخ التسجيل", "وقت التسجيل", "timestamp",
                "registration date", "تاريخ التقديم", "date submitted",
                "تاريخ الإدخال", "insertion date", "تاريخ الطلب",
                "أنشئ في", "created"]
        ts_col = None
        for c in cols:
            cl = str(c).lower().strip()
            if any(k in cl for k in keys):
                ts_col = c
                break
        if ts_col is None:
            return df

        _ar2w = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

        def _parse(v):
            try:
                if v is None:
                    return pd.NaT
                s = str(v).translate(_ar2w).strip()
                if not s or s.lower() == "nan":
                    return pd.NaT
                if 'ص' in s or 'م' in s:
                    mk = 'AM' if 'ص' in s else 'PM'
                    s = re.sub(r'[صم]', '', s).strip() + " " + mk
                try:
                    from dateutil import parser as _prs
                    return pd.Timestamp(_prs.parse(s, dayfirst=False))
                except Exception:
                    return pd.to_datetime(s, errors='coerce')
            except Exception:
                return pd.NaT

        out = df.copy()
        out["__reg_sort__"] = out[ts_col].apply(_parse)
        out = out.sort_values(by="__reg_sort__", ascending=False,
                              kind="mergesort", na_position="last")
        return out.drop(columns=["__reg_sort__"], errors="ignore")
    except Exception:
        return df
