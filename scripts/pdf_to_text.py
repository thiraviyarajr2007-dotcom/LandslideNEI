import fitz
import os

INPUT = "input/pdf"
OUTPUT = "output/text"

os.makedirs(OUTPUT, exist_ok=True)

for filename in os.listdir(INPUT):

    if not filename.lower().endswith(".pdf"):
        continue

    pdf_path = os.path.join(INPUT, filename)

    document = fitz.open(pdf_path)

    text = ""

    for page_number, page in enumerate(document, start=1):

        page_text = page.get_text()

        text += f"\n--- PAGE {page_number} ---\n"
        text += page_text

    output_name = filename.replace(".pdf", ".txt")

    output_path = os.path.join(
        OUTPUT,
        output_name
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(text)

    document.close()

    print("Completed:", filename)
