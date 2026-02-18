import streamlit as st
import pandas as pd
from database import create_tables, connect
from auth import register, login, ROLES, create_developer
from utils import validate_password, now, format_datetime, calculate_minutes
from datetime import datetime

create_tables()
create_developer()

if "user" not in st.session_state:
    st.session_state.user = None


# ================= LOGIN / REGISTER =================

if not st.session_state.user:

    menu = st.sidebar.selectbox("Menu", ["Login", "Register"])

    if menu == "Register":

        st.title("Register")

        full = st.text_input("Full Name")
        email = st.text_input("Email")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ROLES)

        if st.button("Create Account"):

            if not validate_password(password):
                st.error("Password must be 8 characters with uppercase & number.")
                st.stop()

            try:
                register(full, email, username, password, role)
                st.success("Account created!")

            except:
                st.error("Username or Email already exists.")

    else:

        st.title("Login")

        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("Login"):

            user = login(u, p)

            if user and user[2] == 1:

                st.session_state.user = {
                    "username": user[0],
                    "role": user[1]
                }

                st.rerun()

            else:
                st.error("Invalid login or account held.")

    st.stop()


# ================= AFTER LOGIN =================

user = st.session_state.user

st.sidebar.write(f"👤 {user['username']} ({user['role']})")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

menu = st.sidebar.selectbox(
    "Menu",
    ["Create Incident", "View/Search", "Delete Requests", "User Control"]
)


# ================= CREATE INCIDENT =================

if menu == "Create Incident":

    st.header("Create Incident")

    error = st.text_input("Error")
    component = st.text_input("Component")
    root = st.text_area("Root Cause")
    action = st.text_area("Action Taken")

    st.subheader("Start Time")

    s_date = st.date_input("Start Date", datetime.today())
    s_time = st.time_input("Start Time", datetime.now().time())

    st.subheader("End Time")

    e_date = st.date_input("End Date", datetime.today())
    e_time = st.time_input("End Time", datetime.now().time())

    status = st.selectbox("Status", ["Open", "Monitoring", "Resolved"])

    if st.button("Submit"):

        start_str, start_dt = format_datetime(s_date, s_time)
        end_str, end_dt = format_datetime(e_date, e_time)

        if end_dt <= start_dt:
            st.error("End must be after start.")
            st.stop()

        downtime = calculate_minutes(start_dt, end_dt)

        with connect() as conn:

            conn.execute("""
            INSERT INTO incidents(
            error,component,root_cause,action_taken,
            start_time,end_time,downtime,status,
            created_by,modified
            )
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """, (
                error, component, root, action,
                start_str, end_str, downtime,
                status,
                user["username"],
                f"Modified by {user['username']} on {now()}"
            ))

        st.success("Incident created.")


# ================= VIEW / SEARCH =================

elif menu == "View/Search":

    keyword = st.text_input("Search")

    if keyword:

        df = pd.read_sql("""
        SELECT * FROM incidents
        WHERE error LIKE ?
        OR component LIKE ?
        """, connect(), params=(f"%{keyword}%", f"%{keyword}%"))

    else:

        df = pd.read_sql("SELECT * FROM incidents", connect())

    st.dataframe(df, use_container_width=True)


# ================= DELETE REQUEST =================

elif menu == "Delete Requests":

    if user["role"] not in ["CS Leader", "Developer"]:
        st.warning("Only CS Leader can approve deletes.")
        st.stop()

    df = pd.read_sql("SELECT * FROM delete_requests", connect())
    st.dataframe(df)

    inc_id = st.number_input("Incident ID")

    if st.button("Approve Delete"):

        with connect() as conn:
            conn.execute("DELETE FROM incidents WHERE id=?", (inc_id,))
            conn.execute("DELETE FROM delete_requests WHERE incident_id=?", (inc_id,))

        st.success("Deleted.")


# ================= USER CONTROL =================

elif menu == "User Control":

    if user["role"] != "Developer":
        st.warning("Developer only.")
        st.stop()

    users = pd.read_sql("SELECT username,role,is_active FROM users", connect())
    st.dataframe(users)

    target = st.text_input("Username")

    role = st.selectbox(
        "Role",
        ["SO Engineer", "Service Field Engineer", "CS Leader"]
    )

    if st.button("Update Role"):
        with connect() as conn:
            conn.execute(
                "UPDATE users SET role=? WHERE username=?",
                (role, target)
            )
        st.success("Role updated.")

    if st.button("Hold Account"):
        with connect() as conn:
            conn.execute(
                "UPDATE users SET is_active=0 WHERE username=?",
                (target,)
            )
        st.success("Account held.")
