import statistics


class StreamIntelligenceEngine:

    def __init__(self, telemetry, logger, predictor, trend_engine):
        self.telemetry = telemetry
        self.logger = logger
        self.predictor = predictor
        self.trend_engine = trend_engine

    async def analyze(self, user_login):

        rows = await self.telemetry.get_recent_snapshots(user_login)

        if len(rows) < 5:
            return None

        viewers = [r["viewer_count"] for r in rows]

        mean = statistics.mean(viewers)
        stdev = statistics.stdev(viewers) if len(viewers) > 1 else 0

        volatility = round((stdev / mean) * 100, 2) if mean else 0
        momentum = viewers[0] - viewers[-1]
        momentum_rate = round(momentum / len(viewers), 2)

        trend = self.trend_engine.compute_trend(viewers)
        predicted_next = self.predictor.predict_next(viewers)

        stability = max(0, 100 - volatility)
        growth = max(0, min(100, momentum_rate * 2 + 50))

        health = round(
            (growth * 0.4) +
            (stability * 0.3) +
            (50 if trend == "upward" else 30 if trend == "stable" else 10) * 0.3,
            2
        )

        await self.telemetry.log_stream_intelligence(
            user_login,
            volatility,
            momentum,
            momentum_rate,
            trend,
            health,
            predicted_next
        )

        result = {
            "user": user_login,
            "health_score": health,
            "trend": trend
        }

        self.logger.log("stream_intelligence", result)

        return result
