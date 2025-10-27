import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import hashlib
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
import os

st.set_page_config(page_title="Smart Meter Stock Workflow", page_icon="📦", layout="wide")

# === Directories ===
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
PHOTO_DIR = ROOT / "photos"
ISSUED_PHOTOS_DIR = PHOTO_DIR / "issued"
REPORT_DIR = ROOT / "reports"
for d in [DATA_DIR, PHOTO_DIR, ISSUED_PHOTOS_DIR, REPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "stock_requests.csv"

# === Try to display Acucomm logo ===
logo_path = ROOT / "acucomm logo.jpg"
if logo_path.exists():
    st.image(str(logo_path), width=220)
else:
    st.warning("⚠️ 'acucomm logo.jpg' not found in the folder. Place it next to this .py file.")

st.title("📦 Smart Meter Stock Workflow")

# === User Database ===
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

raw_users = {
    "Deezlo": {"name": "Deezlo", "password": "Deezlo123", "role": "contractor"},
    "ethekwini": {"name": "ethekwini", "password": "ethekwini123", "role": "city"},
    "installer1": {"name": "installer1", "password": "installer123", "role": "installer"},
    "Reece": {"name": "Reece", "password": "Reece123!", "role": "manager"},
}

CREDENTIALS = {
    u: {
        "name": v["name"],
        "password_hash": hash_password(v["password"]),
        "role": v["role"],
    }
    for u, v in raw_users.items()
}

# === Utility Functions ===
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

# === Login ===
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
            st.error("Invalid credentials.")

def logout():
    st.session_state.auth = {"logged_in": False, "username": None, "role": None, "name": None}
    safe_rerun()

# === Contractor UI ===
def contractor_ui():
    st.header("👷 Contractor - Submit Stock Request")
    contractor_name = st.session_state.auth["name"]

    installer_name = st.text_input("Installer Name")

    st.subheader("Select Stock Items & Quantities")
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

# === City UI ===
def city_ui():
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

# === Installer UI ===
def installer_ui():
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

# === Manager UI ===
def manager_ui():
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

    st.download_button("📥 Download CSV", data=df.to_csv(index=False), file_name="stock_requests.csv", mime="text/csv")

    # Export PDF with logo
    if st.button("📄 Generate PDF Report"):
        pdf_path = REPORT_DIR / f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        doc = SimpleDocTemplate(str(pdf_path), pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        elems = []

        # Add logo to PDF
        if logo_path.exists():
            elems.append(Image(str(logo_path), width=100, height=50))
            elems.append(Spacer(1, 10))

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

# === Role Routing ===
if not st.session_state.auth["logged_in"]:
    login_ui()
else:
    st.sidebar.write(f"Logged in as **{st.session_state.auth['name']}** ({st.session_state.auth['role']})")
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
