import streamlit as st

# This function handles your theme and page settings properly
st.set_page_config(
    page_title="Protellect v1",
    layout="wide",
    initial_sidebar_state="expanded",
)

# If you want to add custom CSS to match your colors:
st.markdown(f"""
    <style>
    .stApp {{
        background-color: #04080f;
        color: #d0e8ff;
    }}
    </style>
    """, unsafe_allow_value=True)

st.title("Protellect v1")
st.write("App is now running correctly!")

# Add the rest of your app logic below this line
