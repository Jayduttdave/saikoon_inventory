from pathlib import Path

def get_image_dir():
    path = Path.home() / "AppData" / "Local" / "Saikoon" / "images"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)