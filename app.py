"""
Alice Gitau Photography - backend
---------------------------------
A small Flask server that:
  1. serves the website (index, about, contact pages, images, css, js)
  2. saves booking requests from the contact form into a SQLite database (POST /api/contact)
  3. shows them in a password-protected inbox (/login, then /messages) where you can
     track each request's status: new -> replied -> booked -> done
     (the login and inbox pages live in the templates/ folder)

Run locally:
    pip install -r requirements.txt
    export ADMIN_PASSWORD="pick-a-password"     (Windows: set ADMIN_PASSWORD=...)
    python app.py
Then open http://127.0.0.1:5000  (inbox: http://127.0.0.1:5000/login)
"""

import hmac
import os
import re
import sqlite3
from datetime import date, datetime, timezone

from flask import (Flask, abort, g, jsonify, redirect,
                   render_template, request, send_from_directory, session)

SITE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(SITE_DIR, "instance")          # database lives here, never served
DB_PATH = os.path.join(DB_DIR, "messages.db")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")    # inbox is locked unless this is set

# Only these file types are served to visitors (so app.py and the database stay private)
ALLOWED_EXTENSIONS = {".html", ".css", ".js", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico"}

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_NAME, MAX_EMAIL, MAX_MESSAGE = 100, 254, 5000

# The choices on the contact form (value saved in the database -> label shown to people)
SHOOT_TYPES = {"headshots": "Headshots", "event": "Event", "senior": "Senior portraits", "other": "Other"}
LOCATIONS = {"campus": "On campus", "outdoors": "Outdoors", "studio": "Indoors / studio", "unsure": "Not sure yet"}
STATUSES = ["new", "replied", "booked", "done"]

app = Flask(__name__, static_folder=None)
# Signs the login cookie. Set SECRET_KEY to stay logged in across restarts.
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)


# ===== Database =====

def get_db():
    """Open one database connection per request."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row      # lets us use row["name"]
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the table the first time, and add the booking columns to older databases."""
    os.makedirs(DB_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL,
                email      TEXT    NOT NULL,
                message    TEXT    NOT NULL,
                created_at TEXT    NOT NULL,
                shoot_type TEXT    NOT NULL DEFAULT 'other',
                shoot_date TEXT,
                location   TEXT    NOT NULL DEFAULT 'unsure',
                status     TEXT    NOT NULL DEFAULT 'new'
            )
        """)
        # If the database was made by the earlier version, add the new columns
        existing = {row[1] for row in db.execute("PRAGMA table_info(messages)")}
        new_columns = {
            "shoot_type": "TEXT NOT NULL DEFAULT 'other'",
            "shoot_date": "TEXT",
            "location": "TEXT NOT NULL DEFAULT 'unsure'",
            "status": "TEXT NOT NULL DEFAULT 'new'",
        }
        for column, definition in new_columns.items():
            if column not in existing:
                db.execute(f"ALTER TABLE messages ADD COLUMN {column} {definition}")


# ===== Website pages =====

@app.route("/")
def home():
    return send_from_directory(SITE_DIR, "index.html")


@app.route("/<path:filename>")
def site_files(filename):
    if os.path.splitext(filename)[1].lower() not in ALLOWED_EXTENSIONS:
        abort(404)
    if filename.startswith("templates/"):      # page templates are only used by Python
        abort(404)
    return send_from_directory(SITE_DIR, filename)


# ===== Booking request API =====

@app.post("/api/contact")
def save_message():
    data = request.get_json(silent=True) or {}

    # Honeypot: real people never fill in this hidden field, spam bots do
    if data.get("website"):
        return jsonify(ok=True)

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    message = str(data.get("message", "")).strip()
    shoot_type = str(data.get("shoot_type", "")).strip()
    location = str(data.get("location", "")).strip() or "unsure"
    shoot_date = str(data.get("shoot_date", "")).strip() or None

    if not name or not email or not message or not shoot_type:
        return jsonify(ok=False, error="Please fill out every required field."), 400
    if not EMAIL_PATTERN.match(email):
        return jsonify(ok=False, error="Please enter a valid email address."), 400
    if shoot_type not in SHOOT_TYPES or location not in LOCATIONS:
        return jsonify(ok=False, error="Please pick an option from the list."), 400
    if len(name) > MAX_NAME or len(email) > MAX_EMAIL or len(message) > MAX_MESSAGE:
        return jsonify(ok=False, error="That message is a little too long."), 400
    if shoot_date:
        try:
            if date.fromisoformat(shoot_date) < date.today():
                return jsonify(ok=False, error="Please pick a date that hasn't passed yet."), 400
        except ValueError:
            return jsonify(ok=False, error="Please pick a valid date."), 400

    db = get_db()
    # The ? placeholders keep user input out of the SQL itself (prevents SQL injection)
    db.execute(
        """INSERT INTO messages (name, email, message, created_at, shoot_type, shoot_date, location)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, email, message, datetime.now(timezone.utc).isoformat(timespec="seconds"),
         shoot_type, shoot_date, location),
    )
    db.commit()
    return jsonify(ok=True), 201


# ===== Login =====

def back_to_inbox():
    """Return to the inbox page you were on (keeps your status filter)."""
    ref = request.referrer or ""
    return redirect(ref if ref.startswith(request.host_url + "messages") else "/messages")


def is_admin():
    return session.get("admin") is True


def ask_for_login():
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        typed = request.form.get("password", "")
        if not ADMIN_PASSWORD:
            error = "Set ADMIN_PASSWORD in the terminal before starting the server."
        elif hmac.compare_digest(typed.encode(), ADMIN_PASSWORD.encode()):
            session["admin"] = True
            return redirect("/messages")
        else:
            error = "That password isn't right. Try again!"
    return render_template("login.html", error=error)


@app.post("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ===== Private inbox =====

@app.get("/messages")
def inbox():
    if not is_admin():
        return ask_for_login()
    db = get_db()

    current = request.args.get("status")
    if current not in STATUSES:
        current = None

    if current:
        messages = db.execute(
            "SELECT * FROM messages WHERE status = ? ORDER BY created_at DESC", (current,)
        ).fetchall()
    else:
        messages = db.execute("SELECT * FROM messages ORDER BY created_at DESC").fetchall()

    # How many requests are in each status
    counts = {s: 0 for s in STATUSES}
    for row in db.execute("SELECT status, COUNT(*) AS n FROM messages GROUP BY status"):
        counts[row["status"]] = row["n"]
    total = sum(counts.values())

    # Requests received this month (created_at starts with "YYYY-MM")
    this_month = db.execute(
        "SELECT COUNT(*) FROM messages WHERE created_at LIKE ?",
        (datetime.now(timezone.utc).strftime("%Y-%m") + "%",)
    ).fetchone()[0]

    # The most requested type of shoot
    top = db.execute(
        "SELECT shoot_type, COUNT(*) AS n FROM messages GROUP BY shoot_type ORDER BY n DESC LIMIT 1"
    ).fetchone()
    popular = SHOOT_TYPES.get(top["shoot_type"], top["shoot_type"]) if top else None

    return render_template(
        "messages.html", messages=messages, counts=counts, total=total,
        this_month=this_month, popular=popular, current=current, statuses=STATUSES,
        shoot_types=SHOOT_TYPES, locations=LOCATIONS,
    )


@app.post("/messages/<int:message_id>/status")
def update_status(message_id):
    if not is_admin():
        return ask_for_login()
    status = request.form.get("status")
    if status in STATUSES:
        db = get_db()
        db.execute("UPDATE messages SET status = ? WHERE id = ?", (status, message_id))
        db.commit()
    return back_to_inbox()


@app.post("/messages/<int:message_id>/delete")
def delete_message(message_id):
    if not is_admin():
        return ask_for_login()
    db = get_db()
    db.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    db.commit()
    return back_to_inbox()


init_db()

if __name__ == "__main__":
    app.run(debug=True)