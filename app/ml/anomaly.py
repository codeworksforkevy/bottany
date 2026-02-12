# Isolation Forest Anomaly Detection Module
from sklearn.ensemble import IsolationForest
import numpy as np

class OfferAnomalyDetector:

    def __init__(self):
        self.model = IsolationForest(contamination=0.1)
        self.trained = False

    def train(self, historical_counts):
        X = np.array(historical_counts).reshape(-1, 1)
        self.model.fit(X)
        self.trained = True

    def detect(self, current_value):
        if not self.trained:
            return False
        prediction = self.model.predict([[current_value]])
        return prediction[0] == -1