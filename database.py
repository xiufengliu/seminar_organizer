import sqlite3
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from icalendar import Calendar, Event
import pytz
import bcrypt

class SeminarDB:
    def __init__(self, db_file='seminars.db'):
        self.db_file = db_file
        self.conn = None
        self.cursor = None
        self.initialize_database()
        self.email_config = {
            'username': 'scicloudadm',
            'app_passwd': 'ywgyayhvoonpvcey',
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587
        }

    def initialize_database(self):
        # Use context manager to handle the connection
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Create seminars table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS seminars (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    speaker_name TEXT NOT NULL,
                    speaker_email TEXT NOT NULL,
                    speaker_bio TEXT,
                    topic TEXT NOT NULL,
                    abstract TEXT,
                    room TEXT NOT NULL,
                    seminar_type TEXT NOT NULL DEFAULT 'Others'        
                )
            ''')
            
            # Create seminar requests table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS seminar_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    speaker_name TEXT NOT NULL,
                    speaker_email TEXT NOT NULL,
                    speaker_bio TEXT,
                    topic TEXT NOT NULL,
                    abstract TEXT,
                    room TEXT NOT NULL,
                    submitter_name TEXT NOT NULL,
                    submitter_email TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    seminar_type TEXT NOT NULL DEFAULT 'Others' 
                )
            ''')
            
            # Create admin accounts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_accounts (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL
                )
            ''')
            
            # Hash the default admin password
            hashed_password = bcrypt.hashpw('nimda1234'.encode('utf-8'), bcrypt.gensalt())
            
            # Insert the hardcoded admin account if not already present
            cursor.execute('''
                INSERT OR IGNORE INTO admin_accounts (username, password)
                VALUES (?, ?)
            ''', ('admin', hashed_password.decode('utf-8')))
            
            # Commit the transaction
            conn.commit()


    def connect(self):
        return sqlite3.connect(self.db_file)


    def check_time_conflict(self, date, start_time, end_time, room, exclude_id=None):
        query = '''
        SELECT COUNT(*) FROM seminars 
        WHERE date = ? 
        AND room = ?
        AND (
            (start_time < ? AND end_time > ?) OR
            (start_time < ? AND end_time > ?) OR
            (start_time >= ? AND end_time <= ?)
        )
        '''
        params = [date, room, end_time, start_time, start_time, start_time, start_time, end_time]
        
        if exclude_id is not None:
            query += ' AND id != ?'
            params.append(exclude_id)
        
        # Use context manager to automatically manage the connection
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            count = cursor.fetchone()[0]
        
        return count > 0


    def fetch_future_seminars(self):
        now = datetime.now().date()
        
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Fetch all seminars happening today or later
            cursor.execute('''
                SELECT * FROM seminars 
                WHERE date >= ? 
                ORDER BY date ASC, start_time ASC
            ''', (now.strftime("%Y-%m-%d"),))
            
            # Fetch all results
            seminars = cursor.fetchall()
            
            # Reformat the seminars to renumber the IDs
            renumbered_seminars = []
            for i, seminar in enumerate(seminars, start=1):
                # Convert the seminar to a list so we can modify it
                seminar_list = list(seminar)
                seminar_list[0] = i  # Replace the original ID (assuming it's the first column) with a new sequential ID
                renumbered_seminars.append(tuple(seminar_list))  # Convert back to a tuple to match the original format

        return renumbered_seminars


    def fetch_past_seminars(self):
        now = datetime.now().date()
        
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Fetch all seminars happening today or later
            cursor.execute('''
                SELECT * FROM seminars 
                WHERE date < ? 
                ORDER BY date DESC, start_time DESC
            ''', (now.strftime("%Y-%m-%d"),))
            
            # Fetch all results
            seminars = cursor.fetchall()
            
            # Reformat the seminars to renumber the IDs
            renumbered_seminars = []
            for i, seminar in enumerate(seminars, start=1):
                # Convert the seminar to a list so we can modify it
                seminar_list = list(seminar)
                seminar_list[0] = i  # Replace the original ID (assuming it's the first column) with a new sequential ID
                renumbered_seminars.append(tuple(seminar_list))  # Convert back to a tuple to match the original format

        return renumbered_seminars


    def create_seminar_request(self, date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, submitter_name, submitter_email, seminar_type):
        # Use a context manager to manage the connection
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Check if a similar request already exists
            cursor.execute('''
                SELECT COUNT(*) FROM seminar_requests
                WHERE date = ? AND start_time = ? AND end_time = ? AND speaker_name = ? AND topic = ? AND room = ?
            ''', (date, start_time, end_time, speaker_name, topic, room))
            
            count = cursor.fetchone()[0]
            
            if count > 0:
                return False, "A similar seminar request already exists."
            
            # If no similar request exists, insert the new request
            cursor.execute('''
                INSERT INTO seminar_requests (date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, submitter_name, submitter_email, seminar_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, submitter_name, submitter_email, seminar_type))
            
            # Commit the transaction
            conn.commit()
            
        # After committing, send an email notification to the seminar coordinator
        self.send_email_to_coordinator(speaker_name, speaker_email, topic, date, start_time, end_time, room)

        return True, "Seminar request submitted successfully."

    def read_seminar_requests(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM seminar_requests')
            seminar_requests = cursor.fetchall()
        
        return seminar_requests

    def update_seminar_request(self, request_id, date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, status, seminar_type):
        try:
            # Use context manager to handle connection and ensure it's closed after the operation
            with self.connect() as conn:
                cursor = conn.cursor()
                
                # Fetch the seminar request data to use it in the email after any operation (update or rejection)
                cursor.execute('SELECT submitter_name, submitter_email, topic FROM seminar_requests WHERE id = ?', (request_id,))
                seminar_request = cursor.fetchone()
                
                if not seminar_request:
                    return False, "Seminar request not found."
                
                # Extract information for sending email
                submitter_name, submitter_email, topic = seminar_request
                
                if status == "rejected":
                    # Send rejection email notification BEFORE deleting the request
                    self.send_email_notification(submitter_name, submitter_email, topic, status)
                    
                    # After email is sent, delete the seminar request
                    self.delete_seminar_request(request_id)
                    
                    # Commit the changes to the database
                    conn.commit()
                    
                    return True, "Seminar request rejected and removed from the list."
                else:
                    # Update the seminar request with the provided details
                    cursor.execute('''
                        UPDATE seminar_requests
                        SET date = ?, start_time = ?, end_time = ?, speaker_name = ?, speaker_email = ?, speaker_bio = ?, topic = ?, abstract = ?, room = ?, status = ?, seminar_type=? 
                        WHERE id = ?
                    ''', (date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, status, seminar_type, request_id))
                    
                    # Commit the changes to the database
                    conn.commit()
                    
                    # Send email notification after successful update
                    self.send_email_notification(submitter_name, submitter_email, topic, status)
                    
                    return True, "Seminar request updated successfully."
        except Exception as e:
            # Log error and return failure message
            return False, f"Error updating seminar request: {str(e)}"

    def approve_seminar_request(self, request_id):
        try:
            # Use context manager to handle the connection
            with self.connect() as conn:
                cursor = conn.cursor()
                
                # Fetch the seminar request
                cursor.execute('SELECT * FROM seminar_requests WHERE id = ?', (request_id,))
                request = cursor.fetchone()
                
                if request:
                    # Extract necessary fields for creating a seminar and sending the email
                    submitter_name = request[10]
                    submitter_email = request[11]
                    topic = request[7]
                    
                    # Create a new seminar using the relevant request data (excluding id and status)
                    self.create_seminar(*request[1:11])
                    
                    # After creating the seminar, delete the request from the seminar_requests table
                    cursor.execute('DELETE FROM seminar_requests WHERE id = ?', (request_id,))
                    
                    # Commit the changes to the database
                    conn.commit()
                    
                    # Send an email to notify the submitter about the approval
                    self.send_email_notification(submitter_name, submitter_email, topic, 'approved')
                    
                    return True, "Seminar request approved and added to schedule."
                else:
                    return False, "Seminar request not found."
        except Exception as e:
            # Log error and return failure message
            return False, f"Error approving seminar request: {str(e)}"

    def check_existing_request(self, date, start_time, end_time, speaker_name, topic, room):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM seminar_requests
                WHERE date = ? AND start_time = ? AND end_time = ? AND speaker_name = ? AND topic = ? AND room = ?
            ''', (date, start_time, end_time, speaker_name, topic, room))
            count = cursor.fetchone()[0]
        
        return count > 0


    def create_seminar(self, date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, seminar_type):
        # First, check if there is a time conflict in the room
        if self.check_time_conflict(date, start_time, end_time, room):
            return False, "Time conflict: Another seminar is scheduled in the same room during this time slot."
        
        # Use context manager to handle connection and ensure it is properly closed
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO seminars (date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, seminar_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, seminar_type))
            
            # Commit the transaction to save the new seminar
            conn.commit()
        
        return True, "Seminar added successfully."


    def update_seminar(self, seminar_id, date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, seminar_type):
        # Check if there's a time conflict with other seminars
        if self.check_time_conflict(date, start_time, end_time, room, exclude_id=seminar_id):
            return False, "Time conflict: Another seminar is scheduled in the same room during this time slot."
        
        # Use context manager to handle connection
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE seminars
                SET date = ?, start_time = ?, end_time = ?, speaker_name = ?, speaker_email = ?, speaker_bio = ?, topic = ?, abstract = ?, room = ?, seminar_type=?
                WHERE id = ?
            ''', (date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, seminar_type, seminar_id))
            
            # Commit the transaction to save the updates
            conn.commit()
        
        return True, "Seminar updated successfully."


    def read_seminars(self):
        # Use context manager to handle connection
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM seminars')
            seminars = cursor.fetchall()        
        return seminars


    def delete_seminar(self, seminar_id):
        # Use context manager to handle connection
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM seminars WHERE id = ?', (seminar_id,))
            conn.commit()

    def delete_seminar_request(self, request_id):
        # Use context manager to handle connection
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM seminar_requests WHERE id = ?', (request_id,))
            conn.commit()


    def verify_admin(self, username, password):
        # Use context manager to handle the connection
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Fetch the hashed password for the provided username
            cursor.execute('SELECT password FROM admin_accounts WHERE username = ?', (username,))
            result = cursor.fetchone()
            
            if result:
                stored_hashed_password = result[0]
                
                # Verify the provided password against the stored hashed password
                return bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password.encode('utf-8'))
            
        return False


    def send_email_notification(self, submitter_name, submitter_email, topic, status):
        subject = f"Seminar Request Update: {topic}"
        body = f"Dear {submitter_name},\n\nYour seminar request '{topic}' has been {status}.\n\nBest regards,\nSeminar Organizer"

        msg = MIMEMultipart()
        msg['From'] = self.email_config['username']
        msg['To'] = submitter_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['username'], self.email_config['app_passwd'])
                server.send_message(msg)
            print(f"Email notification sent to {submitter_email}")
        except Exception as e:
            print(f"Error sending email: {e}")


    def send_calendar_invitation(self, seminar_id, recipient_emails):
        # Open a connection and use a cursor to retrieve the seminar data
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM seminars WHERE id = ?', (seminar_id,))
            seminar = cursor.fetchone()

            if not seminar:
                return False, "Seminar not found."

            # Extract relevant seminar details
            date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room = seminar[1:10]

            # Create the calendar event
            cal = Calendar()
            cal.add('prodid', '-//My Seminar Application//mxm.dk//')
            cal.add('version', '2.0')

            event = Event()
            event.add('summary', topic)
            event.add('description', abstract)
            event.add('dtstart', datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC))
            event.add('dtend', datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC))
            event.add('location', room)
            event.add('organizer', self.email_config['username'])
            event.add('uid', f'{seminar_id}@myseminarapp.com')  # Unique event ID
            event.add('priority', 5)

            # Add the event to the calendar
            cal.add_component(event)

            # Create the email message
            msg = MIMEMultipart()
            msg['Subject'] = f"Invitation: {topic}"
            msg['From'] = self.email_config['username']
            msg['To'] = ', '.join(recipient_emails)

            # Attach the calendar event
            filename = "invitation.ics"
            part = MIMEBase('text', 'calendar', method='REQUEST', name=filename)
            part.set_payload(cal.to_ical())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)

            # Add email body
            body = f"""
            You are invited to the following seminar:

            Topic: {topic}
            Speaker: {speaker_name}
            Date: {date}
            Time: {start_time} - {end_time}
            Room: {room}

            Please find the calendar invitation attached.
            """
            msg.attach(MIMEText(body, 'plain'))

            try:
                with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                    server.starttls()
                    server.login(self.email_config['username'], self.email_config['app_passwd'])
                    server.send_message(msg)
                return True, f"Calendar invitations sent to {', '.join(recipient_emails)}"
            except Exception as e:
                return False, f"Error sending calendar invitations: {str(e)}"


    def send_email_to_coordinator(self, speaker_name, speaker_email, topic, date, start_time, end_time, room):
        coordinator_email = "xiazhan@dtu.dk"  # Seminar coordinator's email
        coordinator_name = "Xiaobing"  # Seminar coordinator's name
        subject = "New Seminar Request for Approval"
        
        # Email body
        body = f"""
        Dear {coordinator_name},

        A new seminar request has been submitted for your approval.

        Seminar Details:
        - Speaker: {speaker_name} ({speaker_email})
        - Topic: {topic}
        - Date: {date}
        - Time: {start_time} - {end_time}
        - Room: {room}

        Please review and approve the request.

        Best regards,
        Seminar Organizer
        """
        
        # Create the email
        msg = MIMEMultipart()
        msg['From'] = self.email_config['username']
        msg['To'] = coordinator_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            # Send the email using SMTP
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['username'], self.email_config['app_passwd'])
                server.send_message(msg)
            print(f"Email sent to {coordinator_name} ({coordinator_email})")
        except Exception as e:
            print(f"Failed to send email: {e}")    

    def close(self):
        pass