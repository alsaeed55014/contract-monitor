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
            text-align: center;
        }

        /* Stats Cards */
        div[data-testid="stMetricValue"] {
            color: #D4AF37;
            font-family: 'Orbitron', sans-serif;
        }

        /* Login Box */
        .login-box {
            background-color: #1E1E1E;
            padding: 20px; /* Reduced padding */
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            text-align: center;
            border: 1px solid #333;
            max-width: 400px; /* Limit width */
            margin: 0 auto;
        }
        
        .programmer-credit {
            color: #D4AF37;
            font-family: 'Orbitron', sans-serif;
            margin-top: 15px;
            font-size: 0.8em;
            letter-spacing: 1px;
            text-align: center;
        }

        /* Custom Buttons */
        .stButton > button {
            background-color: #D4AF37;
            color: #000000;
            font-weight: bold;
            border: none;
            border-radius: 5px;
            padding: 8px 20px;
            transition: all 0.3s;
            width: 100%;
        }
        .stButton > button:hover {
            background-color: #B2912F;
            color: #fff;
            box-shadow: 0 0 10px #D4AF37;
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #1E1E1E;
        }
        
        /* Smaller Inputs for Login */
        .stTextInput > div > div > input {
            background-color: #2b2b2b;
            color: white;
            border: 1px solid #444;
            padding: 5px 10px; /* Smaller padding */
            font-size: 0.9rem;
        }
        
        /* Hide User Text */
        .user-text {
            display: None;
        }
    </style>
    """
