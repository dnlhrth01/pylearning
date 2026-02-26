"""
OpsLog dummy data seeder.

Creates sample users, incidents, updates, and a delete request using the
current database schema and validation rules.
"""

from database import (
    assign_role,
    create_incident,
    create_tables,
    get_user,
    request_delete_incident,
    tx,
    update_incident,
)
from auth import create_manager, register


DEFAULT_PASSWORD = "Password1!"
MANAGER_USERNAME = "manager"


def ensure_user(full_name, email, username, role):
    if not get_user(username):
        register(full_name, email, username, DEFAULT_PASSWORD)
    if role:
        assign_role(MANAGER_USERNAME, username, role)


def seed_users():
    users = [
        ("Alex Turner", "alex.turner@opslog.test", "alex", "SO Engineer"),
        ("Bianca Cruz", "bianca.cruz@opslog.test", "bianca", "SO Engineer"),
        ("Carlos Diaz", "carlos.diaz@opslog.test", "carlos", "Service Field Engineer"),
        ("Dina Noor", "dina.noor@opslog.test", "dina", "Service Field Engineer"),
        ("Evan Koh", "evan.koh@opslog.test", "evan", "CS Leader"),
        ("Farah Lim", "farah.lim@opslog.test", "farah", "CS Leader"),
    ]
    for full_name, email, username, role in users:
        ensure_user(full_name, email, username, role)
    print(f"Seeded users: {len(users)}")


def seed_incidents():
    incidents = [
        {
            "incident_id": "INC-2026-0001",
            "error_name": "Payment Timeout",
            "component": "Payment API",
            "root_cause": "Upstream gateway latency spike.",
            "remark": "Observed during peak load.",
            "action_taken": "Increased timeout and rerouted traffic.",
            "start_date": "15/01/2026",
            "start_time": "09:10 AM",
            "end_date": "15/01/2026",
            "end_time": "09:45 AM",
            "duration_minutes": 35,
            "actor_username": "alex",
            "actor_full_name": "Alex Turner",
        },
        {
            "incident_id": "INC-2026-0002",
            "error_name": "Database Connection Drop",
            "component": "Order Service",
            "root_cause": "Connection pool exhaustion.",
            "remark": "Intermittent failures for 20 minutes.",
            "action_taken": "Restarted service and tuned pool size.",
            "start_date": "18/01/2026",
            "start_time": "01:00 PM",
            "end_date": "18/01/2026",
            "end_time": "01:50 PM",
            "duration_minutes": 50,
            "actor_username": "bianca",
            "actor_full_name": "Bianca Cruz",
        },
        {
            "incident_id": "INC-2026-0003",
            "error_name": "Sensor Sync Failure",
            "component": "Field Gateway",
            "root_cause": "Invalid firmware config checksum.",
            "remark": "Affects site cluster B.",
            "action_taken": "Rolled back firmware and re-synced.",
            "start_date": "22/01/2026",
            "start_time": "07:20 AM",
            "end_date": "22/01/2026",
            "end_time": "08:05 AM",
            "duration_minutes": 45,
            "actor_username": "carlos",
            "actor_full_name": "Carlos Diaz",
        },
        {
            "incident_id": "INC-2026-0004",
            "error_name": "Report Generation Delay",
            "component": "Analytics Worker",
            "root_cause": "Queue backlog from retry storm.",
            "remark": "Backlog reached 12k jobs.",
            "action_taken": "Scaled workers and throttled retries.",
            "start_date": "25/01/2026",
            "start_time": "10:00 PM",
            "end_date": "25/01/2026",
            "end_time": "11:30 PM",
            "duration_minutes": 90,
            "actor_username": "dina",
            "actor_full_name": "Dina Noor",
        },
        {
            "incident_id": "INC-2026-0005",
            "error_name": "Authentication Error Burst",
            "component": "Auth Service",
            "root_cause": "Expired signing certificate in one node.",
            "remark": "Spike in 401 responses.",
            "action_taken": "Rotated cert and restarted affected node.",
            "start_date": "30/01/2026",
            "start_time": "03:15 PM",
            "end_date": "30/01/2026",
            "end_time": "04:05 PM",
            "duration_minutes": 50,
            "actor_username": "alex",
            "actor_full_name": "Alex Turner",
        },
    ]

    created = 0
    skipped = 0
    for item in incidents:
        payload = {k: v for k, v in item.items() if not k.startswith("actor_")}
        try:
            create_incident(payload, item["actor_username"], item["actor_full_name"])
            created += 1
        except ValueError:
            skipped += 1
    print(f"Seeded incidents: created={created}, skipped_existing={skipped}")


def seed_updates():
    updates = [
        (
            "INC-2026-0001",
            {
                "remark": "Latency normalized after reroute.",
                "action_taken": "Reroute complete, timeout reverted to baseline.",
                "status": "Monitoring",
                "start_time": "09:10 AM",
                "end_time": "09:45 AM",
                "duration_minutes": 35,
            },
            "evan",
            "Evan Koh",
        ),
        (
            "INC-2026-0002",
            {
                "root_cause": "Pool settings too low for burst traffic.",
                "status": "Resolved",
                "start_time": "01:00 PM",
                "end_time": "01:50 PM",
                "duration_minutes": 50,
            },
            "farah",
            "Farah Lim",
        ),
    ]

    applied = 0
    for incident_id, patch, actor_username, actor_full_name in updates:
        try:
            update_incident(incident_id, patch, actor_username, actor_full_name)
            applied += 1
        except ValueError:
            continue
    print(f"Seeded incident updates: {applied}")


def seed_delete_request():
    try:
        request_delete_incident("INC-2026-0005", "evan", "CS Leader")
        print("Seeded pending delete request for INC-2026-0005")
    except ValueError:
        print("Delete request already exists or incident unavailable; skipped.")


def seed_manager_status():
    # Ensure manager stays active/role-correct in case of reused DBs.
    with tx(immediate=True) as conn:
        conn.execute(
            "UPDATE users SET role='Manager', is_active=1 WHERE username=?",
            (MANAGER_USERNAME,),
        )


def main():
    create_tables()
    create_manager()
    seed_manager_status()
    seed_users()
    seed_incidents()
    seed_updates()
    seed_delete_request()
    print(f"Dummy data ready. Default user password: {DEFAULT_PASSWORD}")
    print("Manager login: manager / Manager@123")


if __name__ == "__main__":
    main()
