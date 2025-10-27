import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import hashlib
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import os
from PIL import Image

# -------------------------
# Paths & Logo preparation
# -------------------------
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
PHOTO_DIR = ROOT / "photos"
ISSUED_PHOTOS_DIR = PHOTO_DIR / "issued"
REPORT_DIR = ROOT / "reports"
for d in [DATA_DIR, PHOTO_DIR, ISSUED_PHOTOS_DIR, REPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "stock_requests.csv"

# Locate logo (supports various filenames)
SUPPLIED_LOGO_PATHS = [
    DATA_DIR / "acucomm logo.png",
    ROOT / "acucomm logo.png",
    ROOT / "Acucomm logo.jpg",
    ROOT / "Acucomm_logo.png"
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

        # Generate favicon from cropped logo section
        img = Image.open(logo_path).convert("RGBA")
        w, h = img.size
        crop_box = (0, 0, max(32, int(w * 0.25)), h)
        icon_img = img.crop(crop_box).resize((32, 32), Image.LANCZOS)
        bio = BytesIO()
        icon_img.save(bio, format="PNG")
        bio.seek(0)
        _favicon_bytes = bio.read()
    except Exception:
        _favicon_bytes = _full_logo_bytes

page_icon = _favicon_bytes if _favicon_bytes else "📦"
st.set_page_config(page_title="Acucomm Stock Management", page_icon=page_icon, layout="centered")

# -------------------------
# Utility Helpers
# -------------------------
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

# -------------------------
# User Credentials
# -------------------------
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

# -------------------------
# Custom CSS (Branding)
# -------------------------
st.markdown("""
    <style>
    body {
        background-color: #f5f7fb;
    }
    .login-card {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 40px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        width: 420px;
        margin: 60px auto;
        text-align: center;
    }
    .login-title {
        color: #0a3d62;
        font-size: 32px;
        font-weight: 700;
        margin-bottom: 30px;
    }
    .login-subtext {
        font-size: 16px;
        color: #4b6584;
        margin-bottom: 40px;
    }
    .stTextInput>div>div>input {
        border-radius: 8px;
        border: 1px solid #ccc;
    }
    .stButton>button {
        background-color: #0a3d62;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 10px 0;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #1e6091;
    }
    .small-note {
        font-size: 12px;
        color: #8395a7;
        margin-top: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------
# Render Header with Logo
# -------------------------
def render_header():
    if _full_logo_bytes:
        st.image(_full_logo_bytes, width=180)
    st.markdown("<div style='text-align:center;'><h1 class='login-title'>Acucomm Stock Management</h1></div>", unsafe_allow_html=True)

# -------------------------
# Login UI (Modern Card)
# -------------------------
def login_ui():
    st.markdown("<div class='login-card'>", unsafe_allow_html=True)

    if _full_logo_bytes:
        st.image(_full_logo_bytes, width=140)
    st.markdown("<div class='login-title'>Login</div>", unsafe_allow_html=True)
    st.markdown("<div class='login-subtext'>Use your contractor / city / installer credentials.</div>", unsafe_allow_html=True)

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

def logout():
    st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None}
    safe_rerun()

# -------------------------
# Routing
# -------------------------
if not st.session_state.auth["logged_in"]:
    login_ui()
else:
    render_header()
    st.sidebar.write(f"Logged in as **{st.session_state.auth['name']}** ({st.session_state.auth['role']})")
    if st.sidebar.button("Logout"):
        logout()
    st.success("✅ Dashboard access granted.")
