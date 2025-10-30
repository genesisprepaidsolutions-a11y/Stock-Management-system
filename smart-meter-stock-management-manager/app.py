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
WHITE = "#FFFFFF"

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
        }}
        .stButton>button:hover {{
            background-color: {PRIMARY_BLUE};
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {PRIMARY_BLUE}, {SECONDARY_BLUE});
            color: {WHITE};
        }}
        [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {{
            color: {WHITE};
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
REPORT_DIR = ROOT / "reports"
DUMP_DIR = DATA_DIR / "dumps"
for d in [DATA_DIR, PHOTO_DIR, REPORT_DIR, DUMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "stock_requests.csv"

# ====================================================
# === ONEDRIVE CONFIG ===
# ====================================================
ONE_DRIVE_SYNC_ROOT = Path(r"C:\Users\ADMIN\OneDrive")
ONE_DRIVE_BACKUP_DIR = ONE_DRIVE_SYNC_ROOT / "SmartMeter_Backups"
ONE_DRIVE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_FILE = ROOT / "data_backup.zip"

def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key)

ONEDRIVE_ACCESS_TOKEN = get_secret("ONEDRIVE_ACCESS_TOKEN")

# ====================================================
# === BACKUP & RESTORE ===
# ====================================================
def create_local_zip():
    try:
        if BACKUP_FILE.exists():
            BACKUP_FILE.unlink()
        archive_path = shutil.make_archive(str(BACKUP_FILE.with_suffix('')), 'zip', root_dir=str(DATA_DIR))
        return Path(archive_path)
    except Exception as e:
        st.warning(f"Backup error: {e}")
        return None

def copy_zip_to_onedrive(zip_path: Path):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = ONE_DRIVE_BACKUP_DIR / f"{zip_path.stem}_{timestamp}{zip_path.suffix}"
        shutil.copy2(zip_path, dest)
        return True
    except Exception:
        return False

def upload_zip_to_onedrive_graph(zip_path: Path):
    token = ONEDRIVE_ACCESS_TOKEN
    if not token:
        return False
    try:
        upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/Apps/AcucommBackups/{zip_path.name}:/content"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/zip"}
        with open(zip_path, "rb") as f:
            r = requests.put(upload_url, headers=headers, data=f)
        return r.status_code in (200, 201)
    except Exception:
        return False

def backup_data():
    zip_path = create_local_zip()
    if not zip_path:
        return False
    return copy_zip_to_onedrive(zip_path) or upload_zip_to_onedrive_graph(zip_path)

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
        return False
    recipients = [to_emails] if isinstance(to_emails, str) else to_emails
    try:
        msg = MIMEMultipart()
        msg["From"], msg["To"], msg["Subject"] = SENDER_EMAIL, ", ".join(recipients), subject
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        return True
    except Exception:
        return False

# ====================================================
# === HEADER & LOGO ===
# ====================================================
logo_path = ROOT / "DBN_Metro.png"
if logo_path.exists():
    encoded_logo = base64.b64encode(open(logo_path, "rb").read()).decode()
    st.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{encoded_logo}' width='70'/></div>", unsafe_allow_html=True)

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

CREDENTIALS = {u: {"name": v["name"], "password_hash": hash_password(v["password"]), "role": v["role"], "email": v["email"]}
               for u, v in raw_users.items()}

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None}

def safe_rerun():
    try:
        st.rerun()
    except Exception:
        pass

# ====================================================
# === DATA HANDLING ===
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
        "Date_Approved", "Date_Received"
    ]
    return pd.DataFrame(columns=cols)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)
    dump_filename = f"stock_requests_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
    df.to_csv(DUMP_DIR / dump_filename, index=False)
    backup_data()

def generate_request_id(prefix="REQ"):
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

# ====================================================
# === LOGIN ===
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
    contractor_name = st.session_state.auth["name"]
    installer_name = st.text_input("Installer Name")
    st.subheader("Select Stock Items & Quantities")
    col1, col2 = st.columns(2)
    meter_qty = col1.number_input("DN15 Meter Quantity", min_value=0, value=0)
    keypad_qty = col2.number_input("CIU Keypad Quantity", min_value=0, value=0)
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
                    rid = f"{base_rid}-{item_type.replace(' ', '_')[:10]}"
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
                        "Date_Received": ""
                    })
            df = pd.concat([df, pd.DataFrame(entries)], ignore_index=True)
            save_data(df)
            st.success(f"✅ Request(s) submitted under ID {base_rid}")

def city_ui():
    st.header("eThekwini Municipality - Verify Contractor Requests")
    df = load_data()
    if df.empty:
        st.info("No records in the system.")
        return

    st.markdown("### Filters")
    col1, col2 = st.columns([1,1])
    view_choice = col1.selectbox("Show records", ["All", "Pending Verification", "Approved / Issued", "Declined", "Received"])
    filter_type = col2.selectbox("Product Type (or All)", ["All"] + sorted(df["Meter_Type"].dropna().unique().tolist()))
    view_df = df.copy()
    if view_choice != "All":
        view_df = view_df[view_df["Status"] == view_choice]
    if filter_type != "All":
        view_df = view_df[view_df["Meter_Type"] == filter_type]

    st.dataframe(view_df.fillna(""), use_container_width=True)
    st.markdown("---")
    sel_id = st.selectbox("Select Request ID to act on", [""] + view_df["Request_ID"].tolist())
    if sel_id:
        record = df[df["Request_ID"] == sel_id].iloc[0].to_dict()
        st.write("Record details:", record)
        if record.get("Status") == "Pending Verification":
            qty = st.number_input("Approved Qty", min_value=0, value=int(record.get("Requested_Qty") or 0))
            photo = st.file_uploader("Upload proof photo", type=["jpg", "png"])
            notes = st.text_area("Notes")
            decline_reason = st.text_input("Decline reason")
            if st.button("Approve Request"):
                df.loc[df["Request_ID"] == sel_id, ["Approved_Qty", "Status", "City_Notes", "Date_Approved"]] = \
                    [str(qty), "Approved / Issued", notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                if photo:
                    dest = PHOTO_DIR / f"{sel_id}_{photo.name}"
                    with open(dest, "wb") as f:
                        f.write(photo.getbuffer())
                    df.loc[df["Request_ID"] == sel_id, "Photo_Path"] = str(dest)
                save_data(df)
                st.success("✅ Approved and issued.")
                safe_rerun()
            if st.button("Decline Request"):
                df.loc[df["Request_ID"] == sel_id, ["Status", "Decline_Reason"]] = ["Declined", decline_reason]
                save_data(df)
                st.error("❌ Declined.")
                safe_rerun()
        else:
            st.info("Selected record is not actionable from this panel.")

def installer_ui():
    st.header("Installer - Mark Received Stock")
    df = load_data()
    installer = st.session_state.auth["name"].lower()
    approved = df[df["Installer_Name"].str.lower() == installer] if "Installer_Name" in df.columns else df
    approved = approved[approved["Status"].str.contains("Approved", na=False)]
    st.dataframe(approved.fillna(""), use_container_width=True)
    sel = st.selectbox("Mark as received (Request ID)", [""] + approved["Request_ID"].tolist())
    if sel and st.button("✅ Mark as Received"):
        df.loc[df["Request_ID"] == sel, ["Status", "Date_Received"]] = ["Received", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        save_data(df)
        st.success(f"Request {sel} marked as received.")
        safe_rerun()

def manager_ui():
    st.header("Project Manager - Reconciliation & Export")
    df = load_data()
    st.dataframe(df.fillna(""), use_container_width=True)
    dumps = sorted(DUMP_DIR.glob("*.csv"), reverse=True)
    if dumps:
        dump_names = [d.name for d in dumps]
        selected_dump = st.selectbox("Select Dump File", dump_names)
        if selected_dump:
            dump_df = pd.read_csv(DUMP_DIR / selected_dump)
            st.dataframe(dump_df.fillna(""), use_container_width=True)
            st.download_button("Download Selected Dump", dump_df.to_csv(index=False).encode(), selected_dump, "text/csv")
    if st.button("Create & Upload Backup Now"):
        zipfile = create_local_zip()
        if zipfile and (copy_zip_to_onedrive(zipfile) or upload_zip_to_onedrive_graph(zipfile)):
            st.success("Backup created and sent to OneDrive.")
        else:
            st.warning("Backup created locally only.")

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
            bottom: 0;
            left: 0;
            width: 100%;
            background-color: {PRIMARY_BLUE};
            color: white;
            text-align: center;
            padding: 10px 0;
            font-size: 14px;
        }}
    </style>
    <div class="footer">
        © {datetime.now().year} eThekwini Municipality-WS7761 | Smart Meter Stock Management System
    </div>
""", unsafe_allow_html=True)
