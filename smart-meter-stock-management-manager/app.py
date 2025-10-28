import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

# ---------------------- PAGE SETUP ----------------------
st.set_page_config(page_title="Stock Management Dashboard", layout="wide")

# ---------------------- ENV SETUP -----------------------
ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=ROOT / ".env")

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)

# ---------------------- EMAIL FUNCTION ------------------
def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"] = FROM_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Microsoft Exchange (Office 365) SMTP
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        st.success(f"✅ Email sent to {to_email}")
    except Exception as e:
        st.error(f"❌ Email failed to send: {e}")

# ---------------------- STOCK MANAGEMENT LOGIC ----------------------

if "stock_data" not in st.session_state:
    st.session_state.stock_data = pd.DataFrame(columns=["Item", "Category", "Quantity", "Last Updated"])

st.title("📦 Acucomm Stock Management")

# --- INPUT SECTION ---
st.subheader("Add or Update Stock")

with st.form("stock_form"):
    item = st.text_input("Item Name")
    category = st.text_input("Category")
    quantity = st.number_input("Quantity", min_value=0, step=1)
    submitted = st.form_submit_button("Add / Update")

    if submitted:
        if item and category:
            existing_index = st.session_state.stock_data[st.session_state.stock_data["Item"] == item].index
            if not existing_index.empty:
                st.session_state.stock_data.loc[existing_index, ["Quantity", "Last Updated"]] = [
                    quantity,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ]
                st.success(f"Updated stock for **{item}**.")
            else:
                new_entry = pd.DataFrame(
                    [[item, category, quantity, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]],
                    columns=["Item", "Category", "Quantity", "Last Updated"],
                )
                st.session_state.stock_data = pd.concat([st.session_state.stock_data, new_entry], ignore_index=True)
                st.success(f"Added new stock item **{item}**.")
        else:
            st.warning("Please fill in all fields before submitting.")

# --- DISPLAY STOCK TABLE ---
st.subheader("Current Stock")
st.dataframe(st.session_state.stock_data, use_container_width=True)

# --- EXPORT TO PDF ---
def export_to_pdf(df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()

    title = Paragraph("Acucomm Stock Report", styles["Title"])
    elements.append(title)
    elements.append(Spacer(1, 12))

    data = [df.columns.tolist()] + df.values.tolist()
    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#004C97")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("📄 Export as PDF"):
        if not st.session_state.stock_data.empty:
            pdf_file = export_to_pdf(st.session_state.stock_data)
            st.download_button(
                label="⬇️ Download PDF Report",
                data=pdf_file,
                file_name=f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
            )
        else:
            st.warning("No data to export.")

with col2:
    email_recipient = st.text_input("Recipient Email Address")
    if st.button("📧 Email Stock Report"):
        if not email_recipient:
            st.warning("Please enter a recipient email address.")
        elif st.session_state.stock_data.empty:
            st.warning("No stock data to send.")
        else:
            body = (
                "Hello,\n\nPlease find attached the latest Acucomm Stock Report.\n\nRegards,\nAcucomm Team"
            )
            # Send confirmation email (without attachment)
            send_email(email_recipient, "Acucomm Stock Report", body)

# ---------------------- DEBUG INFO (optional) ----------------------
with st.expander("SMTP Debug Info"):
    st.write(f"Server: {SMTP_SERVER}")
    st.write(f"Port: {SMTP_PORT}")
    st.write(f"User: {SMTP_USER}")
    st.write(f"Password Loaded: {'✅' if SMTP_PASS else '❌'}")

