import pandas as pd
from database import get_all_incidents


def export_to_excel() -> str:
    data = get_all_incidents()

    columns = [
        "ID", "Error", "Component",
        "Root Cause", "Action Taken",
        "Start Time", "End Time",
        "Status", "Date"
    ]

    df = pd.DataFrame(data, columns=columns)

    file_name = "incident_report.xlsx"
    df.to_excel(file_name, index=False)

    return file_name
