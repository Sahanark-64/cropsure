"""Create a deterministic, per-class train/validation split using hard links."""
import argparse
import random
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    source = args.data.resolve()
    output = args.output.resolve()
    if not source.is_dir() or output == source or source in output.parents:
        raise SystemExit("Choose an existing source folder and a separate output folder.")
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Output folder must be empty: {output}")
    if not 0 < args.validation_fraction < 1:
        raise SystemExit("validation-fraction must be between 0 and 1")
    rng = random.Random(args.seed)
    count = 0
    for class_dir in sorted(p for p in source.iterdir() if p.is_dir()):
        files = sorted(p for p in class_dir.iterdir() if p.is_file())
        if len(files) < 2:
            raise SystemExit(f"Need at least two images in {class_dir.name}")
        rng.shuffle(files)
        split_at = max(1, min(len(files) - 1, round(len(files) * (1 - args.validation_fraction))))
        for subset, group in (("train", files[:split_at]), ("validation", files[split_at:])):
            target = output / subset / class_dir.name
            target.mkdir(parents=True, exist_ok=True)
            for image in group:
                (target / image.name).hardlink_to(image)
                count += 1
    print(f"Created {count} hard links across {len(list((output / 'train').iterdir()))} classes at {output}")


if __name__ == "__main__":
    main()
