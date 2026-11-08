"""
Image Resizer
-------------
Put images in the "input" folder, run this script, and smaller copies show
up in the "output" folder. The original images are never changed.

    python resize_images.py                  # asks how you want to shrink them
    python resize_images.py -s 1920          # longest side at most 1920 pixels
    python resize_images.py -p 50            # half the width and height
    python resize_images.py --max-kb 500     # every file at most 500 KB
    python resize_images.py -s 1920 -f webp  # resize and save as webp

See README.md for all the details.
"""

import argparse
import io
import shutil
import sys
from collections import Counter
from pathlib import Path

try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError:
    sys.exit("Error: Pillow is not installed.\nFix it by running:  pip install -r requirements.txt")

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False

# The input/output folders live next to this script, so it works no matter
# which folder you run it from.
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

# format name -> (file extension, Pillow format name, keeps transparency, uses --quality)
FORMATS = {
    "jpg":  (".jpg",  "JPEG", False, True),
    "png":  (".png",  "PNG",  True,  False),
    "webp": (".webp", "WEBP", True,  True),
    "heic": (".heic", "HEIF", True,  True),
    "gif":  (".gif",  "GIF",  True,  False),
    "bmp":  (".bmp",  "BMP",  False, False),
    "tiff": (".tiff", "TIFF", True,  False),
}

# Formats you can pick with --format. Without it, each image keeps its own format.
CONVERT_TO = ["jpg", "png", "webp"]

# Formats that can carry photo info (date taken, camera, ...) and color profiles.
KEEPS_PHOTO_INFO = {"jpg", "png", "webp", "heic", "tiff"}

# Input file extension -> format name. Some formats have more than one extension.
INPUT_EXTENSIONS = {
    ".jpg": "jpg", ".jpeg": "jpg", ".jfif": "jpg", ".png": "png", ".webp": "webp",
    ".heic": "heic", ".heif": "heic", ".gif": "gif", ".bmp": "bmp",
    ".tif": "tiff", ".tiff": "tiff",
}

DEFAULT_QUALITY = 85
LOWEST_QUALITY = 40  # --max-kb won't go below this; it shrinks the image instead
HEIC_HINT = "HEIC needs pillow-heif. Fix it by running:  pip install -r requirements.txt"


def find_input_files(input_dir: Path) -> list[Path]:
    """Return the images in input_dir. Other files are listed as ignored."""
    images = []
    for path in sorted(input_dir.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file() or path.name.startswith("."):
            continue
        fmt = INPUT_EXTENSIONS.get(path.suffix.lower())
        if fmt == "heic" and not HEIC_SUPPORTED:
            print(f"  [ignored] {path.name} ({HEIC_HINT})")
        elif fmt:
            images.append(path)
        else:
            print(f"  [ignored] {path.name} (not a supported image file)")
    return images


def ask_number(prompt: str, low: int, high=None) -> int:
    while True:
        answer = input(prompt).strip().lstrip("﻿").lower().rstrip("%").replace("px", "").replace("kb", "").strip()
        if answer.isdigit() and int(answer) >= low and (high is None or int(answer) <= high):
            return int(answer)
        limit = f"between {low} and {high}" if high else f"of at least {low}"
        print(f"  Please type a whole number {limit}.")


def ask_settings(args):
    """Ask how to shrink the images when no options were given on the command line."""
    print("\nHow do you want to shrink them?")
    print("  1) Limit the longest side   (for example 1920 pixels)")
    print("  2) Scale by a percentage    (for example 50%)")
    print("  3) Limit the file size      (for example 500 KB)")
    print("  4) Keep the size, just compress them")
    while True:
        choice = input("Choose 1-4: ").strip().lstrip("﻿")
        if choice in ("1", "2", "3", "4"):
            break
        print("  Please type 1, 2, 3 or 4.")
    if choice == "1":
        args.size = ask_number("Longest side in pixels: ", 1)
    elif choice == "2":
        args.percent = ask_number("Percentage (1-100): ", 1, 100)
    elif choice == "3":
        args.max_kb = ask_number("Maximum file size in KB: ", 1)


def open_image(src: Path) -> Image.Image:
    """Open an image and turn it the right way up (phone photos are often stored sideways)."""
    try:
        with Image.open(src) as img:
            return ImageOps.exif_transpose(img)
    except UnidentifiedImageError:
        raise ValueError("not a valid image (the file may be damaged)") from None


def prepare(img: Image.Image, keeps_transparency: bool) -> Image.Image:
    """Give the image colors the target format can save."""
    has_transparency = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
    if has_transparency and keeps_transparency:
        return img.convert("RGBA")
    if has_transparency:
        # Formats like jpg can't store transparency, so put the image on a white background.
        rgba = img.convert("RGBA")
        flat = Image.new("RGB", rgba.size, "white")
        flat.paste(rgba, mask=rgba.getchannel("A"))
        flat.info = img.info
        return flat
    return img.convert("RGB")


def new_dimensions(width: int, height: int, args) -> tuple[int, int]:
    """Work out the new size, keeping the shape of the image. Never makes images bigger."""
    scale = 1.0
    if args.percent:
        scale = min(scale, args.percent / 100)
    if args.size:
        scale = min(scale, args.size / max(width, height))
    if args.width:
        scale = min(scale, args.width / width)
    if args.height:
        scale = min(scale, args.height / height)
    return max(1, round(width * scale)), max(1, round(height * scale))


def encode(img: Image.Image, fmt: str, quality: int, extras: dict) -> bytes:
    """Save the image to memory and return the file's bytes."""
    _, pil_format, _, uses_quality = FORMATS[fmt]
    options = dict(extras)
    if uses_quality:
        options["quality"] = quality
    if pil_format in ("JPEG", "PNG"):
        options["optimize"] = True
    if pil_format == "TIFF":
        options["compression"] = "tiff_lzw"  # lossless compression
    buffer = io.BytesIO()
    img.save(buffer, pil_format, **options)
    return buffer.getvalue()


def fit_file_size(img: Image.Image, fmt: str, quality: int, extras: dict, limit: int):
    """
    Make the file fit under `limit` bytes. First lowers the quality (for jpg, webp
    and heic), and if that's not enough, shrinks the image a bit and tries again.
    Returns (file bytes, image).
    """
    uses_quality = FORMATS[fmt][3]
    while True:
        data = encode(img, fmt, quality, extras)
        if len(data) <= limit:
            return data, img
        if uses_quality:
            # Find the highest quality that fits, between LOWEST_QUALITY and quality.
            low, high, best = LOWEST_QUALITY, quality - 1, None
            while low <= high:
                middle = (low + high) // 2
                attempt = encode(img, fmt, middle, extras)
                if len(attempt) <= limit:
                    best, low = attempt, middle + 1
                else:
                    high = middle - 1
            if best:
                return best, img
        if min(img.size) <= 16:
            return data, img  # can't make it any smaller
        smaller = (max(1, round(img.width * 0.8)), max(1, round(img.height * 0.8)))
        img = img.resize(smaller, Image.Resampling.LANCZOS)


def process(src: Path, out_path: Path, fmt: str, args) -> bool:
    """Resize/compress one image. Returns True on success."""
    try:
        img = prepare(open_image(src), FORMATS[fmt][2])
        old_dims = img.size
        dims = new_dimensions(*img.size, args)
        if dims != img.size:
            img = img.resize(dims, Image.Resampling.LANCZOS)

        extras = {}
        if fmt in KEEPS_PHOTO_INFO:
            exif = img.getexif()
            if len(exif):
                extras["exif"] = exif.tobytes()
            if img.info.get("icc_profile"):
                extras["icc_profile"] = img.info["icc_profile"]

        if args.max_kb:
            data, img = fit_file_size(img, fmt, args.quality, extras, args.max_kb * 1024)
        else:
            data = encode(img, fmt, args.quality, extras)

        old_bytes = src.stat().st_size
        same_format = INPUT_EXTENSIONS[src.suffix.lower()] == fmt
        if same_format and img.size == old_dims and len(data) >= old_bytes:
            # Saving it again would only make it bigger, so keep the original file.
            shutil.copy2(src, out_path)
            note = "already small, copied as-is"
            new_bytes = old_bytes
        else:
            out_path.write_bytes(data)
            new_bytes = len(data)
            saved = 100 - new_bytes * 100 / old_bytes if old_bytes else 0
            note = f"{saved:.0f}% smaller" if saved >= 0 else f"{-saved:.0f}% bigger"
    except Exception as error:
        out_path.unlink(missing_ok=True)  # don't leave half-written files behind
        print(f"  [fail] {src.name}: {error}")
        return False

    dims_text = f"{old_dims[0]}x{old_dims[1]} -> {img.width}x{img.height}"
    size_text = f"{old_bytes / 1024:,.0f} KB -> {new_bytes / 1024:,.0f} KB"
    print(f"  [ok]   {out_path.name:<30} {dims_text:<24} {size_text}  ({note})")
    if args.max_kb and new_bytes > args.max_kb * 1024:
        print(f"         couldn't get it under {args.max_kb} KB, this is as small as it goes")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Make every image in the input folder smaller (dimensions and/or file size).",
        epilog="With no options, it asks you what to do.",
    )
    parser.add_argument("-s", "--size", type=int, metavar="PIXELS",
                        help="longest side at most this many pixels, e.g. 1920")
    parser.add_argument("-p", "--percent", type=int, choices=range(1, 101), metavar="1-100",
                        help="scale width and height to this percentage, e.g. 50")
    parser.add_argument("--width", type=int, metavar="PIXELS", help="width at most this many pixels")
    parser.add_argument("--height", type=int, metavar="PIXELS", help="height at most this many pixels")
    parser.add_argument("--max-kb", type=int, metavar="KB", help="make each file at most this many KB")
    parser.add_argument("-q", "--quality", type=int, choices=range(1, 101), metavar="1-100",
                        help=f"quality for jpg, webp and heic (default: {DEFAULT_QUALITY})")
    parser.add_argument("-f", "--format", choices=CONVERT_TO,
                        help="also convert to this format (default: keep each image's format)")
    parser.add_argument("-i", "--input", type=Path, default=INPUT_DIR,
                        help="folder to read images from (default: the input folder)")
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT_DIR,
                        help="folder to save images to (default: the output folder)")
    args = parser.parse_args()

    for name in ("size", "width", "height", "max_kb"):
        value = getattr(args, name)
        if value is not None and value < 1:
            sys.exit(f"Error: --{name.replace('_', '-')} must be at least 1.")

    nothing_chosen = all(getattr(args, name) is None
                         for name in ("size", "percent", "width", "height", "max_kb", "quality", "format"))
    if args.quality is None:
        args.quality = DEFAULT_QUALITY

    args.input.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)

    print(f"Looking in: {args.input}")
    files = find_input_files(args.input)
    if not files:
        print("No images found. Put the images you want resized in that folder, then run this again.")
        return

    print(f"Found {len(files)} image(s).")
    if nothing_chosen:
        ask_settings(args)

    # Converting "logo.png" and "logo.gif" both to jpg would give two "logo.jpg" files,
    # so those keep their old extension in the name: "logo_png.jpg", "logo_gif.jpg".
    stem_counts = Counter(f.stem.lower() for f in files)
    duplicate_stems = {stem for stem, count in stem_counts.items() if count > 1}

    print()
    done = failed = 0
    for src in files:
        if args.format:
            fmt = args.format
            stem = f"{src.stem}_{src.suffix.lstrip('.').lower()}" if src.stem.lower() in duplicate_stems else src.stem
            out_path = args.output / (stem + FORMATS[fmt][0])
        else:
            fmt = INPUT_EXTENSIONS[src.suffix.lower()]
            out_path = args.output / src.name
        if process(src, out_path, fmt, args):
            done += 1
        else:
            failed += 1

    print(f"\nDone: {done} resized, {failed} failed.")
    print(f"Resized images are in: {args.output}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        sys.exit(1)
