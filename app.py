# Necessary libraries and modules
from datetime import datetime
from flask import Flask, current_app, flash, session, render_template, redirect, url_for, request  # Flask core functions
from flask_migrate import Migrate  # For handling databse migrations
from config import Config  # Imports configuration settings
from database import db, create_db  # Imports the database instance
from auth import auth  # Imports the authentication blueprint 
from models import User, Event, ServicePackage, Booking, PortfolioItem  # Imports the models to interact with the database
from modules.event_manager import is_time_slot_available, create_service_package, update_event, delete_event
from modules.portfolio import MAX_ITEMS, PortfolioForm, allowed_file, check_max_items, portfolio_bp, get_portfolio_items, save_portfolio_item, update_portfolio_item
import sqlite3
import os

# Initialize the Flask application
app = Flask(__name__)

# Loads the configuration from the Config class in the config.py file
app.config.from_object(Config)

# Initializes the database with the app
db.init_app(app)
create_db(app)

# Initializes Flask-Migrate for handling database migrations
migrate = Migrate(app, db)

# Register the Blueprint for authentication routes (login, logout, signup) needed for modularization
app.register_blueprint(auth)
app.register_blueprint(portfolio_bp, url_prefix='/portfolio')

# Detects if logged in
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Define the home route for the main page
@app.route('/')
@login_required  # This ensures that the user is logged in
def home2():
    
    user = db.session.get(User, session['user_id'])  # Retrieve the user by user_id from session

    if user is None:
        # If no user is found, redirect to the login page
        return redirect(url_for('auth.login'))

    return render_template('home.html', name=user.first_name)  # Render the home page with user's first name

# Portfolio Routes
@app.route('/portfolio', methods=['GET'])
def portfolio_index():
    category = request.args.get('category')
    items = get_portfolio_items(category)
    categories = ['All', 'Bridal', 'Birthday', 'Fashion']
    return render_template('showcase.html', items=items, categories=categories, selected_category=category or 'All')

@app.route('/upload', methods=['GET', 'POST'])
def portfolio_upload():
    form = PortfolioForm()
    if check_max_items():
        flash(f'You can only upload up to {MAX_ITEMS} portfolio items.', 'warning')
        return redirect(url_for('portfolio_index'))  # Use 'portfolio_index' directly

    if form.validate_on_submit():
        file = form.file.data
        if file and allowed_file(file.filename):
            save_portfolio_item(file, form.title.data, form.category.data)
            flash('Portfolio item uploaded successfully!', 'success')
            return redirect(url_for('portfolio_index'))  # Corrected here

        flash('Invalid file type or upload error.', 'danger')

    return render_template('portfolioupload.html', form=form)

@app.route('/portfolio/edit/<int:item_id>', methods=['GET', 'POST'])
def portfolio_edit(item_id):
    item = PortfolioItem.query.get_or_404(item_id)
    form = PortfolioForm(obj=item)
    if form.validate_on_submit():
        update_portfolio_item(item_id, form.title.data, form.category.data, form.file.data)
        flash('Portfolio item updated successfully!', 'success')
        return redirect(url_for('portfolio.portfolio_index'))

    return render_template('portfolioedit.html', form=form, item=item)

@app.route('/portfolio/delete/<int:item_id>', methods=['POST'])
def portfolio_delete(item_id):
    # Find the portfolio item by id
    item = PortfolioItem.query.get_or_404(item_id)
    
    # Remove the file from the file system
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], item.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete the item from the database
    db.session.delete(item)
    db.session.commit()
    
    # Redirect to portfolio showcase
    return redirect(url_for('portfolio_index'))

# Route for events page
@app.route('/events', methods=['GET', 'POST'])
@login_required
def events():
    user = db.session.get(User, session['user_id'])

    if request.method == 'POST':
        if 'create_event_package' in request.form:
            # Retrieve form data
            makeup_artist_name = request.form['makeup_artist_name']
            location = request.form['location']
            event_date_time = request.form['event_date_time']  # Get event date time
            event_name = request.form['event_name']

            # Check if the values are valid (not empty)
            if not makeup_artist_name or not location:
                return "Makeup artist name and location are required!", 400

            event_date_time = datetime.strptime(event_date_time, '%Y-%m-%dT%H:%M')  # Convert to datetime object

            if is_time_slot_available(event_date_time):
                # Create a new event and commit it to the database
                event = Event(
                    name=event_name,
                    date=event_date_time,
                    location=location,  # Assign location
                    makeup_artist_name=makeup_artist_name,  # Assign makeup artist name
                    user_id=user.id,
                    client_id=user.id
                )
                db.session.add(event)
                db.session.commit()

                # Create a service package for this event
                create_service_package(name="Basic Package", description="Standard makeup service", price=100.0, event_id=event.id)

                return redirect(url_for('events'))  # Redirect to the events page

            else:
                return "Time slot unavailable", 400  # If the slot is already booked

    # Fetch all events for the logged-in user
    events = Event.query.filter_by(user_id=user.id).all()
    return render_template('events.html', name=user.first_name, events=events)

# Route to edit an event
@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    user = db.session.get(User, session['user_id'])
    event = db.session.get(Event, event_id)

    if not event or event.user_id != user.id:
        return render_template('error.html', message="Event not found or unauthorized"), 404

    if request.method == 'POST':
        makeup_artist_name = request.form['makeup_artist_name']
        location = request.form['location']
        event_date_time = request.form['event_date_time']
        event_name = request.form['event_name']

        event_date_time = datetime.strptime(event_date_time, '%Y-%m-%dT%H:%M')

        if is_time_slot_available(event_date_time):
            update_event(event, makeup_artist_name, location, event_date_time, event_name)
            return redirect(url_for('events'))
        else:
            return "Time slot unavailable", 400

    return render_template('edit_event.html', event=event)

# Route to delete an event
@app.route('/delete_event/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    user = db.session.get(User, session['user_id'])
    event = db.session.get(Event, event_id)

    if not event or event.user_id != user.id:
        return render_template('error.html', message="Event not found or unauthorized"), 404

    delete_event(event)
    return redirect(url_for('events'))

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

# @app.route('/booking')
# def hello():
#     return render_template('index.html',name="Ry")

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

@app.route('/booking')
def hello():
    return render_template('index.html',name="Ry")

@app.route("/products")
def products():
    return render_template("product.html")

@app.route('/date1',methods=['POST'])
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

# Run the application
if __name__ == '__main__':
    app.run(debug=True)

