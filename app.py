from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Use environment variable for secret key
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key')  # Replace with a secure key if needed

# Database configuration for PythonAnywhere
db_config = {
    'user': os.environ.get('DB_USER', 'Demo124578'),  # Replace with your actual username
    'password': os.environ.get('DB_PASSWORD', 'Admin@1234'),  # Set this in PythonAnywhere
    'host': 'Demo124578.mysql.pythonanywhere-services.com',  # Replace with your database host
    'database': 'Demo124578$fms'  # Replace with your database name
}

# Establish database connection
def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

# Helper function to get pasture growth and consumption
def recalculate_pasture(paddocks):
    pasture_growth_rate = 50  # Example growth rate (kg DM/ha per day)
    stock_consumption_rate = 10  # Example consumption rate (kg DM per animal per day)

    for paddock in paddocks:
        # Growth per day
        paddock['pasture_growth'] = paddock['total_area'] * pasture_growth_rate

        # Consumption per day
        paddock['pasture_consumption'] = paddock['stock_count'] * stock_consumption_rate if paddock['stock_count'] > 0 else 0

        # Update total DM
        paddock['total_dm'] += paddock['pasture_growth'] - paddock['pasture_consumption']
        paddock['dm_per_ha'] = paddock['total_dm'] / paddock['total_area']

    return paddocks

# Home route
@app.route('/')
def home():
    if 'curr_date' not in session:
        session['curr_date'] = '2024-01-01'  # Initial date for the simulator
    return render_template('home.html', curr_date=session['curr_date'])

# Mobs route
@app.route('/mobs')
def mobs():
    connection = get_db_connection()
    if connection is None:
        flash('Database connection failed', 'danger')
        return redirect(url_for('home'))

    cursor = connection.cursor(dictionary=True)
    cursor.execute('''
        SELECT mobs.id, mobs.mob_name, paddocks.paddock_name, mobs.stock_count
        FROM mobs
        LEFT JOIN paddocks ON mobs.paddock_id = paddocks.id
        ORDER BY mobs.mob_name
    ''')
    mobs_data = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('mobs.html', mobs=mobs_data, curr_date=session['curr_date'])

# Paddocks route
@app.route('/paddocks')
def paddocks():
    connection = get_db_connection()
    if connection is None:
        flash('Database connection failed', 'danger')
        return redirect(url_for('home'))

    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM paddocks ORDER BY paddock_name')
    paddocks_data = cursor.fetchall()

    # Recalculate pasture growth and consumption
    paddocks_data = recalculate_pasture(paddocks_data)

    cursor.close()
    connection.close()
    return render_template('paddocks.html', paddocks=paddocks_data, curr_date=session['curr_date'])

# Route to move mobs between paddocks
@app.route('/move_mob', methods=['POST'])
def move_mob():
    mob_id = request.form['mob_id']
    new_paddock_id = request.form['new_paddock_id']

    connection = get_db_connection()
    if connection is None:
        flash('Database connection failed', 'danger')
        return redirect(url_for('mobs'))

    cursor = connection.cursor()
    try:
        cursor.execute('UPDATE mobs SET paddock_id = %s WHERE id = %s', (new_paddock_id, mob_id))
        connection.commit()
        flash('Mob successfully moved to a new paddock', 'success')
    except mysql.connector.Error as err:
        flash(f'Error: {err}', 'danger')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('mobs'))

# Advance the date and recalculate pasture levels
@app.route('/advance_date')
def advance_date():
    # Advance the date by 1 day
    curr_date = datetime.strptime(session['curr_date'], '%Y-%m-%d')
    new_date = curr_date + timedelta(days=1)
    session['curr_date'] = new_date.strftime('%Y-%m-%d')

    connection = get_db_connection()
    if connection is None:
        flash('Database connection failed', 'danger')
        return redirect(url_for('paddocks'))

    # Recalculate pasture for the new day
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM paddocks')
    paddocks_data = cursor.fetchall()
    paddocks_data = recalculate_pasture(paddocks_data)

    # Update the recalculated data into the database
    try:
        for paddock in paddocks_data:
            cursor.execute('''
                UPDATE paddocks
                SET total_dm = %s, dm_per_ha = %s
                WHERE id = %s
            ''', (paddock['total_dm'], paddock['dm_per_ha'], paddock['id']))

        connection.commit()
        flash('Date advanced and pasture recalculated', 'success')
    except mysql.connector.Error as err:
        flash(f'Error updating pasture data: {err}', 'danger')
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('paddocks'))

# Route to display farms
@app.route('/farms')
def farms():
    connection = get_db_connection()
    if connection is None:
        flash('Database connection failed', 'danger')
        return redirect(url_for('home'))

    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM farms ORDER BY farm_name')
    farms_data = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('farms.html', farms=farms_data)

# Comment this out when deploying to PythonAnywhere
# if __name__ == '__main__':
#     app.run(debug=False)  # Keep debug=True only for local development
