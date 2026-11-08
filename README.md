# Image Resizer

Makes images smaller, in dimensions, file size, or both. Useful for emailing photos, uploading to websites
that have a size limit, or saving disk space. Put your images in the `input` folder, run the script, and get the smaller
copies in the `output` folder.

## Folder layout

```
image_resizer/
├── resize_images.py   the script
├── requirements.txt   Python packages to install
├── README.md          this file
├── input/             put the images you want resized here
└── output/            smaller copies appear here, with the same names
```

## Setup (one time)

1. Install **Python 3.9 or newer** from https://www.python.org/downloads/
   (on Windows, tick "Add Python to PATH" during install).
2. Open a terminal in the `image_resizer` folder and run:

   ```
   pip install -r requirements.txt
   ```

## How to use

1. Copy the images you want resized into the `input` folder.
2. Open a terminal in the `image_resizer` folder and run:

   ```
   python resize_images.py
   ```

3. It asks how you want to shrink them:
   - **Limit the longest side**, for example to 1920 pixels. Good for most uses.
   - **Scale by a percentage**, for example to 50% of the width and height.
   - **Limit the file size**, for example to 500 KB. Good for upload forms with a size limit.
   - **Keep the size, just compress them.**
4. The smaller images are saved in `output` with the same names. For each image it shows the old and new dimensions
   and file size.

You can also give the settings straight away so it doesn't ask:

| Command | What it does |
|---|---|
| `python resize_images.py` | Asks how you want to shrink them |
| `python resize_images.py -s 1920` | Longest side at most 1920 pixels |
| `python resize_images.py -p 50` | Half the width and height |
| `python resize_images.py --max-kb 500` | Every file at most 500 KB |
| `python resize_images.py -s 1920 --max-kb 500` | Both: at most 1920 pixels and at most 500 KB |
| `python resize_images.py --width 800` | Width at most 800 pixels |
| `python resize_images.py -s 1920 -f webp` | Resize and also convert to webp |
| `python resize_images.py -q 70` | Keep the dimensions, compress harder |
| `python resize_images.py --help` | Shows all options |

## Options

| Option | Default | Meaning |
|---|---|---|
| `-s`, `--size` | none | Longest side (width or height) at most this many pixels |
| `-p`, `--percent` | none | Scale width and height to this percentage (1–100) |
| `--width` | none | Width at most this many pixels |
| `--height` | none | Height at most this many pixels |
| `--max-kb` | none | Make each file at most this many KB. It lowers the quality first, then shrinks the image if it's still too big |
| `-q`, `--quality` | `85` | Quality from 1 to 100 for jpg, webp and heic. Lower gives smaller files that look worse |
| `-f`, `--format` | keep | Also convert to `jpg`, `png` or `webp`. Without it, each image keeps its own format |
| `-i`, `--input` | `input` folder | Folder to read images from |
| `-o`, `--output` | `output` folder | Folder to save resized images to |

You can combine options. When you use several size limits, the image is shrunk until it meets all of them.

**Common sizes:** 3840 (4K screens), 1920 (Full HD, fine for most websites and screens), 1280 (email and chat),
800 (thumbnails, small web images).

**Image types it accepts:** `.jpg .jpeg .jfif .png .webp .heic .heif .gif .bmp .tif .tiff`.
Other files are listed as "ignored" and left alone.

## Good to know

- **Original images are never changed or deleted.** The script only reads from `input`.
- **Images are never made bigger.** If an image is already smaller than the size you ask for, it keeps its dimensions.
- **The shape stays the same.** Width and height are always scaled together, so nothing gets stretched.
- **If re-saving would make a file bigger** (this happens with images that are already well compressed),
  the original is copied as-is instead.
- **`--max-kb` works best with jpg and webp.** For png, gif, bmp and tiff it can only make the image smaller in
  dimensions to reach the limit. Add `-f jpg` or `-f webp` to get much smaller files.
- **Running it again overwrites earlier results** with the same name in `output`.
- **Sideways phone photos are turned the right way up** automatically.
- **Transparent images converted to jpg get a white background.**
- **Photo info is kept** (date taken, camera, and also GPS location if the photo has it).
- **Animated GIFs**: only the first frame is kept.
- **Subfolders inside `input` are not scanned.** Put the images directly in `input`.

## Troubleshooting

**`Error: Pillow is not installed`**
Run `pip install -r requirements.txt` from inside the `image_resizer` folder.

**HEIC files are listed as ignored**
pillow-heif isn't installed. Run `pip install -r requirements.txt`.

**`couldn't get it under ... KB`**
The limit is very small for that image. Try a bigger limit, or add `-f jpg` or `-f webp` if it's a png.

**`'python' is not recognized`**
Python isn't on your PATH. On Windows, try `py resize_images.py` instead, or reinstall Python with "Add Python to PATH" ticked.

**An image shows `[fail]`**
The reason is printed next to it. Usually the file is damaged or isn't really an image. The other images still get resized.
