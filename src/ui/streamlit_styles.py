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
            text-shadow: 0 1px 2px rgba(0,0,0,0.5);
            margin: 0 !important;
            padding: 0 !important;
        }

        /* 1. Login Screen Centering Container (Strict 100vh) */
        .login-screen-wrapper {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 90vh; /* Full focus */
            width: 100%;
            margin: 0;
            padding: 0;
        }

        /* 2. Profile Picture (Hyper Compact 70px) */
        .login-screen-wrapper img {
            width: 70px !important;
            height: 70px !important;
            border-radius: 50% !important;
            object-fit: cover !important;
            border: 2px solid #D4AF37 !important;
            box-shadow: 0 0 10px rgba(212, 175, 55, 0.2) !important;
            margin-bottom: 6px !important; /* Very close to title */
            display: block;
            margin-left: auto;
            margin-right: auto;
        }

        /* 3. Premium Login Card (Targeting Streamlit Form) - Compact */
        .login-screen-wrapper div[data-testid="stForm"] {
            background: rgba(22, 22, 22, 0.96) !important;
            padding: 18px 20px !important; /* Tight Padding */
            border-radius: 16px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3) !important;
            border: 1px solid rgba(255, 255, 255, 0.04) !important;
            backdrop-filter: blur(10px) !important;
            max-width: 380px !important; /* Explicit Max Width */
            width: 100% !important;
            margin: 0 auto !important;
            gap: 8px !important; /* Tight spacing between elements */
        }
        
        /* Typography - Compact */
        .welcome-title {
            font-family: 'Cairo', sans-serif;
            font-size: 18px !important;
            color: #E0E0E0 !important;
            font-weight: 700;
            margin-bottom: 2px !important;
            text-align: center;
            line-height: 1.1 !important;
            letter-spacing: 0px !important;
        }
        
        .welcome-subtitle {
            font-family: 'Cairo', sans-serif;
            font-size: 11px !important;
            color: #777 !important;
            margin-bottom: 10px !important;
            text-align: center;
            line-height: 1.1 !important;
        }

        /* 4. Input Fields (Hyper Compact 38px) */
        .stTextInput {
            margin-bottom: 0px !important; 
        }
        
        div[data-testid="stForm"] .stTextInput > div > div > input {
            background-color: #151515 !important;
            color: #E0E0E0 !important;
            border: 1px solid #2A2A2A !important;
            border-radius: 8px !important;
            height: 38px !important; /* Small Height */
            min-height: 38px !important;
            padding: 0 10px !important;
            font-size: 13px !important;
            transition: all 0.2s ease;
        }
        
        div[data-testid="stForm"] .stTextInput > div > div > input:focus {
            border-color: #D4AF37 !important;
            background-color: #1A1A1A !important;
        }

        /* 5. Login Button (Compact 40px) */
        .login-screen-wrapper div[data-testid="stForm"] .stButton {
            padding-top: 8px !important;
        }

        .login-screen-wrapper div[data-testid="stForm"] .stButton > button {
            background: linear-gradient(135deg, #CFAA36 0%, #B07E08 100%) !important;
            color: #000 !important;
            font-weight: 600 !important;
            font-family: 'Cairo', sans-serif !important;
            border: none !important;
            padding: 0 !important;
            height: 40px !important; /* Small Button */
            min-height: 40px !important;
            border-radius: 8px !important;
            width: 100% !important;
            font-size: 14px !important;
            box-shadow: 0 2px 8px rgba(212, 175, 55, 0.15) !important;
            transition: all 0.2s ease !important;
        }
        
        .login-screen-wrapper div[data-testid="stForm"] .stButton > button:hover {
            transform: translateY(-1px);
            filter: brightness(1.08);
        }

        /* Footer & Language Toggle - Very Small */
        .programmer-credit {
            color: #555;
            font-family: 'Inter', sans-serif;
            margin-top: 12px !important;
            font-size: 0.7em !important;
            letter-spacing: 0.5px;
            text-align: center;
            opacity: 0.6;
            margin-bottom: 4px !important;
        }

        /* Language Toggle - Mini */
        div:has(> #lang-toggle-anchor) + div .stButton > button {
            width: auto !important;
            min-width: 60px !important;
            height: 28px !important;
            border-radius: 14px !important;
            font-size: 12px !important; 
            font-weight: 500 !important;
            background-color: transparent !important;
            color: #666 !important;
            border: 1px solid #222 !important;
            margin: 4px auto !important;
            box-shadow: none !important;
            padding: 0 12px !important;
        }
        
        div:has(> #lang-toggle-anchor) + div .stButton > button:hover {
            color: #D4AF37 !important;
            border-color: #D4AF37 !important;
            background-color: rgba(212, 175, 55, 0.05) !important;
        }
        
        /* Remove default Streamlit block spacing */
        .block-container {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
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
