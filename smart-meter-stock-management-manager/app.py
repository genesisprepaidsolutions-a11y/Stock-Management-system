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
# === DIRECTORY SETUP ===
# ====================================================
DATA_DIR = ROOT / "data"
PHOTO_DIR = ROOT / "photos"
ISSUED_PHOTOS_DIR = PHOTO_DIR / "issued"
REPORT_DIR = ROOT / "reports"
DUMP_DIR = DATA_DIR / "dumps"
BACKUP_ZIP_PREFIX = ROOT / "data_backup"
BACKUP_FILE = Path(str(BACKUP_ZIP_PREFIX) + ".zip")

for d in [DATA_DIR, PHOTO_DIR, ISSUED_PHOTOS_DIR, REPORT_DIR, DUMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DATA_FILE = DATA_DIR / "stock_requests.csv"

# ====================================================
# === ONE DRIVE CONFIG ===
# ====================================================
ONE_DRIVE_SYNC_ROOT = Path(r"C:\Users\ADMIN\OneDrive")
ONE_DRIVE_BACKUP_DIR = ONE_DRIVE_SYNC_ROOT / "SmartMeter_Backups"
try:
    ONE_DRIVE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key)

ONEDRIVE_ACCESS_TOKEN = get_secret("ONEDRIVE_ACCESS_TOKEN")

# ====================================================
# === BACKUP & RESTORE HELPERS ===
# ====================================================
def create_local_zip():
    try:
        if BACKUP_FILE.exists():
            BACKUP_FILE.unlink()
        archive_path = shutil.make_archive(str(BACKUP_ZIP_PREFIX), 'zip', root_dir=str(DATA_DIR))
        return Path(archive_path)
    except Exception as e:
        st.warning(f"Could not create archive: {e}")
        return None

def copy_zip_to_onedrive(zip_path: Path):
    if not ONE_DRIVE_BACKUP_DIR.exists():
        return False
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = ONE_DRIVE_BACKUP_DIR / f"{zip_path.stem}_{timestamp}{zip_path.suffix}"
        shutil.copy2(zip_path, dest)
        st.info(f"Backup copied to OneDrive folder: {dest}")
        return True
    except Exception as e:
        st.warning(f"Failed to copy backup to OneDrive folder: {e}")
        return False

def upload_zip_to_onedrive_graph(zip_path: Path):
    token = ONEDRIVE_ACCESS_TOKEN
    if not token:
        return False
    try:
        filename = zip_path.name
        remote_path = f"/Apps/AcucommBackups/{filename}"
        upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:{remote_path}:/content"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/zip"}
        with open(zip_path, "rb") as f:
            resp = requests.put(upload_url, headers=headers, data=f)
        if resp.status_code in (200, 201):
            st.info("Backup uploaded to OneDrive via Microsoft Graph.")
            return True
        else:
            st.warning(f"Graph upload failed ({resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        st.warning(f"Exception uploading to Graph: {e}")
        return False

def backup_data():
    zip_path = create_local_zip()
    if not zip_path:
        return False
    ok_local = copy_zip_to_onedrive(zip_path)
    ok_graph = upload_zip_to_onedrive_graph(zip_path)
    return ok_local or ok_graph

# ====================================================
# === EMAIL CONFIG ===
# ====================================================
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
    except Exception:
        return False

# ====================================================
# === LOGO & HEADER ===
# ====================================================
logo_path = ROOT / "DBN_Metro.png"
if logo_path.exists():
    with open(logo_path, "rb") as img_file:
        encoded_logo = base64.b64encode(img_file.read()).decode()
    st.markdown(
        f"<div style='text-align:center;'><img src='data:image/png;base64,{encoded_logo}' width='70'/></div>",
        unsafe_allow_html=True,
    )

st.markdown(f"<h1 style='text-align:center;color:{PRIMARY_BLUE};'>Ethekwini Smart Meter Stock Management-WS7761</h1>", unsafe_allow_html=True)
st.markdown("---")

# ====================================================
# === AUTH & DATA ===
# ====================================================
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()

raw_users = {
    "Deezlo": {"name": "Deezlo", "password": "Deezlo123", "role": "contractor", "email": CONTRACTOR_EMAIL},
    "ethekwini": {"name": "ethekwini", "password": "ethekwini123", "role": "city", "email": ETHEKWINI_EMAIL},
    "installer1": {"name": "installer1", "password": "installer123", "role": "installer", "email": INSTALLER_EMAIL},
    "Reece": {"name": "Reece", "password": "Reece123!", "role": "manager", "email": MANAGER_EMAIL},
    "manufacturer1": {"name": "manufacturer1", "password": "manufacturer123", "role": "manufacturer", "email": MANUFACTURER_EMAIL},
}
CREDENTIALS = {u: {"password_hash": hash_password(v["password"]), "role": v["role"], "name": v["name"], "email": v["email"]} for u, v in raw_users.items()}

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None}

def load_data():
    if DATA_FILE.exists():
        try:
            return pd.read_csv(DATA_FILE, dtype=str)
        except Exception:
            pass
    cols = [
        "Date_Requested","Request_ID","Contractor_Name","Installer_Name","Meter_Type",
        "Requested_Qty","Approved_Qty","Photo_Path","Status","Contractor_Notes","City_Notes",
        "Decline_Reason","Date_Approved","Date_Received",
        "Manufacturer_Name","Batch_Number","Dispatch_Qty","Dispatch_Date","Dispatch_Note","Dispatch_Docs"
    ]
    return pd.DataFrame(columns=cols)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)
    dump_name = f"stock_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(DUMP_DIR / dump_name, index=False)
    try:
        backup_data()
    except Exception:
        pass

def generate_request_id(prefix="REQ"):
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

def login_ui():
    st.title("🔐 Login")
    user = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    if st.button("Login"):
        if user in CREDENTIALS and hash_password(pw) == CREDENTIALS[user]["password_hash"]:
            st.session_state.auth.update({
                "logged_in": True, "username": user,
                "role": CREDENTIALS[user]["role"], "name": CREDENTIALS[user]["name"]
            })
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

def logout():
    st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None}
    st.rerun()

# ====================================================
# === CITY UI (Modified Record Display) ===
# ====================================================
def city_ui():
    st.header("eThekwini Municipality - Verify Requests & Manufacturer Deliveries")
    df = load_data()
    if df.empty:
        st.info("No records found.")
        return

    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        view_choice = st.selectbox("Show", ["All","Pending Verification","Pending City Approval (Manufacturer Delivery)","Approved / Issued","Declined","Received"])
    with col2:
        filter_manu = st.text_input("Filter Manufacturer")
    with col3:
        filter_type = st.selectbox("Product Type", ["All"] + sorted(df["Meter_Type"].dropna().unique().tolist()))

    view_df = df.copy()
    if view_choice != "All":
        view_df = view_df[view_df["Status"] == view_choice]
    if filter_manu:
        view_df = view_df[view_df["Manufacturer_Name"].fillna("").str.contains(filter_manu, case=False)]
    if filter_type != "All":
        view_df = view_df[view_df["Meter_Type"] == filter_type]

    st.dataframe(view_df.fillna(""), use_container_width=True)
    st.markdown("---")

    sel_id = st.selectbox("Select Request/Dispatch ID", [""] + view_df["Request_ID"].tolist())
    if sel_id:
        record = df[df["Request_ID"] == sel_id].iloc[0].to_dict()
        st.markdown("### Record Details")
        record_df = pd.DataFrame(list(record.items()), columns=["Field", "Value"])
        st.table(record_df)

        # (actions below unchanged)
        if record.get("Status", "").startswith("Pending City Approval"):
            st.subheader("Manufacturer Dispatch Actions")
            approved_qty = st.number_input("Approved Quantity", min_value=0, value=int(record.get("Dispatch_Qty") or 0))
            city_notes = st.text_area("City Notes")
            decline_reason = st.text_input("Decline Reason (if declining)")
            photo = st.file_uploader("Upload proof photo", type=["jpg","png"])
            approve_col, decline_col = st.columns(2)
            if approve_col.button("Approve Dispatch"):
                df.loc[df["Request_ID"] == sel_id, "Approved_Qty"] = str(approved_qty)
                if photo:
                    dest = PHOTO_DIR / f"{sel_id}_{photo.name}"
                    with open(dest,"wb") as f: f.write(photo.getbuffer())
                    df.loc[df["Request_ID"] == sel_id, "Photo_Path"] = str(dest)
                df.loc[df["Request_ID"] == sel_id, ["Status","City_Notes","Date_Approved"]] = ["Approved / Issued", city_notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                save_data(df)
                st.success("✅ Approved and issued.")
                st.rerun()
            if decline_col.button("Decline Dispatch"):
                reason = decline_reason or "No reason provided"
                df.loc[df["Request_ID"] == sel_id, ["Status","Decline_Reason","City_Notes"]] = ["Declined", reason, city_notes]
                save_data(df)
                st.error("❌ Declined.")
                st.rerun()

        elif record.get("Status") == "Pending Verification":
            st.subheader("Contractor Request Verification")
            default_qty = int(record.get("Requested_Qty") or 0)
            qty = st.number_input("Approved Qty", min_value=0, value=default_qty)
            notes = st.text_area("Notes")
            decline_reason = st.text_input("Decline Reason")
            photo = st.file_uploader("Upload Proof Photo", type=["jpg","png"])
            if st.button("Approve Request"):
                ppath = ""
                if photo:
                    dest = PHOTO_DIR / f"{sel_id}_{photo.name}"
                    with open(dest,"wb") as f: f.write(photo.getbuffer())
                    ppath = str(dest)
                df.loc[df["Request_ID"] == sel_id, ["Approved_Qty","Photo_Path","Status","City_Notes","Date_Approved"]] = [str(qty), ppath,"Approved / Issued",notes,datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                save_data(df)
                st.success("✅ Approved and issued.")
                st.rerun()
            if st.button("Decline Request"):
                df.loc[df["Request_ID"] == sel_id, ["Status","Decline_Reason"]] = ["Declined", decline_reason]
                save_data(df)
                st.error("❌ Declined.")
                st.rerun()
        else:
            st.info("No actions available for this record.")

# ====================================================
# === ROUTING ===
# ====================================================
if not st.session_state.auth["logged_in"]:
    login_ui()
else:
    st.sidebar.markdown(f"### {st.session_state.auth['name']}")
    st.sidebar.markdown(f"**Role:** {st.session_state.auth['role'].title()}")
    if st.sidebar.button("Logout"):
        logout()
    role = st.session_state.auth["role"]
    if role == "city":
        city_ui()
    else:
        st.info("Other roles unchanged for brevity.")

# ====================================================
# === FOOTER ===
# ====================================================
st.markdown(f"""
    <style>
        .footer {{
            position: fixed;
            left: 0; bottom: 0;
            width: 100%;
            background-color: #003366;
            color: white;
            text-align: center;
            padding: 10px 0;
            font-size: 14px;
            border-top: 1px solid #ddd;
        }}
    </style>
    <div class="footer">
        © {datetime.now().year} eThekwini Municipality-WS7761 | Smart Meter Stock Management System
    </div>
""", unsafe_allow_html=True)
