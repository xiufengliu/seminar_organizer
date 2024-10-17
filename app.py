import streamlit as st
from views import admin, calendar

# Set page config to hide the sidebar by default
st.set_page_config(page_title="Seminar Organizer", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS to adjust the width of the sidebar and main content
st.markdown("""
<style>
    [data-testid="stSidebar"][aria-expanded="true"] > div:first-child {
        width: 300px;
    }
    [data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
        width: 0px;
        margin-left: -300px;
    }
    [data-testid="stVerticalBlock"] {
        padding-left: 0rem;
        padding-right: 0rem;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to", ["Calendar", "Admin"])

# Main content
if selection == "Calendar":
    calendar.show()
elif selection == "Admin":
    admin.show()

# Run the selected page
if __name__ == "__main__":
    pass  # The page is already being shown based on the selection