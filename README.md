# iphone-backup-linux

Back up an iPhone to an external disk from Linux, with no iTunes and no sudo. You get:

- **A full encrypted backup** in the same format iTunes and Finder use, so you can restore it to any iPhone. Later runs are incremental and copy only what changed.
- **An add-only photo archive**: every photo and video as a plain file in `YYYY/MM/` folders, keeping its original date. That includes iCloud Photos synced from your other devices. Reruns copy only new photos and never delete anything, so you can clear photos off the phone and they stay safe on the disk.
- **Photo extraction** from the encrypted backup, if you ever need it.

It's a [Claude Code](https://claude.com/claude-code) plugin: install it, say "back up my iPhone", and Claude walks through detecting the disk, mounting it, pairing, encryption, the backup and the archive, and handles the gotchas below. The scripts also work on their own.

> **Status:** submitted to Claude's plugin directory and in review. Until it's listed there, install it straight from GitHub as shown below.

## Quick start: paste this into Claude Code

Plug in your iPhone and your external disk, open Claude Code on the Linux machine, and paste:

```
Back up my iPhone to my external disk using the iphone-backup-linux plugin.
Install it first if it's missing:
  claude plugin marketplace add abhibansal60/iphone-backup-linux
  claude plugin install iphone-backup-linux@iphone-backup-linux
Then follow the plugin's skills/iphone-backup/SKILL.md step by step:
ask me which disk to use, make a full encrypted backup, then run the photo archive.
```

Or install it yourself inside Claude Code:

```
/plugin marketplace add abhibansal60/iphone-backup-linux
/plugin install iphone-backup-linux@iphone-backup-linux
```

Then say "back up my iPhone". Next time, the same request runs an incremental backup and archives only new photos.

## Requirements

- Linux with `usbmuxd` running and `udisks2`. Ubuntu, Fedora and most desktop distros ship both. `ntfs-3g` too, if your disk is NTFS.
- Python 3.10 or newer (tested on 3.12 and 3.14).
- An external disk formatted exFAT, NTFS or ext4. FAT32 can't hold files over 4 GB, and long videos exceed that.
- Claude Code or Cowork running on that machine, because the plugin runs commands locally. On claude.ai in the browser it can explain the steps but can't run them.

## Use the scripts directly

```sh
VENV=~/.local/share/iphone-backup/venv
python3 -m venv $VENV    # if this fails with "ensurepip is not available", see below
$VENV/bin/pip install pymobiledevice3 iphone_backup_decrypt

# pair: unlock the phone and tap Trust
$VENV/bin/pymobiledevice3 lockdown pair

# full or incremental backup
mkdir -p /path/to/disk/iPhone-Backup
$VENV/bin/pymobiledevice3 backup2 backup /path/to/disk/iPhone-Backup

# add-only photo archive (rerun any time; it resumes and copies only new photos)
$VENV/bin/python skills/iphone-backup/photo-archive.py /path/to/disk/iPhone-Photos

# decrypt photos out of an encrypted backup
$VENV/bin/python skills/iphone-backup/extract-photos.py /path/to/disk/iPhone-Backup/<UDID> ~/Pictures/from-backup
```

If `python3 -m venv` fails because your distro split `venv` into a separate package, use [uv](https://docs.astral.sh/uv/), which installs into your home folder without sudo:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
~/.local/bin/uv venv $VENV && ~/.local/bin/uv pip install --python $VENV/bin/python pymobiledevice3 iphone_backup_decrypt
```

Run `python3 skills/iphone-backup/test_photo_archive.py` to check the archive logic against a fake phone.

## Gotchas this handles

- **The NTFS disk won't mount** ("wrong fs type, bad superblock"). The disk was unplugged from Windows without ejecting. Mount it with `udisksctl mount -b /dev/sdXN -t ntfs`, which uses ntfs-3g and needs no sudo.
- **`usbmux list` returns `[]` while `lsusb` shows the iPhone.** usbmuxd has dropped the device. Replug the phone straight into the computer, not through a hub. If the disk was on the same hub, it gets unmounted too.
- **Pairing ends in `BadDevError ... Number: 2`.** The pairing actually worked; only handing the record to usbmuxd failed. Check with `pymobiledevice3 lockdown info`.
- **The backup sits at 0%.** The phone is waiting for you to enter its passcode.
- **Backups mirror the phone.** An incremental backup drops whatever you deleted from the phone since the last run. The photo archive exists for exactly this reason.

## Data and privacy

Everything stays on your computer. The plugin sends no data anywhere: backups and photos go straight from the iPhone over USB to the disk you choose. The only network access is installing `pymobiledevice3` and `iphone_backup_decrypt` from PyPI (and uv, if you use it). You type backup passwords into your own terminal; they are never stored or passed to Claude.

## Credits

Built on [pymobiledevice3](https://github.com/doronz88/pymobiledevice3) and [iphone_backup_decrypt](https://github.com/jsharkey13/iphone_backup_decrypt). Built end-to-end with Claude Opus 5.5. Licensed GPL-3.0-or-later, the same as pymobiledevice3.
