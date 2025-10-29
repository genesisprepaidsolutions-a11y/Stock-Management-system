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
import requests  # optional: only used if Graph upload is enabled
import json

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
from PIL import Image

favicon_path = Path(__file__).parent / "favicon.jpg"
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
ROOT = Path(__file__).parent
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
# === ONE DRIVE CONFIG (LOCAL SYNC FOLDER) ===
# ====================================================
# Local OneDrive path (you provided C:\Users\ADMIN)
ONE_DRIVE_SYNC_ROOT = Path(r"C:\Users\ADMIN\OneDrive")
ONE_DRIVE_BACKUP_DIR = ONE_DRIVE_SYNC_ROOT / "SmartMeter_Backups"
# ensure the OneDrive backup folder exists (if OneDrive installed & path valid)
try:
    ONE_DRIVE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    # folder may not exist or permission denied; we'll handle this gracefully later
    pass

# Optionally: Microsoft Graph token (not required for local OneDrive)
def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key)

ONEDRIVE_ACCESS_TOKEN = get_secret("ONEDRIVE_ACCESS_TOKEN")  # optional

# ====================================================
# === BACKUP & RESTORE HELPERS ===
# ====================================================
def create_local_zip():
    """
    Creates a zip archive of the DATA_DIR and returns the Path to the zip.
    """
    try:
        # remove any existing zip first to ensure fresh content
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

def copy_zip_to_onedrive(zip_path: Path):
    """
    Copy the zip to the local OneDrive sync folder (timestamped).
    Returns True if successful.
    """
    if not ONE_DRIVE_BACKUP_DIR or not Path(ONE_DRIVE_BACKUP_DIR).exists():
        # OneDrive folder not present or not configured
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
    """
    Optional: Upload to OneDrive via Microsoft Graph using ONEDRIVE_ACCESS_TOKEN.
    Returns True if successful.
    """
    token = ONEDRIVE_ACCESS_TOKEN
    if not token:
        return False
    try:
        filename = zip_path.name
        remote_path = f"/Apps/AcucommBackups/{filename}"
        upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:{remote_path}:/content"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/zip"
        }
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
    """
    Create local zip and attempt to copy to OneDrive sync folder (and Graph if token present).
    Returns True if either OneDrive copy or Graph upload succeeded.
    """
    zip_path = create_local_zip()
    if not zip_path:
        return False
    ok_local = copy_zip_to_onedrive(zip_path)
    ok_graph = upload_zip_to_onedrive_graph(zip_path)
    # keep local zip as well
    return ok_local or ok_graph

def find_latest_onedrive_backup():
    """
    Returns Path to the newest backup zip in the OneDrive backup folder (if present), else None.
    """
    try:
        if not ONE_DRIVE_BACKUP_DIR.exists():
            return None
        pattern = str(ONE_DRIVE_BACKUP_DIR / "data_backup_*.zip")
        matches = sorted(glob.glob(pattern), reverse=True)
        if matches:
            return Path(matches[0])
        # also match other zip patterns
        pattern2 = str(ONE_DRIVE_BACKUP_DIR / "data_backup*.zip")
        matches2 = sorted(glob.glob(pattern2), reverse=True)
        if matches2:
            return Path(matches2[0])
        # if no specific prefix matches, pick latest zip in folder
        zips = sorted(ONE_DRIVE_BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        if zips:
            return zips[0]
    except Exception:
        pass
    return None

def restore_from_zip(zip_path: Path):
    """
    Extracts zip_path into DATA_DIR (overwrites if necessary).
    """
    try:
        # ensure data dir exists and is empty before extracting
        if DATA_DIR.exists():
            # remove contents for clean restore (but keep folder)
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
    """
    If local DATA_FILE does not exist or is empty, attempt to restore:
    - first from any local BACKUP_FILE (data_backup.zip) in project,
    - then from the latest OneDrive backup (ONE_DRIVE_BACKUP_DIR).
    """
    # If data file exists and has content, skip restore
    if DATA_FILE.exists():
        try:
            df = pd.read_csv(DATA_FILE)
            if not df.empty:
                return  # nothing to restore
        except Exception:
            pass

    # Try local backup zip first
    if BACKUP_FILE.exists():
        try:
            shutil.unpack_archive(str(BACKUP_FILE), extract_dir=str(DATA_DIR))
            st.info("Restored data from local backup zip.")
            return
        except Exception:
            pass

    # Try OneDrive latest backup
    latest = find_latest_onedrive_backup()
    if latest:
        restored = restore_from_zip(latest)
        if restored:
            return
    # nothing to restore
    st.info("No backup found to restore from (local or OneDrive). If this is first run, data folder is initialized empty.")

# Attempt auto-restore at startup
try:
    auto_restore_if_needed()
except Exception:
    pass

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
    "ethekwini": {"name": "ethekwini", "password": "ethekwini123", "role": "city", "email": ETHEKWINI_EMAIL},
    "installer1": {"name": "installer1", "password": "installer123", "role": "installer", "email": INSTALLER_EMAIL},
    "Reece": {"name": "Reece", "password": "Reece123!", "role": "manager", "email": MANAGER_EMAIL},
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
            df = pd.read_csv(DATA_FILE)
            return df
        except Exception:
            pass
    # default columns
    cols = ["Date_Requested", "Request_ID", "Contractor_Name", "Installer_Name",
            "Meter_Type", "Requested_Qty", "Approved_Qty", "Photo_Path",
            "Status", "Contractor_Notes", "City_Notes", "Decline_Reason",
            "Date_Approved", "Date_Received"]
    return pd.DataFrame(columns=cols)

def save_data(df):
    # Save main CSV
    try:
        df.to_csv(DATA_FILE, index=False)
    except Exception as e:
        st.warning(f"Could not save main data file: {e}")

    # Create dated dump for redundancy
    try:
        dump_filename = f"stock_requests_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
        df.to_csv(DUMP_DIR / dump_filename, index=False)
    except Exception as e:
        st.warning(f"Could not create dump: {e}")

    # Create zip archive of data folder and push to OneDrive (local sync folder)
    try:
        ok = backup_data()
        if ok:
            st.success("Backup succeeded (OneDrive copy or Graph upload).")
        else:
            st.info("Backup created locally; OneDrive copy/upload not configured or failed.")
    except Exception as e:
        st.warning(f"Automatic backup failed: {e}")

def generate_request_id():
    return f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}"

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
# === ROLE UI PANELS ===
# ====================================================
def contractor_ui():
    st.header("Contractor - Submit Stock Request")

    contractor_logo = ROOT / "contractor logo.jpg"
    if contractor_logo.exists():
        st.markdown("<div style='display:flex;justify-content:center;'>", unsafe_allow_html=True)
        st.image(str(contractor_logo), width=500)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    contractor_name = st.session_state.auth["name"]
    installer_name = st.text_input("Installer Name")
    st.subheader("Select Stock Items & Quantities")
    col1, col2 = st.columns(2)
    meter_qty = col1.number_input("DN15 Meter Quantity", min_value=0, value=0, step=1)
    keypad_qty = col2.number_input("CIU Keypad Quantity", min_value=0, value=0, step=1)
    notes = st.text_area("Notes")

    if st.button("Submit Request"):
        if not installer_name:
            st.warning("Please enter installer name")
        elif meter_qty == 0 and keypad_qty == 0:
            st.warning("Please request at least one item.")
        else:
            df = load_data()
            rid = generate_request_id()
            for item_type, qty in [("DN15 Meter", meter_qty), ("CIU Keypad", keypad_qty)]:
                if qty > 0:
                    df = pd.concat([df, pd.DataFrame([{
                        "Date_Requested": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Request_ID": f"{rid}-{item_type[0]}",
                        "Contractor_Name": contractor_name,
                        "Installer_Name": installer_name,
                        "Meter_Type": item_type,
                        "Requested_Qty": qty,
                        "Approved_Qty": "",
                        "Photo_Path": "",
                        "Status": "Pending Verification",
                        "Contractor_Notes": notes,
                        "City_Notes": "",
                        "Decline_Reason": "",
                        "Date_Approved": "",
                        "Date_Received": "",
                    }])], ignore_index=True)
            save_data(df)
            st.success(f"✅ Request(s) submitted under base ID {rid}")

def city_ui():
    st.header("eThekwini Municipality - Verify Requests")
    df = load_data()
    pending = df[df["Status"] == "Pending Verification"]
    st.dataframe(pending, use_container_width=True)
    sel = st.selectbox("Select Request ID", [""] + pending["Request_ID"].tolist())
    if sel:
        row = df[df["Request_ID"] == sel].iloc[0]
        st.write(row.to_dict())
        # approved qty default uses requested qty if parseable
        try:
            default_qty = int(row.get("Requested_Qty", 0))
        except Exception:
            default_qty = 0
        qty = st.number_input("Approved Qty", min_value=0, value=default_qty)
        photo = st.file_uploader("Upload proof photo", type=["jpg", "png"])
        notes = st.text_area("Notes")
        decline_reason = st.text_input("Decline reason")

        if st.button("Approve"):
            df.loc[df["Request_ID"] == sel, "Approved_Qty"] = qty
            ppath = ""
            if photo:
                dest = PHOTO_DIR / f"{sel}_{photo.name}"
                with open(dest, "wb") as f:
                    f.write(photo.getbuffer())
                ppath = str(dest)
            df.loc[df["Request_ID"] == sel, "Photo_Path"] = ppath
            df.loc[df["Request_ID"] == sel, "Status"] = "Approved / Issued"
            df.loc[df["Request_ID"] == sel, "City_Notes"] = notes
            df.loc[df["Request_ID"] == sel, "Date_Approved"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_data(df)
            st.success("✅ Approved and issued.")
            safe_rerun()

        if st.button("Decline"):
            df.loc[df["Request_ID"] == sel, "Status"] = "Declined"
            df.loc[df["Request_ID"] == sel, "Decline_Reason"] = decline_reason
            save_data(df)
            st.error("❌ Declined.")
            safe_rerun()

def installer_ui():
    st.header("Meter Installer - Mark Received Stock")

    acucomm_logo = ROOT / "acucomm logo.jpg"
    if acucomm_logo.exists():
        st.markdown("<div style='display:flex;justify-content:center;'>", unsafe_allow_html=True)
        st.image(str(acucomm_logo), width=250)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    df = load_data()
    installer = st.session_state.auth["name"].strip().lower()
    if "Installer_Name" in df.columns:
        try:
            approved = df[df["Installer_Name"].str.lower() == installer]
        except Exception:
            approved = df.copy()
    else:
        approved = df.copy()
    # filter approved statuses
    try:
        approved = approved[approved["Status"].str.contains("Approved", na=False)]
    except Exception:
        pass

    st.dataframe(approved, use_container_width=True)

    sel = st.selectbox("Mark as received (Request ID)", [""] + approved["Request_ID"].tolist())
    if sel and st.button("✅ Mark as Received"):
        df.loc[df["Request_ID"] == sel, "Status"] = "Received"
        df.loc[df["Request_ID"] == sel, "Date_Received"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_data(df)
        st.success(f"Request {sel} marked as received.")
        safe_rerun()

def manager_ui():
    st.header("Project Manager - Reconciliation & Export")
    df = load_data()
    st.dataframe(df, use_container_width=True)

    st.markdown("### 📦 Data Dump & Backup")
    dumps = sorted(DUMP_DIR.glob("*.csv"), reverse=True)
    if dumps:
        dump_names = [d.name for d in dumps]
        selected_dump = st.selectbox("Select Dump File", dump_names)
        if selected_dump:
            dump_df = pd.read_csv(DUMP_DIR / selected_dump)
            st.dataframe(dump_df, use_container_width=True)
            st.download_button("Download Selected Dump", dump_df.to_csv(index=False).encode(), selected_dump, "text/csv")
    else:
        st.info("No dump files available yet.")

    st.markdown("### 🔁 Manual Backup")
    if st.button("Create & Upload Backup Now"):
        zipfile = create_local_zip()
        if zipfile:
            one_local = copy_zip_to_onedrive(zipfile)
            graph_uploaded = upload_zip_to_onedrive_graph(zipfile)
            if one_local or graph_uploaded:
                st.success("Backup created and sent to configured OneDrive destination.")
            else:
                st.warning("Backup created locally but OneDrive upload not configured or failed.")

    st.markdown("### 🔄 Restore from Latest OneDrive Backup")
    if st.button("Restore Latest OneDrive Backup"):
        latest = find_latest_onedrive_backup()
        if latest:
            ok = restore_from_zip(latest)
            if ok:
                st.success("Restore complete from OneDrive latest backup. Data reloaded.")
                safe_rerun()
            else:
                st.error("Restore failed. Check logs.")
        else:
            st.warning("No OneDrive backups found in configured folder.")

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
    if role == "contractor":
        contractor_ui()
    elif role == "city":
        city_ui()
    elif role == "installer":
        installer_ui()
    elif role == "manager":
        manager_ui()
    else:
        st.error("Unknown role.")

# ====================================================
# === FOOTER ===
# ====================================================
st.markdown(f"""
    <style>
        .footer {{
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            background-color: #003366;
            color: white;
            text-align: center;
            padding: 10px 0;
            font-size: 14px;
            border-top: 1px solid #ddd;
            z-index: 100;
        }}
    </style>
    <div class="footer">
        © {datetime.now().year} eThekwini Municipality-WS7761 | Smart Meter Stock Management System
    </div>
""", unsafe_allow_html=True)
