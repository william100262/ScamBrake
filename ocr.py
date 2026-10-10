"""Bounded local screenshot OCR. No network calls, logging, or content cache."""
from io import BytesIO
import os
import math
from pathlib import Path
import shutil
from statistics import median
from threading import Lock

from PIL import Image, ImageOps, ImageStat
from ui.validation import validate_image

MAX_OCR_SIDE = 3200
MAX_OCR_PIXELS = 6_000_000
OCR_TIMEOUT = 20
_ENGINE_LOCK = Lock()
UNREADABLE_MESSAGE = "We couldn't reliably read a message from this image. Try a clearer screenshot or paste the message instead."


def _threshold(name, default, maximum=100):
    """Reject invalid configuration safely rather than disabling quality gates."""
    try:
        value = float(os.environ.get(name, str(default)))
        if not math.isfinite(value) or not 0 < value <= maximum:
            raise ValueError
        return value
    except ValueError:
        raise OCRError("OCR confidence settings are invalid. Check the README configuration or paste the message instead.") from None


def _readable_token(text):
    # No dictionary or spelling correction: preserve names, numbers and URLs.
    # Punctuation-only fragments cannot establish that a message is readable.
    return (text.isprintable() and "\ufffd" not in text
            and sum(c.isalnum() for c in text) / len(text) >= 0.4)


def _filter_detections(data):
    """Reconstruct only credible lines from native Tesseract TSV word records.

    Scores are engine heuristics, not calibrated probabilities. An empty result
    means insufficient reliable text, not proof that the image contains no text.
    """
    word_min = _threshold("SCAMBRAKE_OCR_WORD_CONFIDENCE", 60)
    line_min = _threshold("SCAMBRAKE_OCR_LINE_CONFIDENCE", 80)
    single_min = _threshold("SCAMBRAKE_OCR_SINGLE_WORD_CONFIDENCE", 90)
    fraction_min = _threshold("SCAMBRAKE_OCR_RELIABLE_FRACTION", 0.5, 1)
    fields = ("text", "conf", "level", "page_num", "block_num", "par_num", "line_num",
              "left", "top", "width", "height")
    if not isinstance(data, dict) or any(not isinstance(data.get(key), list) for key in fields):
        raise OCRError("Text extraction returned an unreadable result. Please retry or type the message below.")
    count = len(data["text"])
    if any(len(data[key]) != count for key in fields):
        raise OCRError("Text extraction returned an unreadable result. Please retry or type the message below.")
    lines = {}
    total = 0
    for i in range(count):
        text = data["text"][i]
        if not isinstance(text, str) or not text.strip():
            continue
        text = text.strip()
        try:
            if int(data["level"][i]) != 5:
                continue  # Structural records have confidence -1, not words.
            total += 1
            confidence = float(data["conf"][i])
            key = tuple(int(data[field][i]) for field in ("page_num", "block_num", "par_num", "line_num"))
            left, top, width, height = (int(data[field][i]) for field in ("left", "top", "width", "height"))
            valid = (math.isfinite(confidence) and word_min <= confidence <= 100
                     and min(left, top) >= 0 and min(width, height) > 0 and _readable_token(text))
        except (ValueError, TypeError, OverflowError):
            continue  # Invalid records contribute to the rejection denominator.
        lines.setdefault(key, []).append((text, confidence, left, top, width, height, valid))
    accepted = []
    accepted_count = 0
    # Tesseract's block/paragraph/line IDs retain its reading order; never join
    # separate lines merely because individual words have high confidence.
    for key in sorted(lines):
        words = lines[key]
        credible = [word for word in words if word[-1]]
        if not credible or len(credible) / len(words) < fraction_min:
            continue
        height = median(word[5] for word in credible)
        baseline = median(word[3] + word[5] for word in credible)
        aligned = [word for word in credible
                   if 0.4 * height <= word[5] <= 2.5 * height
                   and abs(word[3] + word[5] - baseline) <= 0.6 * height]
        if not aligned or len(aligned) / len(words) < fraction_min:
            continue
        minimum = max(line_min, single_min) if len(aligned) == 1 else line_min
        if sum(word[1] for word in aligned) / len(aligned) < minimum:
            continue
        accepted.append(" ".join(word[0] for word in sorted(aligned, key=lambda word: word[2])))
        accepted_count += len(aligned)
    # A few accidental confident words in a page full of noise are insufficient.
    if not total or accepted_count / total < fraction_min:
        return ""
    return "\n".join(accepted)


class OCRError(RuntimeError):
    """Safe public error; engine diagnostics and screenshot text are never exposed."""


def tesseract_command():
    """Resolve trusted administrator configuration, PATH, or Windows defaults."""
    configured = os.environ.get("SCAMBRAKE_TESSERACT_CMD", "").strip()
    if configured:
        if Path(configured).is_file():
            return configured
        raise OCRError("The configured OCR engine could not be found. Check SCAMBRAKE_TESSERACT_CMD or paste the message instead.")
    found = shutil.which("tesseract")
    if found:
        return found
    for folder in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("LOCALAPPDATA", "")):
        candidate = Path(folder) / "Tesseract-OCR" / "tesseract.exe"
        if candidate.is_file():
            return str(candidate)
    raise OCRError("Local OCR is not installed. Install Tesseract using the README instructions, or type the message below.")


def _prepare(data):
    with Image.open(BytesIO(data)) as source:
        # EXIF orientation also handles phone images without guessing from text.
        oriented = ImageOps.exif_transpose(source)
        width, height = oriented.size
        scale = min(2.0 if width < 1000 else 1.0, MAX_OCR_SIDE / max(width, height),
                    (MAX_OCR_PIXELS / (width * height)) ** 0.5)
        if scale != 1:
            oriented = oriented.resize((max(1, int(width * scale)), max(1, int(height * scale))), Image.Resampling.LANCZOS)
        rgba = oriented.convert("RGBA")
        background = Image.new("RGBA", rgba.size, "white")
        gray = Image.alpha_composite(background, rgba).convert("L")
        # Light text on a predominantly dark background benefits from inversion.
        if ImageStat.Stat(gray).mean[0] < 100:
            gray = ImageOps.invert(gray)
        return ImageOps.autocontrast(gray)


def _recognize(image):
    try:
        import pytesseract
    except ImportError:
        raise OCRError("The OCR Python dependency is unavailable. Install requirements.txt or paste the message instead.") from None
    command = tesseract_command()
    # pytesseract uses a global command. Serialize configuration and OCR, and
    # fail promptly under load rather than queuing unbounded OCR work.
    if not _ENGINE_LOCK.acquire(timeout=1):
        raise OCRError("Text extraction is busy. Please retry in a moment.")
    try:
        pytesseract.pytesseract.tesseract_cmd = command
        # Uses temporary files, removed by pytesseract's finally block on success,
        # error, and timeout. Never pass an uploaded filename to the executable.
        return pytesseract.image_to_data(image, lang="eng", config="--psm 6",
                                        output_type=pytesseract.Output.DICT, timeout=OCR_TIMEOUT)
    except pytesseract.TesseractNotFoundError:
        raise OCRError("Local OCR could not start. Check the Tesseract installation or type the message below.") from None
    except pytesseract.TesseractError:
        raise OCRError("Local OCR failed. Check that Tesseract's English language data is installed, or type the message below.") from None
    except RuntimeError:
        raise OCRError("Text extraction took too long. Try a smaller crop or type the message below.") from None
    except Exception:
        raise OCRError("Text extraction failed. Please retry with a clearer screenshot or type the message below.") from None
    finally:
        _ENGINE_LOCK.release()


def extract_text(data: bytes, name: str = "screenshot.png") -> str:
    """Return confidence-filtered literal OCR words, or empty if unreliable.

    The filename only supplies an additional format consistency check. Image
    contents, dimensions, integrity, and byte size are independently validated.
    """
    validate_image(name, data)
    try:
        with _prepare(data) as image:
            detections = _recognize(image)
        return _filter_detections(detections)
    except OCRError:
        raise
    except Exception:
        raise OCRError("Text extraction failed. Please try a clearer screenshot or type the message below.") from None
