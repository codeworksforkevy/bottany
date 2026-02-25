import statistics


class ViewerAnomalyDetector:

    def __init__(self, telemetry, logger, threshold=2.5):
        self.telemetry = telemetry
        self.logger = logger
        self.threshold = threshold

    async def check(self, user_login: str, current_viewers: int):

        rows = await self.telemetry.get_recent_snapshots(user_login, limit=15)

        if len(rows) < 5:
            return  # not enough data

        historical = [r["viewer_count"] for r in rows]

        mean = statistics.mean(historical)
        stdev = statistics.stdev(historical)

        if stdev == 0:
            return

        deviation = abs(current_viewers - mean)

        if deviation > self.threshold * stdev:

            self.logger.log(
                "viewer_anomaly_detected",
                {
                    "user": user_login,
                    "current": current_viewers,
                    "mean": round(mean, 2),
                    "stdev": round(stdev, 2),
                    "deviation": round(deviation, 2)
                }
            )
