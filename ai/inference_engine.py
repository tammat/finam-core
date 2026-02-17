# Комментарии:
# Делает inference по feature_dict.
# Не генерирует события — только возвращает сигнал.

import numpy as np


class InferenceEngine:

    def __init__(self, model, threshold, feature_order):
        self.model = model
        self.threshold = threshold
        self.feature_order = feature_order

    def predict(self, feature_dict):
        X = np.array([[feature_dict[f] for f in self.feature_order]])
        proba = self.model.predict_proba(X)[0][1]

        if proba >= self.threshold:
            return "LONG", proba
        else:
            return "SHORT", proba