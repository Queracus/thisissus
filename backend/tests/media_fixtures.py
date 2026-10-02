"""Generated images for media tests (no binary fixtures in the repo)."""
import io
import os

import pillow_heif
from PIL import ExifTags, Image

pillow_heif.register_heif_opener()


def jpeg_bytes(w=800, h=600, gps=False, noise=False) -> bytes:
    img = Image.frombytes("RGB", (w, h), os.urandom(w * h * 3)) if noise else Image.new("RGB", (w, h), (200, 80, 120))
    exif = Image.Exif()
    exif[ExifTags.Base.Make] = "TestCam"
    if gps:  # Bled: 46°22'N 14°6'E
        exif[ExifTags.IFD.GPSInfo] = {1: "N", 2: (46.0, 22.0, 0.0), 3: "E", 4: (14.0, 6.0, 0.0)}
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=95, exif=exif)
    return buf.getvalue()


def heic_bytes(w=640, h=480) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (30, 140, 90)).save(buf, format="HEIF")
    return buf.getvalue()


def open_image(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))
