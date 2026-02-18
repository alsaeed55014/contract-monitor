def get_css():
    return """
    <style>
        /* General Imports */
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;700&family=Cinzel:wght@600&family=Orbitron:wght@600&display=swap');
        
        /* Main Container */
        .stApp {
            background-color: #0F0F0F;
            color: #F8F8F8;
            font-family: 'Tajawal', sans-serif;
        }

        /* Headers */
        h1, h2, h3 {
            color: #D4AF37 !important; /* Gold */
            font-family: 'Tajawal', sans-serif;
            text-align: center;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }

        /* Login Screen Prestigious Layout */
        .login-screen-wrapper {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px 20px;
        }

        .login-screen-wrapper img {
            border-radius: 50%;
            border: 3px solid #D4AF37;
            box-shadow: 0 0 25px rgba(212, 175, 55, 0.4);
            margin-bottom: 25px;
        }

        .login-box-premium {
            background: rgba(30, 30, 30, 0.85);
            padding: 45px;
            border-radius: 30px;
            box-shadow: 0 25px 60px rgba(0,0,0,1);
            border: 1px solid rgba(212, 175, 55, 0.35);
            backdrop-filter: blur(20px);
            max-width: 480px;
            width: 100%;
            text-align: center;
        }

        /* Programmer Credit - Prestigious */
        .programmer-credit {
            color: #D4AF37;
            font-family: 'Cinzel', serif;
            margin-top: 5px;
            font-size: 1.2em;
            letter-spacing: 4px;
            text-align: center;
            font-weight: 700;
            text-shadow: 0 0 12px rgba(212, 175, 55, 0.4);
            text-transform: uppercase;
        }
        
        /* Premium Buttons */
        .login-box-premium .stButton > button {
            background: linear-gradient(135deg, #D4AF37 0%, #B8860B 100%) !important;
            color: #000 !important;
            font-weight: 800 !important;
            letter-spacing: 1px !important;
            border: none !important;
            padding: 12px 0 !important;
            box-shadow: 0 4px 15px rgba(212, 175, 55, 0.4) !important;
        }
        
        .login-box-premium .stButton > button:hover {
            background: linear-gradient(135deg, #ECC846 0%, #D4AF37 100%) !important;
            box-shadow: 0 0 25px rgba(212, 175, 55, 0.7) !important;
            transform: scale(1.02);
        }

        /* Sidebar Styling & Centering */
        section[data-testid="stSidebar"] {
            background-color: #161616 !important;
            border-left: 1px solid rgba(212, 175, 55, 0.1);
        }
        
        section[data-testid="stSidebar"] .stImage {
             display: flex;
             justify-content: center;
             margin-bottom: 0px !important;
        }
        
        section[data-testid="stSidebar"] .stImage img {
            border-radius: 50%;
            border: 2px solid #D4AF37;
            padding: 3px;
        }

        /* All Sidebar Buttons Uniform */
        section[data-testid="stSidebar"] .stButton > button {
            background-color: #D4AF37;
            color: #000;
            font-weight: 700;
            border: none;
            border-radius: 8px;
            padding: 12px 0px;
            margin: 8px 0px !important; /* Equal spacing */
            width: 100% !important;
            height: 45px !important;
            display: flex;
            justify-content: center;
            align-items: center;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            font-size: 0.95rem;
        }
        
        section[data-testid="stSidebar"] .stButton > button:hover {
            background-color: #ECC846;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(212, 175, 55, 0.4);
        }

        /* Data Tables - Modern Green Text */
        div[data-testid="stDataFrame"] td, 
        div[data-testid="stTable"] td,
        .styled-table td {
            color: #4CAF50 !important; /* Elegant Green */
            font-weight: 500;
        }
        
        div[data-testid="stDataFrame"] th, 
        div[data-testid="stTable"] th {
            color: #D4AF37 !important;
            font-weight: 700;
            background-color: #1A1A1A !important;
        }

        /* Custom Inputs */
        .stTextInput > div > div > input {
            background-color: #222 !important;
            color: #fff !important;
            border: 1px solid #444 !important;
            border-radius: 8px !important;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #D4AF37 !important;
            box-shadow: 0 0 5px rgba(212, 175, 55, 0.5) !important;
        }
    </style>
    """
