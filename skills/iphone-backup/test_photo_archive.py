"""Checks the add-only archive logic against a fake phone. Run: python test_photo_archive.py"""

import asyncio
import datetime as dt
import importlib.util
import shutil
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("pa", Path(__file__).with_name("photo-archive.py"))
pa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pa)


class FakeAfc:
    """In-memory stand-in for pymobiledevice3's AfcService: {path: (bytes, birthtime)}."""

    def __init__(self, files):
        self.files = dict(files)

    def _children(self, d):
        return {p[len(d) + 1:].split("/")[0] for p in self.files if p.startswith(d + "/")}

    async def listdir(self, d):
        return sorted(self._children(d))

    async def isdir(self, p):
        return bool(self._children(p))

    async def exists(self, p):
        return p in self.files or bool(self._children(p))

    async def dirlist(self, root, depth):
        yield root
        for p in sorted(self.files):
            if p.startswith(root + "/"):
                yield p

    async def stat(self, p):
        data, born = self.files[p]
        return {"st_size": len(data), "st_birthtime": born}

    async def pull(self, src, dst, progress_bar=True):
        Path(dst).write_bytes(self.files[src][0])


def run(afc, dest):
    return asyncio.run(pa.archive(afc, dest, log=lambda *a, **k: None))


jan, feb = dt.datetime(2024, 1, 5), dt.datetime(2024, 2, 9)
phone = FakeAfc({
    "/DCIM/100APPLE/IMG_0001.HEIC": (b"a" * 10, jan),
    "/DCIM/100APPLE/IMG_0001.AAE": (b"x", jan),
    "/DCIM/101APPLE/IMG_0001.HEIC": (b"b" * 20, jan),   # same name, different photo
    "/DCIM/ispRegDump.bin": (b"junk", jan),
    "/PhotoData/CPLAssets/group3/CLOUD.MOV": (b"c" * 5, feb),
})
dest = Path(tempfile.mkdtemp())
try:
    assert run(phone, dest) == (3, 1)
    assert (dest / "2024/01/IMG_0001.HEIC").read_bytes() == b"a" * 10
    assert (dest / "2024/01/IMG_0001-1.HEIC").read_bytes() == b"b" * 20
    assert (dest / "2024/02/CLOUD.MOV").exists()
    assert not list(dest.rglob("*.AAE")) and not list(dest.rglob("*.part"))

    # rerun copies nothing
    assert run(phone, dest) == (0, 4)

    # deleted on the phone -> stays in the archive; new photo -> copied
    del phone.files["/DCIM/100APPLE/IMG_0001.HEIC"]
    phone.files["/DCIM/101APPLE/IMG_0002.HEIC"] = (b"d" * 7, feb)
    assert run(phone, dest) == (1, 3)
    assert (dest / "2024/01/IMG_0001.HEIC").exists() and (dest / "2024/02/IMG_0002.HEIC").exists()

    # crash after copy but before indexing -> no duplicate on the next run
    phone.files["/DCIM/101APPLE/IMG_0003.HEIC"] = (b"e" * 3, feb)
    (dest / "2024/02/IMG_0003.HEIC").write_bytes(b"e" * 3)
    assert run(phone, dest) == (1, 4)
    assert not (dest / "2024/02/IMG_0003-1.HEIC").exists()
    print("ok")
finally:
    shutil.rmtree(dest)
