import streamlit as st
from PIL import Image

# ============================================
#   PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="Stock Management",
    layout="wide",
    page_icon="🟩"
)

# ============================================
#   THEME COLORS
# ============================================
ACUCOMM_GREEN = "#2e7d32"
LIGHT_GREEN = "#e8f5e9"
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
            margin-top: 60px;
        }}
        .login-box {{
            background-color: white;
            padding: 20px 40px;
            border-radius: 16px;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.1);
            width: 380px;
            margin-top: 20px;
        }}
        .stTextInput > div > div > input {{
            text-align: center;
        }}
        .login-btn > button {{
            background-color: {ACUCOMM_GREEN};
            color: white;
            border-radius: 8px;
            font-weight: 600;
            padding: 0.6em 2.5em;
            width: 60%;
            margin-top: 8px;
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
        st.image(logo, width=260)
    except Exception:
        st.warning("Logo not found — please ensure 'Acucomm logo.jpg' is in the same directory.")

    # Title and subtitle
    st.markdown(f"<h2 style='color:{ACUCOMM_GREEN}; margin-bottom:0;'>Acucomm Stock Management</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:gray; font-size:14px;'>Use your contractor / city / installer credentials to access the system.</p>", unsafe_allow_html=True)

    # Login form
    with st.form("login_form"):
        username = st.text_input("Username", key="username")
        password = st.text_input("Password", type="password", key="password")

        st.markdown("<div class='login-btn'>", unsafe_allow_html=True)
        login_btn = st.form_submit_button("Login")
        st.markdown("</div>", unsafe_allow_html=True)

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
        .card {{
            background-color: white;
            border-left: 6px solid {ACUCOMM_GREEN};
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0px 2px 6px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .card h3 {{
            margin: 0;
            color: {ACUCOMM_GREEN};
            font-size: 18px;
        }}
        .card p {{
            font-size: 22px;
            font-weight: bold;
            margin-top: 8px;
            color: #333;
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

    # KPI Cards
    st.markdown("### Key Inventory Metrics")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("<div class='card'><h3>Smart Meters</h3><p>150</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='card'><h3>Connectors</h3><p>300</p></div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='card'><h3>Cables</h3><p>120</p></div>", unsafe_allow_html=True)
    with c4:
        st.markdown("<div class='card'><h3>Panels</h3><p>45</p></div>", unsafe_allow_html=True)

    st.markdown("### Detailed Inventory Table")
    st.dataframe({
        "Item": ["Smart Meters", "Connectors", "Cables", "Panels"],
        "In Stock": [150, 300, 120, 45],
        "Dispatched": [45, 120, 30, 15],
        "Remaining": [105, 180, 90, 30]
    })

    st.success("✅ System connected successfully with Acucomm corporate theme loaded.")


# ============================================
#   PAGE LOGIC
# ============================================
if not st.session_state.logged_in:
    login_page()
else:
    dashboard()
