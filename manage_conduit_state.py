#!/usr/bin/env python3

import argparse
import gzip
import shutil
from pathlib import Path


STATE_FILES = [
    Path("locate_tickets_history.json"),
    Path("topaz_event_registry.json"),
]


def compressed_path(path):
    return Path(str(path) + ".gz")


def compress_file(source):
    target = compressed_path(source)
    temp = Path(str(target) + ".tmp")

    if not source.exists():
        raise FileNotFoundError(
            f"Missing state file: {source}"
        )

    with source.open("rb") as src:
        with gzip.open(
            temp,
            "wb",
            compresslevel=9
        ) as dst:
            shutil.copyfileobj(src, dst)

    temp.replace(target)

    raw_size = source.stat().st_size
    compressed_size = target.stat().st_size

    print(
        f"PACKED  {source} -> {target} "
        f"({raw_size / 1024 / 1024:.2f} MiB -> "
        f"{compressed_size / 1024 / 1024:.2f} MiB)"
    )


def decompress_file(target):
    source = compressed_path(target)
    temp = Path(str(target) + ".tmp")

    if not source.exists():
        raise FileNotFoundError(
            f"Missing compressed state file: {source}"
        )

    with gzip.open(source, "rb") as src:
        with temp.open("wb") as dst:
            shutil.copyfileobj(src, dst)

    temp.replace(target)

    print(
        f"UNPACKED {source} -> {target}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Manage persistent Conduit engine state"
    )

    parser.add_argument(
        "action",
        choices=["pack", "unpack"]
    )

    args = parser.parse_args()

    for path in STATE_FILES:
        if args.action == "pack":
            compress_file(path)
        else:
            decompress_file(path)

    print()
    print(
        f"CONDUIT STATE {args.action.upper()}: PASS"
    )


if __name__ == "__main__":
    main()
