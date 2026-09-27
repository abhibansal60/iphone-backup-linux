"""Pull the camera roll (photos + videos) out of the encrypted iPhone backup as plain files.

Usage: extract-photos.py BACKUP_DIR OUTPUT_DIR
Prompts for the backup password.
BACKUP_DIR is the device folder (named after the UDID) that contains Manifest.db.
Photos taken on the phone land in OUTPUT_DIR/Media/DCIM/, iCloud-synced ones in
OUTPUT_DIR/Media/PhotoData/CPLAssets/.
"""

import getpass
import sys
from pathlib import Path

from iphone_backup_decrypt import DomainLike, EncryptedBackup
from iphone_backup_decrypt.exceptions import IncorrectPassphraseError

if len(sys.argv) != 3:
    sys.exit(__doc__)
backup, out = Path(sys.argv[1]), Path(sys.argv[2])
if not (backup / "Manifest.db").exists():
    sys.exit(f"{backup} has no Manifest.db; pass the device folder inside the backup directory")
password = getpass.getpass("iPhone backup password: ")

eb = EncryptedBackup(backup_directory=str(backup), passphrase=password)
try:
    n = sum(
        eb.extract_files(domain_like=DomainLike.CAMERA_ROLL, relative_paths_like=paths,
                         output_folder=str(out), preserve_folders=True)
        for paths in ("Media/DCIM/%", "Media/PhotoData/CPLAssets/%")
    )
except IncorrectPassphraseError:
    sys.exit("Wrong backup password.")
print(f"extracted {n} files to {out}")
