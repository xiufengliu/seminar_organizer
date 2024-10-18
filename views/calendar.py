import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
from database import SeminarDB
from datetime import datetime, time
import logging

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

def show():
    st.title("Seminar Calendar")
    db = SeminarDB()

    tab1, tab2 = st.tabs(["Seminar Schedule", "Request Seminar"])

    with tab1:
        seminars = db.fetch_future_seminars()
        
        if not seminars:
            st.warning("No upcoming seminars found.")
        else:
            df = pd.DataFrame(seminars, columns=['id', 'date', 'start_time', 'end_time', 'speaker_name', 'speaker_email', 'speaker_bio', 'topic', 'abstract', 'room'])
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')  # Show only date in format: DD/MM/YYYY
            df['start_time'] = pd.to_datetime(df['start_time'], format='%H:%M:%S').dt.strftime('%H:%M')  # Strip seconds
            df['end_time'] = pd.to_datetime(df['end_time'], format='%H:%M:%S').dt.strftime('%H:%M')  # Strip seconds
            df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['start_time'].astype(str))
            df = df.sort_values('datetime')

            # Ensure 'id' is included in the AgGrid table for selection purposes
            gb = GridOptionsBuilder.from_dataframe(df[['id', 'date', 'start_time', 'end_time', 'topic', 'speaker_name', 'room']])

            # Configure the width of each column
            gb.configure_column("id", width=15)            # Small width for 'id'
            gb.configure_column("date", width=35)         # Smaller width for 'date'
            gb.configure_column("start_time", width=35)    # Small width for 'start_time'
            gb.configure_column("end_time", width=35)      # Small width for 'end_time'
            gb.configure_column("topic", width=350)        # Larger width for 'topic'
            gb.configure_column("speaker_name", width=100) # Normal width for 'speaker_name'
            gb.configure_column("room", width=40)         # Normal width for 'room'

            # Build the grid options
            gb.configure_selection('single', use_checkbox=False, groupSelectsChildren=True, groupSelectsFiltered=True)
            gb.configure_grid_options(domLayout='normal')
            grid_options = gb.build()

            # AgGrid Table
            grid_response = AgGrid(
                df[['id', 'date', 'start_time', 'end_time', 'topic', 'speaker_name', 'room']],
                gridOptions=grid_options,
                height=300,
                data_return_mode='AS_INPUT', 
                update_mode='SELECTION_CHANGED',
                fit_columns_on_grid_load=True,
                allow_unsafe_jscode=True
            )
            selected_rows = grid_response['selected_rows']


            if selected_rows is not None and not selected_rows.empty and 'id' in selected_rows.columns:
                # Retrieve the 'id' of the selected seminar
                selected_seminar_id = selected_rows.iloc[0]['id']

                # Use the selected seminar ID to get full seminar details from the original DataFrame
                selected_seminar = df[df['id'] == selected_seminar_id].iloc[0].to_dict()
                st.session_state.selected_seminar = selected_seminar
            else:
                st.session_state.selected_seminar = None

            # Display seminar details if a seminar is selected
            if st.session_state.selected_seminar is not None:
                seminar = st.session_state.selected_seminar
                seminar_date = pd.to_datetime(seminar['date']).strftime('%Y-%m-%d')  # Format date to YYYY-MM-DD
                seminar_start_time = seminar['start_time']  # Already formatted in AgGrid
                seminar_end_time = seminar['end_time']
                with st.container():
                    st.markdown(f"""
                            <style>
                                .seminar-details {{
                                    background-color: #f0f2f6;
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
                                }}
                                .speaker-abstract-container {{
                                    display: flex;
                                    justify-content: space-between;
                                    gap: 10px;
                                }}
                                .speaker-abstract-container div {{
                                    width: 48%;
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

                    col1, col2 = st.columns(2)
                    with col1:
                        with st.expander("", expanded=True):
                            st.markdown(f"""
                            <div style='background-color: white; padding: 0px; border-radius: 5px;'>
                                <h4 style='color: #1f77b4; margin-bottom: 10px;'>Speaker Bio</h4>
                                {seminar.get('speaker_bio', 'No bio available.')}
                            </div>
                            """, unsafe_allow_html=True)

                    with col2:
                        with st.expander("", expanded=True):
                            st.markdown(f"""
                            <div style='background-color: white; padding: 0px; border-radius: 5px;'>
                                <h4 style='color: #1f77b4; margin-bottom: 10px;'>Abstract</h4>
                                {seminar.get('abstract', 'No abstract available.')}
                            </div>
                            """, unsafe_allow_html=True)


    with tab2:
        st.subheader("Request a Seminar")
        with st.form("request_seminar_form"):
            # Mandatory fields with red asterisks
            date = st.date_input("Seminar Date *")  # Seminar date is mandatory
            start_time = time_picker("Start Time *", default_time=time(12, 0))  # Start time is mandatory
            end_time = time_picker("End Time *", default_time=time(13, 0))  # End time is mandatory
            room = st.text_input("Preferred Meeting Room *")  # Mandatory field
            speaker_name = st.text_input("Speaker Name")  # Optional
            speaker_email = st.text_input("Speaker Email")  # Optional
            speaker_bio = st.text_area("Speaker Bio")  # Optional
            topic = st.text_input("Topic *")  # Mandatory field
            abstract = st.text_area("Abstract")
            
            st.markdown("--------------")
            submitter_name = st.text_input("Your Name *")  # Mandatory field
            submitter_email = st.text_input("Your Email *")  # Mandatory field
            
            submit_button = st.form_submit_button("Submit Request")

        # Validation when form is submitted
        if submit_button:
            # Check if all mandatory fields are filled
            if not date or not start_time or not end_time or not room or not topic or not submitter_name or not submitter_email:
                st.error("Please fill in all mandatory fields marked with *")
            else:
                success, message = db.create_seminar_request(
                    str(date), start_time.strftime("%H:%M:%S"), end_time.strftime("%H:%M:%S"),
                    speaker_name, speaker_email, speaker_bio, topic, abstract, room,
                    submitter_name, submitter_email
                )
                if success:
                    st.success(message)
                else:
                    st.warning(message)


    db.close()