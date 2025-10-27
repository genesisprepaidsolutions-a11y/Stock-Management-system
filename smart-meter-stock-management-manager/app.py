# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import hashlib
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import os
from PIL import Image

# ======================================================
# CONFIG & PATHS
# ======================================================
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
PHOTO_DIR = ROOT / "photos"
ISSUED_PHOTOS_DIR = PHOTO_DIR / "issued"
REPORT_DIR = ROOT / "reports"
for d in [DATA_DIR, PHOTO_DIR, ISSUED_PHOTOS_DIR, REPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "stock_requests.csv"

# Possible logo paths (user indicated: acucomm logo.PNG in data folder)
SUPPLIED_LOGO_PATHS = [
    DATA_DIR / "acucomm logo.PNG",
    DATA_DIR / "acucomm logo.png",
    DATA_DIR / "acucomm_logo.PNG",
    DATA_DIR / "acucomm_logo.png",
    Path("/mnt/data/acucomm logo.PNG"),
    Path("/mnt/data/58a301d8-6c4d-4d41-b9e1-dadf14e5ad54.png"),
    ROOT / "Acucomm logo.jpg",
    ROOT / "Acucomm_logo.png",
]

def find_logo_path():
    for p in SUPPLIED_LOGO_PATHS:
        if p and p.exists():
            return p
    return None

logo_path = find_logo_path()
_full_logo_bytes = None
_favicon_bytes = None

if logo_path:
    try:
        with open(logo_path, "rb") as f:
            _full_logo_bytes = f.read()

        # Create a cropped favicon from the left portion of the image (assumes mark is left)
        img = Image.open(logo_path).convert("RGBA")
        w, h = img.size
        # crop left portion (adjustable): using 28% to capture mark
        crop_x = max(1, int(w * 0.28))
        crop_box = (0, 0, crop_x, h)
        icon_img = img.crop(crop_box)
        # make square by padding if needed
        sq = max(icon_img.size)
        square_img = Image.new("RGBA", (sq, sq), (255, 255, 255, 0))
        square_img.paste(icon_img, ((sq - icon_img.width) // 2, (sq - icon_img.height) // 2), icon_img)
        icon_img = square_img.resize((32, 32), Image.LANCZOS)
        bio = BytesIO()
        icon_img.save(bio, format="PNG")
        bio.seek(0)
        _favicon_bytes = bio.read()
    except Exception:
        _favicon_bytes = _full_logo_bytes

# Use favicon bytes if available; otherwise default emoji
page_icon = _favicon_bytes if _favicon_bytes else "📦"
st.set_page_config(page_title="Acucomm Stock Management", page_icon=page_icon, layout="wide")

# ======================================================
# THEME / STYLES (Acucomm palette & modern card)
# ======================================================
# Corporate palette (greens)
PRIMARY = "#2E7A3E"      # dark green
ACCENT = "#7BC26A"       # light green
ACCENT_DARK = "#1F5A2A"  # darker green for accents
CARD_BG = "rgba(255,255,255,0.96)"  # card background with slight transparency

app_css = f"""
<style>
:root {{
  --primary: {PRIMARY};
  --accent: {ACCENT};
  --accent-dark: {ACCENT_DARK};
}}
/* page background gradient */
[data-testid="stAppViewContainer"] {{
  background: linear-gradient(180deg, rgba(243,249,240,1) 0%, rgba(255,255,255,1) 40%);
}}

/* header area and logo spacing */
.header-row {{
  display:flex;
  align-items:center;
  gap:16px;
  margin-bottom: 18px;
}}

/* title styling */
.app-title {{
  font-size:28px;
  font-weight:700;
  color: var(--primary);
  margin:0;
}}

/* centered login card */
.brand-card {{
  background: {CARD_BG};
  border-radius: 12px;
  box-shadow: 0 6px 20px rgba(31,90,42,0.12);
  padding: 26px;
  max-width: 820px;
  margin: 22px auto;
  border-left: 6px solid var(--accent);
}}

/* label and headings */
.login-heading {{
  font-size:26px;
  font-weight:700;
  color: var(--accent-dark);
  margin-bottom:6px;
}}

/* streamline buttons look */
.stButton>button {{
  background: linear-gradient(90deg, var(--primary), var(--accent));
  color: white;
  border-radius: 8px;
  padding: 10px 18px;
  border: none;
}}
.stButton>button:hover {{
  filter: brightness(1.05);
}}

/* smaller tweaks for inputs to look roomy */
.stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>div>textarea {{
  padding: 12px;
  border-radius: 8px;
}}
/* center alignment helper */
.center-wrapper {{
  display:flex;
  justify-content:center;
}}
/* small footer */
.small-note {{
  color: #556B4A;
  font-size:12px;
}}
</style>
"""
st.markdown(app_css, unsafe_allow_html=True)

# ======================================================
# UTILITY FUNCTIONS
# ======================================================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

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

def generate_request_id():
    return f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}"

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None}

def safe_rerun():
    try:
        st.rerun()
    except Exception:
        pass

# ======================================================
# USERS / CREDENTIALS (unchanged plus Nimba)
# ======================================================
raw_users = {
    "Deezlo": {"name": "Deezlo", "password": "Deezlo123", "role": "contractor"},
    "ethekwini": {"name": "ethekwini", "password": "ethwkwini123", "role": "city"},
    "installer1": {"name": "installer1", "password": "installer123", "role": "installer"},
    "Reece": {"name": "Reece", "password": "Reece123!", "role": "manager"},
    "Nimba": {"name": "Nimba", "password": "Nimba123", "role": "contractor"},
}
CREDENTIALS = {
    u: {
        "name": v["name"],
        "password_hash": hash_password(v["password"]),
        "role": v["role"],
    }
    for u, v in raw_users.items()
}

# ======================================================
# HEADER RENDER (logo top-left, title, subtle spacing)
# ======================================================
def render_header(compact=False):
    # compact param used for small header in sidebar pages if needed
    cols = st.columns([0.9, 9.1])
    with cols[0]:
        if _full_logo_bytes:
            try:
                st.image(_full_logo_bytes, width=140)
            except Exception:
                st.markdown(f"<div style='font-weight:700; color:{PRIMARY}'>Acucomm</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='font-weight:700; color:{PRIMARY}'>Acucomm</div>", unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"<div style='padding-left:6px; margin-top:6px'><h1 class='app-title'>Acucomm Stock Management</h1></div>", unsafe_allow_html=True)

# ======================================================
# LOGIN UI (modern card)
# ======================================================
def login_ui():
    # Full page header
    render_header()

    # card container (centered)
    st.markdown("<div class='brand-card'>", unsafe_allow_html=True)
    cols = st.columns([1, 2, 1])
    with cols[0]:
        st.write("")  # spacer
    with cols[1]:
        st.markdown("<div class='login-heading'>🔐 Login</div>", unsafe_allow_html=True)
        st.write("")  # small spacer

        # Username & password entries with generous spacing
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")

        # Login button full width
        login_col1, login_col2 = st.columns([1, 1])
        with login_col1:
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
                    st.error("Invalid credentials. Please verify username and password.")
        with login_col2:
            # placeholder for future actions (e.g., "Forgot password")
            if st.button("Need help?"):
                st.info("Contact Acucomm support: support@acucomm.local")

        st.write("")
        st.markdown("<div class='small-note'>Use your contractor/city/installer credentials. Example contractor: <b>Nimba</b> / <b>Nimba123</b></div>", unsafe_allow_html=True)

    with cols[2]:
        st.write("")  # spacer
    st.markdown("</div>", unsafe_allow_html=True)

# ======================================================
# Contractor UI
# ======================================================
def contractor_ui():
    render_header()
    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
    st.header("👷 Contractor - Submit Stock Request")
    contractor_name = st.session_state.auth["name"]

    installer_name = st.text_input("Installer Name")

    st.subheader("Select Stock Items & Quantities")
    col1, col2 = st.columns(2)
    with col1:
        meter_qty = st.number_input("DN15 Meter Quantity", min_value=0, value=0, step=1)
    with col2:
        keypad_qty = st.number_input("CIU Keypad Quantity", min_value=0, value=0, step=1)

    notes = st.text_area("Notes", height=110)

    if st.button("Submit Request"):
        if not installer_name:
            st.warning("Please enter installer name")
        elif meter_qty == 0 and keypad_qty == 0:
            st.warning("Please request at least one item.")
        else:
            df = load_data()
            rid = generate_request_id()

            # DN15 Meter request
            if meter_qty > 0:
                df = pd.concat([df, pd.DataFrame([{
                    "Date_Requested": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Request_ID": f"{rid}-M",
                    "Contractor_Name": contractor_name,
                    "Installer_Name": installer_name,
                    "Meter_Type": "DN15 Meter",
                    "Requested_Qty": meter_qty,
                    "Approved_Qty": "",
                    "Photo_Path": "",
                    "Status": "Pending Verification",
                    "Contractor_Notes": notes,
                    "City_Notes": "",
                    "Decline_Reason": "",
                    "Date_Approved": "",
                    "Date_Received": "",
                }])], ignore_index=True)

            # CIU Keypad request
            if keypad_qty > 0:
                df = pd.concat([df, pd.DataFrame([{
                    "Date_Requested": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Request_ID": f"{rid}-K",
                    "Contractor_Name": contractor_name,
                    "Installer_Name": installer_name,
                    "Meter_Type": "CIU Keypad",
                    "Requested_Qty": keypad_qty,
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

    st.subheader("📋 My Requests")
    df = load_data()
    myreq = df[df["Contractor_Name"] == contractor_name]
    st.dataframe(myreq, use_container_width=True)

# ======================================================
# City UI
# ======================================================
def city_ui():
    render_header()
    st.header("🏙️ City - Verify Requests")
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

# ======================================================
# Installer UI
# ======================================================
def installer_ui():
    render_header()
    st.header("🔧 Installer - Mark Received Stock")
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

# ======================================================
# Manager UI
# ======================================================
def manager_ui():
    render_header()
    st.header("📊 Manager - Reconciliation & Export")
    df = load_data()
    st.dataframe(df, use_container_width=True)

    total = len(df)
    pending = (df["Status"] == "Pending Verification").sum()
    approved = (df["Status"].str.contains("Approved", na=False)).sum()
    declined = (df["Status"] == "Declined").sum()
    received = (df["Status"] == "Received").sum()

    st.subheader("Summary")
    st.write(f"Total: {total} | Pending: {pending} | Approved: {approved} | Declined: {declined} | Received: {received}")

    # Export CSV
    st.download_button("📥 Download CSV", data=df.to_csv(index=False), file_name="stock_requests.csv", mime="text/csv")

    # Export PDF
    if st.button("📄 Generate PDF Report"):
        pdf_path = REPORT_DIR / f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        doc = SimpleDocTemplate(str(pdf_path), pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        elems = []
        elems.append(Paragraph("<b>Smart Meter Stock Report</b>", styles['Title']))
        elems.append(Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), styles['Normal']))
        elems.append(Spacer(1, 12))
        data_summary = [
            ["Metric", "Count"],
            ["Total", total],
            ["Pending", pending],
            ["Approved", approved],
            ["Declined", declined],
            ["Received", received],
        ]
        table = Table(data_summary)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]))
        elems.append(table)
        elems.append(Spacer(1, 20))
        elems.append(Paragraph("<b>Detailed Records</b>", styles['Heading2']))
        data_table = [df.columns.tolist()] + df.values.tolist()
        t = Table(data_table, repeatRows=1)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ]))
        elems.append(t)
        doc.build(elems)
        st.success(f"PDF generated: {pdf_path.name}")
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download PDF", f, file_name=pdf_path.name)

# ======================================================
# ROUTING
# ======================================================
if not st.session_state.auth["logged_in"]:
    login_ui()
else:
    # render header and sidebar
    render_header()
    st.sidebar.write(f"Logged in as **{st.session_state.auth['name']}** ({st.session_state.auth['role']})")
    if st.sidebar.button("Logout"):
        st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None}
        safe_rerun()

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

