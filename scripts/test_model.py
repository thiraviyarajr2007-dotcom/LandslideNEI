import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from gliner2 import GLiNER2

print("Loading model...")

model = GLiNER2.from_pretrained(
    "fastino/gliner2-multi-v1"
)

print("Model loaded!")

text = """
A landslide occurred near Cherrapunji
in East Khasi Hills, Meghalaya on
12 July 2022.

The region received 182 mm rainfall.
The slope angle was 38 degrees.
The elevation was approximately 850 metres.
"""

result = model.extract_entities(
    text,
    [
        "landslide location",
        "district",
        "state",
        "date",
        "rainfall",
        "slope angle",
        "elevation"
    ]
)

print(result)
