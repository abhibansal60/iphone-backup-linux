"""Add-only archive of the iPhone camera roll as plain files, sorted into YYYY/MM folders.

Copies DCIM (photos taken on this phone) and PhotoData/CPLAssets (iCloud Photos synced from
other devices). Never deletes or overwrites anything in the archive, so photos stay safe after
they are deleted from the phone. Reruns copy only files not archived before.

Usage: photo-archive.py DEST
"""

import asyncio
import os
import re
import sys
from pathlib import Path

SKIP_EXT = {".AAE"}  # Apple edit sidecars, useless outside Photos.app
CPL = "/PhotoData/CPLAssets"


def free_name(folder: Path, name: str) -> Path:
    """First path in folder for name that doesn't exist yet: IMG_1.HEIC, IMG_1-1.HEIC, ..."""
    target, stem, ext, n = folder / name, Path(name).stem, Path(name).suffix, 1
    while target.exists():
        target, n = folder / f"{stem}-{n}{ext}", n + 1
    return target


async def sources(afc):
    """Yield (index key, device path) for every photo/video on the phone.

    DCIM keys look like "127APPLE/IMG_1234.HEIC"; iCloud keys like "CPLAssets/group3/ABCD.HEIC".
    """
    for folder in sorted(await afc.listdir("/DCIM")):
        if re.fullmatch(r"\d{3}\w+", folder) and await afc.isdir(f"/DCIM/{folder}"):
            for name in sorted(await afc.listdir(f"/DCIM/{folder}")):
                yield f"{folder}/{name}", f"/DCIM/{folder}/{name}"
    if await afc.exists(CPL):
        async for path in afc.dirlist(CPL, -1):
            if path != CPL and not await afc.isdir(path):
                yield "CPLAssets" + path[len(CPL):], path


async def archive(afc, dest: Path, log=print) -> tuple[int, int]:
    """Copy every photo/video not yet in dest/.archived.txt. Returns (copied, skipped)."""
    dest.mkdir(parents=True, exist_ok=True)
    index_path = dest / ".archived.txt"  # one key per line
    done = set(index_path.read_text().split("\n")) if index_path.exists() else set()
    copied = skipped = 0
    with index_path.open("a") as index:
        async for key, src in sources(afc):
            name = Path(key).name
            if key in done or Path(name).suffix.upper() in SKIP_EXT or name.startswith("."):
                skipped += 1
                continue
            st = await afc.stat(src)
            taken = st["st_birthtime"]  # when the file was created on the phone
            month = dest / f"{taken:%Y}" / f"{taken:%m}"
            month.mkdir(parents=True, exist_ok=True)
            same = month / name
            if not (same.exists() and same.stat().st_size == st["st_size"]):
                # a same-name, same-size file means a crashed run copied it but never indexed it
                target = free_name(month, name)
                part = target.with_name(target.name + ".part")
                # pull to .part, then rename: an interrupted run never leaves a half file marked done
                await afc.pull(src, str(part), progress_bar=False)
                os.replace(part, target)
            index.write(key + "\n")
            index.flush()
            copied += 1
            if copied % 100 == 0:
                log(f"copied {copied} (now at {key})", flush=True)
    return copied, skipped


async def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.afc import AfcService

    dest = Path(sys.argv[1])
    async with AfcService(await create_using_usbmux()) as afc:
        copied, skipped = await archive(afc, dest)
    print(f"DONE copied={copied} already-archived/skipped={skipped} dest={dest}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
