import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import SeminarDB
from datetime import datetime, time

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

            fig = go.Figure(data=[go.Table(
                columnwidth=[1, 1, 4, 1, 1],  # Adjusting column widths: Date, Time, Room smaller; Topic wider
                header=dict(
                    values=['Date', 'Time', 'Topic', 'Speaker', 'Room'],
                    fill_color='#4CAF50',
                    align='left',
                    font=dict(color='white', size=14)
                ),
                cells=dict(
                    values=[
                        df.date.dt.strftime('%Y-%m-%d'),
                        df.start_time.apply(lambda t: t.strftime('%H:%M')) + ' - ' + df.end_time.apply(lambda t: t.strftime('%H:%M')),
                        df.topic,
                        df.speaker_name,
                        df.room
                    ],
                    align='left',
                    font=dict(color='darkslate gray', size=13),
                    fill_color='white',
                    height=30  # Adjust row height for better spacing
                )
            )])

            fig.update_layout(
                title='Upcoming Seminars',
                height=300,  # Set a fixed height for the table
                margin=dict(l=0, r=0, t=30, b=0),
                paper_bgcolor='white'
            )

            st.plotly_chart(fig, use_container_width=True)



            st.markdown('-----------------')
            st.subheader("Seminar Details")
            selected_seminar = st.selectbox("Select a seminar for more information", df['topic'])
            if selected_seminar:
                seminar = df[df['topic'] == selected_seminar].iloc[0]
                
                # Create a styled container for seminar details
                with st.container():
                    st.markdown(f"""
                            <style>
                                .seminar-details {{
                                    background-color: #f0f2f6;
                                    border-radius: 10px;
                                    padding: 20px;
                                    margin-bottom: 20px;
                                    border: 1px solid #ccc; /* Added border to frame the section */
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
                                    gap: 10px; /* Reduced the gap between the Speaker Bio and Abstract sections */
                                }}
                                .speaker-abstract-container div {{
                                    width: 48%; /* Adjusting width of each column */
                                }}
                            </style>

                            <div class="seminar-details">
                                <h4>{seminar['topic']}</h4>
                                <div class="seminar-info">
                                    <div><span class="label">Date:</span> {seminar['date'].strftime('%Y-%m-%d')}</div>
                                    <div><span class="label">Time:</span> {seminar['start_time'].strftime('%H:%M')} - {seminar['end_time'].strftime('%H:%M')}</div>
                                    <div><span class="label">Room:</span> {seminar['room']}</div>
                                    <div><span class="label">Speaker:</span> {seminar['speaker_name']}</div>
                                    <div><span class="label">Email:</span> {seminar['speaker_email']}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                    col1, col2 = st.columns(2)
                    with col1:
                        with st.expander("", expanded=True):
                            st.markdown(f"""
                            <div style='background-color: white; padding: 0px; border-radius: 5px;'>
                                <h4 style='color: #1f77b4; margin-bottom: 10px;'>Speaker Bio</h4>  <!-- Custom styled title -->
                                {seminar['speaker_bio']}
                            </div>
                            """, unsafe_allow_html=True)

                    with col2:
                        with st.expander("", expanded=True):
                            st.markdown(f"""
                            <div style='background-color: white; padding: 0px; border-radius: 5px;'>
                                <h4 style='color: #1f77b4; margin-bottom: 10px;'>Abstract</h4>  <!-- Custom styled title -->
                                {seminar['abstract']}
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