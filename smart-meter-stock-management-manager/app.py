import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import hashlib
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
import os
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL")

# === Streamlit Config ===
st.set_page_config(page_title="Acucomm Stock Management", page_icon="📦", layout="wide")

# === Directories ===
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
PHOTO_DIR = ROOT / "photos"
ISSUED_PHOTOS_DIR = PHOTO_DIR / "issued"
REPORT_DIR = ROOT / "reports"
for d in [DATA_DIR, PHOTO_DIR, ISSUED_PHOTOS_DIR, REPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "stock_requests.csv"

# === Display Logo ===
logo_path = ROOT / "Acucomm logo.jpg"
if logo_path.exists():
    st.image(str(logo_path), width=200)
st.markdown("<h1 style='text-align: center;'>Stock Management</h1>", unsafe_allow_html=True)
st.markdown("---")

# === Email Utility ===
def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"] = FROM_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.set_debuglevel(1)  # DEBUG prints to console
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        server.quit()
        st.success(f"[EMAIL SENT] To: {to_email} | Subject: {subject}")
        return True, "Email sent successfully!"
    except Exception as e:
        st.error(f"[EMAIL FAILED] To: {to_email} | Subject: {subject} | Error: {e}")
        return False, f"Email failed: {e}"

# === User Database ===
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

raw_users = {
    "Deezlo": {"name": "Deezlo", "password": "Deezlo123", "role": "contractor", "email": "thando@acucomm.co.za"},
    "ethekwini": {"name": "ethekwini", "password": "ethekwini123", "role": "city", "email": "amanda@acucomm.co.za"},
    "installer1": {"name": "installer1", "password": "installer123", "role": "installer", "email": "alistair@acucomm.co.za"},
    "Reece": {"name": "Reece", "password": "Reece123!", "role": "manager", "email": "reece@acucomm.co.za"},
}

CREDENTIALS = {
    u: {
        "name": v["name"],
        "password_hash": hash_password(v["password"]),
        "role": v["role"],
        "email": v["email"],
    }
    for u, v in raw_users.items()
}

# === Utility Functions ===
def load_data():
    cols = [
        "Date_Requested", "Request_ID", "Contractor_Name", "Installer_Name",
        "Meter_Type", "Requested_Qty", "Approved_Qty", "Photo_Path",
        "Status", "Contractor_Notes", "City_Notes", "Decline_Reason",
        "Date_Approved", "Date_Received"
    ]
    if DATA_FILE.exists():
        try:
            df = pd.read_csv(DATA_FILE)
        except Exception as e:
            st.error(f"Error loading CSV: {e}")
            df = pd.DataFrame(columns=cols)
    else:
        df = pd.DataFrame(columns=cols)

    # Enforce proper dtypes
    numeric_cols = ["Requested_Qty", "Approved_Qty"]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    date_cols = ["Date_Requested", "Date_Approved", "Date_Received"]
    for c in date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    text_cols = ["Request_ID", "Contractor_Name", "Installer_Name", "Meter_Type",
                 "Photo_Path", "Status", "Contractor_Notes", "City_Notes", "Decline_Reason"]
    for c in text_cols:
        if c in df.columns:
            df[c] = df[c].astype(str)

    return df

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def generate_request_id():
    return f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}"

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None, "email": None}

def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        pass

# === Login ===
def login_ui():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in CREDENTIALS and hash_password(password) == CREDENTIALS[username]["password_hash"]:
            st.session_state.auth.update({
                "logged_in": True,
                "username": username,
                "role": CREDENTIALS[username]["role"],
                "name": CREDENTIALS[username]["name"],
                "email": CREDENTIALS[username]["email"]
            })
            safe_rerun()
        else:
            st.error("Invalid credentials.")

def logout():
    st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None, "email": None}
    safe_rerun()

# === Contractor UI ===
def contractor_ui():
    st.header("👷 Contractor - Submit Stock Reque
