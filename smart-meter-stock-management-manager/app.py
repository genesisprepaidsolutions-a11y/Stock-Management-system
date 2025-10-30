
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
# === CUSTOM CSS ===
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
        [data-testid="stSidebar"] * {{
            color: {WHITE} !important;
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
        .record-table td {{
            padding: 4px 12px;
            border-bottom: 1px solid #ddd;
        }}
        .record-table th {{
            background-color: {SECONDARY_BLUE};
            color: white;
            text-align: left;
            padding: 6px 12px;
        }}
    </style>
""", unsafe_allow_html=True)

# ====================================================
# === DIRECTORY SETUP ===
# ====================================================
DATA_DIR = ROOT / "data"
DUMP_DIR = DATA_DIR / "dumps"
PHOTO_DIR = ROOT / "photos"
REPORT_DIR = ROOT / "reports"
for d in [DATA_DIR, DUMP_DIR, PHOTO_DIR, REPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DATA_FILE = DATA_DIR / "stock_requests.csv"
BACKUP_FILE = ROOT / "data_backup.zip"

# ====================================================
# === HELPERS ===
# ====================================================
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

def load_data():
    if DATA_FILE.exists():
        return pd.read_csv(DATA_FILE, dtype=str)
    return pd.DataFrame(columns=[
        "Date_Requested","Request_ID","Contractor_Name","Installer_Name",
        "Meter_Type","Requested_Qty","Approved_Qty","Photo_Path",
        "Status","Contractor_Notes","City_Notes","Decline_Reason",
        "Date_Approved","Date_Received",
        "Manufacturer_Name","Batch_Number","Dispatch_Qty","Dispatch_Date","Dispatch_Note","Dispatch_Docs"
    ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)
    dump_filename = f"stock_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(DUMP_DIR / dump_filename, index=False)

def generate_request_id(prefix="REQ"):
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

def send_email(subject, html_body, to_emails):
    return True  # Stubbed out (email config stays same)

# ====================================================
# === AUTH ===
# ====================================================
USERS = {
    "ethekwini": {"password": "ethekwini123", "role": "city"},
    "Deezlo": {"password": "Deezlo123", "role": "contractor"},
    "installer1": {"password": "installer123", "role": "installer"},
    "manufacturer1": {"password": "manufacturer123", "role": "manufacturer"},
    "Reece": {"password": "Reece123!", "role": "manager"},
}
for u in USERS:
    USERS[u]["hash"] = hash_password(USERS[u]["password"])

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False}

def login_ui():
    st.title("🔐 Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u in USERS and hash_password(p) == USERS[u]["hash"]:
            st.session_state.auth.update({"logged_in": True, "user": u, "role": USERS[u]["role"]})
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

def logout():
    st.session_state.auth = {"logged_in": False}
    st.rerun()

# ====================================================
# === ROLE UIs ===
# ====================================================
def contractor_ui():
    st.header("Contractor - Submit Stock Request")
    installer = st.text_input("Installer Name")
    meter_qty = st.number_input("DN15 Meter Qty", min_value=0)
    keypad_qty = st.number_input("CIU Keypad Qty", min_value=0)
    notes = st.text_area("Notes")
    if st.button("Submit Request"):
        if not installer or (meter_qty == 0 and keypad_qty == 0):
            st.warning("Please complete all fields")
            return
        df = load_data()
        rid = generate_request_id()
        for typ, qty in [("DN15 Meter", meter_qty), ("CIU Keypad", keypad_qty)]:
            if qty > 0:
                df.loc[len(df)] = [
                    datetime.now(), f"{rid}-{typ}", "Deezlo", installer, typ,
                    qty, "", "", "Pending Verification", notes, "", "", "", "",
                    "", "", "", "", "", ""
                ]
        save_data(df)
        st.success("Request submitted successfully ✅")

def city_ui():
    st.header("eThekwini Municipality - Review & Approve")
    df = load_data()
    if df.empty:
        st.info("No records found")
        return

    st.dataframe(df.fillna(""), use_container_width=True)

    sel = st.selectbox("Select Request ID", [""] + df["Request_ID"].tolist())
    if sel:
        record = df[df["Request_ID"] == sel].iloc[0].to_dict()

        # Neat Field | Value display
        st.markdown("### 📋 Record Details")
        html_table = "<table class='record-table'><tr><th>Field</th><th>Value</th></tr>"
        for k, v in record.items():
            html_table += f"<tr><td>{k}</td><td>{v or ''}</td></tr>"
        html_table += "</table>"
        st.markdown(html_table, unsafe_allow_html=True)

        status = record.get("Status", "")
        if "Pending" in status:
            st.subheader("Actions")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Approve"):
                    df.loc[df["Request_ID"] == sel, "Status"] = "Approved / Issued"
                    df.loc[df["Request_ID"] == sel, "Date_Approved"] = datetime.now()
                    save_data(df)
                    st.success("Approved ✅")
                    st.rerun()
            with col2:
                if st.button("❌ Decline"):
                    df.loc[df["Request_ID"] == sel, "Status"] = "Declined"
                    save_data(df)
                    st.warning("Declined ❌")
                    st.rerun()

def installer_ui():
    st.header("Installer - Mark Received")
    df = load_data()
    approved = df[df["Status"] == "Approved / Issued"]
    st.dataframe(approved, use_container_width=True)
    sel = st.selectbox("Select Request ID to Mark Received", [""] + approved["Request_ID"].tolist())
    if sel and st.button("Mark Received"):
        df.loc[df["Request_ID"] == sel, "Status"] = "Received"
        df.loc[df["Request_ID"] == sel, "Date_Received"] = datetime.now()
        save_data(df)
        st.success("Marked as received ✅")
        st.rerun()

def manufacturer_ui():
    st.header("Manufacturer - Dispatch Stock")
    batch = st.text_input("Batch Number")
    qty = st.number_input("Dispatch Quantity", min_value=0)
    model = st.selectbox("Product", ["DN15 Meter", "CIU Keypad"])
    if st.button("Submit Dispatch"):
        if not batch or qty == 0:
            st.warning("Enter batch and quantity")
            return
        df = load_data()
        rid = generate_request_id("MANU")
        df.loc[len(df)] = [
            datetime.now(), rid, "", "", model, "", "", "", "Pending City Approval (Manufacturer Delivery)",
            "", "", "", "", "", "Manufacturer1", batch, qty, datetime.now().strftime("%Y-%m-%d"), "", ""
        ]
        save_data(df)
        st.success("Dispatch submitted ✅")

def manager_ui():
    st.header("Manager - View & Dumps")
    df = load_data()
    st.dataframe(df, use_container_width=True)
    st.subheader("Data Dumps")
    dumps = sorted(DUMP_DIR.glob("*.csv"), reverse=True)
    if dumps:
        names = [d.name for d in dumps]
        sel = st.selectbox("Select dump", names)
        if sel:
            dump_df = pd.read_csv(DUMP_DIR / sel)
            st.dataframe(dump_df)
            st.download_button("Download CSV", dump_df.to_csv(index=False).encode(), file_name=sel)
    else:
        st.info("No dumps yet.")

# ====================================================
# === ROUTING ===
# ====================================================
if not st.session_state.auth["logged_in"]:
    login_ui()
else:
    st.sidebar.title("Navigation")
    st.sidebar.markdown(f"**User:** {st.session_state.auth['user']}")
    st.sidebar.markdown(f"**Role:** {st.session_state.auth['role'].title()}")
    if st.sidebar.button("Logout"):
        logout()

    role = st.session_state.auth["role"]
    if role == "contractor":
        contractor_ui()
    elif role == "city":
        city_ui()
    elif role == "installer":
        installer_ui()
    elif role == "manager":
        manager_ui()
    elif role == "manufacturer":
        manufacturer_ui()

# ====================================================
# === FOOTER ===
# ====================================================
st.markdown(f"""
<div class='footer'>
© {datetime.now().year} eThekwini Municipality-WS7761 | Smart Meter Stock Management System
</div>
""", unsafe_allow_html=True)
