import streamlit as st
import os
import json
from datetime import datetime
from src.utils.phone_utils import mask_phone

def show_toast(msg, typ="info", container=None):
    """Modern toast with luxury styling."""
    color = "#D4AF37" # Gold
    if typ == "success": color = "#00FF41" # Neon Green
    elif typ == "error": color = "#FF3131" # Neon Red
    
    html = f"""
    <div style="
        padding: 15px 25px;
        background: rgba(10, 10, 10, 0.9);
        border-left: 5px solid {color};
        border-radius: 10px;
        color: white;
        font-family: 'Cairo', sans-serif;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        margin: 10px 0;
        animation: toast-in 0.5s ease-out;
    ">
        {msg}
    </div>
    <style>
    @keyframes toast-in {{
        from {{ transform: translateX(100%); opacity: 0; }}
        to {{ transform: translateX(0); opacity: 1; }}
    }}
    </style>
    """
    if container:
        container.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(html, unsafe_allow_html=True)

def get_flag(nat_name):
    """Converts nationality name to emoji flag."""
    nat_name = str(nat_name).lower().strip()
    flags = {
        'مصر': '🇪🇬', 'مصري': '🇪🇬', 'egypt': '🇪🇬',
        'السودان': '🇸🇩', 'سوداني': '🇸🇩', 'sudan': '🇸🇩',
        'باكستان': '🇵🇰', 'باكستاني': '🇵🇰', 'pakistan': '🇵🇰',
        'الهند': '🇮🇳', 'هندي': '🇮🇳', 'india': '🇮🇳',
        'اليمن': '🇾🇪', 'يمني': '🇾🇪', 'yemen': '🇾🇪',
        'بنجلاديش': '🇧🇩', 'بنجالي': '🇧🇩', 'bangladesh': '🇧🇩',
        'الفلبين': '🇵🇭', 'فلبيني': '🇵🇭', 'philippines': '🇵🇭',
        'كينيا': '🇰🇪', 'كيني': '🇰🇪', 'kenya': '🇰🇪',
        'أوغندا': '🇺🇬', 'أوغندي': '🇺🇬', 'uganda': '🇺🇬',
        'إثيوبيا': '🇪🇹', 'إثيوبي': '🇪🇹', 'ethiopia': '🇪🇹',
    }
    for k, v in flags.items():
        if k in nat_name: return v
    return '🏁'

def safe_val(row, col_name):
    if col_name is None: return '---'
    if hasattr(row, 'get'):
        val = str(row.get(col_name, '---')).strip()
    else:
        val = str(row).strip()
    if val in ['nan', 'None', '', 'NaN']: return '---'
    return val

def find_col(df, options):
    for o in options:
        match = next((c for c in df.columns if o.lower() in str(c).lower()), None)
        if match: return match
    return None

def silent_notification_monitor():
    """Background monitor for new entries (Placeholder for app.py integration)."""
    # This is normally called in app.py to trigger the background check
    pass
