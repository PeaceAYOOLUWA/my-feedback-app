import sqlite3
from werkzeug.security import generate_password_hash
from config import DB_PATH

def init_admin():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Add is_admin column if it doesn't exist
    existing_columns = [info[1] for info in c.execute("PRAGMA table_info(users)").fetchall()]
    if "is_admin" not in existing_columns:
        c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        print("is_admin column added.")
    else:
        print("is_admin column already exists.")

    # Default admin credentials
    username = "peaco"
    email = "peaco@example.com"  # Must have an email, cannot be NULL
    password = "peaco123"
    hashed_password = generate_password_hash(password)

    # Check if admin already exists by username or email
    c.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, email))
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
            (username, email, hashed_password, 1)
        )
        print("Admin user created successfully.")
    else:
        print("Admin user already exists.")

    conn.commit()
    conn.close()
    print(f"Admin initialization completed using database at {DB_PATH}")

# Call the function when running this script directly
if __name__ == "__main__":
    init_admin()
