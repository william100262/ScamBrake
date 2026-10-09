"""Validate submissions in memory before passing them to a provider."""
from io import BytesIO
from pathlib import Path
import warnings

from PIL import Image, UnidentifiedImageError

MAX_CHARACTERS = 5_000
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
MAX_IMAGE_SIDE = 10_000


class InputError(ValueError):
    """A safe, user-facing validation error."""


def validate_text(text: str) -> str:
    if not text.strip():
        raise InputError("Paste a payment request before analyzing it.")
    if len(text) > MAX_CHARACTERS:
        raise InputError("Please shorten your message to 5,000 characters or fewer.")
    return text.strip()


def validate_image(name: str, data: bytes) -> dict:
    suffix = Path(name).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg"}:
        raise InputError("Choose a PNG, JPG, or JPEG screenshot.")
    if not data:
        raise InputError("This file is empty. Please choose another screenshot.")
    if len(data) > MAX_IMAGE_BYTES:
        raise InputError("Your screenshot is larger than 5 MB. Please use a smaller image.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as img:
                expected = "PNG" if suffix == ".png" else "JPEG"
                if img.format != expected:
                    raise InputError("The image format does not match its extension. Export it as PNG or JPEG.")
                width, height = img.size
                if min(width, height) < 32 or max(width, height) > MAX_IMAGE_SIDE or width * height > MAX_IMAGE_PIXELS:
                    raise InputError("Choose a readable screenshot with sides between 32 and 10,000 pixels and at most 20 million pixels.")
                img.verify()
            # verify() checks structure; load() also checks the encoded pixel data.
            with Image.open(BytesIO(data)) as img:
                img.load()
    except InputError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise InputError("We couldn't read this image. Please upload a valid PNG or JPEG screenshot.") from None
    return {"name": name, "bytes": data, "mime_type": "image/png" if suffix == ".png" else "image/jpeg", "width": width, "height": height}
