from datetime import datetime, timezone


def get_server_status(start_time: datetime) -> dict:
    """Return the server status"""

    start_time_iso = start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    uptime = datetime.now(timezone.utc) - start_time

    # Breakdown uptime into days, hours, minutes, seconds
    days = uptime.days
    seconds = uptime.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    # Create a human-readable uptime string
    uptime_formatted = f"{days}d {hours}h {minutes}m {seconds}s"

    return {
        "status": "ok",
        "start_time": start_time_iso,
        "uptime": uptime_formatted,
    }
