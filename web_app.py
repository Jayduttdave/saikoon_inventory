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

from services.supplier_loader import (
    EXCEL_FILE,
    extract_images_once,
    load_supplier_catalog,
    normalize_name,
)
from services.database import Database
from services.pdf_report import generate_pdf_report

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIRS = [
    os.path.join(BASE_DIR, "images"),
    os.path.join(BASE_DIR, "assets", "images"),
]
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)

db = Database()
supplier_catalog = {}
supplier_catalog_mtime = None


def get_supplier_catalog():
    global supplier_catalog, supplier_catalog_mtime

    try:
        current_mtime = os.path.getmtime(EXCEL_FILE)
    except OSError:
        current_mtime = None

    if current_mtime != supplier_catalog_mtime:
        supplier_catalog = load_supplier_catalog()
        if current_mtime is not None:
            extract_images_once(force=True)
        supplier_catalog_mtime = current_mtime

    return supplier_catalog


def find_image_path(filename):
    for image_dir in IMAGE_DIRS:
        path = os.path.join(image_dir, filename)
        if os.path.exists(path):
            return path
    return None


def safe_all_orders():
    try:
        return db.all()
    except Exception as exc:
        app.logger.exception("Failed to load orders: %s", exc)
        return []


def safe_custom_products(supplier=None):
    try:
        return db.get_custom_products(supplier)
    except Exception as exc:
        app.logger.exception("Failed to load custom products: %s", exc)
        return []


@app.route("/")
def index():
    return render_template(
        "index.html",
        suppliers=list(get_supplier_catalog().keys()),
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
    return send_from_directory(app.static_folder, "sw.js")


@app.route("/api/products")
def api_products():
    supplier = request.args.get("supplier", "")
    query = request.args.get("query", "").strip().lower()

    catalog = get_supplier_catalog()
    items = catalog.get(supplier, [])
    default_units = {
        item["name"]: item.get("unit") or "Pièce"
        for item in items
    }

    custom_products = {
        cp["product"]: cp["image_filename"]
        for cp in safe_custom_products(supplier)
    }

    all_orders = {
        (row[0], row[1]): (row[2], row[3] or "Pièce")
        for row in (safe_all_orders() or [])
    }

    products = []
    seen = set()
    product_names = [item["name"] for item in items] + list(custom_products.keys())

    for product in product_names:
        if product in seen:
            continue
        seen.add(product)

        if query and query not in product.lower():
            continue

        qty, unit = all_orders.get(
            (supplier, product),
            (0, default_units.get(product, "Pièce")),
        )
        image_filename = custom_products.get(product)

        if image_filename:
            image_url = url_for("serve_image", filename=image_filename)
        else:
            image_url = url_for(
                "serve_image",
                filename=normalize_name(product) + ".png",
            )

        products.append(
            {
                "name": product,
                "image": image_url,
                "qty": qty,
                "unit": unit,
            }
        )

    return jsonify(products)


@app.route("/api/order", methods=["POST"])
def api_order():
    data = request.get_json(silent=True) or {}
    supplier = data.get("supplier", "")
    product = data.get("product", "")
    qty = data.get("qty", 0)
    unit = data.get("unit", "Pièce")

    if not supplier or not product:
        return jsonify({"error": "Fournisseur et produit requis."}), 400

    try:
        qty = int(qty)
    except (ValueError, TypeError):
        qty = 0

    if unit not in ["Carton", "Pièce"]:
        unit = "Pièce"

    try:
        db.upsert(supplier, product, max(0, qty), unit)
    except Exception as exc:
        app.logger.exception("Failed to save order: %s", exc)
        return jsonify({"error": "Impossible d'enregistrer la commande."}), 503

    return jsonify({"success": True})


@app.route("/api/owner_orders")
def api_owner_orders():
    query = request.args.get("query", "").strip().lower()

    rows = safe_all_orders()
    orders = []
    custom_products = {}

    for custom in safe_custom_products():
        supplier = custom["supplier"]
        product = custom["product"]
        image_filename = custom["image_filename"]
        custom_products.setdefault(supplier, {})[product] = image_filename

    for supplier, product, qty, unit in (rows or []):
        if qty <= 0:
            continue

        if query and query not in product.lower() and query not in supplier.lower():
            continue

        image_filename = custom_products.get(supplier, {}).get(product)
        if image_filename:
            image_url = url_for("serve_image", filename=image_filename)
        else:
            image_url = url_for(
                "serve_image",
                filename=normalize_name(product) + ".png",
            )

        orders.append(
            {
                "supplier": supplier,
                "product": product,
                "qty": qty,
                "unit": unit or "Pièce",
                "image": image_url,
            }
        )

    return jsonify(orders)


@app.route("/api/remove_order", methods=["DELETE"])
def api_remove_order():
    data = request.get_json(silent=True) or {}
    supplier = data.get("supplier", "")
    product = data.get("product", "")

    if not supplier or not product:
        return jsonify({"error": "Fournisseur et produit requis."}), 400

    try:
        db.delete_order(supplier, product)
    except Exception as exc:
        app.logger.exception("Failed to delete order: %s", exc)
        return jsonify({"error": "Impossible de supprimer la commande."}), 503

    return jsonify({"success": True})


@app.route("/api/add_product", methods=["POST"])
def api_add_product():
    supplier = request.form.get("supplier", "")
    product = request.form.get("product", "").strip()
    image_file = request.files.get("image")

    if not supplier or not product:
        return jsonify({"error": "Fournisseur et nom de produit requis."}), 400

    filename = None
    if image_file and image_file.filename:
        ext = os.path.splitext(image_file.filename)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            ext = ".png"

        filename = normalize_name(product) + ext
        image_folder = os.path.join(BASE_DIR, "images")
        os.makedirs(image_folder, exist_ok=True)
        save_path = os.path.join(image_folder, filename)
        image_file.save(save_path)

    try:
        db.add_custom_product(supplier, product, filename)
    except Exception as exc:
        app.logger.exception("Failed to add custom product: %s", exc)
        return jsonify({"error": "Impossible d'ajouter le produit."}), 503

    return jsonify({"success": True})


@app.route("/api/clear_orders", methods=["POST"])
def api_clear_orders():
    try:
        db.clear()
    except Exception as exc:
        app.logger.exception("Failed to clear orders: %s", exc)
        return jsonify({"error": "Impossible d'effacer les commandes."}), 503

    return jsonify({"success": True})


@app.route("/api/order_history")
def api_order_history():
    limit = request.args.get("limit", default=100, type=int)

    try:
        history = db.get_order_history(limit=limit)
    except Exception as exc:
        app.logger.exception("Failed to load order history: %s", exc)
        return jsonify({"error": "Impossible de charger l'historique."}), 503

    return jsonify(history)


@app.route("/download_pdf")
def download_pdf():
    rows = safe_all_orders()
    grouped = {}

    for supplier, product, qty, unit in (rows or []):
        if qty <= 0:
            continue
        grouped.setdefault(supplier, []).append((product, qty, unit or "Pièce"))

    if not grouped:
        return jsonify({"error": "Aucune commande active"}), 400

    file_path = generate_pdf_report(grouped)

    if file_path and os.path.exists(file_path):
        try:
            db.archive_rows(
                rows,
                action_type='pdf_downloaded',
                note=os.path.basename(file_path),
            )
        except Exception as exc:
            app.logger.exception("Failed to archive PDF history: %s", exc)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),
        )

    return jsonify({"error": "Impossible de créer le PDF"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
