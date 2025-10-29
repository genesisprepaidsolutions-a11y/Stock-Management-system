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
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ====================================================
# === PAGE CONFIG ===
# ====================================================
st.set_page_config(
    page_title="Smart Meter Stock Management System",
    page_icon="favicon.jpg",  # ✅ Favicon file
    layout="wide"
)

# ====================================================
# === HEADER ===
# ====================================================
st.markdown(
    """
    <h2 style='text-align: center; color: #003366;'>
        eThekwini Municipality | Smart Meter Stock Management System
    </h2>
    """,
    unsafe_allow_html=True
)

# ====================================================
# === FILE UPLOAD & HASH HANDLING ===
# ====================================================
uploaded_file = st.file_uploader("Upload Stock File", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("File uploaded successfully!")

    st.dataframe(df)

    # Example stock summary
    st.subheader("Stock Overview")
    st.write(f"Total Stock Items: {len(df)}")

# ====================================================
# === EMAIL NOTIFICATION FUNCTION (MS Exchange) ===
# ====================================================
def send_email(recipient, subject, body):
    try:
        sender_email = "youremail@ethekwini.gov.za"  # change this to your email
        smtp_server = "smtp.office365.com"
        smtp_port = 587
        password = "your_password_here"  # use a secure method for real deployment

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)

        st.success(f"Email sent successfully to {recipient}!")

    except Exception as e:
        st.error(f"Error sending email: {e}")

# ====================================================
# === PDF EXPORT EXAMPLE ===
# ====================================================
def export_pdf(dataframe):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("Smart Meter Stock Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    table_data = [list(dataframe.columns)] + dataframe.values.tolist()
    table = Table(table_data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    doc.build(elements)
    return buffer

# ====================================================
# === PDF DOWNLOAD BUTTON ===
# ====================================================
if uploaded_file:
    if st.button("Export as PDF"):
        pdf_buffer = export_pdf(df)
        st.download_button(
            label="Download PDF Report",
            data=pdf_buffer,
            file_name=f"Smart_Meter_Stock_Report_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )

# ====================================================
# === FOOTER (Dark Blue, White Text) ===
# ====================================================
st.markdown(f"""
    <style>
        .footer {{
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            background-color: #003366; /* Dark Blue */
            color: white; /* White Text */
            text-align: center;
            padding: 10px 0;
            font-size: 14px;
            border-top: 2px solid #002244;
            z-index: 100;
        }}
    </style>
    <div class="footer">
        © {datetime.now().year} eThekwini Municipality | Smart Meter Stock Management System
    </div>
""", unsafe_allow_html=True)
