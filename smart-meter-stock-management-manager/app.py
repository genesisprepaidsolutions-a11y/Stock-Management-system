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
import requests  # optional: only used if Graph upload is enabled
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
# === ONE DRIVE CONFIG (LOCAL SYNC FOLDER) ===
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

ONEDRIVE_ACCESS_TOKEN = get_secret("ONEDRIVE_ACCESS_TOKEN")  # optional

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

def copy_zip_to_onedrive(zip_path: Path):
    if not ONE_DRIVE_BACKUP_DIR or not Path(ONE_DRIVE_BACKUP_DIR).exists():
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
    zip_path = create_local_zip()
    if not zip_path:
        return False
    ok_local = copy_zip_to_onedrive(zip_path)
    ok_graph = upload_zip_to_onedrive_graph(zip_path)
    return ok_local or ok_graph

def find_latest_onedrive_backup():
    try:
        if not ONE_DRIVE_BACKUP_DIR.exists():
            return None
        pattern = str(ONE_DRIVE_BACKUP_DIR / "data_backup_*.zip")
        matches = sorted(glob.glob(pattern), reverse=True)
        if matches:
            return Path(matches[0])
        pattern2 = str(ONE_DRIVE_BACKUP_DIR / "data_backup*.zip")
        matches2 = sorted(glob.glob(pattern2), reverse=True)
        if matches2:
            return Path(matches2[0])
        zips = sorted(ONE_DRIVE_BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        if zips:
            return zips[0]
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
    latest = find_latest_onedrive_backup()
    if latest:
        restored = restore_from_zip(latest)
        if restored:
            return
    st.info("No backup found to restore from (local or OneDrive). If this is first run, data folder is initialized empty.")

try:
    auto_restore_if_needed()
except Exception:
    pass

# ====================================================
# === EMAIL CONFIG ===
# ====================================================
SMTP_SERVER = "smtp.acucommholdings.co.za"
SMTP_PORT = 465

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
# Add manufacturer-specific fields to the same data file
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
        # Manufacturer dispatch fields (kept in same CSV)
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
        ok = backup_data()
        if ok:
            st.success("Backup succeeded (OneDrive copy or Graph upload).")
        else:
            st.info("Backup created locally; OneDrive copy/upload not configured or failed.")
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
                        "Date_Received": "",
                        "Manufacturer_Name": "",
                        "Batch_Number": "",
                        "Dispatch_Qty": "",
                        "Dispatch_Date": "",
                        "Dispatch_Note": "",
                        "Dispatch_Docs": ""
                    })
            if entries:
                df = pd.concat([df, pd.DataFrame(entries)], ignore_index=True)
                save_data(df)
                st.success(f"✅ Request(s) submitted under base ID {base_rid}")

def manufacturer_ui():
    st.header("Manufacturer - Dispatch Stock to City")
    st.markdown("Use this panel to notify the city of dispatched batches. City must approve before stock is added to the system.")
    manu_name = st.session_state.auth["name"]
    st.text_input("Manufacturer Name", value=manu_name, key="manu_name_field")
    st.markdown("---")

    # New: allow manufacturer to input quantities per product like contractor
    st.subheader("Select Products & Quantities to Dispatch")
    col1, col2 = st.columns(2)
    manu_meter_qty = col1.number_input("DN15 Meter Dispatch Quantity", min_value=0, value=0, step=1)
    manu_keypad_qty = col2.number_input("CIU Keypad Dispatch Quantity", min_value=0, value=0, step=1)

    batch_num = st.text_input("Batch Number", value="")
    dispatch_date = st.date_input("Dispatch Date", value=datetime.now().date())
    dispatch_note = st.text_area("Delivery Note")
    dispatch_docs = st.file_uploader("Attach Delivery Document (optional)", type=["pdf", "jpg", "png"])

    if st.button("Submit Dispatch to City"):
        if not batch_num.strip():
            st.warning("Please enter a batch number.")
        elif manu_meter_qty == 0 and manu_keypad_qty == 0:
            st.warning("Please enter at least one dispatch quantity for a product.")
        else:
            df = load_data()
            base_rid = generate_request_id(prefix="MANU")
            entries = []
            doc_path = ""
            # Save attached doc once and reuse path
            if dispatch_docs:
                filename = f"{base_rid}_{dispatch_docs.name}"
                dest = DATA_DIR / filename
                try:
                    with open(dest, "wb") as f:
                        f.write(dispatch_docs.getbuffer())
                    doc_path = str(dest)
                except Exception as e:
                    st.warning(f"Could not save attached document: {e}")

            for item_type, qty in [("DN15 Meter", manu_meter_qty), ("CIU Keypad", manu_keypad_qty)]:
                if qty > 0:
                    rid = f"{base_rid}-{item_type.replace(' ', '_')[:10]}"
                    new = {
                        "Date_Requested": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Request_ID": rid,
                        "Contractor_Name": "",  # not applicable
                        "Installer_Name": "",
                        "Meter_Type": item_type,
                        "Requested_Qty": "",  # not used for manufacturer dispatch
                        "Approved_Qty": "",
                        "Photo_Path": "",
                        "Status": "Pending City Approval (Manufacturer Delivery)",
                        "Contractor_Notes": "",
                        "City_Notes": "",
                        "Decline_Reason": "",
                        "Date_Approved": "",
                        "Date_Received": "",
                        "Manufacturer_Name": manu_name,
                        "Batch_Number": batch_num,
                        "Dispatch_Qty": str(qty),
                        "Dispatch_Date": dispatch_date.strftime("%Y-%m-%d"),
                        "Dispatch_Note": dispatch_note,
                        "Dispatch_Docs": doc_path
                    }
                    entries.append(new)

            if entries:
                df = pd.concat([df, pd.DataFrame(entries)], ignore_index=True)
                save_data(df)
                st.success(f"✅ Dispatch submitted to City as base ID {base_rid} ({len(entries)} item rows created)")
                # optional: email notify city
                try:
                    if ETHEKWINI_EMAIL:
                        send_email(
                            subject=f"Manufacturer Dispatch Pending Approval: {base_rid}",
                            html_body=f"<p>Manufacturer <b>{manu_name}</b> submitted dispatch <b>{base_rid}</b> (Batch {batch_num}).</p>",
                            to_emails=ETHEKWINI_EMAIL
                        )
                except Exception:
                    pass

# ====================================================
# === CITY UI (UPDATED REPORT DETAILS) ===
# ====================================================
def _safe(val):
    return "" if val is None or (isinstance(val, float) and pd.isna(val)) else str(val)


def _display_file_link(path_str, label="Download"):
    try:
        p = Path(path_str)
        if p.exists():
            with open(p, "rb") as f:
                data = f.read()
            b64 = base64.b64encode(data).decode()
            href = f"data:application/octet-stream;base64,{b64}"
            st.markdown(f"[{label}]({href})")
            return True
    except Exception:
        pass
    return False


def city_ui():
    st.header("eThekwini Municipality - Verify Requests & Manufacturer Deliveries")
    df = load_data()
    if df.empty:
        st.info("No records in the system.")
        return

    # Show filters
    st.markdown("### Filters")
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        view_choice = st.selectbox("Show records", ["All", "Pending Verification", "Pending City Approval (Manufacturer Delivery)", "Approved / Issued", "Declined", "Received"])
    with col2:
        filter_manu = st.text_input("Filter by Manufacturer Name (partial)")
    with col3:
        filter_type = st.selectbox("Product Type (or All)", options=["All"] + sorted(df["Meter_Type"].dropna().unique().tolist()))

    view_df = df.copy()
    if view_choice != "All":
        view_df = view_df[view_df["Status"] == view_choice]
    if filter_manu:
        view_df = view_df[view_df["Manufacturer_Name"].fillna("").str.contains(filter_manu, case=False, na=False)]
    if filter_type and filter_type != "All":
        view_df = view_df[view_df["Meter_Type"] == filter_type]

    st.markdown("### Matching Records")
    st.dataframe(view_df.fillna(""), use_container_width=True)

    st.markdown("---")
    st.markdown("### Take Action")
    # Provide selection of record to act on
    sel_id = st.selectbox("Select Request/Dispatch ID to act on", [""] + view_df["Request_ID"].tolist())
    if sel_id:
        record = df[df["Request_ID"] == sel_id].iloc[0].to_dict()

        # --- Improved Report Details Section ---
        st.markdown("**Record details:**")
        # Top row: ID, Status, Requested/Approved Qty
        rcol1, rcol2, rcol3 = st.columns([2,2,2])
        rcol1.markdown(f"**Request ID**\n{_safe(record.get('Request_ID'))}")
        rcol2.markdown(f"**Status**\n{_safe(record.get('Status'))}")
        rcol3.markdown(f"**Meter Type**\n{_safe(record.get('Meter_Type'))}")

        # Second row: Dates
        dcol1, dcol2, dcol3 = st.columns([2,2,2])
        dcol1.markdown(f"**Date Requested**\n{_safe(record.get('Date_Requested'))}")
        dcol2.markdown(f"**Date Approved**\n{_safe(record.get('Date_Approved'))}")
        dcol3.markdown(f"**Date Received**\n{_safe(record.get('Date_Received'))}")

        # Third row: Parties and quantities
        p1, p2, p3 = st.columns([2,2,2])
        p1.markdown(f"**Contractor**\n{_safe(record.get('Contractor_Name'))}")
        p2.markdown(f"**Installer**\n{_safe(record.get('Installer_Name'))}")
        p3.markdown(f"**Requested / Approved**\n{_safe(record.get('Requested_Qty'))} / {_safe(record.get('Approved_Qty'))}")

        # Manufacturer & batch info
        m1, m2, m3 = st.columns([2,2,2])
        m1.markdown(f"**Manufacturer**\n{_safe(record.get('Manufacturer_Name'))}")
        m2.markdown(f"**Batch #**\n{_safe(record.get('Batch_Number'))}")
        m3.markdown(f"**Dispatch Qty / Date**\n{_safe(record.get('Dispatch_Qty'))} / {_safe(record.get('Dispatch_Date'))}")

        # Notes and decline reason full width
        st.markdown("**Notes (City / Contractor / Dispatch)**")
        st.write(f"City Notes: {_safe(record.get('City_Notes'))}")
        st.write(f"Contractor Notes: {_safe(record.get('Contractor_Notes'))}")
        st.write(f"Dispatch Note: {_safe(record.get('Dispatch_Note'))}")
        if record.get('Decline_Reason'):
            st.warning(f"Decline Reason: {_safe(record.get('Decline_Reason'))}")

        # Show photo preview if available
        photo_path = _safe(record.get('Photo_Path'))
        if photo_path:
            try:
                p = Path(photo_path)
                if p.exists():
                    st.markdown("**Attached Photo**")
                    st.image(str(p), use_column_width=False, width=300)
                else:
                    st.info("No attached photo found at saved path.")
            except Exception:
                st.info("Could not load attached photo.")

        # Show dispatch docs download link if available
        doc_path = _safe(record.get('Dispatch_Docs'))
        if doc_path:
            st.markdown("**Attached Documents**")
            ok = _display_file_link(doc_path, label="Download dispatch document")
            if not ok:
                st.info("Attached document path is set but file not found.")

        st.markdown("---")
        # If this is a manufacturer dispatch
        if record.get("Status", "").startswith("Pending City Approval"):
            st.subheader("Manufacturer Dispatch Actions")
            approved_qty = st.number_input("Approved Quantity to accept into stock", min_value=0, value=int(record.get("Dispatch_Qty") or 0))
            city_notes = st.text_area("City Notes")
            photo = st.file_uploader("Upload proof photo (optional)", type=["jpg", "png"] )
            decline_reason = st.text_input("Decline reason (if declining)")
            approve_btn, decline_btn = st.columns(2)
            if approve_btn.button("Approve Manufacturer Dispatch"):
                # update row
                df.loc[df["Request_ID"] == sel_id, "Approved_Qty"] = str(approved_qty)
                if photo:
                    dest = PHOTO_DIR / f"{sel_id}_{photo.name}"
                    try:
                        with open(dest, "wb") as f:
                            f.write(photo.getbuffer())
                        df.loc[df["Request_ID"] == sel_id, "Photo_Path"] = str(dest)
                    except Exception:
                        st.warning("Could not save photo.")
                df.loc[df["Request_ID"] == sel_id, "Status"] = "Approved / Issued"
                df.loc[df["Request_ID"] == sel_id, "City_Notes"] = city_notes
                df.loc[df["Request_ID"] == sel_id, "Date_Approved"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_data(df)
                st.success("✅ Manufacturer dispatch approved and issued to stock.")
                # optional: notify manufacturer and manager via email
                try:
                    recipients = []
                    if MANUFACTURER_EMAIL:
                        recipients.append(MANUFACTURER_EMAIL)
                    if MANAGER_EMAIL:
                        recipients.append(MANAGER_EMAIL)
                    if recipients:
                        send_email(
                            subject=f"Dispatch Approved: {sel_id}",
                            html_body=f"<p>Your dispatch <b>{sel_id}</b> has been approved by City. Approved Qty: {approved_qty}</p>",
                            to_emails=recipients
                        )
                except Exception:
                    pass
                safe_rerun()
            if decline_btn.button("Decline Manufacturer Dispatch"):
                reason = decline_reason or "No reason provided"
                df.loc[df["Request_ID"] == sel_id, "Status"] = "Declined"
                df.loc[df["Request_ID"] == sel_id, "Decline_Reason"] = reason
                df.loc[df["Request_ID"] == sel_id, "City_Notes"] = city_notes
                save_data(df)
                st.error("❌ Manufacturer dispatch declined.")
                try:
                    if MANUFACTURER_EMAIL:
                        send_email(
                            subject=f"Dispatch Declined: {sel_id}",
                            html_body=f"<p>Your dispatch <b>{sel_id}</b> was declined by City. Reason: {reason}</p>",
                            to_emails=MANUFACTURER_EMAIL
                        )
                except Exception:
                    pass
                safe_rerun()
        # If this is a contractor request pending verification
        elif record.get("Status", "") == "Pending Verification":
            st.subheader("Contractor Request Verification")
            try:
                default_qty = int(record.get("Requested_Qty") or 0)
            except Exception:
                default_qty = 0
            qty = st.number_input("Approved Qty", min_value=0, value=default_qty)
            photo = st.file_uploader("Upload proof photo", type=["jpg", "png"]) 
            notes = st.text_area("Notes")
            decline_reason = st.text_input("Decline reason")
            if st.button("Approve Contractor Request"):
                df.loc[df["Request_ID"] == sel_id, "Approved_Qty"] = str(qty)
                ppath = ""
                if photo:
                    dest = PHOTO_DIR / f"{sel_id}_{photo.name}"
                    try:
                        with open(dest, "wb") as f:
                            f.write(photo.getbuffer())
                        ppath = str(dest)
                    except Exception:
                        st.warning("Could not save photo.")
                df.loc[df["Request_ID"] == sel_id, "Photo_Path"] = ppath
                df.loc[df["Request_ID"] == sel_id, "Status"] = "Approved / Issued"
                df.loc[df["Request_ID"] == sel_id, "City_Notes"] = notes
                df.loc[df["Request_ID"] == sel_id, "Date_Approved"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_data(df)
                st.success("✅ Approved and issued.")
                safe_rerun()
            if st.button("Decline Contractor Request"):
                df.loc[df["Request_ID"] == sel_id, "Status"] = "Declined"
                df.loc[df["Request_ID"] == sel_id, "Decline_Reason"] = decline_reason
                save_data(df)
                st.error("❌ Declined.")
                safe_rerun()
        else:
            st.info("Selected record is not actionable from this panel. Use Manager or Installer panels for other operations.")

# ====================================================
# === INSTALLER UI ===
# ====================================================
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
    if "Installer_Name" in df.columns and df["Installer_Name"].notna().any():
        try:
            approved = df[df["Installer_Name"].str.lower() == installer]
        except Exception:
            approved = df.copy()
    else:
        approved = df.copy()
    try:
        approved = approved[approved["Status"].str.contains("Approved", na=False)]
    except Exception:
        pass
    st.dataframe(approved.fillna(""), use_container_width=True)
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
    st.dataframe(df.fillna(""), use_container_width=True)

    st.markdown("### 🔎 Record Management (Edit / Delete)")
    if df.empty:
        st.info("No records to manage.")
    else:
        rec_col, action_col = st.columns([3,2])
        with rec_col:
            selected_id = st.selectbox("Select Request ID to edit or delete", [""] + df["Request_ID"].fillna("").tolist())
        if selected_id:
            record = df[df["Request_ID"] == selected_id].iloc[0].to_dict()
            st.markdown("#### Selected Record — editable fields")
            # Editable fields - choose a subset that makes sense for manager edits
            with st.form(key=f"edit_form_{selected_id}"):
                c1, c2 = st.columns(2)
                contractor_name = c1.text_input("Contractor Name", value=_safe(record.get("Contractor_Name")))
                installer_name = c2.text_input("Installer Name", value=_safe(record.get("Installer_Name")))

                m1, m2 = st.columns(2)
                meter_type = m1.text_input("Meter Type", value=_safe(record.get("Meter_Type")))
                requested_qty = m2.text_input("Requested Qty", value=_safe(record.get("Requested_Qty")))

                a1, a2 = st.columns(2)
                approved_qty = a1.text_input("Approved Qty", value=_safe(record.get("Approved_Qty")))
                status_options = sorted(df["Status"].dropna().unique().tolist())
                if not status_options:
                    status_options = ["Pending Verification", "Approved / Issued", "Declined", "Received", "Pending City Approval (Manufacturer Delivery)"]
                status = a2.selectbox("Status", options=status_options, index=status_options.index(_safe(record.get("Status"))) if _safe(record.get("Status")) in status_options else 0)

                mn1, mn2 = st.columns(2)
                contractor_notes = mn1.text_area("Contractor Notes", value=_safe(record.get("Contractor_Notes")))
                city_notes = mn2.text_area("City Notes", value=_safe(record.get("City_Notes")))

                manu1, manu2 = st.columns(2)
                manufacturer_name = manu1.text_input("Manufacturer Name", value=_safe(record.get("Manufacturer_Name")))
                batch_number = manu2.text_input("Batch Number", value=_safe(record.get("Batch_Number")))

                d1, d2 = st.columns(2)
                dispatch_qty = d1.text_input("Dispatch Qty", value=_safe(record.get("Dispatch_Qty")))
                dispatch_date = d2.text_input("Dispatch Date (YYYY-MM-DD)", value=_safe(record.get("Dispatch_Date")))

                # Non-editable but visible for context
                st.markdown(f"**Request ID:** {selected_id}")
                st.markdown(f"**Date Requested:** {_safe(record.get('Date_Requested'))}")
                st.markdown(f"**Photo Path:** {_safe(record.get('Photo_Path'))}")

                submit_edit = st.form_submit_button("Save Changes")

                if submit_edit:
                    # Defensive updates: ensure df reloaded to avoid concurrency issues
                    df = load_data()
                    idx = df.index[df["Request_ID"] == selected_id].tolist()
                    if not idx:
                        st.error("Record not found on disk — it may have been removed. Reloading.")
                        safe_rerun()
                    else:
                        i = idx[0]
                        df.at[i, "Contractor_Name"] = contractor_name
                        df.at[i, "Installer_Name"] = installer_name
                        df.at[i, "Meter_Type"] = meter_type
                        df.at[i, "Requested_Qty"] = requested_qty
                        df.at[i, "Approved_Qty"] = approved_qty
                        df.at[i, "Status"] = status
                        df.at[i, "Contractor_Notes"] = contractor_notes
                        df.at[i, "City_Notes"] = city_notes
                        df.at[i, "Manufacturer_Name"] = manufacturer_name
                        df.at[i, "Batch_Number"] = batch_number
                        df.at[i, "Dispatch_Qty"] = dispatch_qty
                        df.at[i, "Dispatch_Date"] = dispatch_date
                        # if approving now, set Date_Approved if not set
                        try:
                            if status == "Approved / Issued" and not _safe(df.at[i, "Date_Approved"]):
                                df.at[i, "Date_Approved"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            pass
                        save_data(df)
                        st.success("Record updated successfully.")
                        safe_rerun()

            # Delete area (separate from the form)
            st.markdown("#### Delete record")
            st.warning("Deleting a record is irreversible. Proceed with caution.")
            confirm_delete = st.checkbox("I understand this will permanently delete the selected record.")
            delete_btn = st.button("Delete Record")
            if delete_btn:
                if not confirm_delete:
                    st.error("Please confirm deletion by ticking the checkbox before pressing Delete.")
                else:
                    df = load_data()
                    if selected_id not in df["Request_ID"].tolist():
                        st.error("Record not found — it may have already been deleted.")
                        safe_rerun()
                    else:
                        df = df[df["Request_ID"] != selected_id]
                        save_data(df)
                        st.success(f"Record {selected_id} deleted.")
                        safe_rerun()

    st.markdown("### 📦 Data Dump & Backup")
    dumps = sorted(DUMP_DIR.glob("*.csv"), reverse=True)
    if dumps:
        dump_names = [d.name for d in dumps]
        selected_dump = st.selectbox("Select Dump File", dump_names)
        if selected_dump:
            dump_df = pd.read_csv(DUMP_DIR / selected_dump)
            st.dataframe(dump_df.fillna(""), use_container_width=True)
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
    elif role == "manufacturer":
        manufacturer_ui()
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
