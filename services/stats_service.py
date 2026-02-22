
import json
import datetime
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "bot_stats.json"

def load_stats():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_stats(stats):
    with open(DATA_FILE, "w") as f:
        json.dump(stats, f, indent=4)

def log_command(command_name, user_id):
    stats = load_stats()
    stats["total_calls"] += 1
    stats["commands"].setdefault(command_name, 0)
    stats["commands"][command_name] += 1

    today = str(datetime.date.today())
    stats["daily_usage"].setdefault(today, 0)
    stats["daily_usage"][today] += 1

    if user_id not in stats["unique_users"]:
        stats["unique_users"].append(user_id)

    save_stats(stats)

def get_stats():
    return load_stats()
