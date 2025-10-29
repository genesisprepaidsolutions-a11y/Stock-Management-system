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
st.set_page_config(
    page_title="Acucomm Stock Management",
    page_icon="acucomm logo.jpg",
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
ROOT = Path(__file__).parent
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
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587

def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key)

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
# === LOGO & HEADER (Centered) ===
# ====================================================
import base64

logo_path = ROOT / "DBN_Metro.png"
if logo_path.exists():
    # Centered logo using HTML base64 embedding
    with open(logo_path, "rb") as img_file:
        encoded_logo = base64.b64encode(img_file.read()).decode()
    st.markdown(
        f"""
        <div style='text-align:center;'>
            <img src='data:image/png;base64,{encoded_logo}' width='70'/>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.warning("⚠️ Logo not found: DBN_Metro.png")

# Centered page header
st.markdown(
    f"<h1 style='text-align:center;color:{PRIMARY_BLUE};'>Ethekwini Smart Meter Stock Management</h1>",
    unsafe_allow_html=True,
)
st.markdown("---")


# ====================================================
# === USER AUTH ===
# ====================================================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

raw_users = {
    "Deezlo": {"name": "Deezlo", "password": "Deezlo123", "role": "contractor", "email": CONTRACTOR_EMAIL},
    "ethekwini": {"name": "ethekwini", "password": "ethekwini123", "role": "city", "email": ETHEKWINI_EMAIL},
    "installer1": {"name": "installer1", "password": "installer123", "role": "installer", "email": INSTALLER_EMAIL},
    "Reece": {"name": "Reece", "password": "Reece123!", "role": "manager", "email": MANAGER_EMAIL},
}

CREDENTIALS = {
    u: {
        "name": v["name"],
        "password_hash": hash_password(v["password"]),
        "role": v["role"],
        "email": v["email"],
    }
    for u, v in raw_users.items()
}

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None}

def safe_rerun():
    try:
        st.rerun()
    except Exception:
        pass

# ====================================================
# === DATA HELPERS ===
# ====================================================
def load_data():
    if DATA_FILE.exists():
        try:
            return pd.read_csv(DATA_FILE)
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
    dump_filename = f"stock_requests_{datetime.now().strftime('%Y-%m-%d')}.csv"
    dump_path = DUMP_DIR / dump_filename
    df.to_csv(dump_path, index=False)

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
# === ROLE INTERFACES ===
# ====================================================
def contractor_ui():
    st.header("Contractor - Submit Stock Request")

    # === Centered Contractor logo only ===
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
        st.write(row)
        qty = st.number_input("Approved Qty", 0, value=int(row["Requested_Qty"]))
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

    # === Centered Acucomm logo only ===
    acucomm_logo = ROOT / "acucomm logo.jpg"
    if acucomm_logo.exists():
        st.markdown("<div style='display:flex;justify-content:center;'>", unsafe_allow_html=True)
        st.image(str(acucomm_logo), width=500)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    df = load_data()
    installer = st.session_state.auth["name"].strip().lower()
    approved = df[df["Installer_Name"].str.lower() == installer]
    approved = approved[approved["Status"].str.contains("Approved", na=False)]
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
        dump_df = pd.read_csv(DUMP_DIR / selected_dump)
        st.dataframe(dump_df, use_container_width=True)
        st.download_button("Download Selected Dump", dump_df.to_csv(index=False).encode(), selected_dump, "text/csv")
    else:
        st.info("No dump files available yet.")

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
    <div class="footer">
        © {datetime.now().year} eThekwini Municipality | Smart Meter Stock Management System
    </div>
""", unsafe_allow_html=True)
