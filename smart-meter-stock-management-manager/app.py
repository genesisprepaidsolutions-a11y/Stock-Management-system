# app.py
import os
import smtplib
import ssl
import mimetypes
from email.message import EmailMessage
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Acucomm Stock Management", page_icon="📦", layout="wide")

# === Directories ===
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
PHOTO_DIR = ROOT / "photos"
ISSUED_PHOTOS_DIR = PHOTO_DIR / "issued"
REPORT_DIR = ROOT / "reports"
for d in [DATA_DIR, PHOTO_DIR, ISSUED_PHOTOS_DIR, REPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "stock_requests.csv"
USERS_FILE = DATA_DIR / "users.csv"

# === Display Logo ===
logo_path = ROOT / "Acucomm logo.jpg"
if logo_path.exists():
    st.image(str(logo_path), use_container_width=False, width=220)
st.markdown("<h1 style='text-align: center;'>Stock Management</h1>", unsafe_allow_html=True)
st.markdown("---")

# === SMTP / Email config (from environment) ===
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)

SMTP_CONFIGURED = bool(SMTP_SERVER and SMTP_USER and SMTP_PASS)

# === Email helper ===
def send_email(to_email: str, subject: str, body: str, attachment_path: str = None):
    """
    Sends an email via SMTP using environment credentials.
    Returns (True, "Sent") on success, (False, error_message) otherwise.
    """
    if not SMTP_CONFIGURED:
        return False, "SMTP not configured"

    msg = EmailMessage()
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    if attachment_path and Path(attachment_path).exists():
        try:
            with open(attachment_path, "rb") as f:
                data = f.read()
            ctype, encoding = mimetypes.guess_type(attachment_path)
            if ctype is None:
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=Path(attachment_path).name)
        except Exception as e:
            return False, f"Attachment error: {e}"

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True, "Sent"
    except Exception as e:
        return False, str(e)

# === Users file management ===
def ensure_sample_users():
    """Create a sample users.csv if none exists to make testing easy."""
    if not USERS_FILE.exists():
        sample = pd.DataFrame([
            {"email": "deezlo@acucomm.com", "name": "Deezlo", "role": "contractor"},
            {"email": "city@acucomm.com", "name": "ethekwini", "role": "city"},
            {"email": "installer1@acucomm.com", "name": "installer1", "role": "installer"},
            {"email": "manager@acucomm.com", "name": "Reece", "role": "manager"},
        ])
        sample.to_csv(USERS_FILE, index=False)

def load_users_df():
    ensure_sample_users()
    try:
        df = pd.read_csv(USERS_FILE, dtype=str).fillna("")
        # normalize columns
        expected = {"email", "name", "role"}
        if not expected.issubset(set(df.columns)):
            # if format wrong, create minimal empty frame
            st.warning("users.csv missing required columns. Expected columns: email,name,role")
            return pd.DataFrame(columns=["email", "name", "role"])
        return df
    except Exception as e:
        st.error(f"Failed to read users file: {e}")
        return pd.DataFrame(columns=["email", "name", "role"])

users_df = load_users_df()

def find_user_by_email(email: str):
    email = (email or "").strip().lower()
    if email == "":
        return None
    match = users_df[users_df["email"].str.lower() == email]
    if not match.empty:
        row = match.iloc[0]
        return {"email": row["email"], "name": row["name"], "role": row["role"]}
    return None

def find_email_by_name(name: str):
    name = (name or "").strip()
    if name == "":
        return None
    match = users_df[users_df["name"].str.lower() == name.lower()]
    if not match.empty:
        return match.iloc[0]["email"]
    return None

def find_first_email_by_role(role: str):
    role = (role or "").strip().lower()
    match = users_df[users_df["role"].str.lower() == role]
    if not match.empty:
        return match.iloc[0]["email"]
    return None

# === Data file functions ===
def load_data():
    if DATA_FILE.exists():
        try:
            return pd.read_csv(DATA_FILE, dtype=str).fillna("")
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

# === Session auth ===
if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "email": None, "role": None, "name": None}

def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        pass

# === Login UI (email-only) ===
def login_ui():
    st.sidebar.header("🔐 Sign in")
    st.sidebar.write("Enter your work email to continue.")
    email = st.sidebar.text_input("Email", value="", key="login_email")
    if st.sidebar.button("Sign in"):
        user = find_user_by_email(email)
        if user:
            st.session_state.auth.update({
                "logged_in": True,
                "email": user["email"],
                "name": user["name"],
                "role": user["role"]
            })
            st.sidebar.success(f"Signed in as {user['name']} ({user['role']})")
            safe_rerun()
        else:
            st.sidebar.error("Email not recognized. Please contact admin or add your email to data/users.csv.")

def logout():
    st.session_state.auth = {"logged_in": False, "email": None, "role": None, "name": None}
    safe_rerun()

# === Notification helpers (use users_df to find emails) ===
def notify_city_new_request(request_row):
    city_email = find_first_email_by_role("city")
    if not city_email:
        return False, "No city email configured in users.csv"
    subject = f"[Acucomm] New Stock Request {request_row['Request_ID']}"
    body = f"""New stock request submitted.

Request ID: {request_row['Request_ID']}
Contractor: {request_row['Contractor_Name']}
Installer: {request_row['Installer_Name']}
Item: {request_row['Meter_Type']}
Requested Qty: {request_row['Requested_Qty']}
Notes: {request_row.get('Contractor_Notes','')}

Please review and approve/decline in the Acucomm Stock Management app.
"""
    return send_email(city_email, subject, body, None)

def notify_installer_on_approval(request_row):
    installer_name = request_row.get("Installer_Name", "")
    installer_email = find_email_by_name(installer_name)
    if not installer_email:
        return False, "Installer email not found in users.csv"
    subject = f"[Acucomm] Stock Approved {request_row['Request_ID']}"
    body = f"""Your request has been approved and issued.

Request ID: {request_row['Request_ID']}
Item: {request_row['Meter_Type']}
Approved Qty: {request_row.get('Approved_Qty','')}
City Notes: {request_row.get('City_Notes','')}

Please mark as received in the Acucomm Stock Management app once you have received the items.
"""
    attach = request_row.get("Photo_Path") if request_row.get("Photo_Path") else None
    return send_email(installer_email, subject, body, attach)

def notify_installer_on_decline(request_row):
    installer_name = request_row.get("Installer_Name", "")
    installer_email = find_email_by_name(installer_name)
    if not installer_email:
        return False, "Installer email not found in users.csv"
    subject = f"[Acucomm] Stock Declined {request_row['Request_ID']}"
    body = f"""Your request was declined.

Request ID: {request_row['Request_ID']}
Decline Reason: {request_row.get('Decline_Reason','')}

Please contact the city for more information.
"""
    return send_email(installer_email, subject, body, None)

def notify_manager_on_received(request_row):
    manager_email = find_first_email_by_role("manager")
    if not manager_email:
        return False, "No manager email configured in users.csv"
    subject = f"[Acucomm] Stock Received {request_row['Request_ID']}"
    body = f"""Installer has marked the stock as received.

Request ID: {request_row['Request_ID']}
Installer: {request_row['Installer_Name']}
Item: {request_row['Meter_Type']}
Qty Received: {request_row.get('Approved_Qty','')}
Date Received: {request_row.get('Date_Received','')}

Please review reconciliation in the Acucomm Stock Management app.
"""
    return send_email(manager_email, subject, body, None)

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
            rid_base = generate_request_id()
            created_ids = []

            if meter_qty > 0:
                row = {
                    "Date_Requested": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Request_ID": f"{rid_base}-M",
                    "Contractor_Name": contractor_name,
                    "Installer_Name": installer_name,
                    "Meter_Type": "DN15 Meter",
                    "Requested_Qty": str(meter_qty),
                    "Approved_Qty": "",
                    "Photo_Path": "",
                    "Status": "Pending Verification",
                    "Contractor_Notes": notes,
                    "City_Notes": "",
                    "Decline_Reason": "",
                    "Date_Approved": "",
                    "Date_Received": "",
                }
                df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                created_ids.append(row["Request_ID"])

            if keypad_qty > 0:
                row = {
                    "Date_Requested": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Request_ID": f"{rid_base}-K",
                    "Contractor_Name": contractor_name,
                    "Installer_Name": installer_name,
                    "Meter_Type": "CIU Keypad",
                    "Requested_Qty": str(keypad_qty),
                    "Approved_Qty": "",
                    "Photo_Path": "",
                    "Status": "Pending Verification",
                    "Contractor_Notes": notes,
                    "City_Notes": "",
                    "Decline_Reason": "",
                    "Date_Approved": "",
                    "Date_Received": "",
                }
                df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                created_ids.append(row["Request_ID"])

            save_data(df)
            st.success(f"✅ Request(s) submitted under base ID {rid_base}")

            # notify city
            for reqid in created_ids:
                req_row = df[df["Request_ID"] == reqid].iloc[0]
                ok, msg = notify_city_new_request(req_row)
                if ok:
                    st.info(f"City notified about {reqid}")
                else:
                    st.warning(f"City notification skipped for {reqid}: {msg}")

    st.subheader("📋 My Requests")
    df = load_data()
    myreq = df[df["Contractor_Name"].str.lower() == contractor_name.lower()]
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
        try:
            current_requested = int(row.get("Requested_Qty", "0") or 0)
        except:
            current_requested = 0
        qty = st.number_input("Approved Qty", min_value=0, value=current_requested)
        photo = st.file_uploader("Upload proof photo", type=["jpg", "png"])
        notes = st.text_area("Notes")
        decline_reason = st.text_input("Decline reason")

        if st.button("Approve"):
            df.loc[df["Request_ID"] == sel, "Approved_Qty"] = str(qty)
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

            req_row = df[df["Request_ID"] == sel].iloc[0]
            ok, msg = notify_installer_on_approval(req_row)
            if ok:
                st.info(f"Installer {req_row['Installer_Name']} notified for {sel}")
            else:
                st.warning(f"Installer notification skipped for {sel}: {msg}")
            safe_rerun()

        if st.button("Decline"):
            df.loc[df["Request_ID"] == sel, "Status"] = "Declined"
            df.loc[df["Request_ID"] == sel, "Decline_Reason"] = decline_reason
            save_data(df)
            st.error("❌ Declined.")

            req_row = df[df["Request_ID"] == sel].iloc[0]
            ok, msg = notify_installer_on_decline(req_row)
            if ok:
                st.info(f"Installer {req_row['Installer_Name']} notified about decline for {sel}")
            else:
                st.warning(f"Installer decline notification skipped: {msg}")
            safe_rerun()

# === Installer UI ===
def installer_ui():
    st.header("🔧 Installer - Mark Received Stock")
    df = load_data()
    installer_name = st.session_state.auth["name"]
    approved = df[df["Installer_Name"].str.lower() == installer_name.lower()]
    approved = approved[approved["Status"].str.contains("Approved", na=False)]
    st.dataframe(approved, use_container_width=True)

    sel = st.selectbox("Mark as received (Request ID)", [""] + approved["Request_ID"].tolist())
    if sel and st.button("✅ Mark as Received"):
        df.loc[df["Request_ID"] == sel, "Status"] = "Received"
        df.loc[df["Request_ID"] == sel, "Date_Received"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_data(df)
        st.success(f"Request {sel} marked as received.")

        req_row = df[df["Request_ID"] == sel].iloc[0]
        ok, msg = notify_manager_on_received(req_row)
        if ok:
            st.info(f"Manager notified about {sel}")
        else:
            st.warning(f"Manager notification skipped: {msg}")
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

    if st.button("📄 Generate PDF Report"):
        pdf_path = REPORT_DIR / f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        doc = SimpleDocTemplate(str(pdf_path), pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        elems = []

        if logo_path.exists():
            elems.append(Image(str(logo_path), width=120, height=60))
            elems.append(Spacer(1, 6))

        elems.append(Paragraph("<b>Acucomm - Stock Report</b>", styles['Title']))
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

# === Role routing (email-auth) ===
if not st.session_state.auth["logged_in"]:
    login_ui()
else:
    st.sidebar.write(f"Signed in as **{st.session_state.auth['name']}** ({st.session_state.auth['role']})")
    if st.sidebar.button("Logout"):
        logout()

    role = (st.session_state.auth.get("role") or "").lower()
    if role == "contractor":
        contractor_ui()
    elif role == "city":
        city_ui()
    elif role == "installer":
        installer_ui()
    elif role == "manager":
        manager_ui()
    else:
        st.error("Unknown role. Check users.csv for valid roles (contractor, city, installer, manager).")
