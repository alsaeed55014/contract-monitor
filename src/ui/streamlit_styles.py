def get_css():
    return """
    <style>
        /* General Imports */
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;700&family=Orbitron:wght@600&display=swap');
        
        /* Main Container */
        .stApp {
            background-color: #121212;
            color: #E0E0E0;
            font-family: 'Tajawal', sans-serif;
        }

        /* Headers */
        h1, h2, h3 {
            color: #D4AF37 !important; /* Gold */
            font-family: 'Tajawal', sans-serif;
        }

        /* Stats Cards */
        div[data-testid="stMetricValue"] {
            color: #D4AF37;
            font-family: 'Orbitron', sans-serif;
        }

        /* Login Box */
        .login-box {
            background-color: #1E1E1E;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            text-align: center;
            border: 1px solid #333;
        }
        
        .programmer-credit {
            color: #D4AF37;
            font-style: italic;
            margin-top: 20px;
            font-size: 0.9em;
        }

        /* Custom Buttons */
        .stButton > button {
            background-color: #D4AF37;
            color: #000000;
            font-weight: bold;
            border: none;
            border-radius: 5px;
            padding: 10px 20px;
            transition: all 0.3s;
        }
        .stButton > button:hover {
            background-color: #B2912F;
            color: #fff;
            box-shadow: 0 0 10px #D4AF37;
        }
        
        /* Tables */
        .stDataFrame {
            border: 1px solid #333;
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #1E1E1E;
        }
        
        /* Inputs */
        .stTextInput > div > div > input {
            background-color: #2b2b2b;
            color: white;
            border: 1px solid #444;
        }
    </style>
    """
