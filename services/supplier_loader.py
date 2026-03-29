import os
import pandas as pd
from openpyxl import load_workbook


EXCEL_FILE = "Fournisseur Yoomi.xlsx"
IMAGE_FOLDER = "images"


def normalize_name(name):

    return (
        str(name)
        .lower()
        .replace(" ", "_")
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("ç", "c")
        .replace("/", "")
    )


def extract_images_once():

    if not os.path.exists(IMAGE_FOLDER):
        os.makedirs(IMAGE_FOLDER)

    print("Checking product images...")

    wb = load_workbook(
        EXCEL_FILE,
        data_only=True
    )

    for sheet_name in wb.sheetnames:

        ws = wb[sheet_name]

        if not hasattr(ws, "_images"):
            continue

        for image in ws._images:

            row = image.anchor._from.row + 1

            product_name = ws.cell(
                row=row,
                column=2
            ).value

            if not product_name:
                continue

            filename = normalize_name(product_name)

            path = os.path.join(
                IMAGE_FOLDER,
                f"{filename}.png"
            )

            if os.path.exists(path):
                continue

            try:

                data = image._data()

                with open(path, "wb") as f:
                    f.write(data)

                print("Saved:", filename)

            except Exception as e:

                print("Image skip:", e)


def load_suppliers():

    suppliers = {}

    print("Loading suppliers...")

    xls = pd.ExcelFile(EXCEL_FILE)

    for sheet in xls.sheet_names:

        df = pd.read_excel(
            xls,
            sheet
        )

        products = []

        for col in df.columns:

            if "NOM" in col.upper():

                for value in df[col]:

                    if pd.notna(value):

                        products.append(
                            str(value)
                        )

        suppliers[sheet] = products

    return suppliers