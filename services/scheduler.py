"""Background scheduler for auto-refreshing data and sending alerts."""

import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

scheduler = BackgroundScheduler()


def refresh_data():
    """Refresh all data sources and check alerts."""
    from services.competitor_tracker import fetch_all_competitors, check_alerts
    from services.alerts import send_alerts

    print(f"[{datetime.now()}] Running scheduled data refresh...")

    # Refresh competitor data
    try:
        items = fetch_all_competitors(force_refresh=True)
        alerts = check_alerts(items)
        if alerts:
            send_alerts(competitor_alerts=alerts)
            print(f"  Sent {len(alerts)} competitor alerts")
    except Exception as e:
        print(f"  Competitor refresh failed: {e}")

    print(f"[{datetime.now()}] Refresh complete.")


def start_scheduler():
    """Start the background scheduler."""
    interval = int(os.getenv("REFRESH_INTERVAL_HOURS", "4"))

    if not scheduler.running:
        scheduler.add_job(
            refresh_data,
            "interval",
            hours=interval,
            id="data_refresh",
            replace_existing=True,
        )
        scheduler.start()
        print(f"Scheduler started: refreshing every {interval} hours")


def stop_scheduler():
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
