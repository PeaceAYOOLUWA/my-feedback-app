import csv
import sqlite3
from flask import Flask, session, render_template, request, redirect, url_for, flash
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from textblob import TextBlob
from flask_login import login_required
from setup_admin import init_admin
from init_db import init_db
from config import DB_PATH, CSV_PATH

app = Flask(__name__)
app.secret_key = 'yoursecretkey'

# --- DB helper ---
def get_db_connection():
    return sqlite3.connect(DB_PATH)

# --- Initialize Database and Admin ---
init_db()
init_admin()

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("You must be logged in.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("You must be logged in.")
            return redirect(url_for("login"))

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT is_admin FROM users WHERE id = ?", (session["user_id"],))
        user = c.fetchone()
        conn.close()

        if not user or user[0] == 0:
            flash("Access denied. Admins only.")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html")

# --- Signup ---
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        if not username or not email or not password:
            flash("All fields are required.")
            return redirect(url_for("signup"))

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        user_count = c.fetchone()[0]
        is_admin = 1 if user_count == 0 else 0
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        try:
            c.execute(
                "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
                (username, email, hashed_password, is_admin)
            )
            conn.commit()
            flash("Signup successful! You can now log in.")
        except sqlite3.IntegrityError:
            flash("Username or email already exists.")
        finally:
            conn.close()
        return redirect(url_for("login"))

    return render_template("signup.html")

# --- Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, password, is_admin FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        conn.close()

        if row and check_password_hash(row[1], password):
            session['user_id'] = row[0]
            session['is_admin'] = row[2]
            flash("Logged in successfully.", "success")
            return redirect(url_for('admin_dashboard' if row[2] else 'my_feedback'))
        else:
            flash("Invalid username or password.", "error")
            return redirect(url_for('login'))

    return render_template("login.html")

# --- Logout ---
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("is_admin", None)
    flash("Logged out successfully")
    return redirect(url_for("login"))

# --- Submit feedback ---
@app.route('/submit', methods=['POST'])
@login_required
def submit():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    category = request.form.get('category')
    rating = request.form.get('rating')

    if not name or not email or not message or not category or not rating:
        flash("All fields are required.")
        return redirect(url_for("index"))

    if "@" not in email:
        flash("Invalid email address.")
        return redirect(url_for("index"))

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            flash("Rating must be between 1 and 5.")
            return redirect(url_for("index"))
    except ValueError:
        flash("Rating must be a number.")
        return redirect(url_for("index"))

    polarity = TextBlob(message).sentiment.polarity
    sentiment = "Positive" if polarity > 0.1 else "Negative" if polarity < -0.1 else "Neutral"

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO feedback (user_id, name, email, message, category, rating, sentiment) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (session["user_id"], name, email, message, category, rating, sentiment)
    )
    conn.commit()
    conn.close()

    flash("Thank you for your feedback!")
    return redirect(url_for("index"))

# --- Stats ---
@app.route("/stats")
@login_required
def stats():
    conn = get_db_connection()
    c = conn.cursor()

    # Total feedback count
    c.execute("SELECT COUNT(*) FROM feedback")
    total = c.fetchone()[0] or 0

    # Initialize counts
    sentiment_counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
    category_counts = {"General": 0, "Bug": 0, "Feature": 0, "Other": 0}
    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    if total > 0:
        # Sentiment counts
        c.execute("SELECT sentiment, COUNT(*) FROM feedback GROUP BY sentiment")
        for sentiment, count in c.fetchall():
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] = count

        # Category counts
        c.execute("SELECT category, COUNT(*) FROM feedback GROUP BY category")
        for category, count in c.fetchall():
            if category in category_counts:
                category_counts[category] = count

        # Rating counts
        c.execute("SELECT rating, COUNT(*) FROM feedback GROUP BY rating")
        for rating, count in c.fetchall():
            if rating in rating_counts:
                rating_counts[rating] = count

    conn.close()

    # Calculate percentages
    sentiment_percent = {k: f"{(v/total*100):.1f}%" if total else "0%" for k, v in sentiment_counts.items()}
    category_percent = {k: f"{(v/total*100):.1f}%" if total else "0%" for k, v in category_counts.items()}
    rating_percent = {k: f"{(v/total*100):.1f}%" if total else "0%" for k, v in rating_counts.items()}

    return render_template(
        "stats.html",
        total=total,
        sentiment_counts=sentiment_counts,
        sentiment_percent=sentiment_percent,
        category_counts=category_counts,
        category_percent=category_percent,
        rating_counts=rating_counts,
        rating_percent=rating_percent
    )

# --- Export CSV ---
@app.route("/export_local")
@admin_required
def export_local():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, user_id, name, email, message, category, rating, sentiment, created_at FROM feedback"
    )
    feedbacks = c.fetchall()
    conn.close()

    rating_map = {1: "Poor", 2: "Fair", 3: "Good", 4: "Very Good", 5: "Excellent"}

    # Write to CSV
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_ALL)
        # Write header
        writer.writerow(['ID', 'User ID', 'Name', 'Email', 'Message', 'Category', 'Rating', 'Sentiment', 'Created At'])
        # Write data rows
        for row in feedbacks:
            id_, user_id, name, email, message, category, rating, sentiment, created_at = row
            cleaned_row = [
                id_ or '',
                user_id or '',
                name.strip() if name else '',
                email.strip() if email else '',
                message.replace('\n', ' ').strip() if message else '',
                category.strip() if category else 'Other',
                rating_map.get(rating, 'N/A'),
                sentiment.strip() if sentiment else 'Neutral',
                created_at or ''
            ]
            writer.writerow(cleaned_row)

    flash(f"CSV exported successfully! Check '{CSV_PATH}' in your project folder.", "success")
    return redirect(url_for("index"))


# --- Admin dashboard ---
@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, user_id, name, email, message, category, rating, sentiment, created_at FROM feedback ORDER BY created_at ASC")
    entries = c.fetchall()
    c.execute("SELECT COUNT(*) FROM feedback")
    total = c.fetchone()[0]
    conn.close()
    return render_template("admin.html", entries=entries, total=total)

# --- User feedback view ---
@app.route("/my/feedback")
@login_required
def my_feedback():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, name, email, message, category, rating, sentiment, created_at FROM feedback WHERE user_id = ? ORDER BY created_at ASC",
        (session["user_id"],)
    )
    entries = c.fetchall()
    conn.close()
    total = len(entries)
    return render_template("my_feedback.html", entries=entries, total=total)

# --- User dashboard ---
@app.route("/dashboard")
@login_required
def user_dashboard():
    return render_template("user_dashboard.html")

# --- Edit feedback ---
@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, user_id, name, email, message, category, rating FROM feedback WHERE id = ?", (id,))
    entry = c.fetchone()

    if not entry:
        conn.close()
        flash("Feedback not found")
        return redirect(url_for("index"))

    if entry[1] != session["user_id"] and not session.get("is_admin"):
        conn.close()
        flash("You do not have permission to edit this feedback.")
        return redirect(url_for("index"))

    feedback = {
        "id": entry[0],
        "user_id": entry[1],
        "name": entry[2],
        "email": entry[3],
        "message": entry[4],
        "category": entry[5],
        "rating": entry[6]
    }

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")
        category = request.form.get("category")
        rating = request.form.get("rating")

        if not name or not email or not message or not category or not rating:
            flash("All fields are required.")
            return redirect(url_for("edit", id=id))
        if "@" not in email:
            flash("Invalid email address.")
            return redirect(url_for("edit", id=id))
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                flash("Rating must be between 1 and 5.")
                return redirect(url_for("edit", id=id))
        except ValueError:
            flash("Rating must be a number.")
            return redirect(url_for("edit", id=id))

        polarity = TextBlob(message).sentiment.polarity
        sentiment = "Positive" if polarity > 0.1 else "Negative" if polarity < -0.1 else "Neutral"

        c.execute(
            "UPDATE feedback SET name=?, email=?, message=?, category=?, rating=?, sentiment=? WHERE id=?",
            (name, email, message, category, rating, sentiment, id)
        )
        conn.commit()
        conn.close()
        flash("Feedback updated successfully")
        return redirect(url_for("admin_dashboard") if session.get("is_admin") else url_for("my_feedback"))

    conn.close()
    return render_template("edit.html", feedback=feedback)

# --- Delete feedback ---
@app.route("/delete/<int:id>", methods=["POST", "GET"])
@admin_required
def delete(id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM feedback WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash(f"Feedback ID {id} has been deleted.")
    return redirect(url_for("admin_dashboard"))

# --- Run app ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5501)
