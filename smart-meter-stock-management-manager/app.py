# app_fixed_report_details.py
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
import dropbox

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
    layout="centered"
)

# ====================================================
# === CUSTOM CSS FOR THEME ===
# ====================================================
st.markdown(f"""
<style>
.stApp {{ background-color: {WHITE}; color: {PRIMARY_BLUE}; font-family: 'Helvetica Neue', sans-serif; }}
h1, h2, h3, h4 {{ color: {PRIMARY_BLUE}; }}
.stButton>button {{
    background-color: {SECONDARY_BLUE};
    color: {WHITE};
    border: none;
    border-radius: 8px;
    padding: 0.6rem 1rem;
    font-size: 1rem;
    transition: 0.3s;
}}
.stButton>button:hover {{ background-color: {PRIMARY_BLUE}; color: {WHITE}; }}
[data-testid="stSidebar"] {{ background: linear-gradient(180deg, {PRIMARY_BLUE}, {SECONDARY_BLUE}); color: {WHITE}; }}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {{ color: {WHITE}; }}
[data-testid="stSidebar"] a {{ color: {WHITE} !important; }}
.stDataFrame tbody td {{ color: {PRIMARY_BLUE}; }}
.stDataFrame thead th {{ background-color: {SECONDARY_BLUE}; color: {WHITE}; }}
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
# === DROPBOX CONFIG ===
# ====================================================
DROPBOX_ACCESS_TOKEN = st.secrets.get("DROPBOX_ACCESS_TOKEN") or os.getenv("DROPBOX_ACCESS_TOKEN")
DROPBOX_BACKUP_DIR = "/SmartMeter_Backups"

dbx = None
if DROPBOX_ACCESS_TOKEN:
    try:
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
    except Exception as e:
        st.warning(f"Dropbox init failed: {e}")

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

def upload_to_dropbox(zip_path: Path):
    if not dbx:
        return False
    try:
        with open(zip_path, "rb") as f:
            dest_path = f"{DROPBOX_BACKUP_DIR}/{zip_path.name}"
            dbx.files_upload(f.read(), dest_path, mode=dropbox.files.WriteMode.overwrite)
        st.info(f"Backup uploaded to Dropbox: {dest_path}")
        return True
    except Exception as e:
        st.warning(f"Dropbox upload failed: {e}")
        return False

def backup_data():
    zip_path = create_local_zip()
    if not zip_path:
        return False
    ok_dropbox = upload_to_dropbox(zip_path)
    return ok_dropbox

def find_latest_dropbox_backup():
    if not dbx:
        return None
    try:
        res = dbx.files_list_folder(DROPBOX_BACKUP_DIR)
        zips = [entry for entry in res.entries if isinstance(entry, dropbox.files.FileMetadata) and entry.name.endswith(".zip")]
        if not zips:
            return None
        zips.sort(key=lambda x: x.client_modified, reverse=True)
        latest_file = zips[0]
        local_path = ROOT / latest_file.name
        with open(local_path, "wb") as f:
            metadata, res = dbx.files_download(path=latest_file.path_lower)
            f.write(res.content)
        return local_path
    except Exception as e:
        st.warning(f"Failed to find/download Dropbox backup: {e}")
        return None

def restore_from_zip(zip_path: Path):
    try:
        if DATA_DIR.exists():
            for item in DATA_DIR.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        else:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
        shutil.unpack_archive(str(zip_path), extract_dir=str(DATA_DIR))
        st.success(f"Restored data from backup: {zip_path.name}")
        return True
    except Exception as e:
        st.warning(f"Restore failed: {e}")
        return False

def auto_restore_if_needed():
    if DATA_FILE.exists():
        try:
            df = pd.read_csv(DATA_FILE)
            if not df.empty:
                return
        except Exception:
            pass
    if BACKUP_FILE.exists():
        try:
            shutil.unpack_archive(str(BACKUP_FILE), extract_dir=str(DATA_DIR))
            st.info("Restored data from local backup zip.")
            return
        except Exception:
            pass
    latest = find_latest_dropbox_backup()
    if latest:
        restore_from_zip(latest)

try:
    auto_restore_if_needed()
except Exception:
    pass

# ====================================================
# === EMAIL CONFIG ===
# ====================================================
SMTP_SERVER = "mail.onegrid.co.za"
SMTP_PORT = 465
SENDER_EMAIL = st.secrets.get("EXCHANGE_EMAIL") or "admin@acucommholdings.co.za"
SENDER_PASSWORD = st.secrets.get("EXCHANGE_PASSWORD")
CONTRACTOR_EMAIL = st.secrets.get("CONTRACTOR_EMAIL")
ETHEKWINI_EMAIL = st.secrets.get("ETHEKWINI_EMAIL")
INSTALLER_EMAIL = st.secrets.get("INSTALLER_EMAIL")
MANAGER_EMAIL = st.secrets.get("MANAGER_EMAIL")
MANUFACTURER_EMAIL = st.secrets.get("MANUFACTURER_EMAIL")
LAST_EMAIL_ERROR = None

def send_email(subject, html_body, to_emails):
    global LAST_EMAIL_ERROR
    LAST_EMAIL_ERROR = None
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        LAST_EMAIL_ERROR = "Sender credentials missing."
        return False
    recipients = [to_emails] if isinstance(to_emails, str) else list(to_emails)
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        return True
    except Exception as e_ssl:
        LAST_EMAIL_ERROR = f"SSL failed: {e_ssl}"
    try:
        with smtplib.SMTP(SMTP_SERVER, 587, timeout=30) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        return True
    except Exception as e_tls:
        LAST_EMAIL_ERROR = (LAST_EMAIL_ERROR or "") + f" | TLS failed: {e_tls}"
        return False

# ====================================================
# === ROLE-BASED UI PLACEHOLDERS ===
# ====================================================
def login_ui():
    st.sidebar.title("Login")
    role = st.sidebar.selectbox("Select Role", ["Contractor", "Installer", "Manufacturer", "City", "Manager"])
    return role

def contractor_ui():
    st.header("Contractor Dashboard")
    st.write("Contractor-specific functionality goes here.")
    if st.button("Backup Data to Dropbox"):
        backup_data()

def installer_ui():
    st.header("Installer Dashboard")
    st.write("Installer-specific functionality goes here.")

def manufacturer_ui():
    st.header("Manufacturer Dashboard")
    st.write("Manufacturer-specific functionality goes here.")

def city_ui():
    st.header("City Dashboard")
    st.write("City-specific functionality goes here.")

def manager_ui():
    st.header("Manager Dashboard")
    st.write("Manager-specific functionality goes here.")

# ====================================================
# === APP ROUTING ===
# ====================================================
role = login_ui()
if role == "Contractor":
    contractor_ui()
elif role == "Installer":
    installer_ui()
elif role == "Manufacturer":
    manufacturer_ui()
elif role == "City":
    city_ui()
elif role == "Manager":
    manager_ui()

# ====================================================
# === FOOTER ===
# ====================================================
st.markdown("""
<div class="footer">
    &copy; 2025 Acucomm Holdings. All rights reserved.
</div>
""", unsafe_allow_html=True)
