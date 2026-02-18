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

        /* Stats Cards - Standard Appearance */
        div[data-testid="stMetricValue"] {
            color: #D4AF37;
            font-family: 'Orbitron', sans-serif;
        }

        /* Programmer Credit */
        .programmer-credit {
            color: #D4AF37;
            font-family: 'Cinzel', serif; /* Elegant English font */
            margin-top: 10px;
            font-size: 0.9em;
            letter-spacing: 2px;
            text-align: center;
            font-weight: 600;
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
