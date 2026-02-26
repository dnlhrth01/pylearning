import pandas as pd
from database import get_all_incidents


def export_to_excel() -> str:
    rows = get_all_incidents()
    df = pd.DataFrame(rows)
    column_aliases = {
        "incident_id": "Incident ID",
        "error_name": "Error Name",
        "component": "Component",
        "root_cause": "Root Cause",
        "action_taken": "Action Taken",
        "start_date": "Start Date",
        "start_time": "Start Time",
        "end_date": "End Date",
        "end_time": "End Time",
        "duration_minutes": "Duration (Minutes)",
        "status": "Status",
        "modified_by": "Modified By",
        "modified_at": "Modified At",
    }
    if not df.empty:
        df = df.rename(columns=column_aliases)

    file_name = "incident_report.xlsx"
    df.to_excel(file_name, index=False)

    return file_name
