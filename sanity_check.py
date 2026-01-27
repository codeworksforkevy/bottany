from datetime import datetime

def run_sanity_check(free_games, discounted_games, rejected_games):
    report = {
        "timestamp": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "free_count": len(free_games),
        "discounted_count": len(discounted_games),
        "rejected_count": len(rejected_games),
    }
    if not free_games:
        report["warning"] = "No free-to-keep games detected."
    return report
