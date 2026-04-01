import os
from datetime import datetime
from zoneinfo import ZoneInfo

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image
)

from reportlab.lib.styles import getSampleStyleSheet

from services.supplier_loader import normalize_name


# --------------------------
# Paths
# --------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(__file__)
)

IMAGE_DIRS = [
    os.path.join(BASE_DIR, "images"),
    os.path.join(BASE_DIR, "assets", "images")
]

DEFAULT_IMAGE = os.path.join(
    IMAGE_DIRS[0],
    "no_image.png"
)


def find_image_path(filename):

    for image_dir in IMAGE_DIRS:

        path = os.path.join(
            image_dir,
            filename
        )

        if os.path.exists(path):
            return path

    return None


# --------------------------
# PDF generator
# --------------------------

def format_french_datetime(dt):
    weekdays = [
        "lundi",
        "mardi",
        "mercredi",
        "jeudi",
        "vendredi",
        "samedi",
        "dimanche",
    ]
    months = [
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ]
    return (
        f"{weekdays[dt.weekday()]} {dt.day} {months[dt.month - 1]} "
        f"{dt.year} {dt:%H:%M:%S}"
    )


def generate_pdf_report(orders):

    try:

        try:
            now = datetime.now(ZoneInfo("Europe/Paris"))
        except Exception:
            now = datetime.now()

        filename = (
            "commandes_"
            + now.strftime("%Y%m%d_%H%M%S")
            + ".pdf"
        )

        orders_dir = os.path.join(
            BASE_DIR,
            "orders"
        )

        if not os.path.exists(orders_dir):

            os.makedirs(orders_dir)

        file_path = os.path.join(
            orders_dir,
            filename
        )

        doc = SimpleDocTemplate(file_path)

        styles = getSampleStyleSheet()

        elements = []

        # Title

        elements.append(
            Paragraph(
                "Commandes Saikoon Kitchen",
                styles["Title"]
            )
        )

        elements.append(
            Spacer(1, 8)
        )

        elements.append(
            Paragraph(
                format_french_datetime(now),
                styles["Normal"]
            )
        )

        elements.append(
            Spacer(1, 20)
        )

        # Loop suppliers

        for supplier, items in orders.items():

            elements.append(

                Paragraph(
                    supplier,
                    styles["Heading2"]
                )

            )

            elements.append(
                Spacer(1, 10)
            )

            # Loop products

            for item in items:
                if len(item) == 3:
                    product, qty, unit = item
                else:
                    product, qty = item
                    unit = "Pièce"

                image_name = normalize_name(product)

                image_path = find_image_path(image_name + ".png")

                if not image_path:
                    image_path = find_image_path("no_image.png")

                try:

                    if image_path:

                        img = Image(
                            image_path,
                            width=40,
                            height=40
                        )

                        elements.append(img)

                except:

                    pass

                elements.append(

                    Paragraph(
                        f"{product} : {qty} {unit}",
                        styles["BodyText"]
                    )

                )

                elements.append(
                    Spacer(1, 12)
                )

        doc.build(elements)

        print(
            "PDF saved:",
            file_path
        )

        return file_path

    except Exception as e:

        print(
            "PDF error:",
            e
        )

        return None