from flask import Blueprint, render_template, request, flash, current_app, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, SelectField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
import os
from models import PortfolioItem
from database import db

# Configuration
ALLOWED_EXTENSIONS = {'jpg', 'png', 'pdf', 'mp4'}
MAX_ITEMS = 6

# Define the blueprint
portfolio_bp = Blueprint('portfolio', __name__)

# Form for uploading portfolio items
class PortfolioForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    file = FileField('File', validators=[DataRequired()])
    category = SelectField('Category', choices=[('Bridal', 'Bridal'), ('Birthday', 'Birthday'), ('Fashion', 'Fashion')], validators=[DataRequired()])
    submit = SubmitField('Upload')

# Helper function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function to get all portfolio items
def get_portfolio_items(category=None):
    if category and category != 'All':
        return PortfolioItem.query.filter_by(category=category).all()
    return PortfolioItem.query.all()

# Function to check if max items are reached
def check_max_items():
    item_count = PortfolioItem.query.count()
    return item_count >= MAX_ITEMS  # Return True if the item count is greater than or equal to MAX_ITEMS

# Function to save portfolio items
def save_portfolio_item(file, title, category):
    filename = secure_filename(file.filename)
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    new_item = PortfolioItem(title=title, filename=filename, category=category)
    db.session.add(new_item)
    db.session.commit()

# Function to update portfolio items
def update_portfolio_item(item_id, title, category, file=None):
    item = PortfolioItem.query.get_or_404(item_id)

    item.title = title
    item.category = category

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        item.filename = filename

    db.session.commit()

# Function to delete portfolio items
def delete_portfolio_item(item_id):
    item = PortfolioItem.query.get_or_404(item_id)
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], item.filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(item)
    db.session.commit()

# Registering the routes in the portfolio blueprint
@portfolio_bp.route('/portfolio', methods=['GET'])
def portfolio_index():
    category = request.args.get('category')
    items = get_portfolio_items(category)
    categories = ['All', 'Bridal', 'Birthday', 'Fashion']
    return render_template('showcase.html', items=items, categories=categories, selected_category=category or 'All')

@portfolio_bp.route('/portfolio/upload', methods=['GET', 'POST'])
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

@portfolio_bp.route('/portfolio/edit/<int:item_id>', methods=['GET', 'POST'])
def portfolio_edit(item_id):
    item = PortfolioItem.query.get_or_404(item_id)
    form = PortfolioForm(obj=item)
    if form.validate_on_submit():
        update_portfolio_item(item_id, form.title.data, form.category.data, form.file.data)
        flash('Portfolio item updated successfully!', 'success')
        return redirect(url_for('portfolio.portfolio_index'))  # Correct endpoint name

    return render_template('portfolioedit.html', form=form, item=item)

@portfolio_bp.route('/portfolio/delete/<int:item_id>', methods=['POST'])
def portfolio_delete(item_id):
    delete_portfolio_item(item_id)
    flash('Portfolio item deleted successfully!', 'success')
    return redirect(url_for('portfolio.portfolio_index'))  # Correct endpoint name
