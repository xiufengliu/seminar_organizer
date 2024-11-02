import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
from database import SeminarDB
from datetime import datetime, time
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO)

# Initialize session state for selected seminar
if 'selected_seminar' not in st.session_state:
    st.session_state.selected_seminar = None

def time_picker(label, default_time=time(9, 0)):
    col1, col2 = st.columns(2)
    hour = col1.number_input(f"{label} (Hour)", min_value=0, max_value=23, value=default_time.hour)
    minute = col2.number_input(f"{label} (Minute)", min_value=0, max_value=59, value=default_time.minute, step=5)
    return time(hour, minute)

def validate_email(email):
    # Simple regex for validating email format
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w{2,4}$"
    return re.match(email_regex, email) is not None

def display_seminar_details(seminar):
    """Helper function to render seminar details using a container"""
    # Format date safely
    seminar_date = pd.to_datetime(seminar.get('date', 'N/A')).strftime('%Y-%m-%d') if seminar.get('date') else 'N/A'
    seminar_start_time = seminar.get('start_time', 'N/A')
    seminar_end_time = seminar.get('end_time', 'N/A')
    
    # Use st.container to group the details inside a visual frame
    with st.container():
        st.markdown(f"""
            <style>
                .seminar-details {{
                    background-color: #f0f2f6;
                    color: #000000;
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 20px;
                    border: 1px solid #ccc;
                }}
                .seminar-details h4 {{
                    color: #1f77b4;
                    margin-bottom: 15px;
                }}
                .seminar-details .label {{
                    font-weight: bold;
                    color: #2c3e50;
                }}
                .seminar-info {{
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-between;
                }}
                .seminar-info div {{
                    width: 45%;
                    margin-bottom: 10px;
                    color: #000000;
                }}
            </style>
            <div class="seminar-details">
                <h4>{seminar.get('topic', 'N/A')}</h4>
                <div class="seminar-info">
                    <div><span class="label">Time:</span> {seminar_date} {seminar_start_time} - {seminar_end_time}</div>
                    <div><span class="label">Room:</span> {seminar.get('room', 'N/A')}</div>
                    <div><span class="label">Speaker:</span> {seminar.get('speaker_name', 'N/A')}</div>
                    <div><span class="label">Email:</span> {seminar.get('speaker_email', 'N/A')}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

def display_seminars_table(seminars, title):
    """Helper function to display seminars table using AgGrid."""
    df = pd.DataFrame(seminars, columns=['id', 'date', 'start_time', 'end_time', 'speaker_name', 'speaker_email', 'speaker_bio', 'topic', 'abstract', 'room'])
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    df['start_time'] = pd.to_datetime(df['start_time'], format='%H:%M:%S').dt.strftime('%H:%M')
    df['end_time'] = pd.to_datetime(df['end_time'], format='%H:%M:%S').dt.strftime('%H:%M')
    df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['start_time'].astype(str))
    df = df.sort_values('datetime')

    gb = GridOptionsBuilder.from_dataframe(df[['id', 'date', 'start_time', 'end_time', 'topic', 'speaker_name', 'room']])
    gb.configure_column("id", width=4)
    gb.configure_column("date", width=35)
    gb.configure_column("start_time", width=35)
    gb.configure_column("end_time", width=35)
    gb.configure_column("topic", width=200, wrapText=True, autoHeight=True)
    gb.configure_column("speaker_name", width=80)
    gb.configure_column("room", width=60)
    gb.configure_selection('single', use_checkbox=False, groupSelectsChildren=True, groupSelectsFiltered=True)
    grid_options = gb.build()

    grid_response = AgGrid(
        df[['id', 'date', 'start_time', 'end_time', 'topic', 'speaker_name', 'room']],
        gridOptions=grid_options,
        height=300,
        data_return_mode='AS_INPUT',
        update_mode='SELECTION_CHANGED',
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True
    )

    selected_rows = pd.DataFrame(grid_response['selected_rows'])
    if not selected_rows.empty and 'id' in selected_rows.columns:
        selected_seminar_id = selected_rows.iloc[0]['id']
        selected_seminar = df[df['id'] == selected_seminar_id].iloc[0].to_dict()
        st.session_state.selected_seminar = selected_seminar
        logging.info(f"{title} selected: {selected_seminar['topic']}")
    else:
        st.session_state.selected_seminar = None

    if st.session_state.selected_seminar:
        display_seminar_details(st.session_state.selected_seminar)

def show():
    st.title("Seminar Calendar")
    db = SeminarDB()

    tab1, tab2, tab3 = st.tabs(["Upcoming Seminar", "Past Seminar", "Request Seminar"])

    # Upcoming Seminars Tab
    with tab1:
        seminars = db.fetch_future_seminars()
        if not seminars:
            st.warning("No upcoming seminars found.")
        else:
            display_seminars_table(seminars, "Upcoming Seminar")

    # Past Seminars Tab
    with tab2:
        past_seminars = db.fetch_past_seminars()
        if not past_seminars:
            st.warning("No past seminars found.")
        else:
            display_seminars_table(past_seminars, "Past Seminar")
    
    # Request Seminar Tab
    with tab3:
        st.subheader("Request a Seminar")
        with st.form("request_seminar_form"):
            date = st.date_input("Seminar Date *")
            start_time = time_picker("Start Time *", default_time=time(12, 0))
            end_time = time_picker("End Time *", default_time=time(13, 0))
            room = st.text_input("Preferred Meeting Room *")
            speaker_name = st.text_input("Speaker Name")
            speaker_email = st.text_input("Speaker Email")
            speaker_bio = st.text_area("Speaker Bio")
            topic = st.text_input("Topic *")
            abstract = st.text_area("Abstract")
            submitter_name = st.text_input("Your Name *")
            submitter_email = st.text_input("Your Email *")

            submit_button = st.form_submit_button("Submit Request")

        if submit_button:
            validate_and_submit_request(
                db, date, start_time, end_time, room, speaker_name, speaker_email,
                speaker_bio, topic, abstract, submitter_name, submitter_email
            )



    db.close()
