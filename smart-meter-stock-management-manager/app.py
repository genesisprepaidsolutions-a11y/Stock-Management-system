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
import requests  # optional: retained (unused for Drive)
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
# === DIRECTORY SETUP (PERSISTENT STORAGE) ===
# ====================================================
DATA_DIR = ROOT / "data"
PHOTO_DIR = ROOT / "photos"
ISSUED_PHOTOS_DIR = PHOTO_DIR / "issued"
REPORT_DIR = ROOT / "reports"
DUMP_DIR = DATA_DIR / "dumps"
BACKUP_ZIP_PREFIX = ROOT / "data_backup"  # will create data_backup.zip
BACKUP_FILE = Path(str(BACKUP_ZIP_PREFIX) + ".zip")

for d in [DATA_DIR, PHOTO_DIR, ISSUED_PHOTOS_DIR, REPORT_DIR, DUMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DATA_FILE = DATA_DIR / "stock_requests.csv"

# ====================================================
# === DEFAULT GOOGLE DRIVE FOLDER (INSERTED) ===
# ====================================================
DEFAULT_GDRIVE_FOLDER = "171IgGy90h81ecFBs0-8EyUvkbp6jsKLO"

# ====================================================
# === SECRET HELPERS ===
# ====================================================
def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key)

# ====================================================
# === GOOGLE DRIVE CONFIG (SERVICE ACCOUNT) ===
# ====================================================
SERVICE_ACCOUNT_FILE = ROOT / "service_account.json"
GDRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.file']

# ====================================================
# === BACKUP & RESTORE HELPERS ===
# ====================================================
def create_local_zip():
    try:
        if BACKUP_FILE.exists():
            try:
                BACKUP_FILE.unlink()
            except Exception:
                pass
        archive_path = shutil.make_archive(str(BACKUP_ZIP_PREFIX), 'zip', root_dir=str(DATA_DIR))
        return Path(archive_path)
    except Exception as e:
        st.warning(f"Could not create archive: {e}")
        return None

def upload_zip_to_gdrive_service(zip_path: Path, parent_folder_id: str = None):
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except Exception as imp_err:
        st.warning("Google Drive libraries not installed.")
        st.warning(f"Import error: {imp_err}")
        return False

    try:
        if not SERVICE_ACCOUNT_FILE.exists():
            st.warning("service_account.json not found.")
            return False

        creds = service_account.Credentials.from_service_account_file(str(SERVICE_ACCOUNT_FILE), scopes=GDRIVE_SCOPES)
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {'name': zip_path.name}
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]

        media = MediaFileUpload(str(zip_path), mimetype='application/zip', resumable=True)
        request = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = request.get('id')
        st.info(f"Backup uploaded to Google Drive (File ID: {file_id})")
        return True
    except Exception as e:
        st.warning(f"Google Drive upload failed: {e}")
        return False

def archive_zip_to_dumps(zip_path: Path):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = DUMP_DIR / f"{zip_path.stem}_{timestamp}{zip_path.suffix}"
        shutil.copy2(zip_path, dest)
        return dest
    except Exception as e:
        st.warning(f"Could not copy zip to dumps folder: {e}")
        return None

def backup_data(upload_to_gdrive: bool = True, gdrive_folder_id: str = DEFAULT_GDRIVE_FOLDER):
    zip_path = create_local_zip()
    if not zip_path:
        return False
    archive_zip_to_dumps(zip_path)
    ok_local = zip_path.exists()
    ok_gdrive = False
    if upload_to_gdrive:
        ok_gdrive = upload_zip_to_gdrive_service(zip_path, parent_folder_id=gdrive_folder_id)
    if ok_local and ok_gdrive:
        st.success("Backup created locally and uploaded to Google Drive.")
    elif ok_local:
        st.warning("Backup created locally; Google Drive upload failed or not configured.")
    elif ok_gdrive:
        st.info("Backup uploaded to Google Drive (local archive not found).")
    else:
        st.error("Backup failed (no local archive and no Google Drive upload).")
    return ok_local or ok_gdrive

def find_latest_local_backup():
    try:
        dumps_zips = sorted(DUMP_DIR.glob("data_backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        if dumps_zips:
            return dumps_zips[0]
        dumps_any = sorted(DUMP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        if dumps_any:
            return dumps_any[0]
        if BACKUP_FILE.exists():
            return BACKUP_FILE
    except Exception:
        pass
    return None

def restore_from_zip(zip_path: Path):
    try:
        if DATA_DIR.exists():
            for item in DATA_DIR.iterdir():
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                except Exception:
                    pass
        else:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
        shutil.unpack_archive(str(zip_path), extract_dir=str(DATA_DIR))
        st.success(f"Restored data from backup: {zip_path.name}")
        return True
    except Exception as e:
        st.warning(f"Restore failed from {zip_path}: {e}")
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
    latest = find_latest_local_backup()
    if latest:
        restore_from_zip(latest)
    st.info("No backup found to restore from local dumps. Data folder initialized empty if first run.")

try:
    auto_restore_if_needed()
except Exception:
    pass

# ====================================================
# === EMAIL CONFIG ===
# ====================================================
SMTP_SERVER = "mail.onegrid.co.za"
SMTP_PORT = 465
SENDER_EMAIL = get_secret("EXCHANGE_EMAIL") or "admin@acucommholdings.co.za"
SENDER_PASSWORD = get_secret("EXCHANGE_PASSWORD")
CONTRACTOR_EMAIL = get_secret("CONTRACTOR_EMAIL")
ETHEKWINI_EMAIL = get_secret("ETHEKWINI_EMAIL")
INSTALLER_EMAIL = get_secret("INSTALLER_EMAIL")
MANAGER_EMAIL = get_secret("MANAGER_EMAIL")
MANUFACTURER_EMAIL = get_secret("MANUFACTURER_EMAIL")
LAST_EMAIL_ERROR = None

def send_email(subject, html_body, to_emails):
    global LAST_EMAIL_ERROR
    LAST_EMAIL_ERROR = None
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        LAST_EMAIL_ERROR = "Sender credentials not configured."
        return False
    recipients = [to_emails] if isinstance(to_emails, str) else list(to_emails)
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, 465, timeout=30) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        LAST_EMAIL_ERROR = None
        return True
    except Exception as e_ssl:
        LAST_EMAIL_ERROR = f"SSL send failed: {e_ssl}"
    try:
        with smtplib.SMTP(SMTP_SERVER, 587, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        LAST_EMAIL_ERROR = None
        return True
    except Exception as e_tls:
        LAST_EMAIL_ERROR = (LAST_EMAIL_ERROR or "") + f" | STARTTLS failed: {e_tls}"
        return False

# ====================================================
# === LOGO & HEADER ===
# ====================================================
logo_path = ROOT / "DBN_Metro.png"
if logo_path.exists():
    try:
        with open(logo_path, "rb") as img_file:
            encoded_logo = base64.b64encode(img_file.read()).decode()
        st.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{encoded_logo}' width='70'/></div>", unsafe_allow_html=True)
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
    "installer2": {"name": "installer2", "password": "installer123", "role": "installer", "email": INSTALLER_EMAIL},
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
# === DATA HANDLING (with redundancy) ===
# ====================================================
def load_data():
    if DATA_FILE.exists():
        try:
            df = pd.read_csv(DATA_FILE, dtype=str)
            return df
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
        st.warning(f"Could not save main data file: {e}")
    try:
        dump_filename = f"stock_requests_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
        df.to_csv(DUMP_DIR / dump_filename, index=False)
    except Exception as e:
        st.warning(f"Could not create dump: {e}")
    try:
        backup_data(upload_to_gdrive=True, gdrive_folder_id=DEFAULT_GDRIVE_FOLDER)
    except Exception as e:
        st.warning(f"Automatic backup failed: {e}")

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
