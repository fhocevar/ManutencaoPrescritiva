from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.domain.constants import SENSOR_FEATURES
from app.domain.entities import SensorEvent


class SklearnSensorModel:
    def __init__(self, artifact_dir: Path) -> None:
        self.artifact_dir = artifact_dir

        scaler_path = artifact_dir / "sensor_scaler.joblib"
        anomaly_path = artifact_dir / "isolation_forest.joblib"

        self.scaler = (
            joblib.load(scaler_path)
            if scaler_path.exists()
            else None
        )

        self.detector = (
            joblib.load(anomaly_path)
            if anomaly_path.exists()
            else None
        )

    @staticmethod
    def _event_frame(event: SensorEvent) -> pd.DataFrame:
        """
        Cria um DataFrame contendo exatamente as mesmas colunas usadas
        durante o treinamento do StandardScaler.
        """
        return pd.DataFrame(
            [
                {
                    feature: event.metric(feature)
                    for feature in SENSOR_FEATURES
                }
            ],
            columns=list(SENSOR_FEATURES),
            dtype=np.float64,
        )

    @staticmethod
    def _normalize_without_scaler(
        values: np.ndarray,
    ) -> np.ndarray:
        norms = np.linalg.norm(
            values,
            axis=1,
            keepdims=True,
        )

        norms[norms == 0] = 1.0

        return values / norms

    def transform_frame(
        self,
        frame: pd.DataFrame,
    ) -> list[list[float]]:
        """
        Transforma vários registros de uma vez.

        O DataFrame mantém os nomes e a ordem das features, evitando:

        UserWarning: X does not have valid feature names
        """
        feature_frame = frame.loc[:, list(SENSOR_FEATURES)].astype(
            np.float64
        )

        if self.scaler is not None:
            vectors = self.scaler.transform(feature_frame)
        else:
            vectors = self._normalize_without_scaler(
                feature_frame.to_numpy(dtype=np.float64)
            )

        return vectors.astype(float).tolist()

    def transform(self, event: SensorEvent) -> list[float]:
        frame = self._event_frame(event)
        return self.transform_frame(frame)[0]

    def anomaly_score(
        self,
        event: SensorEvent,
    ) -> float | None:
        if self.detector is None or self.scaler is None:
            return None

        frame = self._event_frame(event)
        scaled = self.scaler.transform(frame)

        raw_score = -float(
            self.detector.score_samples(scaled)[0]
        )

        score = 1.0 / (
            1.0 + np.exp(-8.0 * (raw_score - 0.5))
        )

        return round(float(score), 4)