# habit_management.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sqlite3
import datetime

# ------------------- Database Setup -------------------
def create_connection():
    return sqlite3.connect('habit_tracker.db')

def create_tables():
    conn = create_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Habits table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            date DATETIME NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()
    conn.close()

# Call table creation function
create_tables()

# ------------------- Authentication -------------------
def register_user(username, password):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        st.error(f"Registration failed: {e}")
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user

# ------------------- Habit Management -------------------
def load_user_habits(user_id):
    conn = create_connection()
    query = "SELECT * FROM habits WHERE user_id=?"
    habits = pd.read_sql(query, conn, params=(user_id,))
    conn.close()
    if "date" in habits.columns:
        habits["date"] = pd.to_datetime(habits["date"], errors="coerce")
    return habits

def add_habit(user_id, habit_name, notes):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO habits (user_id, name, date, status, notes) VALUES (?, ?, ?, ?, ?)",
                   (user_id, habit_name, datetime.datetime.now(), 'Started', notes))
    conn.commit()
    conn.close()

def log_habit_progress(user_id, habit_name, status):
    conn = create_connection()
    cursor = conn.cursor()
    current_time = datetime.datetime.now()
    cursor.execute(
        "INSERT INTO habits (user_id, name, date, status) VALUES (?, ?, ?, ?)",
        (user_id, habit_name, current_time, status)
    )
    conn.commit()
    conn.close()

# ------------------- Streaks & Visualization -------------------
def calculate_streaks(habit_data):
    streaks = {}
    for habit in habit_data["name"].unique():
        dates = habit_data[habit_data["name"] == habit]["date"].sort_values()
        max_streak, current_streak = 0, 0
        prev_date = None
        for date in dates:
            if prev_date and (date - prev_date).days == 1:
                current_streak += 1
            else:
                current_streak = 1
            max_streak = max(max_streak, current_streak)
            prev_date = date
        streaks[habit] = max_streak
    return streaks

def plot_pie_chart(filtered_data, selected_habit):
    status_counts = filtered_data["status"].value_counts()
    fig, ax = plt.subplots()
    status_counts.plot.pie(autopct="%1.1f%%", startangle=90, ax=ax, colors=["green", "red", "orange"])
    ax.set_ylabel('')
    return fig

def plot_heatmap(filtered_data):
    heatmap_data = filtered_data.pivot_table(index="date", columns="status", aggfunc="size", fill_value=0)
    heatmap_data.index = heatmap_data.index.date
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_yticks(range(len(heatmap_data.index)))
    ax.set_yticklabels([str(date) for date in heatmap_data.index], rotation=0)
    sns.heatmap(heatmap_data, annot=True, fmt="d", cmap="coolwarm", ax=ax)
    return fig

# ------------------- Streamlit UI -------------------
st.set_page_config(page_title="Habit Tracker", layout="wide")
st.title("📊 Enhanced Habit Tracker Application")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if 'habits_data' not in st.session_state:
    st.session_state.habits_data = pd.DataFrame(columns=["id", "user_id", "name", "date", "status", "notes"])

# ------------------- Sidebar Auth -------------------
st.sidebar.subheader("User Authentication")
auth_option = st.sidebar.radio("Select an option:", ["Login", "Register"])

if auth_option == "Register":
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type='password')
    confoirm_password = st.sidebar.text_input("Confirm Password", type='password')
    if st.sidebar.button("Register"):
        if not username or not password:
            st.error("Username and password cannot be empty.")
        elif register_user(username, password):
            st.success("Registered successfully!")
        elif not password or not confoirm_password:
            st.error("Password cannot be empty.")
        elif password != confoirm_password:
            st.error("Passwords do not match.")
        elif st.sidebar.button("Clear"):
            st.sidebar.text_input("Username", value="")
            st.sidebar.text_input("Password", value="")
            st.sidebar.text_input("Confirm Password", value="")
            st.success("Input fields cleared.")            
        else:
            st.error("Username already exists or error occurred.")

            
                
elif auth_option == "Login":
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type='password')
    if st.sidebar.button("Login"):
        if not username or not password:
            st.error("Username and password cannot be empty.")
        else:
            user = login_user(username, password)
            if user:
                st.session_state.user_id = user[0]
                st.session_state.logged_in = True
                st.session_state.habits_data = load_user_habits(st.session_state.user_id)
                st.success(f"Welcome back, {username}!")
            else:
                st.error("Invalid credentials.")
                
            

# ------------------- Main App -------------------
if st.session_state.logged_in:
    menu = st.sidebar.radio("Menu", ["Add Habit", "Log Habit", "View Habits", "Visualize Habits", "Dashboard"])

    if menu == "Add Habit":
        st.subheader("📝 Add a New Habit")
        new_habit = st.text_input("Habit Name:")
        notes = st.text_area("Notes (optional):")
        if st.button("Add Habit"):
            if new_habit:
                add_habit(st.session_state.user_id, new_habit, notes)
                st.session_state.habits_data = load_user_habits(st.session_state.user_id)
                st.success("Habit added successfully.")
            else:
                st.error("Habit name cannot be empty.")

    elif menu == "Log Habit":
        st.subheader("📅 Log Habit Progress")
        if not st.session_state.habits_data.empty:
            habit_names = st.session_state.habits_data["name"].unique()
            selected_habit = st.selectbox("Select a Habit:", habit_names)   
            log_status = st.radio("Status:", ["completed", "inprogress", "skipped"], horizontal=True)
            if st.button("Log Progress"):
                log_habit_progress(st.session_state.user_id, selected_habit, log_status)
                st.session_state.habits_data = load_user_habits(st.session_state.user_id)
                st.success(f"Progress for '{selected_habit}' logged as '{log_status}'.")
        else:
            st.warning("No habits added yet.")

    elif menu == "View Habits":
        st.subheader("📄 Your Habit History")
        if st.session_state.habits_data.empty:
            st.info("No habit logs available.")
        else:
            st.dataframe(st.session_state.habits_data)

    elif menu == "Visualize Habits":
        st.subheader("📊 Visualize Your Habit Progress")
        if st.session_state.habits_data.empty:
            st.info("No habit data available for visualization.")
        else:
            habit_names = st.session_state.habits_data["name"].unique()
            selected_habit = st.selectbox("Select a habit to visualize:", habit_names)

            start_date = st.date_input("Start Date", value=st.session_state.habits_data["date"].min().date())
            end_date = st.date_input("End Date", value=st.session_state.habits_data["date"].max().date())

            filtered_data  = st.session_state.habits_data[
                (st.session_state.habits_data["name"] == selected_habit) &
                (st.session_state.habits_data["date"].dt.date >= start_date) &
                (st.session_state.habits_data["date"].dt.date <= end_date)
            ]

            if filtered_data.empty:
                st.warning("No data available for the selected habit and date range.")
            else:
                st.pyplot(plot_pie_chart(filtered_data, selected_habit))
                st.pyplot(plot_heatmap(filtered_data))

                total_logs = len(filtered_data)
                completed_logs = len(filtered_data[filtered_data["status"] == "completed"])
                success_rate = (completed_logs / total_logs) * 100 if total_logs else 0
                st.metric("Success Rate", f"{success_rate:.2f}%")

                streaks = calculate_streaks(st.session_state.habits_data)
                st.metric("Longest Streak", f"{streaks.get(selected_habit, 0)} days")