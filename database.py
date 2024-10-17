import sqlite3
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from icalendar import Calendar, Event
import pytz

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
        conn = sqlite3.connect(self.db_file)
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
                room TEXT NOT NULL
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
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        # Create admin accounts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_accounts (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        ''')
        
        # Insert hardcoded admin account
        cursor.execute('''
            INSERT OR IGNORE INTO admin_accounts (username, password)
            VALUES (?, ?)
        ''', ('admin', 'nimda1234'))
        
        conn.commit()
        conn.close()

    def connect(self):
        if not self.conn:
            self.conn = sqlite3.connect(self.db_file)
            self.cursor = self.conn.cursor()

    def check_time_conflict(self, date, start_time, end_time, room, exclude_id=None):
        self.connect()
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
        
        self.cursor.execute(query, params)
        count = self.cursor.fetchone()[0]
        return count > 0

    def fetch_future_seminars(self):
        self.connect()
        now = datetime.now().date()
        self.cursor.execute('''
            SELECT * FROM seminars 
            WHERE date >= ? 
            ORDER BY date ASC, start_time ASC
        ''', (now.strftime("%Y-%m-%d"),))
        seminars = self.cursor.fetchall()
        return seminars
    
    def create_seminar_request(self, date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, submitter_name, submitter_email):
        self.connect()
        self.cursor.execute('''
            INSERT INTO seminar_requests (date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, submitter_name, submitter_email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, submitter_name, submitter_email))
        self.conn.commit()


    def read_seminar_requests(self):
        self.connect()
        self.cursor.execute('SELECT * FROM seminar_requests')
        return self.cursor.fetchall()

    def update_seminar_request(self, request_id, date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, status):
        self.connect()
        self.cursor.execute('''
            UPDATE seminar_requests
            SET date = ?, start_time = ?, end_time = ?, speaker_name = ?, speaker_email = ?, speaker_bio = ?, topic = ?, abstract = ?, room = ?, status = ?
            WHERE id = ?
        ''', (date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, status, request_id))
        self.conn.commit()
        
        # Send email notification
        self.send_email_notification(request_id, status)

    def approve_seminar_request(self, request_id):
        self.connect()
        self.cursor.execute('SELECT * FROM seminar_requests WHERE id = ?', (request_id,))
        request = self.cursor.fetchone()
        if request:
            # Create a new seminar
            self.create_seminar(*request[1:10])  # Exclude id and status
            # Delete the request from seminar_requests table
            self.cursor.execute('DELETE FROM seminar_requests WHERE id = ?', (request_id,))
            self.conn.commit()
            return True, "Seminar request approved and added to schedule."
        return False, "Seminar request not found."


    def create_seminar(self, date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room):
        if self.check_time_conflict(date, start_time, end_time, room):
            return False, "Time conflict: Another seminar is scheduled in the same room during this time slot."
        
        self.connect()
        self.cursor.execute('''
            INSERT INTO seminars (date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room))
        self.conn.commit()
        return True, "Seminar added successfully."

    def update_seminar(self, seminar_id, date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room):
        if self.check_time_conflict(date, start_time, end_time, room, exclude_id=seminar_id):
            return False, "Time conflict: Another seminar is scheduled in the same room during this time slot."
        
        self.connect()
        self.cursor.execute('''
            UPDATE seminars
            SET date = ?, start_time = ?, end_time = ?, speaker_name = ?, speaker_email = ?, speaker_bio = ?, topic = ?, abstract = ?, room = ?
            WHERE id = ?
        ''', (date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room, seminar_id))
        self.conn.commit()
        return True, "Seminar updated successfully."

    def read_seminars(self):
        self.connect()
        self.cursor.execute('SELECT * FROM seminars')
        seminars = self.cursor.fetchall()
        print(f"Debug: Read {len(seminars)} seminars from database")
        for seminar in seminars:
            print(f"Debug: Seminar - {seminar}")
        return seminars


    def delete_seminar(self, seminar_id):
        self.connect()
        self.cursor.execute('DELETE FROM seminars WHERE id = ?', (seminar_id,))
        self.conn.commit()

    def verify_admin(self, username, password):
        self.connect()
        self.cursor.execute('SELECT * FROM admin_accounts WHERE username = ? AND password = ?', (username, password))
        return self.cursor.fetchone() is not None

    def send_email_notification(self, request_id, status):
        self.connect()
        self.cursor.execute('SELECT submitter_name, submitter_email, topic FROM seminar_requests WHERE id = ?', (request_id,))
        submitter_name, submitter_email, topic = self.cursor.fetchone()

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
        self.connect()
        self.cursor.execute('SELECT * FROM seminars WHERE id = ?', (seminar_id,))
        seminar = self.cursor.fetchone()

        if not seminar:
            return False, "Seminar not found."

        date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room = seminar[1:10]

        # Create the calendar event
        cal = Calendar()
        event = Event()
        event.add('summary', topic)
        event.add('description', abstract)
        event.add('dtstart', datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC))
        event.add('dtend', datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC))
        event.add('location', room)
        event.add('organizer', self.email_config['username'])
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
        body = f"You are invited to the following seminar:\n\nTopic: {topic}\nSpeaker: {speaker_name}\nDate: {date}\nTime: {start_time} - {end_time}\nRoom: {room}\n\nPlease find the calendar invitation attached."
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['username'], self.email_config['app_passwd'])
                server.send_message(msg)
            return True, f"Calendar invitations sent to {', '.join(recipient_emails)}"
        except Exception as e:
            return False, f"Error sending calendar invitations: {str(e)}"

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None