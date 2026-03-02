import streamlit as st
import time
from src.services.whatsapp_service import WhatsAppService
from src.core.i18n import t

def render_whatsapp_page():
    lang = st.session_state.get('lang', 'ar')
    is_cloud = "/mount/" in __file__
    
    if 'wa_service' not in st.session_state:
        st.session_state.wa_service = WhatsAppService()

    # Sidebar: Reset with one click
    if st.sidebar.button("🔄 Restart WhatsApp Engine"):
        st.session_state.wa_service.close()
        st.session_state.wa_service = WhatsAppService()
        st.rerun()

    st.title(f"📱 {t('wa_title', lang)}")
    
    status = st.session_state.wa_service.get_status()
    
    if status == "Connected":
        st.success(f"✅ {t('wa_online', lang)}")
        if st.button(t("wa_disconnect", lang)):
            st.session_state.wa_service.close()
            st.rerun()
            
    elif status == "Awaiting Login":
        st.info("🎯 SCAN MODE: Please scan the code below carefully")
        
        qr_data = st.session_state.wa_service.get_qr_hd()
        
        if qr_data:
            # Displaying in a strictly white, flat container for maximum contrast
            st.markdown("""
                <div style="background: white; padding: 40px; border-radius: 20px; text-align: center; border: 10px solid #25D366;">
                    <p style="color: black; font-weight: bold; margin-bottom: 20px;">Use WhatsApp on your phone to scan this code</p>
                    <img src="{}" style="width: 450px; image-rendering: pixelated; border: 1px solid #eee;">
                </div>
            """.format(qr_data), unsafe_allow_html=True)
            
            # Slow down refresh to prevent flickering (every 10 seconds)
            time.sleep(10)
            st.rerun()
        else:
            st.warning("Generating Ultra-HD QR... Please wait 10 seconds")
            time.sleep(5)
            st.rerun()
            
    elif status == "Loading...":
        st.info("🚀 Launching Chrome on Cloud... This takes 15-20 seconds")
        time.sleep(5)
        st.rerun()
        
    else:
        st.error(f"❌ {t('wa_offline', lang)}")
        if st.button(t("wa_launch_btn", lang), type="primary"):
            with st.spinner("Starting Engine..."):
                st.session_state.wa_service.start_driver(headless=is_cloud)
                st.rerun()

    # Recipient and Message UI below... (Simplified for Scan Focus)
    if status == "Connected":
        st.markdown("---")
        st.subheader("Broadcast Settings")
        # Recipients / Message logic goes here
