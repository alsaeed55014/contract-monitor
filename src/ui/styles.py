import os
import base64
import streamlit as st

def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def get_css(lang='ar'):
    direction = 'rtl' if lang == 'ar' else 'ltr'
    toggle_side = 'right' if lang == 'ar' else 'left'
    toggle_opposite = 'left' if lang == 'ar' else 'right'
    sidebar_border_side = 'left' if lang == 'ar' else 'right'
    sidebar_border_none = 'right' if lang == 'ar' else 'left'
    checkbox_text_align = 'right' if lang == 'ar' else 'left'
    bell_col_idx = 4 if lang == 'ar' else 1
    
    return f"""
    <style>
        /* Modern 2026 Luxury Executive Design System */
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&family=Inter:wght@300;400;500;600;700&family=Cinzel:wght@500;700&family=Alex+Brush&family=Cairo:wght@400;600;700&family=My+Soul&display=swap');
        
        :root {{
            --luxury-gold: #D4AF37;
            --deep-gold: #B8860B;
            --glass-bg: rgba(26, 26, 26, 0.7);
            --solid-dark: #0A0A0A;
            --accent-green: #00FF41;
            --text-main: #F4F4F4;
            --border-glow: rgba(212, 175, 55, 0.3);
        }}

        /* 1) Global Aesthetics & Scrollbar */
        html, body, .stApp {{
            direction: {direction} !important;
        }}
        
        .stApp {{
            background: radial-gradient(circle at top right, #001F3F, #000000) !important;
            color: var(--text-main);
            font-family: 'Inter', 'Cairo', 'Tajawal', sans-serif;
        }}
        
        .main, [data-testid="stSidebarUserContent"], [data-testid="stSidebar"] {{
            direction: {direction} !important;
        }}

        /* Fix Checkbox Spacing - Icon at start, Text at end */
        div[data-testid="stCheckbox"] label {{
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            gap: 15px !important;
            width: 100% !important;
            justify-content: flex-start !important;
        }}

        div[data-testid="stCheckbox"] label div:first-child {{
            order: 1 !important;
        }}
        
        div[data-testid="stCheckbox"] label div[data-testid="stMarkdownContainer"] {{
            order: 2 !important;
            flex-grow: 1 !important;
            text-align: {checkbox_text_align} !important;
        }}

        div[data-testid="stCheckbox"] label div[data-testid="stMarkdownContainer"] p {{
            margin: 0 !important;
            font-family: 'Cairo', sans-serif !important;
            font-size: 0.95rem !important;
        }}

        /* Custom Premium Scrollbar */
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: #000; }}
        ::-webkit-scrollbar-thumb {{ 
            background: linear-gradient(180deg, #111, #D4AF37); 
            border-radius: 10px; 
        }}

        /* 2) Layout & Spacing - CRITICAL FIX FOR TOP SPACE */
        .main .block-container {{
            padding-top: 0rem !important;
            padding-bottom: 2rem !important;
            max-width: 1200px !important;
        }}

        header[data-testid="stHeader"] {{
            background: transparent !important;
            height: 0 !important;
        }}

        /* 3) Luxury Typography & Large Title */
        .luxury-main-title {{
            font-family: 'Fv Free soul', 'My Soul', 'Cairo', sans-serif !important;
            font-size: 20px !important; /* Specific size requested by user */
            font-weight: 700 !important;
            text-align: center !important;
            background: linear-gradient(to bottom, #FFFFFF 20%, #D4AF37 100%) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            text-shadow: 0 4px 15px rgba(212, 175, 55, 0.4) !important;
            margin: -10px 0 5px 0 !important; /* Raised even higher */
            padding: 0 !important; 
            letter-spacing: 1px !important;
        }}

        .flag-icon {{
            font-size: 20px;
            vertical-align: middle;
            margin: 0 5px;
        }}

        /* 4) Premium Form & Vertical Alignment */
        div[data-testid="stForm"] {{
            background: rgba(10, 10, 10, 0.5) !important;
            backdrop-filter: blur(15px) !important;
            border: 1px solid rgba(212, 175, 55, 0.2) !important;
            border-radius: 20px !important;
            padding: 1.5rem !important;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8) !important;
        }}

        /* Profile Image Alignment Wrapper */
        .profile-row-container {{
            display: flex;
            align-items: center;
            justify-content: flex-start;
            gap: 15px;
            width: 100%;
            margin-bottom: 10px;
        }}

        .profile-img-circular {{
            width: 70px;
            height: 70px;
            border-radius: 50%;
            border: 2px solid var(--luxury-gold);
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.3);
            object-fit: cover;
        }}

        /* Generic Inputs Styling */
        .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] {{
            background-color: rgba(40, 40, 40, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 12px !important;
            color: #FFFFFF !important;
            padding: 8px 12px !important; /* Reduced padding for smaller fields */
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06) !important;
        }}

        .stTextInput input:focus, div[data-baseweb="select"]:focus-within {{
            border-color: var(--luxury-gold) !important;
            box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.2) !important;
            background-color: rgba(50, 50, 50, 0.8) !important;
        }}

        /* Slider Styling */
        div[data-testid="stSlider"] [data-testid="stThumb"] {{
            background-color: var(--luxury-gold) !important;
            border: 2px solid #FFFFFF !important;
        }}
        div[data-testid="stSlider"] [data-testid="stTrack"] > div {{
            background: linear-gradient(90deg, #333, #D4AF37) !important;
        }}

        /* 5) Universal Luxury Button Style */
        .stButton button, div[data-testid="stFormSubmitButton"] button {{
            background: linear-gradient(135deg, #1A1A1A 0%, #262626 100%) !important;
            color: var(--luxury-gold) !important;
            border: 1px solid var(--border-glow) !important;
            border-radius: 12px !important;
            padding: 0.75rem 2rem !important;
            font-weight: 600 !important;
            letter-spacing: 1.5px !important;
            text-transform: uppercase !important;
            transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1) !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5) !important;
            width: 100% !important; /* Default to full width for better mobile behavior */
        }}

        /* Mobile specific button refinements */
        @media screen and (max-width: 768px) {{
            .stButton button, div[data-testid="stFormSubmitButton"] button {{
                padding: 0.6rem 1.2rem !important;
                font-size: 0.85rem !important;
                letter-spacing: 1px !important;
            }}
        }}

        .stButton button:hover, div[data-testid="stFormSubmitButton"] button:hover {{
            background: var(--luxury-gold) !important;
            color: #000 !important;
            border-color: var(--luxury-gold) !important;
            box-shadow: 0 0 25px rgba(212, 175, 55, 0.5) !important;
            transform: translateY(-3px) scale(1.02) !important;
        }}

        /* Primary Search Variation */
        button[kind="primary"] {{
            background: linear-gradient(135deg, #111, #222) !important;
            border: 1px solid var(--luxury-gold) !important;
        }}

        /* WhatsApp Export Button - Red Text */
        .whatsapp-export-btn .stButton button,
        .whatsapp-export-btn .stDownloadButton button {{
            color: #FF0000 !important;
        }}
        .whatsapp-export-btn .stButton button:hover,
        .whatsapp-export-btn .stDownloadButton button:hover {{
            color: #FF0000 !important;
        }}

        /* 6) Table & Data Presentation - WHITE NEON STYLE (For DataFrames) */
        [data-testid="stDataFrame"], [data-testid="stTable"], .neon-white-table {{
            background: rgba(255, 255, 255, 1) !important;
            border: 2px solid #FFFFFF !important;
            border-radius: 12px !important;
            box-shadow: 0 0 30px rgba(255, 255, 255, 0.8), 
                        inset 0 0 15px rgba(255, 255, 255, 0.5) !important;
            margin: 20px 0 !important;
            color: #000000 !important;
        }}
        
        [data-testid="stDataFrame"] *, [data-testid="stTable"] *, .neon-white-table * {{
            color: #000000; /* Removed !important to allow selective overrides */
            font-weight: 500 !important;
        }}

        /* FIX: White Icons for Data Table Toolbars (Fullscreen, Search, Download) */
        [data-testid="stElementToolbar"] button, 
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] svg,
        [data-testid="stTable"] [data-testid="stElementToolbar"] svg {{
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
            filter: drop-shadow(0 0 5px rgba(255, 255, 255, 0.5)) !important;
        }}
        
        [data-testid="stElementToolbar"] button:hover {{
            background-color: rgba(255, 255, 255, 0.1) !important;
            border-radius: 50% !important;
        }}
        
        /* Header specific for dataframes to handle high brightness */
        [data-testid="stDataFrame"] div[role="columnheader"] {{
            background-color: rgba(240, 240, 240, 0.9) !important;
            color: #000000 !important;
            font-weight: 700 !important;
        }}

        /* Status Column Glows - Enhanced for 2026 High-Tech Look */
        .glow-green {{ color: #00FF66 !important; text-shadow: 0 0 10px rgba(0, 255, 102, 0.4) !important; font-weight: 800 !important; }}
        .glow-red {{ color: #FF3333 !important; text-shadow: 0 0 10px rgba(255, 51, 51, 0.4) !important; font-weight: 800 !important; }}
        .glow-orange {{ color: #FF9900 !important; text-shadow: 0 0 10px rgba(255, 153, 0, 0.4) !important; font-weight: 800 !important; }}

        /* 7) Sidebar Professionalism */
        section[data-testid="stSidebar"] {{
            background-color: #080808 !important;
            border-{sidebar_border_side}: 1px solid rgba(212, 175, 55, 0.15) !important;
            border-{sidebar_border_none}: none !important;
        }}
        
        /* Force HIDE sidebar when closed to prevent the "vertical line" artifact */
        section[data-testid="stSidebar"][aria-expanded="false"],
        section[data-testid="stSidebar"][data-collapsed="true"] {{
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
        }}

        .programmer-credit {{
            color: #FFFFFF !important;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.8), 
                         0 0 20px rgba(212, 175, 55, 0.4) !important;
            font-family: 'Tajawal', sans-serif;
            font-weight: 700;
            font-size: 1.3rem;
            text-align: center;
            margin-top: 10px;
            line-height: 1.2;
            white-space: nowrap !important;
        }}
        
        /* English version specific font */
        .programmer-credit.en {{
            font-family: 'Cinzel', serif !important;
            font-size: 1.1rem;
            letter-spacing: 1px;
        }}

        /* 8) Expander Luxury - UNIVERSAL WHITE NEON FRAME STYLE */
        .stExpander {{
            background-color: rgba(10, 14, 26, 0.6) !important;
            border: 2px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 20px !important;
            margin-bottom: 25px !important;
            animation: neonWhitePulse 3s ease-in-out infinite alternate !important;
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.2) !important;
            transition: all 0.4s ease !important;
            overflow: hidden !important;
        }}
        
        .stExpander:hover {{
            border-color: rgba(255, 255, 255, 0.9) !important;
            box-shadow: 0 0 30px rgba(255, 255, 255, 0.6) !important;
            transform: translateY(-2px);
        }}

        /* Target the Header/Summary Area */
        .stExpander > details > summary {{
            background-color: rgba(255, 255, 255, 0.05) !important;
            color: #FFFFFF !important;
            padding: 1.2rem 1.5rem !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
        }}
        
        .stExpander > details > summary:hover {{
            background-color: rgba(255, 255, 255, 0.1) !important;
        }}

        /* Target the internal icons and labels */
        .stExpander summary span, .stExpander summary svg {{
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
        }}

        /* Ensure internal content is appropriately styled */
        .stExpander > details > div[role="region"] {{
            border: none !important;
            background: transparent !important;
            padding: 20px !important;
        }}

        /* Re-refine filter labels for maximum white neon impact */
        .premium-filter-label {{
            color: #FFFFFF !important;
            font-weight: 800 !important;
            text-shadow: 0 0 15px rgba(255, 255, 255, 0.8) !important;
            margin: 15px 0 10px 0 !important;
            font-size: 1.15rem !important;
            border-right: 5px solid #FFFFFF !important;
            padding-right: 12px !important;
            letter-spacing: 1px;
            display: inline-block;
        }}

        /* Signature Neon (Standardized White-Gold) */
        .programmer-signature-neon, .red-neon-signature {{
            font-family: 'Alex Brush', cursive !important;
            color: #FFFFFF !important;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.8), 
                         0 0 20px rgba(212, 175, 55, 0.4) !important;
            font-size: 1.4rem !important; /* Smaller signature */
            text-align: center !important;
            display: block !important;
            width: 100% !important;
            margin: 0 auto 10px auto !important;
            letter-spacing: 1px !important;
            white-space: nowrap !important; /* Prevent vertical wrapping on mobile */
        }}

        /* Signature Under Image */
        .signature-under-img {{
            font-family: 'Alex Brush', cursive !important;
            color: #EEE !important; /* Slightly brighter for better visibility */
            font-size: 0.9rem !important;
            margin-top: 5px;
            text-align: center;
            letter-spacing: 1px;
            white-space: nowrap !important;
        }}

        /* Login Screen Special Centering - FIXED HANGING VERSION */
        .login-screen-wrapper {{
            margin-top: 20px !important;
            text-align: center;
        }}

        /* Target the Streamlit Form - REMOVED GOLD BORDER */
        div[data-testid="stForm"] {{
            background: rgba(10, 10, 10, 0.4) !important;
            backdrop-filter: blur(25px) !important;
            border: none !important; /* NO BORDER */
            border-radius: 25px !important;
            padding: 2rem !important;
            box-shadow: 0 15px 50px rgba(0, 0, 0, 0.8) !important;
            width: 100% !important;
            max-width: 500px !important;
            margin: 0 auto 40px auto !important;
        }}

        /* White Neon Text Effect */
        div[data-testid="stForm"] h3, 
        div[data-testid="stForm"] label,
        .neon-text {{
            color: #FFFFFF !important;
            text-shadow: 0 0 5px #FFF, 0 0 10px #FFF, 0 0 20px #FFF !important;
            text-align: center !important;
            font-weight: bold !important;
        }}

        /* Neon Glow Around Inputs - ENHANCED HALO EFFECT */
        div[data-testid="stForm"] div[data-baseweb="input"] {{
            background: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.4) !important;
            border-radius: 12px !important;
            /* Layered shadows for a 'halo' light effect */
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.2), 
                        0 0 30px rgba(255, 255, 255, 0.1), 
                        inset 0 0 5px rgba(255, 255, 255, 0.1) !important;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        }}

        div[data-testid="stForm"] div[data-baseweb="input"]:focus-within {{
            box-shadow: 0 0 25px rgba(255, 255, 255, 0.7), 
                        0 0 45px rgba(255, 255, 255, 0.3), 
                        inset 0 0 10px rgba(255, 255, 255, 0.1) !important;
            border-color: #FFFFFF !important;
            transform: scale(1.01) !important;
        }}

        div[data-testid="stForm"] .stTextInput input {{
            text-align: center !important;
            background: transparent !important;
            border: none !important;
            color: white !important;
            text-shadow: 0 0 2px rgba(255, 255, 255, 0.5) !important;
        }}

        /* Checkbox Neon Alignment */
        div[data-testid="stForm"] .stCheckbox label p {{
            color: #FFFFFF !important;
            text-shadow: 0 0 8px #FFF !important;
            font-size: 0.95rem !important;
        }}

        /* Buttons Neon Halo - LARGE WHITE GLOW */
        div[data-testid="stForm"] button {{
            background: rgba(255, 255, 255, 0.1) !important;
            border: 1.5px solid rgba(255, 255, 255, 0.4) !important;
            color: white !important;
            border-radius: 15px !important;
            /* Large Layered halo effect */
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.2), 
                        0 0 35px rgba(255, 255, 255, 0.1), 
                        inset 0 0 10px rgba(255, 255, 255, 0.05) !important;
            transition: all 0.4s ease-out !important;
            font-weight: bold !important;
            text-shadow: 0 0 5px #FFF !important;
        }}

        div[data-testid="stForm"] button:hover {{
            background: rgba(255, 255, 255, 0.2) !important;
            box-shadow: 0 0 25px rgba(255, 255, 255, 0.8), 
                        0 0 60px rgba(255, 255, 255, 0.4), 
                        inset 0 0 15px rgba(255, 255, 255, 0.1) !important;
            border-color: #FFFFFF !important;
            transform: translateY(-2px) scale(1.02) !important;
        }}
        
        /* Metric Styling with White Neon Glow */
        @keyframes neonWhitePulse {{
            0% {{ 
                box-shadow: 0 0 10px rgba(255, 255, 255, 0.4), 0 0 20px rgba(255, 255, 255, 0.15), inset 0 0 10px rgba(255, 255, 255, 0.05);
                border-color: rgba(255, 255, 255, 0.5);
            }}
            100% {{ 
                box-shadow: 0 0 20px rgba(255, 255, 255, 0.7), 0 0 40px rgba(255, 255, 255, 0.35), inset 0 0 20px rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.8);
            }}
        }}

        .metric-container {{
            background: rgba(10, 14, 26, 0.7) !important;
            border-radius: 20px !important;
            border: 1.5px solid rgba(255, 255, 255, 0.4) !important;
            padding: 1.8rem 1.5rem !important;
            transition: all 0.3s ease !important;
            animation: neonWhitePulse 3s ease-in-out infinite alternate;
            text-align: center;
        }}
        .metric-container:hover {{ 
            transform: scale(1.05) translateY(-5px);
            border-color: #FFFFFF !important;
            box-shadow: 0 0 30px rgba(255, 255, 255, 0.9), 0 0 60px rgba(255, 255, 255, 0.4) !important;
        }}

        .metric-label {{
            font-size: 0.95rem;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 8px;
            font-weight: 500;
        }}
        .metric-value {{
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1;
        }}

        /* 9) Modern 2026 Premium Loader */
        .loader-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 50px;
            background: rgba(10, 10, 10, 0.4);
            backdrop-filter: blur(15px);
            border-radius: 40px;
            border: 1px solid rgba(212, 175, 55, 0.15);
            box-shadow: 0 20px 40px rgba(0,0,0,0.6), inset 0 0 20px rgba(212, 175, 55, 0.05);
            margin: 40px auto;
            width: fit-content;
            animation: loader-entrance 0.8s ease-out;
        }}

        @keyframes loader-entrance {{
            from {{ opacity: 0; transform: scale(0.9) translateY(20px); }}
            to {{ opacity: 1; transform: scale(1) translateY(0); }}
        }}

        .modern-hourglass-svg {{
            width: 100px;
            height: 100px;
            filter: drop-shadow(0 0 15px rgba(212, 175, 55, 0.6));
            animation: hourglass-rotate 2.5s linear infinite;
        }}

        @keyframes hourglass-rotate {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}

        .modern-hourglass-svg .glass {{
            fill: none;
            stroke: var(--luxury-gold);
            stroke-width: 2.5;
            stroke-linejoin: round;
        }}

        .modern-hourglass-svg .sand {{
            fill: var(--luxury-gold);
            opacity: 0.9;
        }}

        .modern-hourglass-svg .sand-top {{
            animation: sand-sink 2.5s linear infinite;
        }}

        .modern-hourglass-svg .sand-bottom {{
            animation: sand-fill 2.5s linear infinite;
        }}

        .modern-hourglass-svg .sand-drip {{
            fill: var(--luxury-gold);
            animation: sand-drip 2.5s linear infinite;
        }}

        @keyframes hourglass-flip {{
            0%, 85% {{ transform: rotate(0deg); }}
            95%, 100% {{ transform: rotate(180deg); }}
        }}

        @keyframes sand-sink {{
            0% {{ clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%); }}
            85%, 100% {{ clip-path: polygon(0 100%, 100% 100%, 100% 100%, 0 100%); }}
        }}

        @keyframes sand-fill {{
            0% {{ clip-path: polygon(0 100%, 100% 100%, 100% 100%, 0 100%); }}
            85%, 100% {{ clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%); }}
        }}

        @keyframes sand-drip {{
            0%, 5% {{ opacity: 0; height: 0; }}
            10%, 80% {{ opacity: 1; height: 30px; }}
            85%, 100% {{ opacity: 0; height: 0; }}
        }}

        .loading-text-glow {{
            margin-top: 30px;
            font-family: 'Cinzel', serif !important;
            color: var(--luxury-gold) !important;
            font-size: 1.2rem !important;
            letter-spacing: 5px !important;
            text-transform: uppercase !important;
            text-align: center;
            animation: text-pulse-glow 2s ease-in-out infinite alternate;
        }}

        @keyframes text-pulse-glow {{
            from {{ opacity: 0.6; text-shadow: 0 0 10px rgba(212, 175, 55, 0.2); }}
            to {{ opacity: 1; text-shadow: 0 0 25px rgba(212, 175, 55, 0.8), 0 0 15px rgba(212, 175, 55, 0.4); }}
        }}

        /* 10) Persistent Top Banner */
        .persistent-top-banner {{
            position: sticky;
            top: 0;
            z-index: 1000;
            background: rgba(10, 10, 10, 0.7);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-bottom: 2px solid rgba(212, 175, 55, 0.3);
            margin: -1rem -5rem 2rem -5rem !important;
            padding: 1rem 5rem !important;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            animation: banner-slide-down 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .notif-bell-container {{
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 45px;
            height: 45px;
            background: rgba(212, 175, 55, 0.1);
            border: 1px solid rgba(212, 175, 55, 0.3);
            border-radius: 50%;
            transition: all 0.3s ease;
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.1);
        }}

        /* Target the specific Streamlit button inside our bell container (Dynamic Column Shift) */
        div[data-testid="column"]:nth-of-type({bell_col_idx}) button[key*="bell_trig"] {{
            background-color: transparent !important;
            border: none !important;
            padding: 0 !important;
            width: 45px !important;
            height: 45px !important;
            font-size: 24px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: none !important;
            transform: none !important;
        }}

        .notif-badge {{
            position: absolute;
            top: -2px;
            right: -2px;
            background: #FF3131;
            color: white;
            font-size: 11px;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 50%;
            border: 2px solid #0A0A0A;
            box-shadow: 0 0 10px rgba(255, 49, 49, 0.8);
            z-index: 10;
            animation: pulse-red 2s infinite;
        }}

        @keyframes pulse-red {{
            0% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 49, 49, 0.7); }}
            70% {{ transform: scale(1.1); box-shadow: 0 0 0 8px rgba(255, 49, 49, 0); }}
            100% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 49, 49, 0); }}
        }}

        @keyframes banner-slide-down {{
            from {{ transform: translateY(-100%); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}

        .banner-user-info {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
        }}

        .banner-avatar {{
            width: 60px;
            height: 60px;
            border-radius: 50%;
            border: 2px solid #D4AF37;
            object-fit: cover;
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.4);
            transition: transform 0.3s ease;
        }}

        .banner-avatar:hover {{
            transform: scale(1.1) rotate(5deg);
        }}

        .banner-welcome-msg {{
            font-family: 'Cairo', 'Tajawal', sans-serif;
            color: #FFFFFF;
            font-size: 1.1rem;
            font-weight: 600;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            margin: 0;
        }}

        .banner-subtext {{
            font-size: 0.8rem;
            color: rgba(212, 175, 55, 0.8);
            margin-top: -5px;
        }}

        /* 11) Mobile Responsive Overrides */
        @media (max-width: 768px) {{
            .main .block-container {{
                padding: 1rem !important;
                padding-top: 5rem !important; /* Space for the floating banner on mobile */
            }}

            .persistent-top-banner {{
                margin: 0 !important;
                padding: 0.8rem 1rem !important;
                position: fixed !important; /* Fixed at top for mobile */
                width: 100%;
                left: 0;
            }}

            .banner-welcome-msg {{ font-size: 0.95rem; }}
            .banner-subtext {{ font-size: 0.7rem; }}
            .banner-avatar {{ width: 45px; height: 45px; }}

            /* Fix Sidebar Appearance on Mobile - Clean edge when closed */
            section[data-testid="stSidebar"] {{
                background-color: #080808 !important;
                background-image: none !important;
                z-index: 10 !important;
                box-shadow: none !important;
            }}

            /* FORCE HIDE sidebar when closed on mobile to prevent layout competition */
            section[data-testid="stSidebar"][aria-expanded="false"] {{
                display: none !important;
                visibility: hidden !important;
                width: 0 !important;
            }}

            /* Streamlit Mobile Sidebar User Content Fix */
            div[data-testid="stSidebarUserContent"] {{
                background-color: #080808 !important;
            }}

            /* 12) GLOBAL UI CLEANUP: Hide standard header junk */
            .stAppDeployButton, #MainMenu, header[data-testid="stHeader"] a {{
                display: none !important;
            }}

            /* 13) STYLED NEON RED SIDEBAR TOGGLE (Updated to Red) */
            /* This target works for BOTH "Open" and "Close" states */
            button[data-testid="stSidebarCollapse"],
            button[aria-label*="sidebar"],
            .st-emotion-cache-not-found button[kind="headerNoPadding"] {{
                display: flex !important;
                visibility: visible !important;
                position: fixed !important;
                top: 10px !important;
                {toggle_side}: 15px !important;
                {toggle_opposite}: auto !important;
                z-index: 9999999 !important;
                background-color: #FF0000 !important; /* Neon Red */
                border: 2px solid #8B0000 !important;
                border-radius: 50% !important;
                box-shadow: 0 0 15px #FF0000, 0 0 30px rgba(255, 0, 0, 0.4) !important;
                width: 44px !important;
                height: 44px !important;
                opacity: 1 !important;
            }}

            /* Ensure the icon inside is White and clearly visible */
            button[aria-label*="sidebar"] svg,
            button[data-testid="stSidebarCollapse"] svg {{
                fill: #FFFFFF !important;
                color: #FFFFFF !important;
                width: 26px !important;
                height: 26px !important;
                stroke: #FFFFFF !important;
                stroke-width: 0.5px;
            }}

            /* Pulse animation for Neon Red effect */
            button[data-testid="stSidebarCollapse"] {{
                animation: neon-red-pulse 2s infinite alternate;
            }}

            @keyframes neon-red-pulse {{
                0% {{ box-shadow: 0 0 10px #FF0000, 0 0 20px rgba(255, 0, 0, 0.4); }}
                100% {{ box-shadow: 0 0 20px #FF0000, 0 0 40px rgba(255, 0, 0, 0.8); }}
            }}

            /* 14) Log Message Cards */
            .log-card {{
                background: rgba(255, 255, 255, 0.03) !important;
                border: 1px solid rgba(212, 175, 55, 0.1) !important;
                border-radius: 12px !important;
                padding: 12px 15px !important;
                margin-bottom: 8px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: space-between !important;
                transition: all 0.3s ease !important;
                direction: rtl !important;
            }}
            .log-card:hover {{
                background: rgba(212, 175, 55, 0.05) !important;
                border-color: rgba(212, 175, 55, 0.3) !important;
                transform: translateX(-5px) !important;
            }}
            .log-info {{
                display: flex !important;
                flex-direction: column !important;
                gap: 2px !important;
                text-align: right !important;
            }}
            .log-name {{
                font-weight: 700 !important;
                color: #FFF !important;
                font-size: 0.95rem !important;
            }}
            .log-phone {{
                font-size: 0.8rem !important;
                color: rgba(212, 175, 55, 0.8) !important;
            }}
            .log-status-group {{
                display: flex !important;
                flex-direction: column !important;
                align-items: flex-start !important;
                gap: 4px !important;
            }}
            .log-status {{
                display: flex !important;
                align-items: center !important;
                gap: 8px !important;
                font-size: 0.85rem !important;
            }}
            .log-time {{
                font-size: 0.75rem !important;
                color: #888 !important;
                font-family: 'Inter', sans-serif !important;
            }}
            .status-badge {{
                padding: 2px 8px !important;
                border-radius: 6px !important;
                font-size: 0.75rem !important;
                font-weight: 600 !important;
            }}
            .status-success {{ background: rgba(0, 255, 65, 0.1) !important; color: #00FF41 !important; border: 1px solid rgba(0, 255, 65, 0.2) !important; }}
            .status-error {{ background: rgba(255, 49, 49, 0.1) !important; color: #FF3131 !important; border: 1px solid rgba(255, 49, 49, 0.2) !important; }}

            /* === MOBILE RED ICONS: Table toolbar icons (fullscreen, search, download) === */
            [data-testid="stElementToolbar"] button,
            [data-testid="stElementToolbar"] svg,
            [data-testid="stDataFrame"] [data-testid="stElementToolbar"] button,
            [data-testid="stDataFrame"] [data-testid="stElementToolbar"] svg {{
                color: #FF0000 !important;
                fill: #FF0000 !important;
                filter: drop-shadow(0 0 6px rgba(255, 0, 0, 0.6)) !important;
            }}

            /* === MOBILE RED: WhatsApp export button === */
            /* WhatsApp Export Button - Mobile (Unified Luxury Style) */
            .whatsapp-export-btn .stButton button,
            .whatsapp-export-btn .stDownloadButton button,
            .stDownloadButton button {{
                background: linear-gradient(135deg, #0a0e1a 0%, #06080f 100%) !important;
                color: #D4AF37 !important;
                border: 1.5px solid #D4AF37 !important;
                box-shadow: 0 0 10px rgba(212, 175, 55, 0.2) !important;
                text-shadow: 0 0 5px rgba(212, 175, 55, 0.3) !important;
            }}
            .whatsapp-export-btn .stButton button:hover,
            .whatsapp-export-btn .stDownloadButton button:hover,
            .stDownloadButton button:hover {{
                background: #D4AF37 !important;
                color: #000000 !important;
                border-color: #D4AF37 !important;
                box-shadow: 0 0 20px rgba(212, 175, 55, 0.5) !important;
            }}

            /* === MOBILE RED: Selectbox / Dropdown arrows === */
            div[data-baseweb="select"] svg,
            div[data-baseweb="select"] [data-testid="stSelectboxChevron"],
            .stSelectbox svg,
            .stSelectbox [role="combobox"] svg,
            div[data-baseweb="popover"] svg {{
                color: #FF0000 !important;
                fill: #FF0000 !important;
                filter: drop-shadow(0 0 4px rgba(255, 0, 0, 0.5)) !important;
            }}

            /* === MOBILE RED: Expander toggle arrows === */
            .stExpander summary svg,
            .status-error {{ background: rgba(255, 49, 49, 0.1) !important; color: #FF3131 !important; border: 1px solid rgba(255, 49, 49, 0.2) !important; }}

            /* Table Translator Button - Mobile (Red) */
            .table-translator-btn button {{
                background: linear-gradient(135deg, #FF0000 0%, #8B0000 100%) !important;
                color: #FFFFFF !important;
                border: 2px solid #FF3131 !important;
                box-shadow: 0 0 15px rgba(255, 0, 0, 0.4) !important;
            }}

            /* Login Input Fields Mobile Overrides (Black text on Light background) */
            div[data-testid="stForm"] div[data-baseweb="input"] {{
                background: rgba(255, 255, 255, 0.95) !important;
                border-color: #FFFFFF !important;
                box-shadow: 0 0 15px rgba(255, 255, 255, 0.5) !important;
            }}
            div[data-testid="stForm"] .stTextInput input {{
                color: #000000 !important;
                text-shadow: none !important;
                font-weight: bold !important;
            }}
            div[data-testid="stForm"] label p {{
                color: #FFFFFF !important;
                text-shadow: 0 0 8px rgba(255, 255, 255, 0.8) !important;
            }}
        }}


        /* Table Translator Button - Desktop/Tablet (White) */
        .table-translator-btn button {{
            background: linear-gradient(135deg, #FFFFFF 0%, #E0E0E0 100%) !important;
            color: #000000 !important;
            border: 2px solid #FFFFFF !important;
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.3) !important;
            font-weight: 700 !important;
        }}
        .table-translator-btn button:hover {{
            transform: scale(1.05) !important;
            box-shadow: 0 0 25px rgba(255, 255, 255, 0.6) !important;
        }}
    </style>
    """
