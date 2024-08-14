import sqlite3
import bcrypt
from src.device import list_capture_devices

# Initializing the DataBase
def init_db():
    conn = sqlite3.connect('../SURVEILLANCE.db')
    c = conn.cursor()

    # Create Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Create Rooms table
    c.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Create Cameras table
    c.execute('''
        CREATE TABLE IF NOT EXISTS cameras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id TEXT NOT NULL,
            room_id INTEGER,
            FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
    ''')

    # Create Camera Status table
    c.execute('''
        CREATE TABLE IF NOT EXISTS camera_status (
            camera_id TEXT PRIMARY KEY,
            is_assigned INTEGER DEFAULT 0,
            room_id INTEGER,
            FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
    ''')

    conn.commit()
    conn.close()


# Function to hash a password
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())


# Method used to get user data from database
def get_user(username):
    conn = sqlite3.connect('../SURVEILLANCE.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, username FROM users
        WHERE username = ?
        ORDER BY id DESC LIMIT 1
    ''', (username,))
    result = c.fetchone()
    conn.close()
    return result if result else None


# Method to store a new user with hashed password
def store_user(username, password):
    conn = sqlite3.connect('../SURVEILLANCE.db')
    c = conn.cursor()
    hashed_password = hash_password(password)
    try:
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        print("User registered successfully.")
    except sqlite3.IntegrityError:
        print("Username already exists.")
    conn.close()


# Method to verify the user's password
def verify_password(username, password):
    conn = sqlite3.connect('../SURVEILLANCE.db')
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()

    if result is None:
        print("User not found.")
        return False

    stored_hashed_password = result[0]
    if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password):
        print("Password is correct.")
        return True
    else:
        print("Password is incorrect.")
        return False


# Method to add a room for a user
def add_room(user_id, room_name):
    conn = sqlite3.connect('../SURVEILLANCE.db')
    c = conn.cursor()
    c.execute('INSERT INTO rooms (name, user_id) VALUES (?, ?)', (room_name, user_id))
    conn.commit()
    print(f"Room '{room_name}' added successfully.")
    conn.close()


# Method to assign a camera to a room
# Method to assign a camera to a room and update its status
def assign_camera_to_room(room_id, camera_id):
    conn = sqlite3.connect('../SURVEILLANCE.db')
    c = conn.cursor()

    # Update the camera's assignment in the cameras table
    c.execute('INSERT INTO cameras (camera_id, room_id) VALUES (?, ?)', (camera_id, room_id))

    # Update the camera status to assigned
    c.execute('UPDATE camera_status SET is_assigned = 1, room_id = ? WHERE camera_id = ?', (room_id, camera_id))

    conn.commit()
    conn.close()


# Method to get rooms for a specific user
def get_rooms(user_id, room=1):
    conn = sqlite3.connect('../SURVEILLANCE.db')
    c = conn.cursor()
    c.execute('SELECT id, name FROM rooms WHERE user_id = ?', (user_id,))
    rooms = c.fetchall()
    conn.close()
    return rooms


# Method to get all available (unassigned) cameras
def get_available_cameras():
    conn = sqlite3.connect('../SURVEILLANCE.db')
    c = conn.cursor()

    c.execute('SELECT camera_id FROM camera_status WHERE is_assigned = 0')
    available_cameras = c.fetchall()
    conn.close()

    return [camera[0] for camera in available_cameras]

# Method to update the status of a camera when it is unassigned
def unassign_camera(camera_id):
    conn = sqlite3.connect('../SURVEILLANCE.db')
    c = conn.cursor()

    # Remove camera assignment from cameras table
    c.execute('DELETE FROM cameras WHERE camera_id = ?', (camera_id,))

    # Update the camera status to unassigned
    c.execute('UPDATE camera_status SET is_assigned = 0, room_id = NULL WHERE camera_id = ?', (camera_id,))

    conn.commit()
    conn.close()

# Method to get cameras assigned to a room
def get_cameras(room_id):
    conn = sqlite3.connect('../SURVEILLANCE.db')
    c = conn.cursor()
    c.execute('SELECT camera_id FROM cameras WHERE room_id = ?', (room_id,))
    cameras = c.fetchall()
    conn.close()
    return cameras


def delete_room(room_id):
    conn = sqlite3.connect('../SURVEILLANCE.db')
    c = conn.cursor()
    c.execute('DELETE FROM rooms WHERE id = ?', (room_id,))
    c.execute('DELETE FROM cameras WHERE room_id = ?', (room_id,))
    conn.commit()
    conn.close()


def delete_assignment(room_id, camera_id):
    conn = sqlite3.connect('../SURVEILLANCE.db')
    c = conn.cursor()
    c.execute('DELETE FROM cameras WHERE room_id = ? AND camera_id = ?', (room_id, camera_id))
    conn.commit()
    conn.close()


def modify_assignment(room_id, new_camera_id):
    conn = sqlite3.connect('../SURVEILLANCE.db')
    c = conn.cursor()
    c.execute('UPDATE cameras SET camera_id = ? WHERE room_id = ?', (new_camera_id, room_id))
    conn.commit()
    conn.close()

def get_all_rooms_with_cameras():
    conn = sqlite3.connect('../SURVEILLANCE.db')
    c = conn.cursor()

    c.execute('''
        SELECT rooms.name, cameras.camera_id
        FROM rooms
        LEFT JOIN cameras ON rooms.id = cameras.room_id
    ''')

    rooms = {}
    for row in c.fetchall():
        room_name, camera_id = row
        if room_name not in rooms:
            rooms[room_name] = []
        if camera_id:
            rooms[room_name].append(camera_id)

    conn.close()
    return rooms


def add_new_cameras():
    # Fetch all available cameras
    available_cameras = list_capture_devices()

    # Connect to the database
    conn = sqlite3.connect('../SURVEILLANCE.db')
    c = conn.cursor()

    # Fetch existing cameras from the database
    c.execute('SELECT camera_id FROM cameras')
    existing_cameras = {row[0] for row in c.fetchall()}  # Convert to a set for faster lookups

    # Add any new cameras that are not already in the database
    new_cameras = [camera for camera in available_cameras if camera not in existing_cameras]

    for camera_id in new_cameras:
        # Insert into cameras table
        c.execute('INSERT INTO cameras (camera_id, room_id) VALUES (?, NULL)', (camera_id,))

        # Insert into camera_status table with is_assigned set to 0 (unassigned)
        c.execute('INSERT INTO camera_status (camera_id, is_assigned, room_id) VALUES (?, 0, NULL)', (camera_id,))

    conn.commit()
    conn.close()

    return len(new_cameras)  # Return the number of new cameras added

# Test
"""if __name__ == "__main__":
    init_db()

    # User registration and verification
    store_user('john_doe', 'securepassword123')
    print(verify_password('john_doe', 'securepassword123'))
    print(verify_password('john_doe', 'wrongpassword'))

    # Adding rooms and assigning cameras
    user = get_user('john_doe')
    if user:
        user_id = user[0]
        add_room(user_id, 'Living Room')
        add_room(user_id, 'Bedroom')

        rooms = get_rooms(user_id)
        for room in rooms:
            room_id, room_name = room
            print(f"Room: {room_name}")

            assign_camera_to_room(room_id, f"camera_{room_id}_001")
            cameras = get_cameras(room_id)
            print(f"Cameras in {room_name}: {[camera[0] for camera in cameras]}")"""

