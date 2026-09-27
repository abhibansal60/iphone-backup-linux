"""Pull the camera roll (photos + videos) out of the encrypted iPhone backup as plain files.

Usage: extract-photos.py BACKUP_DIR OUTPUT_DIR
Prompts for the backup password.
BACKUP_DIR is the device folder (named after the UDID) that contains Manifest.db.
"""

import getpass
import sys
from pathlib import Path

from iphone_backup_decrypt import EncryptedBackup

if len(sys.argv) != 3:
    sys.exit(__doc__)
backup, out = Path(sys.argv[1]), Path(sys.argv[2])
password = getpass.getpass("iPhone backup password: ")

eb = EncryptedBackup(backup_directory=str(backup), passphrase=password)
n = eb.extract_files(
    domain_like="CameraRollDomain",
    relative_paths_like="Media/DCIM/%",
    output_folder=str(out),
    preserve_folders=True,
)
print(f"extracted {n} files to {out}")
