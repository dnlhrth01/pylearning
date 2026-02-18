import streamlit as st
import pandas as pd
from datetime import datetime

from database import (
    create_tables,
    connect,
    user_exists,
    incident_exists,
    delete_request_exists
)

from auth import register, login, ROLES, create_manager
from utils import validate_password, now, format_datetime, calculate_minutes


create_tables()
create_manager()


# ================= CACHE LOADERS =================

@st.cache_data
def load_users():
    return pd.read_sql("SELECT username,role,is_active FROM users", connect())


@st.cache_data
def load_incidents():
    return pd.read_sql("SELECT * FROM incidents", connect())


@st.cache_data
def load_delete_requests():
    return pd.read_sql("SELECT * FROM delete_requests", connect())


# ================= SESSION =================

if "user" not in st.session_state:
    st.session_state.user = None


# ================= LOGIN =================

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

            valid, msg = validate_password(password)

            if not valid:
                st.error(msg)
                st.stop()

            try:
                register(full, email, username, password, role)
                st.success("Account created!")

                st.cache_data.clear()
                st.rerun()

            except ValueError as e:
                st.error(str(e))

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

    s_date = st.date_input("Start Date", datetime.today())
    s_time = st.time_input("Start Time", datetime.now().time())

    e_date = st.date_input("End Date", datetime.today())
    e_time = st.time_input("End Time", datetime.now().time())

    status = st.selectbox("Status", ["Open", "Monitoring", "Resolved"])

    if st.button("Submit"):

        if not error.strip() or not component.strip():
            st.error("Error and Component required.")
            st.stop()

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

        st.cache_data.clear()
        st.rerun()


# ================= VIEW =================

elif menu == "View/Search":

    keyword = st.text_input("Search")

    if keyword:

        df = pd.read_sql("""
        SELECT * FROM incidents
        WHERE error LIKE ?
        OR component LIKE ?
        """, connect(), params=(f"%{keyword}%", f"%{keyword}%"))

    else:
        df = load_incidents()

    st.dataframe(df, use_container_width=True)


# ================= DELETE =================

elif menu == "Delete Requests":

    if user["role"] not in ["Manager", "CS Leader"]:
        st.warning("Not authorized.")
        st.stop()

    st.dataframe(load_delete_requests())

    inc_id = st.number_input("Incident ID", step=1)

    if st.button("Approve Delete"):

        if not incident_exists(inc_id):
            st.error("Incident does not exist.")
            st.stop()

        if not delete_request_exists(inc_id):
            st.error("No delete request found.")
            st.stop()

        st.warning("⚠️ Permanent deletion.")

        confirm = st.checkbox("I confirm deletion")

        if confirm:

            with connect() as conn:
                conn.execute("DELETE FROM incidents WHERE id=?", (inc_id,))
                conn.execute("DELETE FROM delete_requests WHERE incident_id=?", (inc_id,))

            st.success("Deleted safely.")

            st.cache_data.clear()
            st.rerun()


# ================= USER CONTROL =================

# ================= USER CONTROL =================

elif menu == "User Control":

    if user["role"] != "Manager":
        st.warning("Manager only.")
        st.stop()

    st.subheader("User List")
    st.dataframe(load_users(), use_container_width=True)

    target = st.text_input("Username")

    role = st.selectbox(
        "Change Role To",
        ["SO Engineer", "Service Field Engineer", "CS Leader"]
    )

    # -------- ROLE UPDATE --------

    if st.button("Update Role"):

        if not target.strip():
            st.error("Please enter a username.")
            st.stop()

        if target == user["username"]:
            st.error("Manager cannot change their own role.")
            st.stop()

        if not user_exists(target):
            st.error("User does not exist.")
            st.stop()

        with connect() as conn:
            conn.execute(
                "UPDATE users SET role=? WHERE username=?",
                (role, target)
            )

        st.success("Role updated successfully.")

        st.cache_data.clear()
        st.rerun()

    # -------- HOLD ACCOUNT --------

    if st.button("Hold Account"):

        if not target.strip():
            st.error("Please enter a username.")
            st.stop()

        if target == user["username"]:
            st.error("Manager cannot hold their own account.")
            st.stop()

        if not user_exists(target):
            st.error("User does not exist.")
            st.stop()

        with connect() as conn:
            conn.execute(
                "UPDATE users SET is_active=0 WHERE username=?",
                (target,)
            )

        st.success("Account has been held.")

        st.cache_data.clear()
        st.rerun()

    # -------- ACTIVATE ACCOUNT --------

    if st.button("Activate Account"):

        if not target.strip():
            st.error("Please enter a username.")
            st.stop()

        if target == user["username"]:
            st.error("Manager account is always active.")
            st.stop()

        if not user_exists(target):
            st.error("User does not exist.")
            st.stop()

        with connect() as conn:
            conn.execute(
                "UPDATE users SET is_active=1 WHERE username=?",
                (target,)
            )

        st.success("Account activated successfully.")

        st.cache_data.clear()
        st.rerun()
