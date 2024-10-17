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
                header=dict(
                    values=['Date', 'Time', 'Topic', 'Speaker', 'Room'],
                    fill_color='#4CAF50',
                    align='left',
                    font=dict(color='white', size=12)
                ),
                cells=dict(
                    values=[
                        df.date.dt.strftime('%Y-%m-%d'),
                        df.start_time.astype(str) + ' - ' + df.end_time.astype(str),
                        df.topic,  # Changed from df.abstract to df.topic
                        df.speaker_name,
                        df.room
                    ],
                    align='left',
                    font=dict(color='darkslate gray', size=11)
                )
            )])

            fig.update_layout(
                title='Upcoming Seminars',
                height=200,
                margin=dict(l=0, r=0, t=30, b=0),
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
                        }}
                        .seminar-details h3 {{
                            color: #1f77b4;
                            margin-bottom: 15px;
                        }}
                        .seminar-details .label {{
                            font-weight: bold;
                            color: #2c3e50;
                        }}
                    </style>
                    <div class="seminar-details">
                        <h3>{seminar['topic']}</h3>
                        <p><span class="label">Date:</span> {seminar['date'].strftime('%Y-%m-%d')}</p>
                        <p><span class="label">Time:</span> {seminar['start_time']} - {seminar['end_time']}</p>
                        <p><span class="label">Room:</span> {seminar['room']}</p>
                        <p><span class="label">Speaker:</span> {seminar['speaker_name']}</p>
                        <p><span class="label">Email:</span> {seminar['speaker_email']}</p>
                    </div>
                    """, unsafe_allow_html=True)

                # Speaker bio and abstract in separate containers
                col1, col2 = st.columns(2)
                with col1:
                    with st.expander("Speaker Bio", expanded=True):
                        st.markdown(f"<div style='background-color: #e6f3ff; padding: 10px; border-radius: 5px;'>{seminar['speaker_bio']}</div>", unsafe_allow_html=True)
                with col2:
                    with st.expander("Abstract", expanded=True):
                        st.markdown(f"<div style='background-color: #fff6e6; padding: 10px; border-radius: 5px;'>{seminar['abstract']}</div>", unsafe_allow_html=True)
    with tab2:
        st.subheader("Request a Seminar")
        with st.form("request_seminar_form"):
            date = st.date_input("Seminar Date")
            start_time = time_picker("Start Time", default_time=time(12, 0))
            end_time = time_picker("End Time", default_time=time(13, 0))
            room = st.text_input("Preferred Meeting Room")
            speaker_name = st.text_input("Speaker Name")
            speaker_email = st.text_input("Speaker Email")
            speaker_bio = st.text_area("Speaker Bio")
            topic = st.text_input("Topic")
            abstract = st.text_area("Abstract")
            submit_button = st.form_submit_button("Submit Request")

        if submit_button:
            db.create_seminar_request(str(date), start_time.strftime("%H:%M:%S"), end_time.strftime("%H:%M:%S"), 
                                      speaker_name, speaker_email, speaker_bio, topic, abstract, room)
            st.success("Seminar request submitted successfully!")

    db.close()