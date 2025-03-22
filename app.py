import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

if not os.path.exists('static'):
    os.makedirs('static')

if not os.path.exists('instance'):
    os.makedirs('instance')


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    profile_picture = db.Column(db.String(120), default='pfp_placeholder.png')

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    distance = db.Column(db.Float, nullable=True)
    calories = db.Column(db.Float, nullable=True)
    date = db.Column(db.String(20), nullable=False)

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_distance = db.Column(db.Float, nullable=False)
    progress = db.Column(db.Float, default=0)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose another.', 'error')
            return redirect(url_for('register'))

        # Hash the password (no method argument needed)
        hashed_password = generate_password_hash(password)

        # Create a new user
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login to access the dashboard.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    goal = Goal.query.filter_by(user_id=session['user_id']).first()

    progress = 0
    progress_percentage = 0
    if goal:
        activities = Activity.query.filter_by(user_id=session['user_id']).all()
        progress = sum(activity.distance for activity in activities if activity.distance)
        progress_percentage = (progress / goal.target_distance) * 100 if goal.target_distance else 0

    return render_template('dashboard.html', 
                           username=user.username, 
                           goal=goal, 
                           progress=progress, 
                           progress_percentage=progress_percentage)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please login to access your profile.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    activities = Activity.query.filter_by(user_id=session['user_id']).all()
    total_run = sum(activity.distance for activity in activities if activity.type == 'running' and activity.distance)
    total_bicycle = sum(activity.distance for activity in activities if activity.type == 'cycling' and activity.distance)
    total_gym = sum(activity.duration for activity in activities if activity.type == 'gym' and activity.duration) / 60

    return render_template('profile.html', 
                           username=user.username, 
                           total_run=total_run, 
                           total_bicycle=total_bicycle, 
                           total_gym=total_gym,
                           user=user)

@app.route('/log_activity', methods=['GET', 'POST'])
def log_activity():
    if 'user_id' not in session:
        flash('Please login to log an activity.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        activity_type = request.form['type']
        duration = request.form['duration']
        distance = request.form.get('distance', '')
        calories = request.form.get('calories', '')
        date = request.form['date']

        distance = float(distance) if distance else None
        calories = float(calories) if calories else None

        new_activity = Activity(
            user_id=session['user_id'],
            type=activity_type,
            duration=duration,
            distance=distance,
            calories=calories,
            date=date
        )
        db.session.add(new_activity)
        db.session.commit()

        flash('Activity logged successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('log_activity.html')

@app.route('/activity_history')
def activity_history():
    if 'user_id' not in session:
        flash('Please login to view your activity history.', 'error')
        return redirect(url_for('login'))

    activities = Activity.query.filter_by(user_id=session['user_id']).all()
    return render_template('activity_history.html', activities=activities)

@app.route('/delete_activity/<int:activity_id>', methods=['POST'])
def delete_activity(activity_id):
    if 'user_id' not in session:
        flash('Please login to delete an activity.', 'error')
        return redirect(url_for('login'))

    activity = Activity.query.get(activity_id)
    if activity and activity.user_id == session['user_id']:
        db.session.delete(activity)
        db.session.commit()
        flash('Activity deleted successfully!', 'success')
    else:
        flash('Activity not found or you do not have permission to delete it.', 'error')

    return redirect(url_for('data'))

@app.route('/activity_data')
def activity_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    activities = Activity.query.filter_by(user_id=session['user_id']).all()

    activity_data = []
    for activity in activities:
        activity_data.append({
            'type': activity.type,
            'duration': activity.duration,
            'distance': activity.distance if activity.distance else 'N/A',
            'calories': activity.calories if activity.calories else 'N/A',
            'date': activity.date
        })

    return jsonify({'activities': activity_data})

@app.route('/set_goal', methods=['GET', 'POST'])
def set_goal():
    if 'user_id' not in session:
        flash('Please login to set a goal.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        target_distance = float(request.form['target_distance'])

        existing_goal = Goal.query.filter_by(user_id=session['user_id']).first()
        if existing_goal:
            existing_goal.target_distance = target_distance
            existing_goal.progress = 0 
        else:
            new_goal = Goal(user_id=session['user_id'], target_distance=target_distance)
            db.session.add(new_goal)

        db.session.commit()
        flash('Goal set successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('set_goal.html')

@app.route('/data')
def data():
    if 'user_id' not in session:
        flash('Please login to view your data.', 'error')
        return redirect(url_for('login'))

    activities = Activity.query.filter_by(user_id=session['user_id']).all()

    running_activities = [activity for activity in activities if activity.type == 'running']
    cycling_activities = [activity for activity in activities if activity.type == 'cycling']
    gym_activities = [activity for activity in activities if activity.type == 'gym']

    return render_template('data.html', 
                           running_activities=running_activities, 
                           cycling_activities=cycling_activities, 
                           gym_activities=gym_activities)

@app.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    if 'profile_picture' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400

    file = request.files['profile_picture']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
    filepath = os.path.join('static', filename)
    file.save(filepath)

    user = User.query.get(session['user_id'])
    user.profile_picture = filename
    db.session.commit()

    return jsonify({'success': True, 'filename': filename})



if __name__ == '__main__':
    app.run(debug=True)
