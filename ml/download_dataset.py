"""Download and arrange the public PlantVillage archive for train.py.

The archive is about 828 MiB. It is CC0 1.0 according to its Mendeley Data
record. If the host blocks automated requests, download it in a browser and
pass its path with --archive.
"""
import argparse
import csv
import shutil
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

URL = "https://data.mendeley.com/public-files/datasets/tywbtsjrjv/files/d5652a28-c1d8-4b76-97f3-72fb80f94efc/file_downloaded"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

def download(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(URL, headers={"User-Agent": "CropSure academic dataset setup"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as output:
            total = int(response.headers.get("Content-Length", 0))
            copied = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                copied += len(chunk)
                if total:
                    print(f"\rDownloaded {copied / total:.0%}", end="", flush=True)
        print()
    except Exception:
        target.unlink(missing_ok=True)
        raise

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", help="Use an archive you already downloaded")
    parser.add_argument("--output", default="dataset", help="Output class-folder directory")
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    archive = Path(args.archive).resolve() if args.archive else here / "downloads" / "PlantVillage.zip"
    output = Path(args.output).resolve()
    if not archive.exists():
        print(f"Downloading the PlantVillage archive to {archive}")
        try:
            download(archive)
        except Exception as exc:
            raise SystemExit(f"Download failed ({exc}). Download the CC0 archive in a browser, then run again with --archive <zip-path>.")
    try:
        with zipfile.ZipFile(archive) as zf:
            bad = zf.testzip()
            if bad:
                raise SystemExit(f"Archive integrity check failed at {bad}")
            extract_root = here / ".plantvillage_extract"
            extract_root.mkdir(exist_ok=True)
            for member in zf.infolist():
                # Reject absolute paths and traversal entries before extraction.
                relative = PurePosixPath(member.filename)
                if relative.is_absolute() or ".." in relative.parts:
                    raise SystemExit(f"Unsafe path in archive: {member.filename}")
            zf.extractall(extract_root)
    except zipfile.BadZipFile as exc:
        raise SystemExit(f"Not a readable ZIP archive: {exc}")

    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Output folder already contains files: {output}. Choose another --output or move it first.")
    output.mkdir(parents=True, exist_ok=True)
    manifest = []
    class_dirs = [
        p for p in (here / ".plantvillage_extract").rglob("*")
        if p.is_dir() and "___" in p.name and any(f.suffix.lower() in IMAGE_SUFFIXES for f in p.iterdir() if f.is_file())
    ]
    for class_dir in sorted(class_dirs):
        label = class_dir.name
        if label.casefold() == "background_without_leaves":
            continue
        destination = output / label
        destination.mkdir(parents=True, exist_ok=True)
        for image in sorted(f for f in class_dir.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_SUFFIXES):
            target = destination / image.name
            if target.exists():
                target = destination / f"{image.stem}_{len(manifest)}{image.suffix.lower()}"
            shutil.copy2(image, target)
            manifest.append((label, target.name, str(image.relative_to(here / ".plantvillage_extract"))))
    shutil.rmtree(here / ".plantvillage_extract")
    if not manifest:
        raise SystemExit("No PlantVillage class folders were found. Check the archive contents.")
    with (output / "dataset_manifest.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["class", "image", "archive_path"])
        writer.writerows(manifest)
    counts = {}
    for label, _, _ in manifest:
        counts[label] = counts.get(label, 0) + 1
    print(f"Prepared {len(manifest):,} images in {len(counts)} class folders at {output}")
    print("Review class counts and licensing before training. Keep farm photos for separate field evaluation.")

if __name__ == "__main__":
    main()
