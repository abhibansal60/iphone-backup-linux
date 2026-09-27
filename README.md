# iphone-backup-linux

Back up an iPhone to an external disk from Linux, with no iTunes and no sudo. You get:

- **A full encrypted backup** in the same format iTunes and Finder use, so you can restore it to any iPhone. Later runs are incremental and copy only what changed.
- **An add-only photo archive**: every photo and video as a plain file in `YYYY/MM/` folders, keeping its original date. Reruns copy only new photos and never delete anything, so you can clear photos off the phone and they stay safe on the disk.
- **Photo extraction** from the encrypted backup, if you ever need it.

It's a [Claude Code](https://claude.com/claude-code) skill: install it, say "back up my iPhone", and Claude walks through detecting the disk, mounting it, pairing, encryption, the backup and the archive, and handles the gotchas below. The two scripts also work on their own.

## Install as a Claude Code plugin

```
/plugin marketplace add abhibansal60/iphone-backup-linux
/plugin install iphone-backup-linux@iphone-backup-linux
```

## Use the scripts directly

You need Python 3.10–3.13 and `usbmuxd` running; most desktop distros run it by default.

```sh
python3 -m venv ~/.local/share/iphone-backup/venv
VENV=~/.local/share/iphone-backup/venv
$VENV/bin/pip install pymobiledevice3 iphone_backup_decrypt

# pair: unlock the phone and tap Trust
$VENV/bin/pymobiledevice3 lockdown pair

# full or incremental backup
mkdir -p /path/to/disk/iPhone-Backup
$VENV/bin/pymobiledevice3 backup2 backup /path/to/disk/iPhone-Backup

# add-only photo archive
$VENV/bin/python skills/iphone-backup/photo-archive.py /path/to/disk/iPhone-Photos

# decrypt photos out of an encrypted backup
$VENV/bin/python skills/iphone-backup/extract-photos.py /path/to/disk/iPhone-Backup/<UDID> ~/Pictures/from-backup
```

## Gotchas this handles

- **The NTFS disk won't mount** ("wrong fs type, bad superblock"). The disk was unplugged from Windows without ejecting. Mount it with `udisksctl mount -b /dev/sdXN -t ntfs`, which uses ntfs-3g and needs no sudo.
- **`usbmux list` returns `[]` while `lsusb` shows the iPhone.** usbmuxd has dropped the device. Replug the phone straight into the computer, not through a hub.
- **Pairing ends in `BadDevError ... Number: 2`.** The pairing actually worked; only handing the record to usbmuxd failed. Check with `pymobiledevice3 lockdown info`.
- **The backup sits at 0%.** The phone is waiting for you to enter its passcode.
- **Backups mirror the phone.** An incremental backup drops whatever you deleted from the phone since the last run. The photo archive exists for exactly this reason.

## Credits

Built on [pymobiledevice3](https://github.com/doronz88/pymobiledevice3) and [iphone_backup_decrypt](https://github.com/jsharkey13/iphone_backup_decrypt). Licensed GPL-3.0-or-later, the same as pymobiledevice3.
