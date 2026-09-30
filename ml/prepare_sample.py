"""Create a deterministic, balanced training subset using hard links when possible."""
import argparse
import csv
import os
import random
import shutil
from collections import defaultdict
from pathlib import Path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",default="dataset")
    parser.add_argument("--output",default=".training_sample")
    parser.add_argument("--per-class",type=int,default=150)
    parser.add_argument("--seed",type=int,default=42)
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    source=(root/args.source).resolve()
    output=(root/args.output).resolve()
    manifest=source/"dataset_manifest.csv"
    if not manifest.is_file():
        raise SystemExit(f"Missing dataset manifest: {manifest}")
    if output.exists():
        shutil.rmtree(output)
    by_class=defaultdict(list)
    with manifest.open(newline="",encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_class[row["class"]].append(row["image"])
    rng=random.Random(args.seed)
    counts={}
    for label,files in sorted(by_class.items()):
        chosen=sorted(rng.sample(files,min(args.per_class,len(files))))
        target_dir=output/label
        target_dir.mkdir(parents=True,exist_ok=True)
        for name in chosen:
            src=source/label/name
            dst=target_dir/name
            try:
                os.link(src,dst)
            except OSError:
                shutil.copy2(src,dst)
        counts[label]=len(chosen)
    print(f"Prepared {sum(counts.values())} images across {len(counts)} classes in {output}")
    print(f"Per-class range: {min(counts.values())}–{max(counts.values())}; seed={args.seed}")
if __name__=="__main__":main()
