import sqlite3

def init_db():
    conn = sqlite3.connect("feedback.db")
    c = conn.cursor()

    # --- Create 'users' table ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0 CHECK(is_admin IN (0,1))
        )
    """)

    # --- Create 'feedback' table ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            category TEXT CHECK(category IN ('General','Bug','Feature','Other')) DEFAULT 'General',
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            sentiment TEXT CHECK(sentiment IN ('Positive','Neutral','Negative')),
            status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending','Reviewed','Resolved')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # --- Indexes for faster sorting/searching ---
    c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_category ON feedback(category)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback(rating)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_sentiment ON feedback(sentiment)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at)")

    conn.commit()
    conn.close()
    print("Database initialized successfully with upgraded schema.")

# --- Run directly ---
if __name__ == "__main__":
    init_db()
