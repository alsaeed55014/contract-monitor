import streamlit as st
import os
import time
import base64
from datetime import datetime
from src.core.i18n import t

def show_toast(message, typ="success", duration=5, container=None):
    is_contextual = container is not None
    if is_contextual:
        pos_css = "position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 340px;"
    else:
        pos_css = "position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 90%; max-width: 440px;"
    
    if typ == "success":
        icon_path = '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" fill="#D4AF37"/>'
        bg = "linear-gradient(135deg, #1A1A1A 0%, #000 100%)"
        accent = "#D4AF37"
    elif typ == "error":
        icon_path = '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" fill="#FF4B4B"/>'
        bg = "linear-gradient(135deg, #2D0A0A 0%, #000 100%)"
        accent = "#FF4B4B"
    elif typ == "warning":
        icon_path = '<path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" fill="#FFA500"/>'
        bg = "linear-gradient(135deg, #2D200A 0%, #000 100%)"
        accent = "#FFA500"
    else:
        icon_path = '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z" fill="#00BFFF"/>'
        bg = "linear-gradient(135deg, #0A1A2D 0%, #000 100%)"
        accent = "#00BFFF"

    wrapper_start = '<div style="position: relative; width: 100%; height: 0; min-height: 0;">' if is_contextual else ''
    wrapper_end = '</div>' if is_contextual else ''

    toast_html = f"""
    {wrapper_start}
    <div style="{pos_css} z-index: 2147483647; pointer-events: none; direction: rtl;">
        <div style="
            background: {bg};
            border: 2px solid {accent};
            border-radius: 16px;
            box-shadow: 0 40px 100px rgba(0,0,0,0.95), 0 0 30px {accent}33;
            display: flex;
            align-items: center;
            padding: 18px 25px;
            gap: 18px;
            animation: luxuryToastCenter 5s cubic-bezier(0.1, 0.9, 0.2, 1) forwards;
            overflow: hidden;
            backdrop-filter: blur(10px);
        ">
            <style>
                @keyframes luxuryToastCenter {{
                    0%   {{ opacity: 0; transform: scale(0.6) translateY(20px); }}
                    10%  {{ opacity: 1; transform: scale(1.05) translateY(0); }}
                    15%  {{ transform: scale(1); }}
                    85%  {{ opacity: 1; transform: scale(1); }}
                    100% {{ opacity: 0; transform: scale(0.9) translateY(-20px); visibility: hidden; }}
                }}
            </style>
            <div style="width: 32px; height: 32px; flex-shrink: 0;">
                <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="{accent}22"/>{icon_path}</svg>
            </div>
            <div style="color: #FFF; font-size: 16px; font-weight: 700; flex-grow: 1; text-align: center; font-family: 'Cairo', sans-serif; line-height: 1.4;">
                {message}
            </div>
        </div>
    </div>
    {wrapper_end}
    """
    
    if container:
        container.markdown(toast_html, unsafe_allow_html=True)
    else:
        st.markdown(toast_html, unsafe_allow_html=True)

def show_loading_hourglass(text=None, container=None):
    if text is None:
        text = "جاري التحميل..." if st.session_state.get('lang') == 'ar' else "Loading..."
    
    target = container if container else st.empty()
    with target:
        st.markdown(f"""
            <div id="hourglass-overlay" style="
                position: fixed;
                top: 0; left: 0;
                width: 100vw; height: 100vh;
                background: rgba(0, 0, 0, 0.45);
                backdrop-filter: blur(3px);
                -webkit-backdrop-filter: blur(3px);
                z-index: 999999;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                pointer-events: all;
            ">
                <svg class="modern-hourglass-svg" viewBox="0 0 100 100" style="
                    width: 100px; height: 100px;
                    filter: drop-shadow(0 0 18px rgba(212, 175, 55, 0.8));
                ">
                    <path class="glass" d="M30,20 L70,20 L50,50 L70,80 L30,80 L50,50 Z" />
                    <path class="sand sand-top" d="M30,20 L70,20 L50,50 Z" />
                    <path class="sand sand-bottom" d="M50,50 L70,80 L30,80 Z" />
                    <rect class="sand-drip" x="49.5" y="50" width="1" height="30" />
                </svg>
                <p style="
                    color: #D4AF37;
                    font-size: 16px;
                    margin-top: 20px;
                    font-family: 'Cairo', sans-serif;
                    letter-spacing: 2px;
                    text-shadow: 0 0 10px rgba(212, 175, 55, 0.5);
                ">{text}</p>
            </div>
        """, unsafe_allow_html=True)
    return target

def render_table_translator(df, key_prefix="table"):
    if df is None or df.empty:
        return df

    target_keywords = [
        "وظيفة", "الوظيفة", "مهنة", "المهنة", "مهارة", "مهارات", "خبرة", "الخبرة",
        "job", "profession", "skill", "experience", "occupation"
    ]
    cols_to_translate = [c for c in df.columns if any(kw.lower() in str(c).lower() for kw in target_keywords)]

    if not cols_to_translate:
        return df

    from src.core.translation import TranslationManager
    tm = TranslationManager()

    st.markdown('<div class="table-translator-container">', unsafe_allow_html=True)
    ct1, ct2 = st.columns(2)
    
    t_state_key = f"table_trans_{key_prefix}"
    
    with ct1:
        st.markdown('<div class="table-translator-btn">', unsafe_allow_html=True)
        if st.button("🇸🇦 الترجمة للعربية", key=f"btn_ar_{key_prefix}", use_container_width=True):
            st.session_state[t_state_key] = "ar"
        st.markdown('</div>', unsafe_allow_html=True)

    with ct2:
        st.markdown('<div class="table-translator-btn">', unsafe_allow_html=True)
        if st.button("🇵🇭 ISALIN SA TAGALOG", key=f"btn_tl_{key_prefix}", use_container_width=True):
            st.session_state[t_state_key] = "tl"
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    target_lang = st.session_state.get(t_state_key)
    if target_lang in ['ar', 'tl']:
        with st.spinner("جارِ الترجمة..." if target_lang == 'ar' else "Isinasalin..."):
            for col in cols_to_translate:
                unique_vals = [v for v in df[col].unique() if v and isinstance(v, str)]
                if unique_vals:
                    translations = {val: tm.translate_full_text(val, target_lang=target_lang) for val in unique_vals}
                    df[col] = df[col].map(translations).fillna(df[col])
    
    return df

def render_top_banner(user, lang, auth_manager):
    import streamlit as st
    from datetime import datetime
    
    notifs = st.session_state.get('notifications', [])
    notif_count = len(notifs)

    if st.session_state.get('notif_triggered'):
        st.components.v1.html("""
<script>
(async function(){
    try {
        var AudioContext = window.AudioContext || window.webkitAudioContext;
        var ctx = new AudioContext();
        if (ctx.state === 'suspended') await ctx.resume();
        function playTone(f, t, s, d, v) {
            var o = ctx.createOscillator(); var g = ctx.createGain();
            o.connect(g); g.connect(ctx.destination);
            o.type = t; o.frequency.setValueAtTime(f, ctx.currentTime + s);
            g.gain.setValueAtTime(v, ctx.currentTime + s);
            g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + s + d);
            o.start(ctx.currentTime + s); o.stop(ctx.currentTime + s + d);
        }
        playTone(523.25, 'sine', 0.0, 0.8, 0.6); 
        playTone(1046.50, 'triangle', 0.1, 0.5, 0.4); 
    } catch(e) {}
})();
</script>
""", height=0, width=0)
        st.session_state.notif_triggered = False

    if lang == 'ar':
        f_name = user.get('first_name_ar', ''); fa_name = user.get('father_name_ar', '')
        welcome_prefix = "مرحباً بك،"; program_name = "نظام السعيد المتكامل 💎"
    else:
        f_name = user.get('first_name_en', ''); fa_name = user.get('father_name_en', '')
        welcome_prefix = "Welcome,"; program_name = "Alsaeed Integrated System 💎"

    full_name = f"{f_name} {fa_name}".strip() or user.get('username', 'User')
    avatar_val = auth_manager.get_avatar(user.get('username', ''))
    avatar_src = avatar_val if str(avatar_val).startswith('data:') else f'data:image/png;base64,{avatar_val}' if avatar_val else None
    avatar_html = f'<img src="{avatar_src}" class="banner-avatar" />' if avatar_src else '<div class="banner-avatar" style="background:linear-gradient(135deg,#D4AF37,#8B7520);display:flex;align-items:center;justify-content:center;font-size:24px;">👤</div>'

    with st.container():
        if lang == 'ar':
            cols = st.columns([2, 4.7, 2.5, 0.8])
            c4, c3, c2, c1 = cols[0], cols[1], cols[2], cols[3]
        else:
            cols = st.columns([0.8, 2.5, 4.7, 2])
            c1, c2, c3, c4 = cols[0], cols[1], cols[2], cols[3]
        
        with c1:
            badge_html = f'<span class="notif-badge">{notif_count}</span>' if notif_count > 0 else ''
            st.markdown(f'<div class="notif-bell-container" style="position:relative;">{badge_html}', unsafe_allow_html=True)
            if st.button("🔔", key="bell_trig_v2"):
                st.session_state.notif_panel_open = not st.session_state.get('notif_panel_open', False)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown(f'<div style="display:flex; align-items:center; gap:15px;">{avatar_html}<div><p style="margin:0; font-weight:700; color:white;">{welcome_prefix} {full_name}</p><p style="margin:0; font-size:0.75rem; color:#D4AF37;">{program_name}</p></div></div>', unsafe_allow_html=True)
        
        with c4:
            st.markdown(f'<div style="text-align:right;"><p style="color:rgba(255,255,255,0.6); font-size:0.75rem; margin:0;">{datetime.now().strftime("%Y-%m-%d")}</p></div>', unsafe_allow_html=True)

    if st.session_state.get('notif_panel_open') and notifs:
        with st.expander("Notifications", expanded=True):
            for n in reversed(notifs[-10:]):
                st.write(f"**{n['title']}**: {n['msg']}")
            if st.button("Clear All"):
                st.session_state.notifications = []; st.rerun()

def render_cv_detail_panel(worker_row, selected_idx, lang, key_prefix="search", worker_uid=None):
    """
    Standalone helper to render the professional CV profile card, 
    preview (iframe), and translation logic.
    """
    import streamlit as st
    import hashlib
    import time
    import requests
    from src.core.file_translator import FileTranslator

    # Robust name detection
    name_keys = ["Full Name:", "الاسم الكامل", "Name", "الاسم"]
    worker_name = "Worker"
    for nk in name_keys:
        if nk in worker_row.index:
            worker_name = worker_row[nk]
            break
            
    worker_id = worker_uid
    if not worker_id:
        sheet_row = worker_row.get('__sheet_row', worker_row.get('__sheet_row_backup'))
        if sheet_row:
            worker_id = f"row_{sheet_row}"
        else:
            w_name_fallback = str(worker_row.get("Full Name:", worker_row.get("الاسم الكامل", worker_name)))
            worker_id = hashlib.md5(w_name_fallback.encode()).hexdigest()[:10]

    cv_col = None
    for c in worker_row.index:
        c_clean = str(c).lower()
        if "cv" in c_clean or "سيرة" in c_clean or "download" in c_clean:
            cv_col = c
            break
    cv_url = worker_row.get(cv_col, "") if cv_col else ""
    
    st.markdown(f"<div id='cv-anchor-{key_prefix}'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background: rgba(20, 20, 20, 0.85); 
                backdrop-filter: blur(15px);
                padding: 30px; 
                border-radius: 20px; 
                border-left: 5px solid #D4AF37; 
                border-bottom: 1px solid rgba(212, 175, 55, 0.2);
                margin: 25px 0;
                box-shadow: 0 15px 35px rgba(0,0,0,0.4);">
        <h2 style="color: #D4AF37; 
                   margin: 0; 
                   font-family: 'Cinzel', serif; 
                   letter-spacing: 2px;
                   text-transform: uppercase;
                   font-size: 1.8rem;">
            👤 {worker_name}
        </h2>
    </div>
    """, unsafe_allow_html=True)
    
    col_a, col_b = st.columns([1, 1])
    
    translate_configs = [
        {"lang_code": "ar", "label": t('translate_cv_btn', lang), "key_suffix": "ar", "target": "ar"},
        {"lang_code": "tl", "label": "✨ Isalin ang CV (Filipino)", "key_suffix": "tl", "target": "tl"}
    ]

    for idx, config in enumerate(translate_configs):
        with col_a if idx == 0 else col_b:
            if st.button(config["label"], use_container_width=True, type="primary" if idx == 0 else "secondary", key=f"btn_trans_{key_prefix}_{worker_id}_{config['key_suffix']}"):
                if cv_url and str(cv_url).startswith("http"):
                    trans_loader = show_loading_hourglass(t("extracting", lang))
                    try:
                        file_id = None
                        if "drive.google.com" in cv_url:
                            if "id=" in cv_url: file_id = cv_url.split("id=")[1].split("&")[0]
                            elif "/d/" in cv_url: file_id = cv_url.split("/d/")[1].split("/")[0]

                        session = requests.Session()
                        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})
                        
                        if file_id:
                            dl_url = f"https://docs.google.com/uc?export=download&id={file_id}"
                            resp = session.get(dl_url, stream=True, timeout=15)
                            token = next((v for k, v in resp.cookies.items() if k.startswith('download_warning')), None)
                            if token:
                                dl_url = f"https://docs.google.com/uc?export=download&confirm={token}&id={file_id}"
                                resp = session.get(dl_url, stream=True, timeout=15)
                            if resp.status_code >= 500: resp = requests.get(cv_url, timeout=15)
                        else:
                            resp = requests.get(cv_url, timeout=15)
                        
                        if resp.status_code == 200:
                            content = resp.content
                            content_type = resp.headers.get('Content-Type', '').lower()
                            filename_from_header = ""
                            cd = resp.headers.get('Content-Disposition', '')
                            if 'filename=' in cd: filename_from_header = cd.split('filename=')[1].strip('"')
                            
                            ext = ".pdf"
                            if "word" in content_type or filename_from_header.endswith(".docx"): ext = ".docx"
                            elif "image" in content_type: ext = ".png" if "png" in content_type else ".jpg"
                            elif content.startswith(b"%PDF"): ext = ".pdf"
                            elif content.startswith(b"PK\x03\x04"): ext = ".docx"
                            
                            ft = FileTranslator(source_lang="auto", target_lang=config["target"])
                            virtual_filename = filename_from_header if filename_from_header else f"file{ext}"
                            result = ft.translate(content, virtual_filename)
                            
                            if result.get("success"):
                                st.session_state[f"trans_{key_prefix}_{worker_id}_{config['key_suffix']}"] = {
                                    "orig": result.get("original_text", ""), 
                                    "trans": result.get("translated_text", ""),
                                    "output": result.get("output_bytes"),
                                    "out_filename": result.get("output_filename"),
                                    "target_label": "Arabic" if config["target"] == "ar" else "Filipino"
                                }
                                st.rerun()
                            else:
                                st.error(f"❌ {result.get('error', 'Unknown Error')}")
                        else:
                            st.error(f"خطأ في الوصول للملف: (HTTP {resp.status_code})")
                    except Exception as e: st.error(f"Error: {str(e)}")
                    finally: trans_loader.empty()
                else: st.warning("رابط السيرة الذاتية غير موجود أو غير صالح.")

    st.markdown(f"#### 🔎 {t('preview_cv', lang)}")
    if cv_url and str(cv_url).startswith("http"):
        preview_url = cv_url
        if "drive.google.com" in cv_url:
            f_id = None
            if "id=" in cv_url: f_id = cv_url.split("id=")[1].split("&")[0]
            elif "/d/" in cv_url: f_id = cv_url.split("/d/")[1].split("/")[0]
            if f_id: preview_url = f"https://drive.google.com/file/d/{f_id}/preview"
        st.components.v1.iframe(preview_url, height=600, scrolling=True)
    else: st.info("لا يتوفر رابط معاينة لهذا العامل.")

def login_screen(auth_manager, t, toggle_lang, load_saved_credentials, save_credentials, clear_credentials):
    import streamlit as st
    import os
    lang = st.session_state.lang
    
    # 2026 Luxury Flag Icons
    sa_icon = '<img src="https://flagcdn.com/w40/sa.png" style="width:24px; vertical-align:middle; border-radius:3px; margin:0 4px; box-shadow:0 0 8px rgba(0,0,0,0.4);">'
    ph_icon = '<img src="https://flagcdn.com/w40/ph.png" style="width:24px; vertical-align:middle; border-radius:3px; margin:0 4px; box-shadow:0 0 8px rgba(0,0,0,0.4);">'
    
    if lang == "ar":
        title_text = f'برنامج توريد العمالة الفلبينية {ph_icon} {sa_icon}'
    else:
        title_text = f'Philippines Recruitment Program {ph_icon} {sa_icon}'
    
    st.markdown(f'<div class="luxury-main-title">{title_text}</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([0.5, 2, 0.5]) 
    with col2:
        saved = load_saved_credentials()
        saved_u = saved.get("u", "") if saved else ""
        saved_p = saved.get("p", "") if saved else ""
        
        with st.form(f"login_form_main"):
            head_col1, head_col2 = st.columns([1, 2])
            with head_col2:
                welcome_text = t('welcome_back', lang)
                st.markdown(f'<h3 style="margin-top: 25px;">{welcome_text}</h3>', unsafe_allow_html=True)
            with head_col1:
                # Assuming alsaeed.jpg is in BASE_DIR or ASSETS_DIR
                img_path = "alsaeed.jpg"
                if os.path.exists(img_path):
                    b64 = get_base64_image(img_path)
                    st.markdown(f'<div style="text-align:right;"><img src="data:image/jpeg;base64,{b64}" class="profile-img-circular" style="width:80px; height:80px; border:2px solid #FFF; box-shadow: 0 0 15px #FFF;"></div>', unsafe_allow_html=True)
            
            u = st.text_input(t("username", lang), value=saved_u, label_visibility="collapsed", placeholder=t("username", lang))
            p = st.text_input(t("password", lang), value=saved_p, type="password", label_visibility="collapsed", placeholder=t("password", lang))
            
            persist_txt = "هل تريد حفظ الدخول" if lang == 'ar' else "Do you want to stay logged in?"
            persist = st.checkbox(persist_txt, value=(True if saved else False))
            
            submit = st.form_submit_button(t("login_btn", lang), use_container_width=True)
            lang_toggle = st.form_submit_button("En" if lang == "ar" else "عربي", use_container_width=True)

            if submit:
                if not u or not p:
                    st.error(t("invalid_creds", lang))
                else:
                    login_loader = show_loading_hourglass()
                    user = auth_manager.authenticate(u, p.strip())
                    login_loader.empty()
                    if user:
                        if persist:
                            save_credentials(u, p.strip())
                        else:
                            clear_credentials()
                            
                        user['username'] = u.lower().strip()
                        st.session_state.user = user
                        st.session_state.show_welcome = True
                        st.markdown("<style>div[data-testid='stForm'] { display: none !important; }</style>", unsafe_allow_html=True)
                        st.success("جاري الدخول... | Loading..." if lang == 'ar' else "Loading... | Entering")
                        st.rerun()
                    else:
                        st.error(t("invalid_creds", lang))

            if lang_toggle:
                toggle_lang()
                st.rerun()
