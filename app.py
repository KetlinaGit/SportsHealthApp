from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    fitness_goal = db.Column(db.String(200), nullable=True)

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
    target_date = db.Column(db.String(20), nullable=False)
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

        # Check if the user exists
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id  # Store user ID in session
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
    return render_template('dashboard.html', username=user.username)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please login to access your profile.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user.name = request.form['name']
        user.email = request.form['email']
        user.fitness_goal = request.form['fitness_goal']
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)

@app.route('/log_activity', methods=['GET', 'POST'])
def log_activity():
    if 'user_id' not in session:
        flash('Please login to log an activity.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        activity_type = request.form['type']
        duration = request.form['duration']
        distance = request.form.get('distance', 0)
        calories = request.form.get('calories', 0)
        date = request.form['date']

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

    return redirect(url_for('activity_history'))

@app.route('/activity_data')
def activity_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    activities = Activity.query.filter_by(user_id=session['user_id']).all()
    data = {
        'dates': [activity.date for activity in activities],
        'distances': [activity.distance for activity in activities],
        'calories': [activity.calories for activity in activities]
    }
    return jsonify(data)

@app.route('/set_goal', methods=['GET', 'POST'])
def set_goal():
    if 'user_id' not in session:
        flash('Please login to set a goal.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        target_distance = request.form['target_distance']
        target_date = request.form['target_date']

        new_goal = Goal(
            user_id=session['user_id'],
            target_distance=target_distance,
            target_date=target_date
        )
        db.session.add(new_goal)
        db.session.commit()

        flash('Goal set successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('set_goal.html')

if __name__ == '__main__':
    app.run(debug=True)
