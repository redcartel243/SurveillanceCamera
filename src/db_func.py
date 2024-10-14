import sqlite3
import bcrypt
from src.device import list_capture_devices


# Database connection helper
def connect_db():
    return sqlite3.connect('CAM_SURV.db')


# Error handling and helper functions
class DatabaseError(Exception):
    pass


# Room Management
def add_room(user_id, room_name):
    try:
        conn = connect_db()
        c = conn.cursor()

        # Ensure the room doesn't already exist for the user
        c.execute('SELECT COUNT(*) FROM rooms WHERE room_name = ? AND user_id = ?', (room_name, user_id))
        if c.fetchone()[0] > 0:
            raise DatabaseError(f"Room '{room_name}' already exists for user {user_id}.")

        # Insert new room
        c.execute('INSERT INTO rooms (room_name, user_id) VALUES (?, ?)', (room_name, user_id))
        conn.commit()

        print(f"Room '{room_name}' added successfully.")
    except Exception as e:
        print(f"Error in add_room: {e}")
        raise
    finally:
        conn.close()


def get_rooms_by_user_id(user_id):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute('SELECT room_name FROM rooms WHERE user_id = ?', (user_id,))
        return [room[0] for room in c.fetchall()]  # Return list of room names
    except Exception as e:
        print(f"Error in get_rooms_by_user_id: {e}")
        return []
    finally:
        conn.close()


def delete_room(room_name):
    try:
        conn = connect_db()
        c = conn.cursor()

        # Use a transaction to ensure both the room and cameras are deleted atomically
        conn.execute('BEGIN')

        # Delete the room
        c.execute('DELETE FROM rooms WHERE room_name = ?', (room_name,))

        # Delete all cameras associated with this room
        c.execute('DELETE FROM cameras WHERE room_name = ?', (room_name,))

        # Reset camera statuses for cameras that were in this room
        c.execute('UPDATE camera_status SET is_assigned = 0 WHERE camera_id IN (SELECT camera_id FROM cameras WHERE room_name = ?)', (room_name,))

        conn.commit()
        print(f"Room '{room_name}' and its camera assignments were deleted successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error in delete_room: {e}")
        raise
    finally:
        conn.close()


def get_room_name_by_camera_id(camera_id):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute('SELECT room_name FROM cameras WHERE camera_id = ?', (camera_id,))
        room_name = c.fetchone()
        return room_name[0] if room_name else None
    except Exception as e:
        print(f"Error in get_room_name_by_camera_id: {e}")
        return None
    finally:
        conn.close()


def get_room_id_by_name(room_name):
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute('SELECT id FROM rooms WHERE room_name = ?', (room_name,))
        room_id = c.fetchone()
        return room_id[0] if room_id else None
    except Exception as e:
        print(f"Error in get_room_id_by_name: {e}")
        return None
    finally:
        conn.close()


def verify_password(username, password):
    conn = connect_db()
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()

    if result is None:
        print("User not found.")
        return False

    stored_hashed_password = result[0]
    return bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password)


def store_user(username, password):
    conn = connect_db()
    c = conn.cursor()
    hashed_password = hash_password(password)  # Hash the password before storing
    try:
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        print("User registered successfully.")
    except sqlite3.IntegrityError:
        print("Username already exists.")
    finally:
        conn.close()


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())


def get_user(username):
    conn = connect_db()
    c = conn.cursor()
    c.execute('SELECT id, username FROM users WHERE username = ? ORDER BY id DESC LIMIT 1', (username,))
    result = c.fetchone()
    conn.close()
    return result if result else None


def add_new_cameras():
    available_cameras = list_capture_devices()  # Fetch available cameras
    available_cameras = [str(camera) for camera in available_cameras]  # Ensure all IDs are strings

    conn = connect_db()
    c = conn.cursor()

    # Fetch existing cameras from the database
    c.execute('SELECT camera_id FROM camera_status')
    existing_cameras = {str(row[0]) for row in c.fetchall()}

    # Identify new cameras that aren't already in the database
    new_cameras = [camera for camera in available_cameras if camera not in existing_cameras]

    for camera_id in new_cameras:
        try:
            # Insert new camera into the camera_status table
            c.execute('INSERT INTO camera_status (camera_id, is_assigned) VALUES (?, 0)', (camera_id,))
            # Insert new camera into the cameras table
            c.execute('INSERT INTO cameras (camera_id, room_name, status) VALUES (?, NULL, "OFF")', (camera_id,))
        except sqlite3.IntegrityError as e:
            print(f"Failed to add camera {camera_id}: {e}")

    conn.commit()
    conn.close()

    return len(new_cameras)


# Camera Assignment
def assign_camera_to_room(room_name, camera_id):
    try:
        conn = connect_db()
        c = conn.cursor()

        # Check if the camera is already assigned
        c.execute('SELECT is_assigned FROM camera_status WHERE camera_id = ?', (camera_id,))
        result = c.fetchone()
        if result and result[0] == 1:
            raise DatabaseError(f"Camera {camera_id} is already assigned to a room.")
            
        # Assign the camera to the room and update its status
        conn.execute('BEGIN')
        c.execute('INSERT INTO cameras (camera_id, room_name, status) VALUES (?, ?, "ON")', (camera_id, room_name))
        c.execute('UPDATE camera_status SET is_assigned = 1 WHERE camera_id = ?', (camera_id,))
        conn.commit()

        print(f"Camera {camera_id} assigned to room {room_name}.")
    except Exception as e:
        conn.rollback()
        print(f"Error in assign_camera_to_room: {e}")
        raise
    finally:
        conn.close()


def unassign_camera(camera_id):
    try:
        conn = connect_db()
        c = conn.cursor()

        # Unassign the camera and reset its status
        conn.execute('BEGIN')
        c.execute('UPDATE cameras SET room_name = NULL, status = "OFF" WHERE camera_id = ?', (camera_id,))
        c.execute('UPDATE camera_status SET is_assigned = 0 WHERE camera_id = ?', (camera_id,))
        conn.commit()

        print(f"Camera {camera_id} unassigned successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error in unassign_camera: {e}")
        raise
    finally:
        conn.close()


def get_available_cameras():
    try:
        conn = connect_db()
        c = conn.cursor()
        c.execute('SELECT camera_id FROM cameras WHERE room_name IS NULL')
        return [camera[0] for camera in c.fetchall()]
    except Exception as e:
        print(f"Error in get_available_cameras: {e}")
        return []
    finally:
        conn.close()


def get_all_rooms_with_cameras():
    try:
        conn = connect_db()
        c = conn.cursor()

        # Fetch all rooms with their assigned cameras
        c.execute('''
            SELECT rooms.room_name, cameras.camera_id
            FROM rooms
            LEFT JOIN cameras ON rooms.room_name = cameras.room_name
            ORDER BY rooms.room_name
        ''')

        rooms = {}
        for row in c.fetchall():
            room_name, camera_id = row
            if room_name not in rooms:
                rooms[room_name] = []
            if camera_id:
                rooms[room_name].append(camera_id)

        return rooms
    except Exception as e:
        print(f"Error in get_all_rooms_with_cameras: {e}")
        return {}
    finally:
        conn.close()


# Database Initialization
def init_db():
    try:
        conn = connect_db()
        c = conn.cursor()

        # Create tables if they don't already exist
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_name TEXT NOT NULL,
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id TEXT NOT NULL,
                room_name TEXT,
                status TEXT NOT NULL DEFAULT 'OFF',
                FOREIGN KEY (room_name) REFERENCES rooms(room_name)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS camera_status (
                camera_id TEXT PRIMARY KEY,
                is_assigned INTEGER DEFAULT 0,
                FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
            )
        ''')

        conn.commit()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error in init_db: {e}")
        raise
    finally:
        conn.close()
