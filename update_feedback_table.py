import sqlite3

conn = sqlite3.connect('feedback.db')  # use the path to your database
c = conn.cursor()

# Add user_id column if it doesn't exist
try:
    c.execute("ALTER TABLE feedback ADD COLUMN user_id INTEGER")
    print("user_id column added successfully.")
except sqlite3.OperationalError:
    print("user_id column already exists.")

conn.commit()
conn.close()