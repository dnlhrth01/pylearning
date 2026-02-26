import math
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from auth import ROLES, create_manager, login, register
from database import (
    INCIDENT_STATUSES,
    assign_role,
    approve_delete_request,
    create_incident,
    create_tables,
    get_incident,
    get_user,
    list_delete_requests,
    list_users,
    request_delete_incident,
    search_incidents,
    set_user_active,
    update_incident
)
from utils import normalize_text


INACTIVITY_MINUTES = 30


st.set_page_config(page_title="OpsLog", layout="wide")
create_tables()
create_manager()


def logout():
    st.session_state.user = None
    st.session_state.last_active = None
    st.rerun()


def require_active_session():
    if "user" not in st.session_state:
        st.session_state.user = None
    if "last_active" not in st.session_state:
        st.session_state.last_active = None

    if not st.session_state.user:
        return None

    now = datetime.now()
    if st.session_state.last_active:
        last_active = datetime.fromisoformat(st.session_state.last_active)
        if now - last_active > timedelta(minutes=INACTIVITY_MINUTES):
            logout()
            return None
    st.session_state.last_active = now.isoformat(timespec="seconds")

    db_user = get_user(st.session_state.user["username"])
    if not db_user or not db_user["is_active"]:
        st.error("Your account is not active. Please contact Manager.")
        logout()
        return None

    db_role = normalize_text(db_user["role"])
    if not db_role:
        st.warning("Role not assigned. Please contact Manager.")
        st.sidebar.write(f"User: {db_user['username']}")
        if st.sidebar.button("Logout"):
            logout()
        st.stop()

    st.session_state.user = {
        "username": db_user["username"],
        "full_name": db_user["full_name"],
        "role": db_role
    }
    return st.session_state.user


def render_readonly_table(df):
    if df.empty:
        st.info("No data found.")
        return

    column_aliases = {
        "id": "ID",
        "incident_id": "Incident ID",
        "error_name": "Error Name",
        "component": "Component",
        "root_cause": "Root Cause",
        "remark": "Remark",
        "action_taken": "Action Taken",
        "status": "Status",
        "start_date": "Start Date",
        "start_time": "Start Time",
        "end_date": "End Date",
        "end_time": "End Time",
        "duration_minutes": "Duration (Minutes)",
        "modified_by": "Modified By",
        "modified_at": "Modified At",
        "full_name": "Full Name",
        "email": "Email",
        "username": "Username",
        "role": "Role",
        "is_active": "Is Active",
        "field_name": "Field Name",
        "old_value": "Old Value",
        "new_value": "New Value",
        "requested_by": "Requested By",
        "approver": "Approver",
        "requested_at": "Requested At",
        "approved_at": "Approved At",
        "details": "Details",
        "target_type": "Target Type",
        "target_id": "Target ID",
        "created_at": "Created At",
        "last_attempt": "Last Attempt",
        "locked_until": "Locked Until",
        "failed_attempts": "Failed Attempts"
    }

    display_df = df.copy()
    display_df.columns = [
        column_aliases.get(col, col.replace("_", " ").title())
        for col in display_df.columns
    ]
    st.dataframe(display_df, use_container_width=True, hide_index=True)


user = require_active_session()


if not user:
    menu = st.sidebar.selectbox("Menu", ["Login", "Register"])

    if menu == "Login":
        st.title("OpsLog Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

        if submit:
            db_user, message = login(username, password)
            if not db_user:
                st.error(message)
            else:
                st.session_state.user = {
                    "username": db_user["username"],
                    "full_name": db_user["full_name"],
                    "role": db_user["role"]
                }
                st.session_state.last_active = datetime.now().isoformat(timespec="seconds")
                st.rerun()
    else:
        st.title("OpsLog Registration")
        st.caption("New accounts are created without role. Manager must assign a role.")
        with st.form("register_form"):
            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Create Account")

        if submit:
            if password != confirm_password:
                st.error("Password confirmation does not match.")
            else:
                try:
                    register(full_name, email, username, password)
                    st.success("Account created. Please wait for Manager role assignment.")
                except ValueError as exc:
                    st.error(str(exc))
    st.stop()


st.sidebar.markdown("---")
st.sidebar.write(f"{user['full_name']} ({user['role']})")
if st.sidebar.button("Logout"):
    logout()

if user["role"] == "Manager":
    menu_options = ["Search Incident", "Delete Request Approvals", "User Control"]
else:
    menu_options = ["Create Incident", "Update Incident", "Search Incident"]
    if user["role"] == "CS Leader":
        menu_options.append("Delete Incident Request")

menu = st.sidebar.selectbox("Menu", menu_options)


if menu == "Create Incident":
    st.header("Create Incident")
    st.caption("Duration is read-only and calculated automatically from start/end date-time.")
    with st.form("create_incident_form"):
        error_name = st.text_input("Error Name")
        component = st.text_input("Component")
        root_cause = st.text_area("Root Cause")
        remark = st.text_area("Remark")
        action_taken = st.text_area("Action Taken")
        start_date_value = st.date_input("Start Date")
        start_time = st.text_input("Start Time (HH:MM AM/PM)")
        end_date_value = st.date_input("End Date")
        end_time = st.text_input("End Time (HH:MM AM/PM)")
        submit = st.form_submit_button("Create")

    if submit:
        payload = {
            "error_name": error_name,
            "component": component,
            "root_cause": root_cause,
            "remark": remark,
            "action_taken": action_taken,
            "start_date": start_date_value.strftime("%d/%m/%Y"),
            "start_time": start_time,
            "end_date": end_date_value.strftime("%d/%m/%Y"),
            "end_time": end_time
        }
        try:
            generated_incident_id = create_incident(payload, user["username"], user["full_name"])
            st.success(f"Incident created with ID {generated_incident_id} and status 'Open Case'.")
        except ValueError as exc:
            st.error(str(exc))


elif menu == "Update Incident":
    st.header("Update Incident")
    if "update_loaded_incident_id" not in st.session_state:
        st.session_state.update_loaded_incident_id = ""

    with st.form("load_update_incident_form"):
        incident_id_input = st.text_input("Incident ID (YYYY-####)")
        load_submit = st.form_submit_button("Load Incident")

    if load_submit:
        lookup_id = normalize_text(incident_id_input)
        incident = get_incident(lookup_id)
        if not incident:
            st.session_state.update_loaded_incident_id = ""
            st.error("Incident not found.")
        else:
            st.session_state.update_loaded_incident_id = incident["incident_id"]
            st.success(f"Loaded incident: {incident['incident_id']}")

    loaded_id = normalize_text(st.session_state.update_loaded_incident_id)
    incident = get_incident(loaded_id) if loaded_id else None

    if loaded_id and not incident:
        st.session_state.update_loaded_incident_id = ""
        st.error("Incident not found or already deleted.")

    if incident:
        try:
            start_date_value = datetime.strptime(incident["start_date"], "%d/%m/%Y").date()
        except ValueError:
            start_date_value = datetime.today().date()
        try:
            end_date_value = datetime.strptime(incident["end_date"], "%d/%m/%Y").date()
        except ValueError:
            end_date_value = datetime.today().date()

        st.text_input("Error Name", incident["error_name"], disabled=True)
        st.text_input("Component", incident["component"], disabled=True)
        st.text_input("Incident ID", incident["incident_id"], disabled=True)

        with st.form("update_incident_form"):
            root_cause = st.text_area("Root Cause", value=incident["root_cause"])
            remark = st.text_area("Remark", value=incident["remark"])
            action_taken = st.text_area("Action Taken", value=incident["action_taken"])
            st.date_input("Start Date", value=start_date_value, disabled=True)
            start_time = st.text_input("Start Time (HH:MM AM/PM)", value=incident["start_time"])
            st.date_input("End Date", value=end_date_value, disabled=True)
            end_time = st.text_input("End Time (HH:MM AM/PM)", value=incident["end_time"])
            st.text_input(
                "Duration (Minutes - Auto)",
                value=str(max(1, int(incident["duration_minutes"]))),
                disabled=True
            )
            status = st.selectbox(
                "Status",
                INCIDENT_STATUSES,
                index=INCIDENT_STATUSES.index(incident["status"]) if incident["status"] in INCIDENT_STATUSES else 0
            )
            submit = st.form_submit_button("Update")

        if submit:
            try:
                update_incident(
                    incident_id=incident["incident_id"],
                    updates={
                        "root_cause": root_cause,
                        "remark": remark,
                        "action_taken": action_taken,
                        "start_time": start_time,
                        "end_time": end_time,
                        "status": status
                    },
                    actor_username=user["username"],
                    actor_full_name=user["full_name"]
                )
                st.success("Incident updated.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


elif menu == "Delete Incident Request":
    st.header("Delete Incident Request")
    with st.form("delete_request_form"):
        incident_id = st.text_input("Incident ID (YYYY-####)")
        confirm_one = st.checkbox("I understand this may permanently delete data.")
        confirm_two = st.radio("This data will be permanently deleted. Continue?", ["No", "Yes"])
        submit = st.form_submit_button("Submit Delete Request")

    if submit:
        if not confirm_one or confirm_two != "Yes":
            st.error("Double confirmation is required.")
        else:
            try:
                request_delete_incident(incident_id, user["username"], user["role"])
                st.success("Delete request submitted.")
            except ValueError as exc:
                st.error(str(exc))


elif menu == "Delete Request Approvals":
    st.header("Delete Request Approvals")
    requests_df = pd.DataFrame(list_delete_requests())
    render_readonly_table(requests_df)

    with st.form("approve_delete_form"):
        incident_id = st.text_input("Incident ID to approve (YYYY-####)")
        confirm_one = st.checkbox("I confirm this deletion is final and irreversible.")
        confirm_two = st.radio("This data will be permanently deleted. Continue?", ["No", "Yes"], key="approve_yes_no")
        submit = st.form_submit_button("Approve Delete")

    if submit:
        if not confirm_one or confirm_two != "Yes":
            st.error("Double confirmation is required.")
        else:
            try:
                approve_delete_request(incident_id, user["username"], user["role"])
                st.success("Incident deleted permanently.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


elif menu == "Search Incident":
    st.header("Search Incident")
    keyword = st.text_input("Keyword (searches all fields)")
    page_size = st.selectbox("Rows per page", [10, 20, 50], index=0)
    total, _ = search_incidents(keyword, page=1, page_size=page_size)
    max_pages = max(1, math.ceil(total / page_size))
    page = st.number_input("Page", min_value=1, max_value=max_pages, value=1, step=1)
    total, rows = search_incidents(keyword, page=page, page_size=page_size)
    st.caption(f"Total records: {total} | Page {page}/{max_pages}")
    render_readonly_table(pd.DataFrame(rows))


elif menu == "User Control":
    st.header("User Control")
    users_df = pd.DataFrame(list_users())
    if not users_df.empty:
        users_df["is_active"] = users_df["is_active"].apply(lambda x: "Active" if int(x) == 1 else "Suspended")
    render_readonly_table(users_df)

    st.subheader("Assign Role")
    with st.form("assign_role_form"):
        target_user = st.text_input("Username")
        new_role = st.selectbox("Role", ROLES)
        submit_role = st.form_submit_button("Assign Role")
    if submit_role:
        try:
            assign_role(user["username"], target_user, new_role)
            st.success("Role updated.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    st.subheader("Account Status")
    with st.form("account_status_form"):
        target_user_status = st.text_input("Username ", key="status_target")
        action = st.selectbox("Action", ["Activate", "Suspend"])
        submit_status = st.form_submit_button("Apply")
    if submit_status:
        try:
            set_user_active(user["username"], target_user_status, is_active=(action == "Activate"))
            st.success("Account status updated.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
