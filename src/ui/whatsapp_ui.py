import streamlit as st
import pandas as pd
import time
import threading
from datetime import datetime
from src.services.whatsapp_service import WhatsAppService
from src.utils.phone_utils import validate_numbers, format_phone_number

def get_whatsapp_ui_css():
    return """
    <style>
        .wa-glass-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 25px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }
        .wa-glass-card:hover {
            border-color: rgba(212, 175, 55, 0.4);
            transform: translateY(-5px);
        }
        .wa-status-connected {
            color: #00FF41;
            font-weight: bold;
            text-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
        }
        .wa-status-disconnected {
            color: #FF3131;
            font-weight: bold;
            text-shadow: 0 0 10px rgba(255, 49, 49, 0.5);
        }
        .wa-status-loading {
            color: #D4AF37;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { opacity: 0.6; }
            50% { opacity: 1; }
            100% { opacity: 0.6; }
        }
        .wa-3d-button {
            background: linear-gradient(145deg, #1e1e1e, #111111);
            box-shadow: 5px 5px 10px #0b0b0b, -5px -5px 10px #212121;
            border: none;
            color: #D4AF37;
            padding: 10px 20px;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .wa-3d-button:active {
            box-shadow: inset 2px 2px 5px #050505, inset -2px -2px 5px #1d1d1d;
        }
        .wa-log {
            font-family: 'Consolas', monospace;
            font-size: 0.85rem;
            background: rgba(0,0,0,0.5);
            padding: 15px;
            border-radius: 12px;
            max-height: 200px;
            overflow-y: auto;
            color: #aaa;
        }
        .wa-timer-ring {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 120px;
            height: 120px;
            border-radius: 50%;
            border: 4px solid #333;
            position: relative;
        }
        .wa-timer-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #D4AF37;
        }
    </style>
    """

def render_whatsapp_page():
    lang = st.session_state.lang
    st.markdown(get_whatsapp_ui_css(), unsafe_allow_html=True)
    
    # 1. Title
    st.markdown(f'''<div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #D4AF37; font-family: 'Cinzel', serif;">WhatsApp Luxury Suite 2026</h1>
        <p style="color: #888;">Executive Messaging Engine • Secure • Automated</p>
    </div>''', unsafe_allow_html=True)
    
    # Initialize Service
    if 'wa_service' not in st.session_state:
        st.session_state.wa_service = WhatsAppService()
        st.session_state.wa_thread = None
        st.session_state.wa_running = False
        st.session_state.wa_logs = []
        st.session_state.wa_progress = 0
        st.session_state.wa_total = 0
        st.session_state.wa_sent = 0
        st.session_state.wa_active_numbers = []

    # Layout: Sidebar-like status + Main controls
    col_status, col_main = st.columns([1, 2.5])
    
    with col_status:
        st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader("📡 Status")
        
        status = st.session_state.wa_service.get_status()
        if status == "Connected":
            st.markdown(f'Status: <span class="wa-status-connected">● ONLINE</span>', unsafe_allow_html=True)
            if st.button("Disconnect", use_container_width=True):
                st.session_state.wa_service.close()
                st.rerun()
        elif status == "Awaiting Login":
            st.markdown(f'Status: <span class="wa-status-loading">● QR READY</span>', unsafe_allow_html=True)
            qr_b64 = st.session_state.wa_service.get_qr_base64()
            if qr_b64:
                st.image(f"data:image/png;base64,{qr_b64}", caption="Scan with WhatsApp", use_container_width=True)
                if st.button("Refresh QR", use_container_width=True):
                    st.rerun()
        else:
            st.markdown(f'Status: <span class="wa-status-disconnected">● OFFLINE</span>', unsafe_allow_html=True)
            if st.button("Launch WhatsApp Web", use_container_width=True):
                with st.spinner("Initializing Luxury Browser..."):
                    st.session_state.wa_service.start_driver(headless=False)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Quick Stats Card
        st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader("📊 Session Statistics")
        st.metric("Total Sent", st.session_state.wa_sent)
        st.metric("Pending", st.session_state.wa_total - st.session_state.wa_sent)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_main:
        # Step 2: Numbers Processing
        st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader("📝 Step 1: Manage Recipients")
        
        upload_type = st.radio("Input Method", ["Paste Text / Numbers", "Upload File (Excel/TXT)"], horizontal=True)
        
        raw_input = ""
        if upload_type == "Paste Text / Numbers":
            raw_input = st.text_area("Paste numbers here (one per line, or comma separated)", height=150, placeholder="0541234567, +63963...")
        else:
            uploaded_file = st.file_uploader("Choose a file", type=["xlsx", "txt", "csv"])
            if uploaded_file:
                if uploaded_file.name.endswith('.xlsx'):
                    df = pd.read_excel(uploaded_file)
                    # Try to find a column with 'phone' or 'number' or 'mobile'
                    phone_cols = [c for c in df.columns if any(kw in str(c).lower() for kw in ['phone', 'num', 'mob', 'جوال', 'هاتف'])]
                    if phone_cols:
                        raw_input = "\n".join(df[phone_cols[0]].astype(str).tolist())
                    else:
                        st.error("Could not find a phone number column in the Excel file.")
                else:
                    raw_input = uploaded_file.read().decode('utf-8')

        if raw_input:
            v_sa, v_ph, invalid = validate_numbers(raw_input)
            st.session_state.wa_active_numbers = v_sa + v_ph
            
            c1, c2, c3 = st.columns(3)
            c1.success(f"🇸🇦 Saudi: {len(v_sa)}")
            c2.success(f"🇵🇭 Philippine: {len(v_ph)}")
            c3.error(f"❌ Invalid: {len(invalid)}")
            
            if st.checkbox("Show cleaned numbers"):
                st.code("\n".join(st.session_state.wa_active_numbers))
        st.markdown('</div>', unsafe_allow_html=True)

        # Step 3: Message Content
        st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader("✉️ Step 2: Compose Message")
        msg_text = st.text_area("Message Body", height=150, placeholder="Hello! This is a luxury notification...")
        
        c_att1, c_att2 = st.columns(2)
        with c_att1:
            st.file_uploader("Attach Image/Document (Coming Soon)", disabled=True)
        with c_att2:
            delay = st.slider("Delay between messages (Seconds)", 2, 60, 5)
        st.markdown('</div>', unsafe_allow_html=True)

        # Step 4: Controller
        st.markdown('<div class="wa-glass-card">', unsafe_allow_html=True)
        st.subheader("🚀 Step 3: Deployment")
        
        if st.session_state.wa_running:
            if st.button("⏹️ STOP BROADCAST", type="primary", use_container_width=True):
                st.session_state.wa_running = False
                st.rerun()
        else:
            if st.button("🔥 START LUXURY BROADCAST", use_container_width=True):
                if not st.session_state.wa_active_numbers:
                    st.error("No valid recipients detected.")
                elif not msg_text:
                    st.error("Message content is empty.")
                elif status != "Connected":
                    st.error("WhatsApp is not connected.")
                else:
                    st.session_state.wa_running = True
                    st.session_state.wa_total = len(st.session_state.wa_active_numbers)
                    st.session_state.wa_sent = 0
                    # Start thread logic (for simplicity here, we'll do a mock loop for now)
                    # In a real app, use threading.Thread(target=sender_loop).start()
                    st.rerun()

    if st.session_state.wa_running:
        # Dynamic Progress
        progress_bar = st.progress(st.session_state.wa_sent / st.session_state.wa_total if st.session_state.wa_total > 0 else 0)
        st.write(f"Sending {st.session_state.wa_sent} of {st.session_state.wa_total}...")
        
        # We perform one send per rerun to keep UI updated and avoid complexity of cross-thread UI updates
        if st.session_state.wa_sent < st.session_state.wa_total:
            current_num = st.session_state.wa_active_numbers[st.session_state.wa_sent]
            
            # The actual sending part
            res, info = st.session_state.wa_service.send_message(current_num, msg_text)
            
            status_icon = "✅" if res else "❌"
            log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] {status_icon} {current_num}: {info}"
            st.session_state.wa_logs.append(log_msg)
            st.session_state.wa_sent += 1
            
            if st.session_state.wa_sent == st.session_state.wa_total:
                st.session_state.wa_running = False
                st.balloons()
                # Optional: Success sound (beep) base64
                st.markdown("""<audio autoplay><source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mpeg"></audio>""", unsafe_allow_html=True)
            
            # Non-blocking pause
            time.sleep(delay)
            st.rerun()

        # Logs
        if st.session_state.wa_logs:
            st.markdown('<div class="wa-log">', unsafe_allow_html=True)
            for l in reversed(st.session_state.wa_logs):
                st.write(l)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("Export Report (CSV)"):
                log_df = pd.DataFrame(st.session_state.wa_logs, columns=["Log"])
                st.download_button("Download CSV", log_df.to_csv(index=False), "wa_report.csv", "text/csv")
                
        st.markdown('</div>', unsafe_allow_html=True)
