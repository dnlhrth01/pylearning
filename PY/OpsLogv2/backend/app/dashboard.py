from database import connect


def get_dashboard_stats():
    with connect() as conn:
        summary = conn.execute(
            """
            SELECT
                COUNT(*) AS total_incidents,
                SUM(CASE WHEN status='Open Case' THEN 1 ELSE 0 END) AS open_cases,
                SUM(CASE WHEN status='Monitoring' THEN 1 ELSE 0 END) AS monitoring_cases,
                SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) AS resolved_closed_cases,
                COALESCE(AVG(duration_minutes), 0) AS avg_duration_minutes
            FROM incidents
            WHERE is_deleted=0
            """
        ).fetchone()

        recent = conn.execute(
            """
            SELECT COUNT(*) AS incidents_last_7_days
            FROM incidents
            WHERE is_deleted=0
              AND datetime(modified_at) >= datetime('now', '-7 days')
            """
        ).fetchone()

        top_components_rows = conn.execute(
            """
            SELECT component, COUNT(*) AS total
            FROM incidents
            WHERE is_deleted=0
            GROUP BY component
            ORDER BY total DESC, component ASC
            LIMIT 5
            """
        ).fetchall()

        status_rows = conn.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM incidents
            WHERE is_deleted=0
            GROUP BY status
            ORDER BY total DESC, status ASC
            """
        ).fetchall()

    return {
        "total_incidents": int(summary["total_incidents"] or 0),
        "open_cases": int(summary["open_cases"] or 0),
        "monitoring_cases": int(summary["monitoring_cases"] or 0),
        "resolved_closed_cases": int(summary["resolved_closed_cases"] or 0),
        "avg_duration_minutes": round(float(summary["avg_duration_minutes"] or 0), 2),
        "incidents_last_7_days": int(recent["incidents_last_7_days"] or 0),
        "top_components": [
            {"component": row["component"], "total": int(row["total"])}
            for row in top_components_rows
        ],
        "status_breakdown": [
            {"status": row["status"], "total": int(row["total"])}
            for row in status_rows
        ],
    }

