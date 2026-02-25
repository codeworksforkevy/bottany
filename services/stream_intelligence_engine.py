import statistics


class StreamIntelligenceEngine:

    def __init__(self, telemetry, logger):
        self.telemetry = telemetry
        self.logger = logger

    async def analyze(self, user_login: str):

        rows = await self.telemetry.get_recent_snapshots(user_login, limit=20)

        if len(rows) < 5:
            return  # not enough data

        viewers = [r["viewer_count"] for r in rows]

        mean = statistics.mean(viewers)
        stdev = statistics.stdev(viewers) if len(viewers) > 1 else 0

        first = viewers[-1]
        last = viewers[0]

        # ---------------------------------------------
        # VOLATILITY
        # ---------------------------------------------

        volatility_score = 0
        if mean > 0:
            volatility_score = round((stdev / mean) * 100, 2)

        # ---------------------------------------------
        # MOMENTUM
        # ---------------------------------------------

        momentum = last - first
        momentum_rate = round(momentum / len(viewers), 2)

        # ---------------------------------------------
        # TREND
        # ---------------------------------------------

        if last > mean:
            trend = "upward"
        elif last < mean:
            trend = "downward"
        else:
            trend = "stable"

        # ---------------------------------------------
        # HEALTH SCORE
        # ---------------------------------------------

        stability_factor = max(0, 100 - volatility_score)
        growth_factor = max(0, min(100, momentum_rate * 2 + 50))

        health_score = round(
            (growth_factor * 0.4) +
            (stability_factor * 0.3) +
            (50 if trend == "upward" else 30 if trend == "stable" else 10) * 0.3,
            2
        )

        result = {
            "user": user_login,
            "volatility_score": volatility_score,
            "momentum": momentum,
            "momentum_rate": momentum_rate,
            "trend": trend,
            "health_score": health_score
        }

        self.logger.log("stream_intelligence", result)

        return result
