# app.py
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
import glob
import requests
import json
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
DUMP_DIR = DATA_DIR / "dumps"
for d in [DATA_DIR, PHOTO_DIR, ISSUED_PHOTOS_DIR, REPORT_DIR, DUMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "stock_requests.csv"

# ====================================================
# === BASIC UTILITIES ===
# ====================================================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def safe_rerun():
    try:
        st.rerun()
    except Exception:
        pass

# ====================================================
# === DATA LOAD/SAVE ===
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
        "Manufacturer_Name", "Batch_Number", "Dispatch_Qty", "Dispatch_Date",
        "Dispatch_Note", "Dispatch_Docs"
    ]
    return pd.DataFrame(columns=cols)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)
    dump_filename = f"stock_requests_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
    df.to_csv(DUMP_DIR / dump_filename, index=False)

def generate_request_id(prefix="REQ"):
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

# ====================================================
# === LOGO ===
# ====================================================
logo_path = ROOT / "DBN_Metro.png"
if logo_path.exists():
    with open(logo_path, "rb") as img_file:
        encoded_logo = base64.b64encode(img_file.read()).decode()
    st.markdown(
        f"<div style='text-align:center;'><img src='data:image/png;base64,{encoded_logo}' width='70'/></div>",
        unsafe_allow_html=True,
    )
st.markdown(f"<h1 style='text-align:center;color:{PRIMARY_BLUE};'>Ethekwini Smart Meter Stock Management - WS7761</h1>", unsafe_allow_html=True)
st.markdown("---")

# ====================================================
# === AUTHENTICATION ===
# ====================================================
CREDENTIALS = {
    "ethekwini": {"password": hash_password("ethekwini123"), "role": "city"},
    "Reece": {"password": hash_password("Reece123!"), "role": "manager"},
    "installer1": {"password": hash_password("installer123"), "role": "installer"},
    "Deezlo": {"password": hash_password("Deezlo123"), "role": "contractor"},
    "manufacturer1": {"password": hash_password("manufacturer123"), "role": "manufacturer"},
}

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "username": None, "role": None}

def login_ui():
    st.title("🔐 Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u in CREDENTIALS and hash_password(p) == CREDENTIALS[u]["password"]:
            st.session_state.auth.update({"logged_in": True, "username": u, "role": CREDENTIALS[u]["role"]})
            safe_rerun()
        else:
            st.error("Invalid credentials")

def logout():
    st.session_state.auth = {"logged_in": False, "username": None, "role": None}
    safe_rerun()

# ====================================================
# === CITY UI FIXED DISPLAY ===
# ====================================================
def city_ui():
    st.header("eThekwini Municipality - Verify Requests & Manufacturer Deliveries")
    df = load_data()
    if df.empty:
        st.info("No records found.")
        return

    view_choice = st.selectbox("Filter by Status", ["All"] + sorted(df["Status"].dropna().unique().tolist()))
    filtered = df if view_choice == "All" else df[df["Status"] == view_choice]

    st.dataframe(filtered.fillna(""), use_container_width=True)
    st.markdown("---")

    sel_id = st.selectbox("Select Request/Dispatch ID", [""] + filtered["Request_ID"].tolist())
    if sel_id:
        record = df[df["Request_ID"] == sel_id].iloc[0].to_dict()

        # ✅ Fixed: show in readable table format
        st.markdown("### 📋 Record Details")
        record_df = pd.DataFrame(record.items(), columns=["Field", "Value"])
        st.dataframe(record_df, hide_index=True, use_container_width=True)

        # rest unchanged ...
        if record.get("Status") == "Pending Verification":
            st.subheader("Approve Contractor Request")
            qty = st.number_input("Approved Qty", min_value=0, value=int(record.get("Requested_Qty") or 0))
            photo = st.file_uploader("Upload proof photo", type=["jpg", "png"])
            notes = st.text_area("Notes")
            decline_reason = st.text_input("Decline reason")
            if st.button("Approve"):
                df.loc[df["Request_ID"] == sel_id, "Approved_Qty"] = str(qty)
                df.loc[df["Request_ID"] == sel_id, "Status"] = "Approved / Issued"
                df.loc[df["Request_ID"] == sel_id, "City_Notes"] = notes
                df.loc[df["Request_ID"] == sel_id, "Date_Approved"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_data(df)
                st.success("✅ Approved and issued.")
                safe_rerun()
            if st.button("Decline"):
                df.loc[df["Request_ID"] == sel_id, "Status"] = "Declined"
                df.loc[df["Request_ID"] == sel_id, "Decline_Reason"] = decline_reason
                save_data(df)
                st.error("❌ Declined.")
                safe_rerun()

# ====================================================
# === OTHER SIMPLE UIs ===
# ====================================================
def contractor_ui(): st.info("Contractor panel here (unchanged).")
def manufacturer_ui(): st.info("Manufacturer panel here (unchanged).")
def installer_ui(): st.info("Installer panel here (unchanged).")
def manager_ui(): st.info("Manager panel here (unchanged).")

# ====================================================
# === ROUTING ===
# ====================================================
if not st.session_state.auth["logged_in"]:
    login_ui()
else:
    st.sidebar.markdown(f"**User:** {st.session_state.auth['username']}")
    st.sidebar.markdown(f"**Role:** {st.session_state.auth['role']}")
    if st.sidebar.button("Logout"):
        logout()
    role = st.session_state.auth["role"]
    if role == "city":
        city_ui()
    elif role == "contractor":
        contractor_ui()
    elif role == "manufacturer":
        manufacturer_ui()
    elif role == "installer":
        installer_ui()
    elif role == "manager":
        manager_ui()

# ====================================================
# === FOOTER ===
# ====================================================
st.markdown(f"""
    <div class="footer">
        © {datetime.now().year} eThekwini Municipality-WS7761 | Smart Meter Stock Management System
    </div>
""", unsafe_allow_html=True)
