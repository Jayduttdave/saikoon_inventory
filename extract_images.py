from services.supplier_loader import extract_images_once

print("Starting image extraction...")

extract_images_once(force=True)

print("Images extraction completed.")