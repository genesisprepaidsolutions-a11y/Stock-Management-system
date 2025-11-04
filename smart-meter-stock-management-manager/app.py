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
import requests  # optional for connectivity checks

# ====================================================
# === APP CONFIGURATION ===
# ====================================================
st.set_page_config(page_title="Fixed Report Details", layout="wide")

# ====================================================
# === CONSTANTS & PATHS ===
# ====================================================
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
REPORT_FILE = DATA_DIR / "report_data.csv"

# ====================================================
# === UTILITY FUNCTIONS ===
# ====================================================

def hash_password(password: str) -> str:
    """Return SHA256 hash of password."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username: str, password: str) -> bool:
    """Validate user credentials."""
    user_db = {
        "admin": hash_password("admin123"),
        "manager": hash_password("manager123"),
        "viewer": hash_password("viewer123"),
    }
    return username in user_db and user_db[username] == hash_password(password)

def load_data():
    """Load the main CSV dataset."""
    if REPORT_FILE.exists():
        try:
            df = pd.read_csv(REPORT_FILE)
            return df
        except Exception as e:
            st.error(f"Error loading report data: {e}")
            return pd.DataFrame()
    else:
        return pd.DataFrame()

def save_data(df):
    """Save the updated report data locally."""
    try:
        df.to_csv(REPORT_FILE, index=False)
    except Exception as e:
        st.error(f"Error saving data: {e}")

def send_email_notification(recipient_email, subject, body):
    """Send a basic email notification."""
    try:
        sender_email = "noreply@acureports.local"
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        # Example only: replace with your SMTP details
        # with smtplib.SMTP("smtp.yourdomain.com", 587) as server:
        #     server.starttls()
        #     server.login(sender_email, "password")
        #     server.send_message(msg)
        st.success(f"Email sent to {recipient_email} (simulated)")
    except Exception as e:
        st.error(f"Email failed: {e}")

# ====================================================
# === APP LAYOUT & STYLING ===
# ====================================================

def load_custom_css():
    st.markdown("""
        <style>
            .reportview-container { background: #F5F7FA; }
            .sidebar .sidebar-content { background: #003366; color: white; }
            h1, h2, h3 { color: #003366; }
            .stButton>button {
                background-color: #0072BC;
                color: white;
                border-radius: 8px;
                font-weight: 600;
                padding: 0.5em 1.5em;
            }
            .stButton>button:hover {
                background-color: #005A99;
                color: white;
            }
        </style>
    """, unsafe_allow_html=True)

load_custom_css()

# ====================================================
# === MAIN FUNCTIONALITY ===
# ====================================================

def display_dashboard(username):
    st.title("Fixed Report Details Dashboard")

    df = load_data()

    # Upload CSV
    uploaded_file = st.file_uploader("Upload updated CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        save_data(df)
        st.success("Data uploaded and saved successfully!")

    if df.empty:
        st.info("No report data available yet.")
        return

    # Table view
    st.subheader("Report Summary")
    st.dataframe(df)

    # Data edit section
    with st.expander("Add or Edit Record"):
        new_record = {}
        for col in ["Date_Requested", "Request_ID", "Contractor_Name", "Installer_Name", "Meter_Type", "Requested_Qty", "Approved_Qty", "Status", "Contractor_Notes"]:
            new_record[col] = st.text_input(f"{col}", value="")

        if st.button("Add Record"):
            df = df.append(new_record, ignore_index=True)
            save_data(df)
            st.success("Record added successfully.")

    # Download CSV
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Report as CSV",
        data=csv_data,
        file_name="report_data.csv",
        mime="text/csv"
    )

    # Email Simulation
    st.subheader("Send Email Notification")
    email_recipient = st.text_input("Recipient Email")
    email_subject = st.text_input("Subject")
    email_body = st.text_area("Message")

    if st.button("Send Email"):
        if email_recipient and email_subject:
            send_email_notification(email_recipient, email_subject, email_body)
        else:
            st.warning("Please enter recipient and subject.")

# ====================================================
# === LOGIN INTERFACE ===
# ====================================================

def login_page():
    st.markdown("<h2 style='text-align:center;'>Login Portal</h2>", unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            if verify_login(username, password):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")

# ====================================================
# === MAIN APP LOGIC ===
# ====================================================

def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if st.session_state["logged_in"]:
        col1, col2 = st.columns([10, 1])
        with col2:
            if st.button("Logout"):
                st.session_state["logged_in"] = False
                st.experimental_rerun()
        display_dashboard(st.session_state["username"])
    else:
        login_page()

if __name__ == "__main__":
    main()
