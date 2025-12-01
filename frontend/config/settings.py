"""
Configuración del frontend
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# UI Configuration
PAGE_TITLE = "Dashboard Producción Odoo"
PAGE_ICON = "📦"
LAYOUT = "wide"

# Custom CSS for premium look
CUSTOM_CSS = """
    <style>
        .main {
            background-color: #0e1117;
        }
        .metric-card {
            background: linear-gradient(145deg, #1e1e1e, #2d2d2d);
            padding: 20px;
            border-radius: 15px;
            box-shadow: 5px 5px 15px rgba(0,0,0,0.5), -5px -5px 15px rgba(50,50,50,0.1);
            text-align: center;
            margin: 10px 0;
        }
        .metric-label {
            color: #888;
            font-size: 0.9rem;
            font-weight: 500;
            margin-bottom: 5px;
        }
        .metric-value {
            color: #00ff88;
            font-size: 2rem;
            font-weight: bold;
        }
        .stButton>button {
            background-color: #ff4444;
            color: white;
            border-radius: 10px;
            padding: 10px 24px;
            font-weight: 600;
            border: none;
        }
        .stButton>button:hover {
            background-color: #ff3333;
        }
    </style>
"""
