from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.domain.constants import SENSOR_FEATURES
from app.domain.entities import SensorEvent


class SklearnSensorModel:
    def __init__(self, artifact_dir: Path) -> None:
        self.artifact_dir = artifact_dir

        pipeline_path = artifact_dir / "sensor_pipeline.joblib"
        anomaly_path = artifact_dir / "isolation_forest.joblib"

        self.pipeline = (
            joblib.load(pipeline_path)
            if pipeline_path.exists()
            else None
        )

        self.detector = (
            joblib.load(anomaly_path)
            if anomaly_path.exists()
            else None
        )

    @staticmethod
    def _event_frame(event: SensorEvent) -> pd.DataFrame:
        return pd.DataFrame(
            [{
                feature: event.metric(feature)
                for feature in SENSOR_FEATURES
            }],
            columns=list(SENSOR_FEATURES),
            dtype=np.float64,
        )

    @staticmethod
    def _normalize_vector(values: np.ndarray) -> np.ndarray:
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
        Vetorização usada para busca de similaridade no pgvector.

        Mantida compatível com os vetores históricos já armazenados.
        """
        feature_frame = frame.loc[
            :, list(SENSOR_FEATURES)
        ].astype(np.float64)

        vectors = self._normalize_vector(
            feature_frame.to_numpy(dtype=np.float64)
        )

        return vectors.astype(float).tolist()

    def transform(
        self,
        event: SensorEvent,
    ) -> list[float]:
        frame = self._event_frame(event)
        return self.transform_frame(frame)[0]

    def anomaly_score(
        self,
        event: SensorEvent,
    ) -> float | None:
        """
        Detecção de anomalia usa exatamente o mesmo pipeline
        utilizado no treinamento do Isolation Forest:
        StandardScaler -> PCA -> IsolationForest.
        """
        if self.detector is None or self.pipeline is None:
            return None

        frame = self._event_frame(event)

        transformed = self.pipeline.transform(frame)

        raw_score = -float(
            self.detector.score_samples(transformed)[0]
        )

        score = 1.0 / (
            1.0 + np.exp(-8.0 * (raw_score - 0.5))
        )

        return round(float(score), 4)