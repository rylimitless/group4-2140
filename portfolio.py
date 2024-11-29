from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, SelectField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.exceptions import RequestEntityTooLarge
import os
from werkzeug.utils import secure_filename
from PIL import Image

# Configurations
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'jpg', 'png', 'pdf', 'mp4'}
MAX_ITEMS = 6


# Initialize portfolio and database
portfolio = Flask(__name__)
portfolio.config['SECRET_KEY'] = 'your_secret_key'
portfolio.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portfolio.db'
portfolio.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(portfolio)
portfolio.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max size



# Model for portfolio items
class PortfolioItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)

# Form for uploading portfolio items
class PortfolioForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    file = FileField('File', validators=[DataRequired()])
    category = SelectField('Category', choices=[('Bridal', 'Bridal'), ('Birthday', 'Birthday'), ('Fashion', 'Fashion')], validators=[DataRequired()])
    submit = SubmitField('Upload')

# Helper function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@portfolio.errorhandler(RequestEntityTooLarge)
def handle_file_size_error(e):
    flash('File too large. Maximum size is 16 MB.', 'danger')
    return redirect(request.url)

# Routes
@portfolio.route('/')
def index():
    category = request.args.get('category')  # Get the filter category from the query parameters
    if category and category != 'All':  # If a specific category is selected
        items = PortfolioItem.query.filter_by(category=category).all()
    else:  # Show all items if no filter is portfoliolied or "All" is selected
        items = PortfolioItem.query.all()
    categories = ['All', 'Bridal', 'Birthday', 'Fashion']  # Define filter options
    return render_template('showcase.html', items=items, categories=categories, selected_category=category or 'All')



@portfolio.route('/upload', methods=['GET', 'POST'])
def upload():
    form = PortfolioForm()

    # Check if the maximum number of portfolio items is reached
    item_count = PortfolioItem.query.count()
    max_items = 6
    if item_count >= max_items:
        flash(f'You can only upload up to {max_items} portfolio items.', 'warning')
        return redirect(url_for('index'))

    if form.validate_on_submit():
        file = form.file.data
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(portfolio.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            # Add the new item to the database
            new_item = PortfolioItem(title=form.title.data, filename=filename, category=form.category.data)
            db.session.add(new_item)
            db.session.commit()

            flash('Portfolio item uploaded successfully!', 'success')
            return redirect(url_for('index'))

        else:
            flash('Invalid file type or upload error.', 'danger')

    return render_template('portfolioupload.html', form=form)


@portfolio.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit(item_id):
    # Get the portfolio item by id
    item = PortfolioItem.query.get_or_404(item_id)

    # Create and pre-populate the form
    form = PortfolioForm(obj=item)
    
    if form.validate_on_submit():
        item.title = form.title.data
        item.category = form.category.data

        # Handle file upload if a new file is provided
        if form.file.data:
            file = form.file.data
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(portfolio.config['UPLOAD_FOLDER'], filename))
                item.filename = filename

        # Commit the changes to the database
        db.session.commit()
        flash('Portfolio item updated successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('portfolioedit.html', form=form, item=item)



@portfolio.route('/delete/<int:item_id>', methods=['GET', 'POST'])
def delete(item_id):
    item = PortfolioItem.query.get_or_404(item_id)
    
    # Delete the file from the server
    file_path = os.path.join(portfolio.config['UPLOAD_FOLDER'], item.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete the item from the database
    db.session.delete(item)
    db.session.commit()
    flash('Portfolio item deleted successfully!', 'success')
    return redirect(url_for('index'))

# Main function
if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    with portfolio.app_context():
        db.create_all()  # Create tables if they don't exist
    portfolio.run(debug=True)
