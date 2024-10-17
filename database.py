import sqlite3
from datetime import datetime

class SeminarDB:
    def __init__(self, db_file='seminars.db'):
        self.db_file = db_file
        self.conn = None
        self.cursor = None
        self.initialize_database()

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
    
    def create_seminar_request(self, date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room):
        self.connect()
        self.cursor.execute('''
            INSERT INTO seminar_requests (date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date, start_time, end_time, speaker_name, speaker_email, speaker_bio, topic, abstract, room))
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

    def approve_seminar_request(self, request_id):
        self.connect()
        self.cursor.execute('SELECT * FROM seminar_requests WHERE id = ?', (request_id,))
        request = self.cursor.fetchone()
        if request:
            self.create_seminar(*request[1:10])  # Exclude id and status
            self.cursor.execute('DELETE FROM seminar_requests WHERE id = ?', (request_id,))
            self.conn.commit()

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

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None