import os
from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    send_file,
    send_from_directory,
    abort,
    url_for,
)

from services.supplier_loader import load_suppliers, normalize_name
from services.database import Database
from services.pdf_report import generate_pdf_report

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIRS = [
    os.path.join(BASE_DIR, "images"),
    os.path.join(BASE_DIR, "assets", "images"),
]

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)

db = Database()
suppliers = load_suppliers()


def find_image_path(filename):
    for image_dir in IMAGE_DIRS:
        path = os.path.join(image_dir, filename)
        if os.path.exists(path):
            return path
    return None


@app.route("/")
def index():
    return render_template(
        "index.html",
        suppliers=list(suppliers.keys()),
    )


@app.route("/images/<path:filename>")
def serve_image(filename):
    for image_dir in IMAGE_DIRS:
        path = os.path.join(image_dir, filename)
        if os.path.exists(path):
            return send_from_directory(image_dir, filename)

    fallback = find_image_path("no_image.png")
    if fallback:
        return send_file(fallback)

    abort(404)


@app.route("/sw.js")
def service_worker():
    return send_from_directory(app.static_folder, 'sw.js')


@app.route("/api/products")
def api_products():
    supplier = request.args.get("supplier", "")
    query = request.args.get("query", "").strip().lower()
    items = suppliers.get(supplier, [])

    all_orders = {
        (row[0], row[1]): row[2]
        for row in db.all()
    }

    products = [
        {
            "name": product,
            "image": url_for(
                "serve_image",
                filename=normalize_name(product) + ".png",
            ),
            "qty": all_orders.get((supplier, product), 0),
        }
        for product in items
        if not query or query in product.lower()
    ]

    return jsonify(products)


@app.route("/api/order", methods=["POST"])
def api_order():
    data = request.get_json(silent=True) or {}
    supplier = data.get("supplier", "")
    product = data.get("product", "")
    qty = data.get("qty", 0)

    try:
        qty = int(qty)
    except (ValueError, TypeError):
        qty = 0

    db.upsert(supplier, product, qty)

    return jsonify({"success": True})


@app.route("/api/owner_orders")
def api_owner_orders():
    rows = db.all()
    orders = []

    for supplier, product, qty in rows:
        if qty <= 0:
            continue

        orders.append(
            {
                "supplier": supplier,
                "product": product,
                "qty": qty,
                "image": url_for(
                    "serve_image",
                    filename=normalize_name(product) + ".png",
                ),
            }
        )

    return jsonify(orders)


@app.route("/api/clear_orders", methods=["POST"])
def api_clear_orders():
    db.clear()
    return jsonify({"success": True})


@app.route("/download_pdf")
def download_pdf():
    rows = db.all()
    grouped = {}

    for supplier, product, qty in rows:
        if qty <= 0:
            continue
        grouped.setdefault(supplier, []).append((product, qty))

    if not grouped:
        return jsonify({"error": "No active orders"}), 400

    file_path = generate_pdf_report(grouped)

    if file_path and os.path.exists(file_path):
        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),
        )

    return jsonify({"error": "Unable to create PDF"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
