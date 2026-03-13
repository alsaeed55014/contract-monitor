def get_css(lang='ar'):
    direction = 'rtl' if lang == 'ar' else 'ltr'
    checkbox_text_align = 'right' if lang == 'ar' else 'left'
    bell_col_idx = 4 if lang == 'ar' else 1
    toggle_side = 'right' if lang == 'ar' else 'left'
    toggle_opposite = 'left' if lang == 'ar' else 'right'
    sidebar_border_side = 'left' if lang == 'ar' else 'right'
    
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

        /* Fix Checkbox Spacing */
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

        /* 2) Layout & Spacing */
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
            font-size: 20px !important;
            font-weight: 700 !important;
            text-align: center !important;
            background: linear-gradient(to bottom, #FFFFFF 20%, #D4AF37 100%) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            text-shadow: 0 4px 15px rgba(212, 175, 55, 0.4) !important;
            margin: -10px 0 5px 0 !important;
            padding: 0 !important; 
            letter-spacing: 1px !important;
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

        .profile-img-circular {{
            width: 70px;
            height: 70px;
            border-radius: 50%;
            border: 2px solid var(--luxury-gold);
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.3);
            object-fit: cover;
        }}

        /* Universal Luxury Button Style */
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
            width: 100% !important;
        }}

        .stButton button:hover, div[data-testid="stFormSubmitButton"] button:hover {{
            background: var(--luxury-gold) !important;
            color: #000 !important;
            border-color: var(--luxury-gold) !important;
            box-shadow: 0 0 25px rgba(212, 175, 55, 0.5) !important;
            transform: translateY(-3px) scale(1.02) !important;
        }}

        /* Table & Data Presentation */
        [data-testid="stDataFrame"], [data-testid="stTable"], .neon-white-table {{
            background: rgba(255, 255, 255, 1) !important;
            border: 2px solid #FFFFFF !important;
            border-radius: 12px !important;
            box-shadow: 0 0 30px rgba(255, 255, 255, 0.8), 
                        inset 0 0 15px rgba(255, 255, 255, 0.5) !important;
            margin: 20px 0 !important;
            color: #000000 !important;
        }}

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {{
            background-color: #080808 !important;
            border-{sidebar_border_side}: 1px solid rgba(212, 175, 55, 0.15) !important;
        }}

        /* Persistent Top Banner */
        .persistent-top-banner {{
            position: sticky;
            top: 0;
            z-index: 1000;
            background: rgba(10, 10, 10, 0.7);
            backdrop-filter: blur(20px);
            border-bottom: 2px solid rgba(212, 175, 55, 0.3);
            margin: -1rem -5rem 2rem -5rem !important;
            padding: 1rem 5rem !important;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}

        /* Notification Bell Styling */
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
    </style>
    """
