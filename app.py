iimport streamlit as st

# 1. This MUST be the first line of code
st.set_page_config(page_title="Protellect v1", layout="wide")

# 2. These are your variables
base = "dark"
primaryColor = "#00e5ff"
backgroundColor = "#04080f"
secondaryBackgroundColor = "#070d1a"
textColor = "#d0e8ff"

# 3. This applies your colors to the app
st.markdown(f"""
    <style>
    .stApp {{
        background-color: {backgroundColor};
        color: {textColor};
    }}
    </style>
    """, unsafe_allow_html=True)

# 4. Use "False" with a capital F
gatherUsageStats = False

st.title("Protellect v1")
st.write("The theme is now applied and the code is fixed.")
