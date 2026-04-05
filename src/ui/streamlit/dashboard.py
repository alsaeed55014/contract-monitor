import streamlit as st
import pandas as pd
import time
from datetime import datetime
from src.core.contracts import ContractManager
from src.core.i18n import t, t_col
from src.utils.phone_utils import create_pasha_whatsapp_excel, render_pasha_export_button
from src.ui.streamlit_components import show_loading_hourglass, render_cv_detail_panel, render_table_translator
from src.utils.data_utils import style_df, clean_date_display

def __apply_pinned_columns(df_or_style, cfg=None):
    if cfg is None: cfg = {}
    pin_keywords = ["حالة العقد", "contract status", "status", "وقت", "طابع", "الاسم", "name", "جنسية", "nationality", "🚩", "جنس", "gender"]
    if hasattr(df_or_style, 'data'): cols = df_or_style.data.columns
    elif hasattr(df_or_style, 'columns'): cols = df_or_style.columns
    else: return cfg
    for col in cols:
        if any(kw in str(col).lower() for kw in pin_keywords):
            if col not in cfg: cfg[col] = st.column_config.Column(pinned=True)
            else:
                try: cfg[col].pinned = True
                except: pass
    return cfg

def render_dashboard_content():
    lang = st.session_state.lang
    st.markdown('<div class="programmer-signature-neon">By: Alsaeed Alwazzan (v2.1)</div>', unsafe_allow_html=True)
    st.title(f" {t('contract_dashboard', lang)}")
    
    loading_placeholder = st.empty()
    show_loading_hourglass(container=loading_placeholder)
    
    try:
        df = st.session_state.db.fetch_data()
    except Exception as e:
        loading_placeholder.empty()
        st.error(f"{t('error', lang)}: {e}")
        return

    if df.empty:
        loading_placeholder.empty()
        st.warning(t("no_data", lang))
        return

    cols = df.columns.tolist()
    date_col = next((c for c in cols if any(kw in str(c).lower() for kw in ["contract end", "انتهاء العقد", "contract expiry"])), None)
    
    if not date_col:
        loading_placeholder.empty()
        st.error("Error: Could not find the 'Contract End' column.")
        return

    stats = {'urgent': [], 'expired': [], 'active': []}
    for _, row in df.iterrows():
        try:
            status = ContractManager.calculate_status(row[date_col])
            r = row.to_dict()
            global_status = status['status']
            days = status.get('days', 0) or 9999
            r['__days_sort'] = days
            if lang == 'ar':
                if global_status == 'expired': r['حالة العقد'] = f"❌ منتهي (منذ {abs(days)} يوم)"
                elif global_status in ['urgent', 'warning']: r['حالة العقد'] = f"⚠️ عاجل (متبقى {days} يوم)"
                else: r['حالة العقد'] = f"✅ ساري (متبقى {days} يوم)"
            else:
                r['Contract Status'] = f"{status['label_en']} ({abs(days)} Days)"

            if global_status in ['urgent', 'warning']: stats['urgent'].append(r)
            elif global_status == 'expired': stats['expired'].append(r)
            elif global_status == 'active': stats['active'].append(r)
        except: continue

    loading_placeholder.empty()

    c1, c2, c3 = st.columns(3)
    st.markdown(f'<style>.metric-container {{ text-align:center; padding:20px; border-radius:15px; border:1px solid #444; }} .glow-orange {{ border-color: orange; }} .glow-red {{ border-color: red; }} .glow-green {{ border-color: green; }}</style>', unsafe_allow_html=True)
    with c1: st.markdown(f'<div class="metric-container glow-orange"><div>{t("urgent_7_days", lang)}</div><div style="font-size:2rem;">{len(stats["urgent"])}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-container glow-red"><div>{t("expired", lang)}</div><div style="font-size:2rem;">{len(stats["expired"])}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-container glow-green"><div>{t("active", lang)}</div><div style="font-size:2rem;">{len(stats["active"])}</div></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    t1, t2, t3 = st.tabs([t("tabs_urgent", lang), t("tabs_expired", lang), t("tabs_active", lang)])
    
    def show(data, tab_id):
        if not data: st.info(t("no_data", lang)); return
        d = pd.DataFrame(data)
        if tab_id == 'expired':
            d['__abs_days'] = d['__days_sort'].abs()
            d = d.sort_values(by='__abs_days', ascending=True).drop(columns=['__abs_days'])
        else:
            d = d.sort_values(by='__days_sort', ascending=True)
        
        status_key = 'حالة العقد' if lang == 'ar' else 'Contract Status'
        show_cols = [status_key] + [c for c in cols if c in d.columns and not str(c).startswith('__')]
        d_final = d[show_cols].copy()
        
        new_names = {c: t_col(c, lang) for c in d_final.columns}
        d_final.rename(columns=new_names, inplace=True)
        d_final = clean_date_display(d_final)
        
        final_cfg = {}
        cv_col_found = next((c for c in cols if any(kw in str(c).lower() for kw in ["cv", "سيرة", "download"])), None)
        if cv_col_found and cv_col_found in new_names:
            final_cfg[new_names[cv_col_found]] = st.column_config.LinkColumn(t("cv_download", lang), display_text=t("download_pdf", lang))
        
        d_final = render_table_translator(d_final, key_prefix=f"dash_{tab_id}")
        styled_final = style_df(d_final)
        
        event = st.dataframe(styled_final, use_container_width=True, column_config=__apply_pinned_columns(styled_final, final_cfg), on_select="rerun", selection_mode="single-row", hide_index=True, key=f"dash_table_{lang}_{tab_id}")
        
        if event.selection and event.selection.get("rows"):
            sel_idx = event.selection["rows"][0]
            worker_row = d.iloc[sel_idx]
            render_cv_detail_panel(worker_row, sel_idx, lang, key_prefix=f"dash_{tab_id}")

    with t1: show(stats['urgent'], "urgent")
    with t2: show(stats['expired'], "expired")
    with t3: show(stats['active'], "active")
