class AdaptiveTrackingEngine:

    def adjust(self, tracked_streams, intelligence_results):

        updated = []

        for r in intelligence_results:
            if r["health_score"] > 20:
                updated.append(r["user"])

        return updated if updated else tracked_streams
