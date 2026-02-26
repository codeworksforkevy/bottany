class TrendAnalyticsEngine:

    def compute_trend(self, viewers):

        mean = sum(viewers) / len(viewers)
        last = viewers[0]

        if last > mean:
            return "upward"
        elif last < mean:
            return "downward"
        return "stable"
