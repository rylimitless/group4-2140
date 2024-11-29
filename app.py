from flask import Flask, render_template , request , url_for

import sqlite3


app = Flask(__name__)


def createDB():
    conn = sqlite3.connect("company.db")


    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
	first_name TEXT NOT NULL,
	last_name TEXT NOT NULL,
	email TEXT NOT NULL UNIQUE,
	phone TEXT NOT NULL UNIQUE);
                 """)
    
    conn.execute("""
    CREATE TABLE IF NOT EXISTS dates(
        date TEXT PRIMARY KEY,
        booked BOOLEAN NOT NULL);
                 """)
    
    conn.execute("""
    CREATE TABLE IF NOT EXISTS bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reason TEXT NOT NULL,
        artist TEXT NOT NULL);
                 """)
    
    conn.commit()
    
createDB()


@app.route('/booking')
def hello():
    return render_template('index.html',name="Ry")


@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/events')
def events():
    return render_template('events.html')

@app.route('/date',methods=['POST'])
def home():
    print("Hello")
    date = request.form.get("datetime")
    if date is not None:
        if isUniqueDate(date):
            conn = sqlite3.connect("company.db")
            conn.execute(f"INSERT INTO dates(date,booked) VALUES('{date}',0)")
            conn.commit()
            print("Date added")
            return f"""<textarea name="disabled" disabled>
  {date} has been booked successfully
</textarea>"""
            # return template
        else:
            return f"""<textarea name="disabled" disabled>
  {date} already exists in database , please try another date or time
</textarea>"""

    return f"""<textarea name="disabled" disabled>
   We couldn't process your request
</textarea>"""

@app.route('/bookings')
def bookings():
    conn = sqlite3.connect("company.db")
    cursor = conn.execute("SELECT * FROM bookings")
    bookings = cursor.fetchall()
    return render_template("bookings.html",bookings=bookings)
    


@app.route('/register',methods=['POST'])
def book():
    reason = request.form.get("reason")
    artist = request.form.get("phase")
    comment = request.form.get("comment")

    conn = sqlite3.connect("company.db")
    conn.execute(f"INSERT INTO bookings(reason,artist) VALUES('{reason}','{artist}');")
    conn.commit()

    return f"<textarea readonly> Your booking with {artist} is scheduled </textarea>"

@app.route("/cancel",methods=['POST'])
def cancel():
    conn = sqlite3.connect("company.db")
    id = request.form.get("booking_id")
    conn.execute("DELETE FROM bookings WHERE id = ?",(id,))
    conn.commit()
    return f"<textarea readonly> Booking with id {id} has been cancelled </textarea>"

def isUniqueDate(date):
    conn = sqlite3.connect("company.db")
    cursor = conn.execute("SELECT * FROM dates")
    for row in cursor:
        if row[0] == date:
            return False
    return True

app.run(debug=True)