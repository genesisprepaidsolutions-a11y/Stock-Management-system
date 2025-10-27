import streamlit as st
from PIL import Image

# ============================================
#   PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="Acucomm Stock Management",
    layout="wide",
    page_icon="🟩"
)

# ============================================
#   THEME COLORS
# ============================================
ACUCOMM_GREEN = "#2e7d32"
BACKGROUND_COLOR = "#f9f9f9"

# ============================================
#   SESSION STATE SETUP
# ============================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


# ============================================
#   LOGIN PAGE
# ============================================
def login_page():
    st.markdown(
        f"""
        <style>
        body {{
            background-color: {BACKGROUND_COLOR};
        }}
        .main {{
            display: flex;
            justify-content: center;
            align-items: center;
            flex-direction: column;
            text-align: center;
            margin-top: 80px;
        }}
        .login-box {{
            background-color: white;
            padding: 40px 60px;
            border-radius: 20px;
            box-shadow: 0px 4px 20px rgba(0,0,0,0.1);
            width: 450px;
        }}
        .login-input {{
            width: 80% !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }}
        .stTextInput > div > div > input {{
            text-align: center;
        }}
        .login-btn > button {{
            background-color: {ACUCOMM_GREEN};
            color: white;
            border-radius: 8px;
            font-weight: 600;
            padding: 0.6em 2em;
            width: 50%;
            margin-top: 15px;
            transition: 0.3s ease-in-out;
        }}
        .login-btn > button:hover {{
            background-color: #256428;
            transform: scale(1.05);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Load and display Acucomm logo
    try:
        logo = Image.open("Acucomm logo.jpg")
        st.image(logo, width=250)
    except Exception:
        st.warning("Logo not found — please ensure 'Acucomm logo.jpg' is in the same directory.")

    st.markdown(f"<h2 style='color:{ACUCOMM_GREEN}; margin-bottom:0;'>Acucomm Stock Management</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:gray; font-size:14px;'>Use your contractor / city / installer credentials to access the system.</p>", unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username", key="username")
        password = st.text_input("Password", type="password", key="password")

        login_btn = st.form_submit_button("Login")

        if login_btn:
            if username.strip() != "" and password.strip() != "":
                st.session_state.logged_in = True
                st.session_state.username = username
                st.experimental_rerun()
            else:
                st.error("Please enter both username and password.")


# ============================================
#   DASHBOARD PAGE
# ============================================
def dashboard():
    st.markdown(
        f"""
        <style>
        .main-header {{
            font-size: 28px;
            font-weight: 700;
            color: {ACUCOMM_GREEN};
            text-align: left;
            padding-bottom: 10px;
            border-bottom: 2px solid {ACUCOMM_GREEN};
            margin-bottom: 20px;
        }}
        .logout-btn > button {{
            background-color: {ACUCOMM_GREEN};
            color: white;
            border-radius: 8px;
            font-weight: 600;
            padding: 0.5em 1.5em;
            transition: 0.3s ease-in-out;
        }}
        .logout-btn > button:hover {{
            background-color: #256428;
            transform: scale(1.05);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background-color: {ACUCOMM_GREEN};
            color: white;
            padding: 10px;
            text-align: left;
        }}
        td {{
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Header and Logout button
    col1, col2 = st.columns([8, 1])
    with col1:
        st.markdown("<div class='main-header'>Acucomm Dashboard</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='logout-btn'>", unsafe_allow_html=True)
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.experimental_rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Dashboard content
    st.markdown("### Inventory Summary")
    st.dataframe({
        "Item": ["Smart Meters", "Connectors", "Cables", "Panels"],
        "In Stock": [150, 300, 120, 45],
        "Dispatched": [45, 120, 30, 15],
        "Remaining": [105, 180, 90, 30]
    })

    st.success("✅ System connected successfully with Acucomm theme loaded.")


# ============================================
#   PAGE LOGIC
# ============================================
if not st.session_state.logged_in:
    login_page()
else:
    dashboard()
