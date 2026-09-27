"""Add-only archive of the iPhone camera roll (DCIM) as plain files, sorted into YYYY/MM folders.

Never deletes or overwrites anything in the archive, so photos stay safe after they are
deleted from the phone. Reruns copy only files not archived before.

Usage: photo-archive.py DEST
"""

import asyncio
import os
import re
import sys
from pathlib import Path

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.afc import AfcService

if len(sys.argv) != 2:
    sys.exit(__doc__)
DEST = Path(sys.argv[1])
INDEX = DEST / ".archived.txt"  # one "127APPLE/IMG_1234.HEIC" per line
SKIP_EXT = {".AAE"}  # Apple edit sidecars, useless outside Photos.app


def free_name(folder: Path, name: str) -> Path:
    """First path in folder for name that doesn't exist yet: IMG_1.HEIC, IMG_1-1.HEIC, ..."""
    target, stem, ext, n = folder / name, Path(name).stem, Path(name).suffix, 1
    while target.exists():
        target, n = folder / f"{stem}-{n}{ext}", n + 1
    return target


async def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    done = set(INDEX.read_text().split("\n")) if INDEX.exists() else set()
    copied = skipped = 0
    async with AfcService(await create_using_usbmux()) as afc:
        folders = sorted(d for d in await afc.listdir("/DCIM") if re.fullmatch(r"\d{3}APPLE", d))
        with INDEX.open("a") as index:
            for folder in folders:
                for name in sorted(await afc.listdir(f"/DCIM/{folder}")):
                    key = f"{folder}/{name}"
                    if key in done or Path(name).suffix.upper() in SKIP_EXT:
                        skipped += 1
                        continue
                    src = f"/DCIM/{key}"
                    taken = (await afc.stat(src))["st_birthtime"]
                    month = DEST / f"{taken:%Y}" / f"{taken:%m}"
                    month.mkdir(parents=True, exist_ok=True)
                    target = free_name(month, name)
                    part = target.with_name(target.name + ".part")
                    # pull to .part, then rename: an interrupted run never leaves a half file marked done
                    await afc.pull(src, str(part), progress_bar=False)
                    os.replace(part, target)
                    index.write(key + "\n")
                    index.flush()
                    copied += 1
                    if copied % 100 == 0:
                        print(f"copied {copied} (now at {key})", flush=True)
    print(f"DONE copied={copied} already-archived/skipped={skipped} dest={DEST}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
