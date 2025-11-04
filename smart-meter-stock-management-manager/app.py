# app_fixed_report_details_no_backup.py
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
if favicon_path.exists():
    favicon_image = Image.open(favicon_path)
else:
    favicon_image = None

st.set_page_config(
    page_title="Acucomm Stock Management",
    page_icon=favicon_image,
    layout="centered"
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
        [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {{
            color: {WHITE};
        }}
        [data-testid="stSidebar"] a {{
            color: {WHITE} !important;
        }}
        .stDataFrame tbody td {{
            color: {PRIMARY_BLUE};
        }}
        .stDataFrame thead th {{
            background-color: {SECONDARY_BLUE};
            color: {WHITE};
        }}
    </style>
""", unsafe_allow_html=True)

# ====================================================
# === DIRECTORY SETUP ===
# ====================================================
DATA_DIR = ROOT / "data"
PHOTO_DIR = ROOT / "photos"
ISSUED_PHOTOS_DIR = PHOTO_DIR / "issued"
REPORT_DIR = ROOT / "reports"
DUMP_DIR = DATA_DIR / "dumps"

for d in [DATA_DIR, PHOTO_DIR, ISSUED_PHOTOS_DIR, REPORT_DIR, DUMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DATA_FILE = DATA_DIR / "stock_requests.csv"

# ====================================================
# === EMAIL CONFIG ===
# ====================================================
def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key)

SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587

SENDER_EMAIL = get_secret("EXCHANGE_EMAIL")
SENDER_PASSWORD = get_secret("EXCHANGE_PASSWORD")
CONTRACTOR_EMAIL = get_secret("CONTRACTOR_EMAIL")
ETHEKWINI_EMAIL = get_secret("ETHEKWINI_EMAIL")
INSTALLER_EMAIL = get_secret("INSTALLER_EMAIL")
MANAGER_EMAIL = get_secret("MANAGER_EMAIL")
MANUFACTURER_EMAIL = get_secret("MANUFACTURER_EMAIL")

def send_email(subject, html_body, to_emails):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("Email credentials not configured.")
        return False
    recipients = [to_emails] if isinstance(to_emails, str) else to_emails
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False

# ====================================================
# === LOGO & HEADER ===
# ====================================================
logo_path = ROOT / "DBN_Metro.png"
if logo_path.exists():
    try:
        with open(logo_path, "rb") as img_file:
            encoded_logo = base64.b64encode(img_file.read()).decode()
        st.markdown(
            f"<div style='text-align:center;'><img src='data:image/png;base64,{encoded_logo}' width='70'/></div>",
            unsafe_allow_html=True,
        )
    except Exception:
        st.warning("Logo found but couldn't be displayed.")
else:
    st.warning("⚠️ Logo not found: DBN_Metro.png")

st.markdown(f"<h1 style='text-align:center;color:{PRIMARY_BLUE};'>Ethekwini Smart Meter Stock Management-WS7761</h1>", unsafe_allow_html=True)
st.markdown("---")

# ====================================================
# === AUTHENTICATION ===
# ====================================================
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

raw_users = {
    "Deezlo": {"name": "Deezlo", "password": "Deezlo123", "role": "contractor", "email": CONTRACTOR_EMAIL},
    "Nimba": {"name": "Nimba", "password": "Nimba123", "role": "contractor", "email": CONTRACTOR_EMAIL},
    "ethekwini": {"name": "ethekwini", "password": "ethekwini123", "role": "city", "email": ETHEKWINI_EMAIL},
    "installer1": {"name": "installer1", "password": "installer123", "role": "installer", "email": INSTALLER_EMAIL},
    "Reece": {"name": "Reece", "password": "Reece123!", "role": "manager", "email": MANAGER_EMAIL},
    "manufacturer1": {"name": "manufacturer1", "password": "manufacturer123", "role": "manufacturer", "email": MANUFACTURER_EMAIL},
}

CREDENTIALS = {u: {"name": v["name"], "password_hash": hash_password(v["password"]), "role": v["role"], "email": v["email"]} for u, v in raw_users.items()}

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None}

def safe_rerun():
    try:
        st.rerun()
    except Exception:
        pass

# ====================================================
# === DATA HANDLING (Simplified, no backups) ===
# ====================================================
def load_data():
    if DATA_FILE.exists():
        try:
            return pd.read_csv(DATA_FILE, dtype=str)
        except Exception:
            pass
    cols = [
        "Date_Requested", "Request_ID", "Contractor_Name", "Installer_Name",
        "Meter_Type", "Requested_Qty", "Approved_Qty", "Photo_Path",
        "Status", "Contractor_Notes", "City_Notes", "Decline_Reason",
        "Date_Approved", "Date_Received",
        "Manufacturer_Name", "Batch_Number", "Dispatch_Qty", "Dispatch_Date", "Dispatch_Note", "Dispatch_Docs"
    ]
    return pd.DataFrame(columns=cols)

def save_data(df):
    try:
        df.to_csv(DATA_FILE, index=False)
    except Exception as e:
        st.warning(f"Could not save data: {e}")

def generate_request_id(prefix="REQ"):
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

# ====================================================
# === LOGIN UI ===
# ====================================================
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
                "name": CREDENTIALS[username]["name"]
            })
            safe_rerun()
        else:
            st.error("❌ Invalid credentials")

def logout():
    st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None}
    safe_rerun()

# ====================================================
# === CONTRACTOR UI ===
# ====================================================
def contractor_ui():
    st.header("Contractor - Submit Stock Request")
    contractor_name = st.session_state.auth["name"]
    installer_name = st.text_input("Installer Name")
    meter_qty = st.number_input("DN15 Meter Quantity", min_value=0, step=1)
    keypad_qty = st.number_input("CIU Keypad Quantity", min_value=0, step=1)
    notes = st.text_area("Notes")
    if st.button("Submit Request"):
        if not installer_name:
            st.warning("Please enter installer name")
        elif meter_qty == 0 and keypad_qty == 0:
            st.warning("Please request at least one item.")
        else:
            df = load_data()
            base_rid = generate_request_id(prefix="REQ")
            entries = []
            for item_type, qty in [("DN15 Meter", meter_qty), ("CIU Keypad", keypad_qty)]:
                if qty > 0:
                    rid = f"{base_rid}-{item_type.replace(' ', '_')}"
                    entries.append({
                        "Date_Requested": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Request_ID": rid,
                        "Contractor_Name": contractor_name,
                        "Installer_Name": installer_name,
                        "Meter_Type": item_type,
                        "Requested_Qty": str(qty),
                        "Approved_Qty": "",
                        "Photo_Path": "",
                        "Status": "Pending Verification",
                        "Contractor_Notes": notes,
                        "City_Notes": "",
                        "Decline_Reason": "",
                        "Date_Approved": "",
                        "Date_Received": "",
                        "Manufacturer_Name": "",
                        "Batch_Number": "",
                        "Dispatch_Qty": "",
                        "Dispatch_Date": "",
                        "Dispatch_Note": "",
                        "Dispatch_Docs": ""
                    })
            df = pd.concat([df, pd.DataFrame(entries)], ignore_index=True)
            save_data(df)
            st.success(f"✅ Request(s) submitted under ID {base_rid}")

# ====================================================
# === CITY / MANUFACTURER UIs (Same as before)
# ====================================================
# (retain your previous logic unchanged)
