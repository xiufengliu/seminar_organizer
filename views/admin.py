import streamlit as st
from database import SeminarDB
from datetime import datetime, time

def time_picker(label, default_time=time(9, 0)):
    col1, col2 = st.columns(2)
    hour = col1.number_input(f"{label} (Hour)", min_value=0, max_value=23, value=default_time.hour)
    minute = col2.number_input(f"{label} (Minute)", min_value=0, max_value=59, value=default_time.minute, step=5)
    return time(hour, minute)

def show():
    st.title("Admin Panel")
    db = SeminarDB()

    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if db.verify_admin(username, password):
                st.session_state.admin_logged_in = True
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")
    else:
        tab1, tab2 = st.tabs(["Admin Seminar", "Pending Seminar Requests"])

        with tab1:
            st.header("Manage Seminars")
            seminar_action = st.selectbox("Choose an action", ["Add Seminar", "Update Seminar", "Delete Seminar"])
            
            if seminar_action == "Add Seminar":
                with st.form("add_seminar_form"):
                    date = st.date_input("Seminar Date")
                    start_time = time_picker("Start Time", default_time=time(12, 0))
                    end_time = time_picker("End Time", default_time=time(13, 0))
                    room = st.text_input("Meeting Room")
                    speaker_name = st.text_input("Speaker Name")
                    speaker_email = st.text_input("Speaker Email")
                    speaker_bio = st.text_area("Speaker Bio")
                    topic = st.text_input("Topic")
                    abstract = st.text_area("Abstract")
                    submit_button = st.form_submit_button("Add Seminar")

                if submit_button:
                    success, message = db.create_seminar(str(date), start_time.strftime("%H:%M:%S"), end_time.strftime("%H:%M:%S"), 
                                                        speaker_name, speaker_email, speaker_bio, topic, abstract, room)
                    if success:
                        st.success(message)
                    else:
                        st.warning(message)

            elif seminar_action == "Update Seminar":
                seminars = db.read_seminars()
                if not seminars:
                    st.warning("No seminars available to update.")
                else:
                    seminar_options = [f"{s[1]} - {s[7]}" for s in seminars]  # date - topic
                    selected_seminar = st.selectbox("Select seminar to update", seminar_options)
                    if selected_seminar:
                        seminar = next(s for s in seminars if f"{s[1]} - {s[7]}" == selected_seminar)
                        with st.form("edit_seminar_form"):
                            date = st.date_input("Seminar Date", value=datetime.strptime(seminar[1], "%Y-%m-%d").date())
                            start_time = time_picker("Start Time", default_time=datetime.strptime(seminar[2], "%H:%M:%S").time())
                            end_time = time_picker("End Time", default_time=datetime.strptime(seminar[3], "%H:%M:%S").time())
                            room = st.text_input("Meeting Room", value=seminar[9])
                            speaker_name = st.text_input("Speaker Name", value=seminar[4])
                            speaker_email = st.text_input("Speaker Email", value=seminar[5])
                            speaker_bio = st.text_area("Speaker Bio", value=seminar[6])
                            topic = st.text_input("Topic", value=seminar[7])
                            abstract = st.text_area("Abstract", value=seminar[8])
                            submit_button = st.form_submit_button("Update Seminar")

                        if submit_button:
                            success, message = db.update_seminar(seminar[0], str(date), start_time.strftime("%H:%M:%S"), end_time.strftime("%H:%M:%S"),
                                                                speaker_name, speaker_email, speaker_bio, topic, abstract, room)
                            if success:
                                st.success(message)
                            else:
                                st.warning(message)

                        # Add email invitation section
                        st.markdown("---")
                        st.subheader("Send Calendar Invitations")
                        email_recipients = st.text_area("Enter email recipients (one per line)")
                        if st.button("Invite"):
                            emails = [email.strip() for email in email_recipients.split('\n') if email.strip()]
                            emails.append(speaker_email)
                            if emails:
                                success, message = db.send_calendar_invitation(seminar[0], emails)
                                if success:
                                    st.success(message)
                                else:
                                    st.error(message)
                            else:
                                st.warning("Please enter at least one email address.")


            elif seminar_action == "Delete Seminar":
                seminars = db.read_seminars()
                if not seminars:
                    st.warning("No seminars available to delete.")
                else:
                    seminar_options = [f"{s[1]} - {s[7]}" for s in seminars]  # date - topic
                    selected_seminar = st.selectbox("Select seminar to delete", seminar_options)
                    if selected_seminar:
                        seminar = next(s for s in seminars if f"{s[1]} - {s[7]}" == selected_seminar)
                        if st.button("Delete Seminar"):
                            db.delete_seminar(seminar[0])
                            st.success("Seminar deleted successfully!")

        with tab2:
            st.header("Pending Seminar Requests")
            requests = db.read_seminar_requests()
            if not requests:
                st.warning("No pending seminar requests.")
            else:
                # Group similar requests
                grouped_requests = {}
                for request in requests:
                    key = (request[1], request[2], request[3], request[4], request[7], request[9])  # date, start_time, end_time, speaker_name, topic, room
                    if key not in grouped_requests:
                        grouped_requests[key] = []
                    grouped_requests[key].append(request)

                for key, similar_requests in grouped_requests.items():
                    request = similar_requests[0]  # Use the first request in the group for display
                    with st.expander(f"{request[1]} - {request[7]} ({len(similar_requests)} similar requests)"):
                        st.write(f"Date: {request[1]}")
                        st.write(f"Time: {request[2]} - {request[3]}")
                        st.write(f"Room: {request[9]}")
                        st.write(f"Speaker: {request[4]}")
                        st.write(f"Email: {request[5]}")
                        st.write(f"Bio: {request[6]}")
                        st.write(f"Topic: {request[7]}")
                        st.write(f"Abstract: {request[8]}")

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button("Approve", key=f"approve_{request[0]}"):
                                for r in similar_requests:
                                    db.approve_seminar_request(r[0])
                                st.success(f"Approved {len(similar_requests)} similar seminar requests and added to schedule.")
                                st.experimental_rerun()
                        with col2:
                            if st.button("Reject", key=f"reject_{request[0]}"):
                                for r in similar_requests:
                                    db.update_seminar_request(r[0], *r[1:10], "rejected")
                                st.success(f"Rejected {len(similar_requests)} similar seminar requests.")
                                st.experimental_rerun()
                        with col3:
                            if st.button("Edit", key=f"edit_{request[0]}"):
                                st.session_state.editing_request = request[0]
                                st.experimental_rerun()

            # ... (rest of the code for editing requests remains the same)

                if 'editing_request' in st.session_state:
                    request = next(r for r in requests if r[0] == st.session_state.editing_request)
                    st.subheader(f"Editing request: {request[1]} - {request[7]}")
                    with st.form("edit_request_form"):
                        date = st.date_input("Seminar Date", value=datetime.strptime(request[1], "%Y-%m-%d").date())
                        start_time = time_picker("Start Time", default_time=datetime.strptime(request[2], "%H:%M:%S").time())
                        end_time = time_picker("End Time", default_time=datetime.strptime(request[3], "%H:%M:%S").time())
                        room = st.text_input("Meeting Room", value=request[9])
                        speaker_name = st.text_input("Speaker Name", value=request[4])
                        speaker_email = st.text_input("Speaker Email", value=request[5])
                        speaker_bio = st.text_area("Speaker Bio", value=request[6])
                        topic = st.text_input("Topic", value=request[7])
                        abstract = st.text_area("Abstract", value=request[8])
                        
                        # Handle the case where the status might not be in the list
                        status_options = ["pending", "approved", "rejected"]
                        current_status = request[10] if request[10] in status_options else "pending"
                        status = st.selectbox("Status", status_options, index=status_options.index(current_status))
                        
                        submit_button = st.form_submit_button("Update Request")

                    if submit_button:
                        db.update_seminar_request(
                            request[0], str(date), start_time.strftime("%H:%M:%S"), end_time.strftime("%H:%M:%S"),
                            speaker_name, speaker_email, speaker_bio, topic, abstract, room, status
                        )
                        st.success("Seminar request updated successfully!")
                        del st.session_state.editing_request
                        st.experimental_rerun()

        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.experimental_rerun()

    db.close()