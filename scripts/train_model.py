import os
import json
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report


DATA_PATH = "data/raw/landslide_training.csv"
MODEL_DIR = "model"

FEATURES = [
    "rainfall_24h",
    "rainfall_3d",
    "rainfall_7d",
    "slope",
    "elevation",
    "historical_landslide",
    "distance_to_landslide",
    "soil_risk"
]

TARGET = "risk"


def load_data():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    data = pd.read_csv(DATA_PATH)

    required_columns = FEATURES + [TARGET]

    missing = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns: {missing}"
        )

    return data


def evaluate_model(name, model, X_train, X_test, y_train, y_test):

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    accuracy = accuracy_score(
        y_test,
        predictions
    )

    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    print(f"Accuracy: {accuracy:.4f}")

    print("\nClassification Report:")

    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0
        )
    )

    return model, accuracy


def main():

    os.makedirs(MODEL_DIR, exist_ok=True)

    print("Loading dataset...")

    data = load_data()

    print(f"Dataset rows: {len(data)}")

    X = data[FEATURES]
    y = data[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y
    )

    logistic_model = Pipeline([
        (
            "scaler",
            StandardScaler()
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=2000
            )
        )
    ])

    random_forest_model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        class_weight="balanced"
    )

    models = []

    model, score = evaluate_model(
        "Logistic Regression",
        logistic_model,
        X_train,
        X_test,
        y_train,
        y_test
    )

    models.append(
        ("Logistic Regression", model, score)
    )

    model, score = evaluate_model(
        "Random Forest",
        random_forest_model,
        X_train,
        X_test,
        y_train,
        y_test
    )

    models.append(
        ("Random Forest", model, score)
    )

    best_name, best_model, best_score = max(
        models,
        key=lambda item: item[2]
    )

    model_path = os.path.join(
        MODEL_DIR,
        "landslide_model.pkl"
    )

    joblib.dump(
        best_model,
        model_path
    )

    feature_info = {
        "features": FEATURES,
        "target": TARGET,
        "model": best_name,
        "accuracy": best_score,
        "classes": sorted(
            y.unique().tolist()
        )
    }

    with open(
        os.path.join(
            MODEL_DIR,
            "feature_info.json"
        ),
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            feature_info,
            file,
            indent=4
        )

    print("\n" + "=" * 60)
    print("BEST MODEL")
    print("=" * 60)

    print(f"Model: {best_name}")
    print(f"Accuracy: {best_score:.4f}")

    print(
        f"\nSaved model to: {model_path}"
    )


if __name__ == "__main__":
    main()