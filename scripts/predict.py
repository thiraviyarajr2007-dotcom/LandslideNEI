import os
import joblib
import pandas as pd

MODEL_PATH = "model/landslide_model.pkl"

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


def load_model():

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            "Trained model not found. "
            "Run train_model.py first."
        )

    return joblib.load(MODEL_PATH)


def predict_risk(values):

    model = load_model()

    row = pd.DataFrame(
        [[
            values[feature]
            for feature in FEATURES
        ]],
        columns=FEATURES
    )

    prediction = model.predict(row)[0]

    probabilities = model.predict_proba(row)[0]

    classes = model.classes_

    probability_map = dict(
        zip(
            classes,
            probabilities
        )
    )

    confidence = probability_map[prediction]

    return {
        "risk": prediction,
        "confidence": float(confidence),
        "probabilities": {
            key: float(value)
            for key, value in probability_map.items()
        }
    }


if __name__ == "__main__":

    sample = {
        "rainfall_24h": 20,
        "rainfall_3d": 45,
        "rainfall_7d": 80,
        "slope": 12,
        "elevation": 400,
        "historical_landslide": 0,
        "distance_to_landslide": 8.5,
        "soil_risk": 0.1
    }

    print("Loading landslide model...")

    result = predict_risk(sample)

    print()
    print("=" * 50)
    print("LANDSLIDE RISK PREDICTION")
    print("=" * 50)

    print(f"Risk       : {result['risk']}")
    print(f"Confidence : {result['confidence']:.2%}")

    print()
    print("Probabilities")
    print("-" * 30)

    for risk, probability in result["probabilities"].items():
        print(
            f"{risk:<12}: "
            f"{probability:.2%}"
        )

    print("=" * 50)