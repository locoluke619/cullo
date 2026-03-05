"""
Shared image utilities used across all Cullo scripts.
Handles both standard formats (Pillow) and RAW camera files (rawpy).
"""

from pathlib import Path
from PIL import Image

try:
    import rawpy
    import numpy as np
    RAW_READABLE = True
except ImportError:
    RAW_READABLE = False

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


def open_image(image_path, half_size=False):
    """
    Open any supported image and return a PIL Image (RGB mode).

    For RAW files (CR2, NEF, ARW, DNG, etc.) rawpy decodes the sensor
    data using the camera's own white balance so colours look correct.

    half_size=True  — 2x faster decode, good enough for scoring & hashing
    half_size=False — full resolution, use before sending to Claude
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from config import RAW_FORMATS

    path = Path(image_path)
    ext = path.suffix.lower()

    if ext in RAW_FORMATS:
        if not RAW_READABLE:
            raise ImportError(
                "rawpy is needed to read RAW files.\n"
                "Run:  pip install rawpy numpy"
            )
        with rawpy.imread(str(path)) as raw:
            rgb = raw.postprocess(
                use_camera_wb=True,
                half_size=half_size,
                no_auto_bright=False,
                output_bps=8,
            )
        # fromarray returns a regular PIL Image (not a context manager)
        img = Image.fromarray(rgb)
    else:
        img = Image.open(image_path)
        img.load()  # read into memory so the file handle can be closed

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    return img


def is_raw(image_path):
    """Return True if this file is a RAW camera format."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from config import RAW_FORMATS
    return Path(image_path).suffix.lower() in RAW_FORMATS
