# Necessary libraries and modules
from datetime import datetime
from flask import Flask, session, render_template, redirect, url_for, request  # Flask core functions
from flask_migrate import Migrate  # For handling databse migrations
from config import Config  # Imports configuration settings
from database import db, create_db  # Imports the database instance
from auth import auth  # Imports the authentication blueprint 
from models import User, Event, ServicePackage, Booking  # Imports the models to interact with the database
from modules.event_manager import is_time_slot_available, create_service_package, update_event, delete_event

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
def home():
    
    user = db.session.get(User, session['user_id'])  # Retrieve the user by user_id from session

    if user is None:
        # If no user is found, redirect to the login page
        return redirect(url_for('auth.login'))

    return render_template('home.html', name=user.first_name)  # Render the home page with user's first name

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

# Run the application
if __name__ == '__main__':
    app.run(debug=True)
