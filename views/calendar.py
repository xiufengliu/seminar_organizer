import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
from database import SeminarDB
from datetime import time

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
            df['date'] = pd.to_datetime(df['date'])
            df['start_time'] = pd.to_datetime(df['start_time'], format='%H:%M:%S').dt.time
            df['end_time'] = pd.to_datetime(df['end_time'], format='%H:%M:%S').dt.time
            df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['start_time'].astype(str))
            df = df.sort_values('datetime')

            # Build AgGrid table
            gb = GridOptionsBuilder.from_dataframe(df[['date', 'start_time', 'end_time', 'topic', 'speaker_name', 'room']])
            gb.configure_selection('single', use_checkbox=True, groupSelectsChildren=True, groupSelectsFiltered=True)
            gb.configure_grid_options(domLayout='normal')
            grid_options = gb.build()

            grid_response = AgGrid(
                df[['date', 'start_time', 'end_time', 'topic', 'speaker_name', 'room']],
                gridOptions=grid_options,
                height=300,
                data_return_mode='AS_INPUT', 
                update_mode='SELECTION_CHANGED',
                fit_columns_on_grid_load=True,
                allow_unsafe_jscode=True
            )
            selected_rows = grid_response['selected_rows']
            

            if isinstance(selected_rows, pd.DataFrame) and not selected_rows.empty:
                selected_seminar = selected_rows.to_dict('records')[0]
                st.session_state.selected_seminar = selected_seminar
            elif isinstance(selected_rows, list) and len(selected_rows) > 0:
                selected_seminar = selected_rows[0]
                st.session_state.selected_seminar = selected_seminar               
            else:
                st.session_state.selected_seminar = None

            # Display seminar details if a seminar is selected
            if st.session_state.selected_seminar is not None:
                seminar = st.session_state.selected_seminar
                st.write("Debug: Available columns:", df.columns.tolist())
                
                st.markdown(f"""
                    <div class="seminar-details">
                        <h4>{seminar.get('topic', 'N/A')}</h4>
                        <div class="seminar-info">
                            <div><span class="label">Date:</span> {seminar.get('date', 'N/A')}</div>
                            <div><span class="label">Time:</span> {seminar.get('start_time', 'N/A')} - {seminar.get('end_time', 'N/A')}</div>
                            <div><span class="label">Room:</span> {seminar.get('room', 'N/A')}</div>
                            <div><span class="label">Speaker:</span> {seminar.get('speaker_name', 'N/A')}</div>
                            <div><span class="label">Email:</span> {seminar.get('speaker_email', 'N/A')}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                # Speaker bio and abstract
                st.markdown(f"""
                    <div class="speaker-abstract-container">
                        <div>
                            <h4 style='color: #1f77b4; margin-bottom: 10px;'>Speaker Bio</h4>
                            <div style='background-color: white; padding: 0px; border-radius: 5px;'>
                                {seminar.get('speaker_bio', 'N/A')}
                            </div>
                        </div>
                        <div>
                            <h4 style='color: #1f77b4; margin-bottom: 10px;'>Abstract</h4>
                            <div style='background-color: white; padding: 0px; border-radius: 5px;'>
                                {seminar.get('abstract', 'N/A')}
                            </div>
                        </div>
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