import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import hashlib
import datetime
import os
import random

# Database setup
def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('carbon_tracker.db')
    cursor = conn.cursor()
    
    # Create users table with additional profile fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            first_name TEXT DEFAULT '',
            last_name TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            location TEXT DEFAULT '',
            profile_picture TEXT DEFAULT '',
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create carbon_footprint table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS carbon_footprint (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            electricity_kwh REAL DEFAULT 0,
            natural_gas_therms REAL DEFAULT 0,
            water_gallons REAL DEFAULT 0,
            car_miles REAL DEFAULT 0,
            public_transit_miles REAL DEFAULT 0,
            flights_short_haul INTEGER DEFAULT 0,
            flights_long_haul INTEGER DEFAULT 0,
            meat_servings INTEGER DEFAULT 0,
            dairy_servings INTEGER DEFAULT 0,
            veg_servings INTEGER DEFAULT 0,
            total_carbon REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create user_streaks table for tracking streaks
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_streaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            current_streak INTEGER DEFAULT 0,
            longest_streak INTEGER DEFAULT 0,
            last_entry_date DATE,
            total_entries INTEGER DEFAULT 0,
            streak_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Add profile columns to existing users table if they don't exist
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN first_name TEXT DEFAULT ""')
        cursor.execute('ALTER TABLE users ADD COLUMN last_name TEXT DEFAULT ""')
        cursor.execute('ALTER TABLE users ADD COLUMN bio TEXT DEFAULT ""')
        cursor.execute('ALTER TABLE users ADD COLUMN location TEXT DEFAULT ""')
        cursor.execute('ALTER TABLE users ADD COLUMN profile_picture TEXT DEFAULT ""')
    except sqlite3.OperationalError:
        pass  # Columns already exist
    
    # Add total_carbon column to existing carbon_footprint table if it doesn't exist
    try:
        cursor.execute('ALTER TABLE carbon_footprint ADD COLUMN total_carbon REAL DEFAULT 0')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Create default admin user if it doesn't exist
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        admin_password = hash_password('admin123')
        cursor.execute(
            'INSERT INTO users (username, password, email, is_admin, first_name, last_name) VALUES (?, ?, ?, ?, ?, ?)',
            ('admin', admin_password, 'admin@carbontracker.com', 1, 'System', 'Administrator')
        )
        
        # Create streak record for admin
        admin_id = cursor.lastrowid
        cursor.execute(
            'INSERT INTO user_streaks (user_id) VALUES (?)',
            (admin_id,)
        )
    
    conn.commit()
    conn.close()

# Database connection
@st.cache_resource
def get_db_connection():
    """Get database connection"""
    try:
        conn = sqlite3.connect('carbon_tracker.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        st.stop()

def run_query(query, params=None, fetch=True):
    """Execute SQL query"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        
        if fetch:
            result = [dict(row) for row in cursor.fetchall()]
        else:
            conn.commit()
            result = None
            
        cursor.close()
        return result
    except Exception as e:
        st.error(f"Database query error: {e}")
        return None

# Hash password for security
def hash_password(password):
    """Create SHA-256 hash of password"""
    return hashlib.sha256(password.encode()).hexdigest()

# Authentication functions
def login_user(username, password):
    """Authenticate user with username and password"""
    hashed_password = hash_password(password)
    query = "SELECT * FROM users WHERE username = ? AND password = ?"
    users = run_query(query, (username, hashed_password))
    
    if users and len(users) > 0:
        return True, users[0]
    else:
        return False, None

def register_user(username, password, email, first_name="", last_name=""):
    """Register a new user"""
    # Check if username or email already exists
    query = "SELECT COUNT(*) as count FROM users WHERE username = ? OR email = ?"
    result = run_query(query, (username, email))
    
    if result and result[0]['count'] > 0:
        return False, "Username or email already exists"
    
    hashed_password = hash_password(password)
    try:
        query = "INSERT INTO users (username, password, email, first_name, last_name) VALUES (?, ?, ?, ?, ?)"
        run_query(query, (username, hashed_password, email, first_name, last_name), fetch=False)
        
        # Get the new user ID and create streak record
        user_query = "SELECT id FROM users WHERE username = ?"
        user_result = run_query(user_query, (username,))
        if user_result:
            user_id = user_result[0]['id']
            streak_query = "INSERT INTO user_streaks (user_id) VALUES (?)"
            run_query(streak_query, (user_id,), fetch=False)
        
        return True, "Registration successful"
    except Exception as e:
        return False, f"Registration error: {e}"

def change_password(user_id, old_password, new_password):
    """Change user password"""
    # Verify old password
    old_hashed = hash_password(old_password)
    query = "SELECT COUNT(*) as count FROM users WHERE id = ? AND password = ?"
    result = run_query(query, (user_id, old_hashed))
    
    if not result or result[0]['count'] == 0:
        return False, "Current password is incorrect"
    
    # Update password
    new_hashed = hash_password(new_password)
    update_query = "UPDATE users SET password = ? WHERE id = ?"
    try:
        run_query(update_query, (new_hashed, user_id), fetch=False)
        return True, "Password updated successfully"
    except Exception as e:
        return False, f"Error updating password: {e}"

def update_user_profile(user_id, profile_data):
    """Update user profile information"""
    query = """
    UPDATE users SET 
        first_name = ?, last_name = ?, bio = ?, location = ?, email = ?
    WHERE id = ?
    """
    try:
        run_query(query, (
            profile_data['first_name'],
            profile_data['last_name'],
            profile_data['bio'],
            profile_data['location'],
            profile_data['email'],
            user_id
        ), fetch=False)
        return True, "Profile updated successfully"
    except Exception as e:
        return False, f"Error updating profile: {e}"

def get_user_profile(user_id):
    """Get user profile information"""
    query = "SELECT * FROM users WHERE id = ?"
    result = run_query(query, (user_id,))
    return result[0] if result else None

# Streak functions
def update_user_streak(user_id, entry_date):
    """Update user streak based on new entry"""
    # Get current streak info
    streak_query = "SELECT * FROM user_streaks WHERE user_id = ?"
    streak_result = run_query(streak_query, (user_id,))
    
    if not streak_result:
        # Create new streak record
        insert_query = "INSERT INTO user_streaks (user_id, current_streak, longest_streak, last_entry_date, total_entries) VALUES (?, ?, ?, ?, ?)"
        run_query(insert_query, (user_id, 1, 1, entry_date, 1), fetch=False)
        return
    
    streak_data = streak_result[0]
    current_streak = streak_data['current_streak']
    longest_streak = streak_data['longest_streak']
    last_entry_date = streak_data['last_entry_date']
    total_entries = streak_data['total_entries']
    
    # Convert string date to date object if needed
    if isinstance(entry_date, str):
        entry_date = datetime.datetime.strptime(entry_date, '%Y-%m-%d').date()
    if isinstance(last_entry_date, str):
        last_entry_date = datetime.datetime.strptime(last_entry_date, '%Y-%m-%d').date()
    
    # Calculate new streak
    if last_entry_date:
        days_diff = (entry_date - last_entry_date).days
        if days_diff == 1:  # Consecutive day
            current_streak += 1
        elif days_diff == 0:  # Same day (don't count)
            return
        else:  # Gap in days
            current_streak = 1
    else:
        current_streak = 1
    
    # Update longest streak if current is longer
    longest_streak = max(longest_streak, current_streak)
    total_entries += 1
    
    # Update database
    update_query = """
    UPDATE user_streaks SET 
        current_streak = ?, longest_streak = ?, last_entry_date = ?, 
        total_entries = ?, streak_updated_at = CURRENT_TIMESTAMP
    WHERE user_id = ?
    """
    run_query(update_query, (current_streak, longest_streak, entry_date, total_entries, user_id), fetch=False)

def get_user_streak(user_id):
    """Get user streak information"""
    query = "SELECT * FROM user_streaks WHERE user_id = ?"
    result = run_query(query, (user_id,))
    return result[0] if result else None

# Carbon footprint calculation functions
def calculate_electricity_carbon(kwh):
    """Calculate CO2 from electricity usage (kg)"""
    return kwh * 0.4  # Average emissions factor

def calculate_natural_gas_carbon(therms):
    """Calculate CO2 from natural gas usage (kg)"""
    return therms * 5.3  # CO2 per therm

def calculate_water_carbon(gallons):
    """Calculate CO2 from water usage (kg)"""
    return gallons * 0.0002  # Energy for pumping/treatment

def calculate_car_carbon(miles, efficiency=25):
    """Calculate CO2 from car travel (kg)"""
    gallons = miles / efficiency
    return gallons * 8.887  # Average CO2 per gallon of gasoline

def calculate_public_transit_carbon(miles):
    """Calculate CO2 from public transit (kg)"""
    return miles * 0.17  # Average across modes

def calculate_flight_carbon(short_flights, long_flights):
    """Calculate CO2 from flights (kg)"""
    return (short_flights * 500) + (long_flights * 1600)  # Approximate per flight

def calculate_food_carbon(meat_servings, dairy_servings, veg_servings):
    """Calculate CO2 from food consumption (kg)"""
    meat_carbon = meat_servings * 3.0  # Higher carbon impact
    dairy_carbon = dairy_servings * 0.7  # Medium carbon impact
    veg_carbon = veg_servings * 0.2  # Lower carbon impact
    return meat_carbon + dairy_carbon + veg_carbon

def calculate_total_carbon(data):
    """Calculate total carbon footprint from all sources"""
    total = 0
    if data.get('electricity_kwh'):
        total += calculate_electricity_carbon(data['electricity_kwh'])
    if data.get('natural_gas_therms'):
        total += calculate_natural_gas_carbon(data['natural_gas_therms'])
    if data.get('water_gallons'):
        total += calculate_water_carbon(data['water_gallons'])
    if data.get('car_miles'):
        total += calculate_car_carbon(data['car_miles'])
    if data.get('public_transit_miles'):
        total += calculate_public_transit_carbon(data['public_transit_miles'])
    if data.get('flights_short_haul') or data.get('flights_long_haul'):
        total += calculate_flight_carbon(
            data.get('flights_short_haul', 0),
            data.get('flights_long_haul', 0)
        )
    if data.get('meat_servings') or data.get('dairy_servings') or data.get('veg_servings'):
        total += calculate_food_carbon(
            data.get('meat_servings', 0),
            data.get('dairy_servings', 0),
            data.get('veg_servings', 0)
        )
    return total

# Database operations
def save_carbon_footprint(user_id, data):
    """Save carbon footprint entry to database"""
    total_carbon = calculate_total_carbon(data)
    
    query = """
    INSERT INTO carbon_footprint 
    (user_id, date, electricity_kwh, natural_gas_therms, water_gallons, 
    car_miles, public_transit_miles, flights_short_haul, flights_long_haul, 
    meat_servings, dairy_servings, veg_servings, total_carbon)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    try:
        run_query(query, (
            user_id,
            data.get('date', datetime.date.today()),
            data.get('electricity_kwh', 0),
            data.get('natural_gas_therms', 0),
            data.get('water_gallons', 0),
            data.get('car_miles', 0),
            data.get('public_transit_miles', 0),
            data.get('flights_short_haul', 0),
            data.get('flights_long_haul', 0),
            data.get('meat_servings', 0),
            data.get('dairy_servings', 0),
            data.get('veg_servings', 0),
            total_carbon
        ), fetch=False)
        
        # Update user streak
        update_user_streak(user_id, data.get('date', datetime.date.today()))
        
        return True
    except Exception as e:
        st.error(f"Error saving data: {e}")
        return False

def get_user_footprint_history(user_id):
    """Get carbon footprint history for a user"""
    query = """
    SELECT * FROM carbon_footprint
    WHERE user_id = ?
    ORDER BY date DESC
    """
    results = run_query(query, (user_id,))
    
    if results:
        return pd.DataFrame(results)
    else:
        return pd.DataFrame()

def get_all_users():
    """Get all users for admin dashboard"""
    query = "SELECT id, username, email, first_name, last_name, created_at, is_admin FROM users"
    results = run_query(query)
    
    if results:
        return pd.DataFrame(results)
    else:
        return pd.DataFrame()

def get_all_carbon_entries():
    """Get all carbon footprint entries for admin dashboard"""
    query = """
    SELECT cf.*, u.username 
    FROM carbon_footprint cf
    JOIN users u ON cf.user_id = u.id
    ORDER BY cf.date DESC
    """
    results = run_query(query)
    
    if results:
        return pd.DataFrame(results)
    else:
        return pd.DataFrame()

def get_dashboard_stats(user_id):
    """Get comprehensive dashboard statistics for a user"""
    # Get user's carbon footprint data
    history_df = get_user_footprint_history(user_id)
    
    if history_df.empty:
        return None
    
    # Calculate various statistics
    stats = {}
    
    # Basic stats
    stats['total_entries'] = len(history_df)
    stats['total_carbon'] = history_df['total_carbon'].sum()
    stats['avg_carbon'] = history_df['total_carbon'].mean()
    stats['min_carbon'] = history_df['total_carbon'].min()
    stats['max_carbon'] = history_df['total_carbon'].max()
    
    # Weekly/Monthly trends
    history_df['date'] = pd.to_datetime(history_df['date'])
    history_df['week'] = history_df['date'].dt.isocalendar().week
    history_df['month'] = history_df['date'].dt.month
    
    # Recent vs older comparison (last 30 days vs previous 30 days)
    today = datetime.date.today()
    last_30_days = today - datetime.timedelta(days=30)
    prev_30_days = today - datetime.timedelta(days=60)
    
    recent_data = history_df[history_df['date'] >= str(last_30_days)]
    previous_data = history_df[(history_df['date'] >= str(prev_30_days)) & (history_df['date'] < str(last_30_days))]
    
    stats['recent_avg'] = recent_data['total_carbon'].mean() if not recent_data.empty else 0
    stats['previous_avg'] = previous_data['total_carbon'].mean() if not previous_data.empty else 0
    stats['trend'] = 'improving' if stats['recent_avg'] < stats['previous_avg'] else 'worsening' if stats['recent_avg'] > stats['previous_avg'] else 'stable'
    
    # Category breakdown
    category_totals = {
        'electricity': history_df['electricity_kwh'].sum() * 0.4,
        'natural_gas': history_df['natural_gas_therms'].sum() * 5.3,
        'water': history_df['water_gallons'].sum() * 0.0002,
        'car': (history_df['car_miles'].sum() / 25) * 8.887,
        'transit': history_df['public_transit_miles'].sum() * 0.17,
        'flights': (history_df['flights_short_haul'].sum() * 500) + (history_df['flights_long_haul'].sum() * 1600),
        'food': (history_df['meat_servings'].sum() * 3.0) + (history_df['dairy_servings'].sum() * 0.7) + (history_df['veg_servings'].sum() * 0.2)
    }
    
    stats['category_breakdown'] = category_totals
    
    return stats

# UI Functions
def login_page():
    """Render login page"""
    st.subheader("Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
    
    if submit_button:
        if username and password:
            success, user = login_user(username, password)
            if success:
                st.session_state['logged_in'] = True
                st.session_state['user'] = user
                st.session_state['username'] = user['username']
                st.session_state['user_id'] = user['id']
                st.session_state['is_admin'] = bool(user['is_admin'])
                st.success(f"Welcome back, {username}!")
                st.rerun()
            else:
                st.error("Invalid username or password")
        else:
            st.warning("Please enter both username and password")
    
    st.write("---")
    st.write("Don't have an account?")
    if st.button("Register"):
        st.session_state['auth_page'] = "register"
        st.rerun()

def register_page():
    """Render registration page"""
    st.subheader("Create an Account")
    
    with st.form("registration_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
        with col2:
            last_name = st.text_input("Last Name")
            email = st.text_input("Email")
            confirm_password = st.text_input("Confirm Password", type="password")
        
        submit_button = st.form_submit_button("Register")
    
    if submit_button:
        if not username or not email or not password or not confirm_password:
            st.warning("Please fill in all required fields")
        elif password != confirm_password:
            st.error("Passwords do not match")
        else:
            success, message = register_user(username, password, email, first_name, last_name)
            if success:
                st.success(message)
                st.session_state['auth_page'] = "login"
                st.rerun()
            else:
                st.error(message)
    
    st.write("---")
    st.write("Already have an account?")
    if st.button("Login"):
        st.session_state['auth_page'] = "login"
        st.rerun()

def profile_page():
    """Render user profile page"""
    st.subheader("👤 Your Profile")
    
    # Get current profile data
    profile = get_user_profile(st.session_state['user_id'])
    
    if profile:
        # Profile editing form
        with st.form("profile_form"):
            st.write("### Personal Information")
            col1, col2 = st.columns(2)
            
            with col1:
                first_name = st.text_input("First Name", value=profile.get('first_name', ''))
                email = st.text_input("Email", value=profile.get('email', ''))
                location = st.text_input("Location", value=profile.get('location', ''))
            
            with col2:
                last_name = st.text_input("Last Name", value=profile.get('last_name', ''))
                bio = st.text_area("Bio", value=profile.get('bio', ''), height=100)
            
            if st.form_submit_button("Update Profile"):
                profile_data = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'bio': bio,
                    'location': location
                }
                
                success, message = update_user_profile(st.session_state['user_id'], profile_data)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        st.write("---")
        
        # Password change section
        with st.expander("🔒 Change Password"):
            with st.form("password_form"):
                current_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                confirm_new_password = st.text_input("Confirm New Password", type="password")
                
                if st.form_submit_button("Change Password"):
                    if not current_password or not new_password or not confirm_new_password:
                        st.warning("Please fill in all password fields")
                    elif new_password != confirm_new_password:
                        st.error("New passwords do not match")
                    else:
                        success, message = change_password(st.session_state['user_id'], current_password, new_password)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)

def calculate_page():
    """Render carbon calculation page"""
    st.subheader("Calculate Your Carbon Footprint")
    
    with st.form("carbon_calculator_form"):
        date = st.date_input("Date", value=datetime.date.today())
        
        # Home Energy
        st.write("#### 🏠 Home Energy")
        col1, col2 = st.columns(2)
        with col1:
            electricity_kwh = st.number_input("Electricity (kWh)", min_value=0.0, value=0.0, 
                                            help="Average US household uses ~900 kWh per month")
            natural_gas_therms = st.number_input("Natural Gas (therms)", min_value=0.0, value=0.0,
                                               help="Average US household uses ~70 therms per month")
        with col2:
            water_gallons = st.number_input("Water (gallons)", min_value=0.0, value=0.0,
                                          help="Average US household uses ~3,000 gallons per month")
        
        # Transportation
        st.write("#### 🚗 Transportation")
        col1, col2 = st.columns(2)
        with col1:
            car_miles = st.number_input("Car Travel (miles)", min_value=0.0, value=0.0,
                                      help="Average American drives ~1,000 miles per month")
            public_transit_miles = st.number_input("Public Transit (miles)", min_value=0.0, value=0.0)
        with col2:
            flights_short_haul = st.number_input("Short Flights (<3 hours)", min_value=0, value=0)
            flights_long_haul = st.number_input("Long Flights (>3 hours)", min_value=0, value=0)
        
        # Food
        st.write("#### 🥗 Food")
        col1, col2, col3 = st.columns(3)
        with col1:
            meat_servings = st.number_input("Meat (servings per day)", min_value=0, value=0,
                                          help="A serving is about 4oz (113g)")
        with col2:
            dairy_servings = st.number_input("Dairy (servings per day)", min_value=0, value=0,
                                           help="Includes milk, cheese, yogurt")
        with col3:
            veg_servings = st.number_input("Plant-based meals (per day)", min_value=0, value=0)
        
        submit_button = st.form_submit_button("Calculate & Save")
    
    if submit_button:
        data = {
            'date': date,
            'electricity_kwh': electricity_kwh,
            'natural_gas_therms': natural_gas_therms,
            'water_gallons': water_gallons,
            'car_miles': car_miles,
            'public_transit_miles': public_transit_miles,
            'flights_short_haul': flights_short_haul,
            'flights_long_haul': flights_long_haul,
            'meat_servings': meat_servings,
            'dairy_servings': dairy_servings,
            'veg_servings': veg_servings
        }
        
        # Calculate and display results
        total_carbon = calculate_total_carbon(data)
        
        st.write("## Your Carbon Footprint Results")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Carbon Footprint", f"{total_carbon:.2f} kg CO2")
        with col2:
            # Compare to daily average
            daily_avg = 49.3  # Global average daily CO2 per person
            comparison = ((total_carbon - daily_avg) / daily_avg) * 100
            st.metric("vs Global Average", f"{comparison:+.1f}%")
        with col3:
            # Trees needed to offset
            trees_needed = total_carbon / 21.77  # kg CO2 absorbed per tree per year
            st.metric("Trees to Offset", f"{trees_needed:.1f}")
        
        # Save to database
        if save_carbon_footprint(st.session_state['user_id'], data):
            st.success("✅ Carbon footprint data saved successfully!")
            
            # Show updated streak
            streak_info = get_user_streak(st.session_state['user_id'])
            if streak_info:
                st.info(f"🔥 Current streak: {streak_info['current_streak']} days!")
        else:
            st.error("❌ Error saving data to database")

def history_page():
    """Render history page"""
    st.subheader("📊 Your Carbon Footprint History")
    
    # Get user history
    history_df = get_user_footprint_history(st.session_state['user_id'])
    
    if history_df.empty:
        st.info("You haven't recorded any carbon footprint data yet. Go to the Calculate page to get started!")
    else:
        # Display summary statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Entries", len(history_df))
        with col2:
            st.metric("Total Carbon", f"{history_df['total_carbon'].sum():.2f} kg CO2")
        with col3:
            st.metric("Average per Day", f"{history_df['total_carbon'].mean():.2f} kg CO2")
        with col4:
            latest_entry = history_df.iloc[0]['date']
            st.metric("Latest Entry", latest_entry)
        
        # Plot carbon footprint over time
        if len(history_df) > 1:
            fig = px.line(history_df.sort_values('date'), 
                         x='date', y='total_carbon',
                         title='Carbon Footprint Over Time',
                         labels={'total_carbon': 'CO2 (kg)', 'date': 'Date'})
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Display data table
        st.write("### Detailed History")
        st.dataframe(history_df, use_container_width=True)

# Continuing from dashboard_page() function...

def dashboard_page():
    """Render enhanced dashboard page"""
    st.subheader("📈 Your Carbon Dashboard")
    
    # Get user streak information
    streak_info = get_user_streak(st.session_state['user_id'])
    stats = get_dashboard_stats(st.session_state['user_id'])
    
    if not stats:
        st.info("You haven't recorded any carbon footprint data yet. Go to the Calculate page to get started!")
        return
    
    # Display streak information
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🔥 Current Streak", f"{streak_info['current_streak']} days" if streak_info else "0 days")
    with col2:
        st.metric("🏆 Longest Streak", f"{streak_info['longest_streak']} days" if streak_info else "0 days")
    with col3:
        st.metric("📊 Total Entries", f"{streak_info['total_entries']}" if streak_info else "0")
    with col4:
        trend_emoji = "📈" if stats['trend'] == 'worsening' else "📉" if stats['trend'] == 'improving' else "➡️"
        st.metric(f"{trend_emoji} Trend", stats['trend'].title())
    
    # Carbon footprint summary
    st.write("### Carbon Footprint Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Carbon", f"{stats['total_carbon']:.2f} kg CO2")
    with col2:
        st.metric("Daily Average", f"{stats['avg_carbon']:.2f} kg CO2")
    with col3:
        st.metric("Recent 30-day Avg", f"{stats['recent_avg']:.2f} kg CO2")
    
    # Category breakdown pie chart
    st.write("### Carbon Sources Breakdown")
    category_data = stats['category_breakdown']
    
    # Filter out zero values
    filtered_categories = {k: v for k, v in category_data.items() if v > 0}
    
    if filtered_categories:
        fig = px.pie(
            values=list(filtered_categories.values()),
            names=list(filtered_categories.keys()),
            title="Carbon Footprint by Category"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Historical trend
    history_df = get_user_footprint_history(st.session_state['user_id'])
    if len(history_df) > 1:
        st.write("### Historical Trends")
        
        # Sort by date
        history_df_sorted = history_df.sort_values('date')
        
        # Create line chart
        fig = px.line(history_df_sorted, 
                     x='date', y='total_carbon',
                     title='Carbon Footprint Trend',
                     labels={'total_carbon': 'CO2 (kg)', 'date': 'Date'})
        
        # Add average line
        avg_line = stats['avg_carbon']
        fig.add_hline(y=avg_line, line_dash="dash", 
                     annotation_text=f"Average: {avg_line:.2f} kg CO2")
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent entries
    st.write("### Recent Entries")
    recent_entries = history_df.head(5)
    if not recent_entries.empty:
        st.dataframe(recent_entries[['date', 'total_carbon', 'electricity_kwh', 'car_miles', 'meat_servings']], 
                    use_container_width=True)

def admin_page():
    """Render admin dashboard page"""
    if not st.session_state.get('is_admin', False):
        st.error("Access denied. Admin privileges required.")
        return
    
    st.subheader("🔧 Admin Dashboard")
    
    # Admin tabs
    tab1, tab2, tab3 = st.tabs(["Users", "Carbon Data", "System Stats"])
    
    with tab1:
        st.write("### User Management")
        users_df = get_all_users()
        
        if not users_df.empty:
            st.dataframe(users_df, use_container_width=True)
            
            # User statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Users", len(users_df))
            with col2:
                admin_count = users_df['is_admin'].sum()
                st.metric("Admin Users", admin_count)
            with col3:
                recent_users = len(users_df[users_df['created_at'] >= (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')])
                st.metric("New Users (30d)", recent_users)
        else:
            st.info("No users found")
    
    with tab2:
        st.write("### Carbon Footprint Data")
        carbon_df = get_all_carbon_entries()
        
        if not carbon_df.empty:
            # Summary statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Entries", len(carbon_df))
            with col2:
                st.metric("Total Carbon", f"{carbon_df['total_carbon'].sum():.2f} kg CO2")
            with col3:
                st.metric("Average per Entry", f"{carbon_df['total_carbon'].mean():.2f} kg CO2")
            with col4:
                active_users = carbon_df['user_id'].nunique()
                st.metric("Active Users", active_users)
            
            # Recent entries
            st.write("#### Recent Entries")
            recent_entries = carbon_df.head(10)
            st.dataframe(recent_entries[['date', 'username', 'total_carbon', 'electricity_kwh', 'car_miles']], 
                        use_container_width=True)
            
            # Carbon trends
            if len(carbon_df) > 1:
                st.write("#### System-wide Carbon Trends")
                daily_totals = carbon_df.groupby('date')['total_carbon'].sum().reset_index()
                daily_totals = daily_totals.sort_values('date')
                
                fig = px.bar(daily_totals, x='date', y='total_carbon',
                           title='Daily Carbon Footprint (All Users)',
                           labels={'total_carbon': 'Total CO2 (kg)', 'date': 'Date'})
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No carbon footprint data found")
    
    with tab3:
        st.write("### System Statistics")
        
        # Database info
        users_df = get_all_users()
        carbon_df = get_all_carbon_entries()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("#### Database Status")
            st.info(f"Users table: {len(users_df)} records")
            st.info(f"Carbon footprint table: {len(carbon_df)} records")
            
            # Check database health
            try:
                # Test database connection
                test_query = "SELECT COUNT(*) as count FROM users"
                result = run_query(test_query)
                if result:
                    st.success("✅ Database connection healthy")
                else:
                    st.error("❌ Database connection issues")
            except Exception as e:
                st.error(f"❌ Database error: {e}")
        
        with col2:
            st.write("#### Usage Statistics")
            if not carbon_df.empty:
                # Most active users
                user_activity = carbon_df.groupby('username').size().sort_values(ascending=False).head(5)
                st.write("**Most Active Users:**")
                for username, count in user_activity.items():
                    st.write(f"• {username}: {count} entries")
                
                # Recent activity
                recent_activity = len(carbon_df[carbon_df['created_at'] >= (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')])
                st.metric("Entries This Week", recent_activity)

def logout():
    """Handle user logout"""
    for key in ['logged_in', 'user', 'username', 'user_id', 'is_admin']:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state['auth_page'] = 'login'
    st.rerun()

def main():
    """Main application function"""
    # Initialize database
    init_database()
    
    # Set page configuration
    st.set_page_config(
        page_title="Carbon Footprint Tracker",
        page_icon="🌱",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'auth_page' not in st.session_state:
        st.session_state['auth_page'] = 'login'
    
    # App header
    st.title("🌱 Carbon Footprint Tracker")
    st.markdown("Track, analyze, and reduce your environmental impact")
    
    # Authentication check
    if not st.session_state['logged_in']:
        # Authentication pages
        if st.session_state['auth_page'] == 'login':
            login_page()
        elif st.session_state['auth_page'] == 'register':
            register_page()
    else:
        # Sidebar navigation
        with st.sidebar:
            st.write(f"Welcome, **{st.session_state['username']}**!")
            
            # Navigation menu
            pages = ["Dashboard", "Calculate", "History", "Profile"]
            if st.session_state.get('is_admin', False):
                pages.append("Admin")
            
            selected_page = st.selectbox("Navigation", pages)
            
            # User stats in sidebar
            streak_info = get_user_streak(st.session_state['user_id'])
            if streak_info:
                st.write("---")
                st.write("**Your Stats:**")
                st.write(f"🔥 Current Streak: {streak_info['current_streak']} days")
                st.write(f"🏆 Best Streak: {streak_info['longest_streak']} days")
                st.write(f"📊 Total Entries: {streak_info['total_entries']}")
            
            st.write("---")
            if st.button("Logout", use_container_width=True):
                logout()
        
        # Main content area
        if selected_page == "Dashboard":
            dashboard_page()
        elif selected_page == "Calculate":
            calculate_page()
        elif selected_page == "History":
            history_page()
        elif selected_page == "Profile":
            profile_page()
        elif selected_page == "Admin" and st.session_state.get('is_admin', False):
            admin_page()

if __name__ == "__main__":
    main()