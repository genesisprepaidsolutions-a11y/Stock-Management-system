import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import hashlib
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64
import shutil
import requests
from PIL import Image

# ====================================================
# === THEME & BRAND COLOURS ===
# ====================================================
PRIMARY_BLUE = "#003366"
SECONDARY_BLUE = "#0072BC"
LIGHT_BLUE = "#E6F2FA"
WHITE = "#FFFFFF"
GREY = "#F5F7FA"

# ====================================================
# === PAGE CONFIG ===
# ====================================================
ROOT = Path(__file__).parent
favicon_path = ROOT / "favicon.jpg"
favicon_image = Image.open(favicon_path) if favicon_path.exists() else None

st.set_page_config(
    page_title="Acucomm Stock Management",
    page_icon=favicon_image,
    layout="wide"
)

# ====================================================
# === CUSTOM CSS FOR THEME ===
# ====================================================
st.markdown(f"""
    <style>
        .stApp {{
            background-color: {WHITE};
            color: {PRIMARY_BLUE};
            font-family: 'Helvetica Neue', sans-serif;
        }}
        h1, h2, h3, h4 {{
            color: {PRIMARY_BLUE};
        }}
        .stButton>button {{
            background-color: {SECONDARY_BLUE};
            color: {WHITE};
            border: none;
            border-radius: 8px;
            padding: 0.6rem 1rem;
            font-size: 1rem;
            transition: 0.3s;
        }}
        .stButton>button:hover {{
            background-color: {PRIMARY_BLUE};
            color: {WHITE};
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {PRIMARY_BLUE}, {SECONDARY_BLUE});
            color: {WHITE};
        }}
        .footer {{
            position: fixed;
            bottom: 0;
            width: 100%;
            background-color: {PRIMARY_BLUE};
            color: {WHITE};
            text-align: center;
            padding: 10px;
            font-size: 0.9rem;
        }}
    </style>
""", unsafe_allow_html=True)

# ====================================================
# === DIRECTORIES ===
# ====================================================
DATA_DIR = ROOT / "data"
PHOTO_DIR = ROOT / "photos"
ISSUED_PHOTOS_DIR = PHOTO_DIR / "issued"
REPORT_DIR = ROOT / "reports"
for d in [DATA_DIR, PHOTO_DIR, ISSUED_PHOTOS_DIR, REPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "stock_requests.csv"

# ====================================================
# === EMAIL SETUP (MS Exchange) ===
# ====================================================
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587

SENDER_EMAIL = os.getenv("EXCHANGE_EMAIL")
SENDER_PASSWORD = os.getenv("EXCHANGE_PASSWORD")

def send_email(subject, html_body, to_emails):
    """Send email via Microsoft Exchange"""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        st.warning("⚠️ Email credentials not found.")
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = ", ".join(to_emails if isinstance(to_emails, list) else [to_emails])
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_emails, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Email send failed: {e}")
        return False

# ====================================================
# === LOGO & HEADER ===
# ====================================================
logo_path = ROOT / "DBN_Metro.png"
if logo_path.exists():
    encoded_logo = base64.b64encode(open(logo_path, "rb").read()).decode()
    st.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{encoded_logo}' width='90'/></div>", unsafe_allow_html=True)
st.markdown(f"<h1 style='text-align:center;color:{PRIMARY_BLUE};'>Ethekwini Smart Meter Stock Management - WS7761</h1>", unsafe_allow_html=True)
st.markdown("---")

# ====================================================
# === AUTHENTICATION ===
# ====================================================
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

USERS = {
    "Reece": {"password": hash_password("Reece123!"), "role": "manager"},
    "Deezlo": {"password": hash_password("Deezlo123"), "role": "contractor"},
    "installer1": {"password": hash_password("installer123"), "role": "installer"},
    "ethekwini": {"password": hash_password("ethekwini123"), "role": "city"},
    "manufacturer1": {"password": hash_password("manufacturer123"), "role": "manufacturer"}
}

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "username": None, "role": None}

def login_ui():
    st.subheader("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in USERS and USERS[username]["password"] == hash_password(password):
            st.session_state.auth = {"logged_in": True, "username": username, "role": USERS[username]["role"]}
            st.success(f"Welcome, {username}!")
            st.rerun()
        else:
            st.error("Invalid credentials")

def logout():
    st.session_state.auth = {"logged_in": False, "username": None, "role": None}
    st.rerun()

# ====================================================
# === CITY INTERFACE ===
# ====================================================
def city_ui():
    st.header("🏙️ eThekwini Municipality - Verify Requests & Deliveries")
    df = pd.read_csv(DATA_FILE) if DATA_FILE.exists() else pd.DataFrame()
    if df.empty:
        st.info("No records found.")
        return

    st.dataframe(df.fillna(""), use_container_width=True)
    sel_id = st.selectbox("Select Request ID", [""] + df["Request_ID"].astype(str).tolist())

    if sel_id:
        record = df[df["Request_ID"] == sel_id].iloc[0].to_dict()
        st.write("Record details:")
        record_df = pd.DataFrame(list(record.items()), columns=["Field", "Value"])
        st.table(record_df)

        if st.button("Mark as Verified"):
            df.loc[df["Request_ID"] == sel_id, "Status"] = "Verified"
            df.to_csv(DATA_FILE, index=False)
            st.success(f"Request {sel_id} verified.")
            send_email("Request Verified", f"<p>Request {sel_id} has been verified by eThekwini Municipality.</p>", ["manager@example.com"])

# ====================================================
# === INSTALLER INTERFACE ===
# ====================================================
def installer_ui():
    st.header("🔧 Installer - Record Installations")
    df = pd.read_csv(DATA_FILE) if DATA_FILE.exists() else pd.DataFrame()

    request_id = st.text_input("Request ID")
    meter_serial = st.text_input("Meter Serial Number")
    completion_date = st.date_input("Completion Date")

    if st.button("Submit Installation"):
        new_data = pd.DataFrame([{
            "Request_ID": request_id,
            "Meter_Serial": meter_serial,
            "Completion_Date": completion_date,
            "Status": "Completed"
        }])
        df = pd.concat([df, new_data], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.success("Installation recorded successfully.")
        send_email("Installation Completed", f"<p>Installation {request_id} completed.</p>", ["manager@example.com"])

# ====================================================
# === CONTRACTOR INTERFACE ===
# ====================================================
def contractor_ui():
    st.header("👷 Contractor - Submit Requests")
    df = pd.read_csv(DATA_FILE) if DATA_FILE.exists() else pd.DataFrame()

    request_id = f"REQ{len(df)+1:04d}"
    project_name = st.text_input("Project Name")
    quantity = st.number_input("Quantity", 1)
    description = st.text_area("Description")

    if st.button("Submit Request"):
        new_request = pd.DataFrame([{
            "Request_ID": request_id,
            "Project_Name": project_name,
            "Quantity": quantity,
            "Description": description,
            "Status": "Pending",
            "Submitted_On": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        df = pd.concat([df, new_request], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.success(f"Request {request_id} submitted.")
        send_email("New Stock Request", f"<p>New request {request_id} submitted by Contractor.</p>", ["manager@example.com"])

# ====================================================
# === MANUFACTURER INTERFACE ===
# ====================================================
def manufacturer_ui():
    st.header("🏭 Manufacturer - Confirm Dispatch")
    df = pd.read_csv(DATA_FILE) if DATA_FILE.exists() else pd.DataFrame()
    if df.empty:
        st.info("No pending requests.")
        return

    pending = df[df["Status"] == "Verified"]
    if pending.empty:
        st.info("No verified requests.")
        return

    sel_id = st.selectbox("Select Request to Dispatch", pending["Request_ID"].tolist())
    if st.button("Mark as Dispatched"):
        df.loc[df["Request_ID"] == sel_id, "Status"] = "Dispatched"
        df.to_csv(DATA_FILE, index=False)
        st.success(f"Request {sel_id} marked as dispatched.")
        send_email("Dispatch Notice", f"<p>Request {sel_id} dispatched by manufacturer.</p>", ["manager@example.com"])

# ====================================================
# === MANAGER INTERFACE ===
# ====================================================
def manager_ui():
    st.header("📊 Manager Dashboard")
    df = pd.read_csv(DATA_FILE) if DATA_FILE.exists() else pd.DataFrame()
    if df.empty:
        st.info("No data available.")
        return

    st.dataframe(df.fillna(""), use_container_width=True)
    status_counts = df["Status"].value_counts()
    st.bar_chart(status_counts)

# ====================================================
# === MAIN APP LOGIC ===
# ====================================================
if not st.session_state.auth["logged_in"]:
    login_ui()
else:
    st.sidebar.success(f"Logged in as {st.session_state.auth['username']}")
    st.sidebar.button("Logout", on_click=logout)

    role = st.session_state.auth["role"]
    if role == "city":
        city_ui()
    elif role == "installer":
        installer_ui()
    elif role == "contractor":
        contractor_ui()
    elif role == "manufacturer":
        manufacturer_ui()
    elif role == "manager":
        manager_ui()

# ====================================================
# === FOOTER ===
# ====================================================
st.markdown(f"<div class='footer'>© {datetime.now().year} Acucomm | Smart Meter Stock Management System</div>", unsafe_allow_html=True)
