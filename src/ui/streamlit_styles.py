def get_css():
    return """
    <style>
        /* General Imports */
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;700&family=Cairo:wght@400;600;700&family=Inter:wght@400;600&family=Alex+Brush&display=swap');
        
        /* Main Container */
        .stApp {
            background-color: #0F0F0F;
            color: #F8F8F8;
            font-family: 'Cairo', 'Tajawal', sans-serif;
        }

        /* Headers */
        h1, h2, h3 {
            color: #D4AF37 !important; /* Gold */
            font-family: 'Cairo', sans-serif;
            text-align: center;
            text-shadow: 0 1px 3px rgba(0,0,0,0.5);
            margin: 0 !important;
            padding: 0 !important;
        }

        /* 1. Login Screen Centering Container (Strict 100vh) */
        .login-screen-wrapper {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 85vh; /* Almost full viewport */
            width: 100%;
            margin: 0;
            padding: 0;
        }

        /* 2. Profile Picture (Compact 80px) */
        .login-screen-wrapper img {
            width: 80px !important;
            height: 80px !important;
            border-radius: 50% !important;
            object-fit: cover !important;
            border: 2px solid #D4AF37 !important;
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.3) !important;
            margin-bottom: 8px !important; /* Close to title */
            display: block;
            margin-left: auto;
            margin-right: auto;
        }

        /* 3. Premium Login Card (Targeting Streamlit Form) */
        .login-screen-wrapper div[data-testid="stForm"] {
            background: rgba(25, 25, 25, 0.95) !important;
            padding: 22px 24px !important; /* Compact Padding */
            border-radius: 18px !important;
            box-shadow: 0 8px 25px rgba(0,0,0,0.25) !important;
            border: 1px solid rgba(255, 255, 255, 0.05) !important;
            backdrop-filter: blur(10px) !important;
            max-width: 420px !important;
            width: 100% !important;
            margin: 0 auto !important;
            gap: 10px !important; /* Spacing between elements */
        }
        
        /* Typography */
        .welcome-title {
            font-family: 'Cairo', sans-serif;
            font-size: 20px !important;
            color: #E0E0E0 !important;
            font-weight: 700;
            margin-bottom: 4px !important;
            text-align: center;
            line-height: 1.2 !important;
        }
        
        .welcome-subtitle {
            font-family: 'Cairo', sans-serif;
            font-size: 12px !important;
            color: #888 !important;
            margin-bottom: 12px !important;
            text-align: center;
            line-height: 1.2 !important;
        }

        /* 4. Input Fields (Compact 42px) */
        .stTextInput {
            margin-bottom: 0px !important; /* Remove default margin */
        }
        
        .stTextInput > div > div > input {
            background-color: #1A1A1A !important;
            color: #E0E0E0 !important;
            border: 1px solid #333 !important;
            border-radius: 10px !important;
            height: 42px !important;
            padding: 0 12px !important;
            font-size: 14px !important;
            transition: all 0.2s ease;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #D4AF37 !important;
            box-shadow: 0 0 0 1px rgba(212, 175, 55, 0.3) !important;
            background-color: #202020 !important;
        }

        /* 5. Login Button (Compact 44px) */
        .login-screen-wrapper div[data-testid="stForm"] .stButton {
            padding-top: 10px !important;
        }

        .login-screen-wrapper div[data-testid="stForm"] .stButton > button {
            background: linear-gradient(135deg, #CFAA36 0%, #B07E08 100%) !important;
            color: #000 !important;
            font-weight: 600 !important;
            font-family: 'Cairo', sans-serif !important;
            border: none !important;
            padding: 0 !important;
            height: 44px !important;
            border-radius: 10px !important;
            width: 100% !important;
            font-size: 15px !important;
            box-shadow: 0 4px 10px rgba(212, 175, 55, 0.2) !important;
            transition: all 0.2s ease !important;
        }
        
        .login-screen-wrapper div[data-testid="stForm"] .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 12px rgba(212, 175, 55, 0.3) !important;
            filter: brightness(1.1);
        }

        /* Footer & Language Toggle */
        .programmer-credit {
            color: #666;
            font-family: 'Inter', sans-serif;
            margin-top: 15px !important;
            font-size: 0.75em !important;
            letter-spacing: 0.5px;
            text-align: center;
            opacity: 0.8;
            margin-bottom: 5px !important;
        }

        /* Language Toggle - Compact Pill */
        div:has(> #lang-toggle-anchor) + div .stButton > button {
            width: auto !important;
            min-width: 70px !important;
            height: 32px !important;
            border-radius: 16px !important;
            font-size: 13px !important; 
            font-weight: 600 !important;
            background-color: transparent !important;
            color: #777 !important;
            border: 1px solid #333 !important;
            margin: 5px auto !important;
            box-shadow: none !important;
        }
        
        div:has(> #lang-toggle-anchor) + div .stButton > button:hover {
            color: #D4AF37 !important;
            border-color: #D4AF37 !important;
            background-color: rgba(212, 175, 55, 0.05) !important;
        }

        /* Sidebar Styling (Unchanged) */
        section[data-testid="stSidebar"] {
            background-color: #161616 !important;
            border-left: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        section[data-testid="stSidebar"] div:has(> #lang-toggle-anchor) + div .stButton > button {
             height: 120px !important;
             width: 120px !important;
             background-color: #1E1E1E !important;
             color: #F8F8F8 !important;
             border-radius: 25px !important;
             margin: 0 auto !important;
        }
        
        /* Data Tables */
        div[data-testid="stDataFrame"] td, 
        div[data-testid="stTable"] td,
        .styled-table td {
            color: #E0E0E0 !important;
            border-bottom: 1px solid #333 !important;
        }
        
        div[data-testid="stDataFrame"] th, 
        div[data-testid="stTable"] th {
            color: #D4AF37 !important;
            font-weight: 700;
            background-color: #1A1A1A !important;
        }
    </style>
    """
