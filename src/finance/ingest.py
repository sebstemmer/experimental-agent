from pathlib import Path

import pdfplumber

folder = Path("data/finance")

for file in folder.glob("*.pdf"):
    with pdfplumber.open(file) as pdf:
        print(f"{file.name}: {len(pdf.pages)} pages")

        page = pdf.pages[0]

        print("--- extract_text() ---")
        print(page.extract_text())

        print()
        print("--- extract_table() ---")
        table = page.extract_table()
        if table:
            print(table)
            for row in table[:15]:
                print("--- row ---")
                print(row)
        else:
            print(None)

    break
