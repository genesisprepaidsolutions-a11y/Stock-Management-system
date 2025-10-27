import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import hashlib
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import os
from PIL import Image

# ======================================================
# PATHS & INITIAL SETUP
# ======================================================
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
PHOTO_DIR = ROOT / "photos"
ISSUED_PHOTOS_DIR = PHOTO_DIR / "issued"
REPORT_DIR = ROOT / "reports"

for d in [DATA_DIR, PHOTO_DIR, ISSUED_PHOTOS_DIR, REPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DATA_FILE = DATA_DIR / "stock_requests.csv"

# Locate logo (multiple filename options)
SUPPLIED_LOGO_PATHS = [
    ROOT / "Acucomm logo.jpg",
    ROOT / "Acucomm_logo.png",
    ROOT / "acucomm_logo.png",
    ROOT / "acucomm logo.png"
]

def find_logo_path():
    for p in SUPPLIED_LOGO_PATHS:
        if p.exists():
            return p
    return None

logo_path = find_logo_path()
_full_logo_bytes = None
_favicon_bytes = None

if logo_path:
    try:
        with open(logo_path, "rb") as f:
            _full_logo_bytes = f.read()
        img = Image.open(logo_path).convert("RGBA")
        w, h = img.size
        icon_img = img.crop((0, 0, max(32, int(w * 0.25)), h)).resize((32, 32), Image.LANCZOS)
        bio = BytesIO()
        icon_img.save(bio, format="PNG")
        bio.seek(0)
        _favicon_bytes = bio.read()
    except Exception:
        _favicon_bytes = _full_logo_bytes

page_icon = _favicon_bytes if _favicon_bytes else "📦"
st.set_page_config(page_title="Acucomm Stock Management", page_icon=page_icon, layout="wide")

# ======================================================
# UTILITIES
# ======================================================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def load_data():
    if DATA_FILE.exists():
        try:
            return pd.read_csv(DATA_FILE)
        except Exception:
            pass
    cols = [
        "Date_Requested", "Request_ID", "Contractor_Name", "Installer_Name",
        "Meter_Type", "Requested_Qty", "Approved_Qty", "Photo_Path",
        "Status", "Contractor_Notes", "City_Notes", "Decline_Reason",
        "Date_Approved", "Date_Received"
    ]
    return pd.DataFrame(columns=cols)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def generate_request_id():
    return f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}"

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None}

def safe_rerun():
    try:
        st.rerun()
    except Exception:
        pass

# ======================================================
# USERS
# ======================================================
raw_users = {
    "Deezlo": {"name": "Deezlo", "password": "Deezlo123", "role": "contractor"},
    "ethekwini": {"name": "ethekwini", "password": "ethwkwini123", "role": "city"},
    "installer1": {"name": "installer1", "password": "installer123", "role": "installer"},
    "Reece": {"name": "Reece", "password": "Reece123!", "role": "manager"},
    "Nimba": {"name": "Nimba", "password": "Nimba123", "role": "contractor"},
}

CREDENTIALS = {
    u: {
        "name": v["name"],
        "password_hash": hash_password(v["password"]),
        "role": v["role"],
    }
    for u, v in raw_users.items()
}

# ======================================================
# BRANDING CSS
# ======================================================
st.markdown("""
    <style>
    body {
        background: linear-gradient(135deg, #4CAF50, #2E7D32);
        color: #1b1b1b;
        font-family: "Helvetica Neue", sans-serif;
    }
    .login-card {
        background-color: #ffffff;
        border-radius: 20px;
        padding: 40px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        width: 400px;
        margin: 80px auto;
        text-align: center;
    }
    .login-title {
        font-size: 28px;
        font-weight: 700;
        color: #2E7D32;
        margin-bottom: 15px;
    }
    .login-subtext {
        font-size: 15px;
        color: #4b6584;
        margin-bottom: 30px;
    }
    .stTextInput>div>div>input {
        border-radius: 8px;
        border: 1px solid #ccc;
        padding: 8px;
    }
    .stButton>button {
        background-color: #2E7D32;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 10px 0;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #43A047;
    }
    .footer-note {
        font-size: 12px;
        color: #ffffff;
        text-align: center;
        margin-top: 30px;
    }
    /* Dashboard elements */
    .stDataFrame, .stTable {
        border-radius: 10px;
        background-color: #ffffff;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# ======================================================
# LOGIN UI
# ======================================================
def login_ui():
    st.markdown("<div class='login-card'>", unsafe_allow_html=True)
    if _full_logo_bytes:
        st.image(_full_logo_bytes, width=180)
    st.markdown("<div class='login-title'>Acucomm Stock Management</div>", unsafe_allow_html=True)
    st.markdown("<div class='login-subtext'>Use your contractor / city / installer credentials to access the system.</div>", unsafe_allow_html=True)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in CREDENTIALS and hash_password(password) == CREDENTIALS[username]["password_hash"]:
            st.session_state.auth.update({
                "logged_in": True,
                "username": username,
                "role": CREDENTIALS[username]["role"],
                "name": CREDENTIALS[username]["name"]
            })
            safe_rerun()
        else:
            st.error("Invalid username or password.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='footer-note'>Need help? Contact <a style='color:white;' href='mailto:reece@acucomm.co.za'>reece@acucomm.co.za</a></div>", unsafe_allow_html=True)

def logout():
    st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None}
    safe_rerun()

# ======================================================
# DASHBOARD
# ======================================================
def render_dashboard():
    if _full_logo_bytes:
        st.sidebar.image(_full_logo_bytes, width=140)
    st.sidebar.title(f"Welcome, {st.session_state.auth['name']}")
    st.sidebar.write(f"Role: **{st.session_state.auth['role']}**")

    if st.sidebar.button("Logout"):
        logout()

    st.title("📦 Acucomm Stock Dashboard")
    st.write("Overview of all meter stock requests and statuses.")

    df = load_data()
    st.dataframe(df, use_container_width=True)

# ======================================================
# ROUTING
# ======================================================
if not st.session_state.auth["logged_in"]:
    login_ui()
else:
    render_dashboard()
