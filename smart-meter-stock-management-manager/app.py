
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
from PIL import Image
import os

st.set_page_config(page_title="Acucomm Stock Management", page_icon="assets/acucomm_logo.jpg", layout="wide")

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
DATA_DIR = ROOT / "data"
PHOTO_DIR = ROOT / "photos"
ISSUED_PHOTOS_DIR = PHOTO_DIR / "issued"
REPORT_DIR = ROOT / "reports"
for d in [DATA_DIR, PHOTO_DIR, ISSUED_PHOTOS_DIR, REPORT_DIR, ASSETS]:
    d.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "stock_requests.csv"

# branding colors
PRIMARY = "#6BBE44"
DARK = "#2B6C3D"
ACCENT = "#A1D884"
BG = "#F5F8F5"

# load logo
logo_path = ASSETS / "acucomm_logo.jpg"
if logo_path.exists():
    logo = Image.open(logo_path)
else:
    logo = None

# users
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

raw_users = {
    "Deezlo": {"name": "Deezlo", "password": "Deezlo123", "role": "contractor"},
    "ethekwini": {"name": "ethekwini", "password": "ethwkwini123", "role": "city"},
    "installer1": {"name": "installer1", "password": "installer123", "role": "installer"},
    "Reece": {"name": "Reece", "password": "Reece123!", "role": "manager"},
}

CREDENTIALS = {}
for u,v in raw_users.items():
    CREDENTIALS[u] = {"name": v["name"], "password_hash": hash_password(v["password"]), "role": v["role"]}

# helpers
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
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_FILE, index=False)

def generate_request_id():
    return "REQ-" + datetime.now().strftime("%Y%m%d%H%M%S")

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None}

def safe_rerun():
    try:
        st.rerun()
    except Exception:
        pass

# CSS
st.markdown(f"""<style>
.sidebar .sidebar-content {{
    background-color: {BG};
}}
.stButton>button {{
    background: linear-gradient(90deg, {PRIMARY}, {ACCENT});
    color: white;
    border: none;
}}
.card {{
    background: white;
    border-radius:8px;
    padding:12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}}
</style>""", unsafe_allow_html=True)

# header
col1, col2 = st.columns([1,6])
with col1:
    if logo:
        st.image(logo, width=120)
with col2:
    st.markdown(f"""<div style='padding-top:20px'>
        <h1 style='margin:0;color:{DARK};'>Acucomm Stock Management</h1>
        <div style='color: #666;'>Manage stock requests, approvals and reconciliations</div>
    </div>""", unsafe_allow_html=True)

# login UI
def login_ui():
    st.sidebar.header("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username in CREDENTIALS and hash_password(password) == CREDENTIALS[username]["password_hash"]:
            st.session_state.auth.update({
                "logged_in": True,
                "username": username,
                "role": CREDENTIALS[username]["role"],
                "name": CREDENTIALS[username]["name"]
            })
            safe_rerun()
        else:
            st.sidebar.error("Invalid credentials.")

def logout():
    st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None}
    safe_rerun()

# contractor UI
def contractor_ui():
    st.subheader("👷 Contractor — Submit Stock Request")
    contractor_name = st.session_state.auth["name"]
    installer_name = st.text_input("Installer Name")
    st.markdown("""<div class='card'><strong>Select stock items and quantities</strong></div>""", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        meter_qty = st.number_input("DN15 Meter Quantity", min_value=0, value=0, step=1)
    with col2:
        keypad_qty = st.number_input("CIU Keypad Quantity", min_value=0, value=0, step=1)
    notes = st.text_area("Notes")

    if st.button("Submit Request"):
        if not installer_name:
            st.warning("Please enter installer name")
        elif meter_qty == 0 and keypad_qty == 0:
            st.warning("Please request at least one item.")
        else:
            df = load_data()
            base_id = generate_request_id()
            if meter_qty > 0:
                df = pd.concat([df, pd.DataFrame([{
                    "Date_Requested": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Request_ID": base_id + "-M",
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
            if keypad_qty > 0:
                df = pd.concat([df, pd.DataFrame([{
                    "Date_Requested": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Request_ID": base_id + "-K",
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
            st.success("Request(s) submitted under base ID " + base_id)

    st.markdown("---")
    st.subheader("📋 My Requests")
    df = load_data()
    st.dataframe(df[df["Contractor_Name"] == contractor_name].sort_values(by="Date_Requested", ascending=False), use_container_width=True)

# city UI
def city_ui():
    st.subheader("🏙️ City — Verify Requests")
    df = load_data()
    pending = df[df["Status"] == "Pending Verification"].sort_values(by="Date_Requested")
    st.dataframe(pending, use_container_width=True)
    sel = st.selectbox("Select Request ID", [""] + pending["Request_ID"].tolist())
    if sel:
        row = df[df["Request_ID"] == sel].iloc[0]
        st.write(row.to_dict())
        qty = st.number_input("Approved Qty", 0, value=int(row["Requested_Qty"]))
        photo = st.file_uploader("Upload proof photo", type=["jpg", "png"])
        notes = st.text_area("Notes")
        decline_reason = st.text_input("Decline reason")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Approve"):
                df.loc[df["Request_ID"] == sel, "Approved_Qty"] = qty
                ppath = ""
                if photo:
                    dest = ISSUED_PHOTOS_DIR / f"{sel}_{photo.name}"
                    with open(dest, "wb") as f:
                        f.write(photo.getbuffer())
                    ppath = str(dest)
                df.loc[df["Request_ID"] == sel, "Photo_Path"] = ppath
                df.loc[df["Request_ID"] == sel, "Status"] = "Approved / Issued"
                df.loc[df["Request_ID"] == sel, "City_Notes"] = notes
                df.loc[df["Request_ID"] == sel, "Date_Approved"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_data(df)
                st.success("Approved and issued.")
                safe_rerun()
        with col2:
            if st.button("Decline"):
                if not decline_reason:
                    st.warning("Provide a reason to decline.")
                else:
                    df.loc[df["Request_ID"] == sel, "Status"] = "Declined"
                    df.loc[df["Request_ID"] == sel, "Decline_Reason"] = decline_reason
                    df.loc[df["Request_ID"] == sel, "City_Notes"] = notes
                    save_data(df)
                    st.error("Declined.")
                    safe_rerun()

# installer UI
def installer_ui():
    st.subheader("🔧 Installer — Mark Received Stock")
    df = load_data()
    installer = st.session_state.auth["name"].strip().lower()
    assigned = df[df["Installer_Name"].str.lower() == installer]
    assigned = assigned[assigned["Status"].str.contains("Approved", na=False)]
    st.dataframe(assigned.sort_values(by="Date_Approved", ascending=False), use_container_width=True)
    sel = st.selectbox("Mark as received (Request ID)", [""] + assigned["Request_ID"].tolist())
    if sel and st.button("Mark as Received"):
        df.loc[df["Request_ID"] == sel, "Status"] = "Received"
        df.loc[df["Request_ID"] == sel, "Date_Received"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_data(df)
        st.success(f"Request {sel} marked as received.")
        safe_rerun()

# manager UI
def manager_ui():
    st.subheader("📊 Manager — Reconciliation & Export")
    df = load_data()
    st.dataframe(df.sort_values(by="Date_Requested", ascending=False), use_container_width=True)
    total = len(df)
    pending = (df["Status"] == "Pending Verification").sum()
    approved = (df["Status"].str.contains("Approved", na=False)).sum()
    declined = (df["Status"] == "Declined").sum()
    received = (df["Status"] == "Received").sum()
    st.markdown(f"**Summary** — Total: {total} | Pending: {pending} | Approved: {approved} | Declined: {declined} | Received: {received}")

    st.download_button("📥 Download CSV", data=df.to_csv(index=False), file_name="stock_requests.csv", mime="text/csv")

    if st.button("📄 Generate PDF Report"):
        pdf_path = REPORT_DIR / f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        doc = SimpleDocTemplate(str(pdf_path), pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        elems = []
        elems.append(Paragraph("<b>Acucomm Stock Report</b>", styles['Title']))
        elems.append(Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), styles['Normal']))
        elems.append(Spacer(1, 12))
        data_summary = [["Metric", "Count"], ["Total", total], ["Pending", pending], ["Approved", approved], ["Declined", declined], ["Received", received]]
        table = Table(data_summary)
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.grey), ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                                   ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("GRID", (0, 0), (-1, -1), 1, colors.black)]))
        elems.append(table)
        elems.append(Spacer(1, 20))
        elems.append(Paragraph("<b>Detailed Records</b>", styles['Heading2']))
        data_table = [df.columns.tolist()] + df.values.tolist()
        t = Table(data_table, repeatRows=1)
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.black), ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey)]))
        elems.append(t)
        doc.build(elems)
        st.success(f"PDF generated: {pdf_path.name}")
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download PDF", f, file_name=pdf_path.name)

# main
if not st.session_state.auth["logged_in"]:
    login_ui()
else:
    st.sidebar.markdown(f"<div style='text-align:center;padding:8px'><img src='assets/acucomm_logo.jpg' width=160/></div>", unsafe_allow_html=True)
    st.sidebar.write(f"Signed in as **{st.session_state.auth['name']}**  
Role: **{st.session_state.auth['role']}**")
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
