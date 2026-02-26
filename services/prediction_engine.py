class PredictionEngine:

    def predict_next(self, viewers):

        if len(viewers) < 3:
            return viewers[0]

        first = viewers[-1]
        last = viewers[0]

        slope = (last - first) / len(viewers)

        return round(last + slope, 2)
