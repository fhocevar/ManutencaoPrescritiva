import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.domain.constants import SENSOR_FEATURES


def main(csv_path: Path, artifact_dir: Path) -> None:
    frame = pd.read_csv(csv_path)
    missing = [column for column in SENSOR_FEATURES if column not in frame.columns]
    if missing:
        raise ValueError(f"Colunas ausentes no CSV: {missing}")

    features = frame[list(SENSOR_FEATURES)].apply(pd.to_numeric, errors="coerce")
    features = features.fillna(features.median(numeric_only=True)).fillna(0)

    # Mantém 23 dimensões para compatibilidade com pgvector e adiciona PCA como etapa auditável.
    pipeline = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("pca", PCA(n_components=min(len(SENSOR_FEATURES), features.shape[1]), random_state=42)),
        ]
    )
    transformed = pipeline.fit_transform(features)

    detector = IsolationForest(
        n_estimators=300,
        contamination="auto",
        random_state=42,
        n_jobs=-1,
    )
    detector.fit(transformed)

    artifact_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, artifact_dir / "sensor_pipeline.joblib")
    joblib.dump(detector, artifact_dir / "isolation_forest.joblib")
    print(f"Artefatos gravados em {artifact_dir.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    main(args.csv, args.artifacts)
