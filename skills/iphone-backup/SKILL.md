---
name: iphone-backup
description: Back up an iPhone over USB on Linux without sudo, as a full or incremental encrypted iTunes-style backup plus an add-only photo archive, onto an external disk. Use when asked to back up an iPhone, update an iPhone backup, archive iPhone photos, or pull photos out of an iPhone backup.
---

# iPhone backup on Linux

Tool: [`pymobiledevice3`](https://github.com/doronz88/pymobiledevice3), a pure-Python replacement for `idevicebackup2` that installs without sudo. It talks to the system `usbmuxd` daemon, which most desktop distros ship and run by default. `photo-archive.py` and `extract-photos.py` sit next to this file; `<skill-dir>` below means this skill's base directory.

```
VENV=~/.local/share/iphone-backup/venv
P=$VENV/bin/pymobiledevice3
```

## Steps

1. **Detect.** Run `lsusb | grep -i apple` and `lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT`. Ask the user which disk partition to use. Done when the phone and the chosen partition are both listed.
   - On a `vfat` (FAT32) partition, warn the user first: FAT32 can't hold files over 4 GB, and long iPhone videos exceed that. exFAT, NTFS and ext4 are fine.

2. **Mount the disk.** If `lsblk` already shows a mount point (desktops auto-mount under `/media/$USER/` or `/run/media/$USER/`), use it. Otherwise run `udisksctl mount -b /dev/<partition>`, which prints `Mounted ... at <path>`. Set `DISK=<that path>`, `DEST=$DISK/iPhone-Backup` and `PHOTOS=$DISK/iPhone-Photos`.
   - On NTFS, a disk unplugged from Windows without ejecting is flagged "dirty". The kernel `ntfs3` driver then refuses it with "wrong fs type, bad superblock", and so does the file manager. `udisksctl mount -b /dev/<partition> -t ntfs` makes udisks use the ntfs-3g FUSE helper (package `ntfs-3g`), which mounts it read/write. udisks rejects both `-t ntfs-3g` and `-o force`. Suggest `chkdsk /f` on Windows as the permanent fix.
   - Check that the mount is writable and that free space is at least the phone's used storage. Done when both checks pass.

3. **Install, only if `$P` is missing.** Run `python3 -m venv $VENV && $VENV/bin/pip install pymobiledevice3 iphone_backup_decrypt` (Python 3.10 or newer; tested on 3.12 and 3.14).
   - If `venv` fails with "ensurepip is not available", the distro split venv into a package that needs sudo. Use [uv](https://docs.astral.sh/uv/) instead, which installs into the home folder: `curl -LsSf https://astral.sh/uv/install.sh | sh`, then `~/.local/bin/uv venv $VENV && ~/.local/bin/uv pip install --python $VENV/bin/python pymobiledevice3 iphone_backup_decrypt`.
   - Done when `$P version` prints a version.

4. **Connect.** Run `$P usbmux list`. It must return the device, not `[]`.
   - If it returns `[]` while `lsusb` shows the iPhone, usbmuxd has dropped the device (`journalctl -u usbmuxd` shows "Removed device"). Ask the user to replug the phone straight into the computer, not through a hub. Unplugging a hub also unmounts any disk on it, so repeat step 2 after a replug.
   - Pair with `$P lockdown pair` while the user unlocks the phone and taps Trust. If it ends in `BadDevError ... 'Number': 2`, the pairing still worked: the record was saved to `~/.local/share/pymobiledevice3/` and only the copy handed to usbmuxd failed. Confirm with `$P lockdown info`. Done when it prints `DeviceName`.

5. **Check encryption.** Run `$P backup2 encryption` with no arguments; it reports the current state.
   - Encryption on means a backup password is already set. The backup is encrypted with it, and it includes saved passwords, Health and Wi-Fi data. Restoring needs that password.
   - Encryption off: recommend turning it on. The user runs this in their own terminal so the password stays out of the chat and the shell history: `read -rsp 'Backup password: ' PW && $P backup2 encryption on "$PW"; unset PW`. The phone asks for its passcode to confirm.
   - If the user doesn't know an existing password, they reset it on the phone under Settings → General → Transfer or Reset iPhone → Reset → Reset All Settings. This keeps their data.

6. **Back up.** Run in the background, with a log:
   ```
   mkdir -p "$DEST" && cd "$DEST" && $P backup2 backup . > ~/iphone-backup.log 2>&1; echo "EXIT $?" >> ~/iphone-backup.log
   ```
   - This is **incremental** when a valid backup already exists in `$DEST`: only changes are transferred. `--full` forces a fresh full backup.
   - The phone asks for its passcode at the start (the log shows "Please enter the device passcode"). Tell the user right away. Nothing proceeds until they enter it.
   - Watch progress with a background monitor that prints `du -s` of `$DEST` plus the latest `N/100` from the log every 20 GB, and prints on `EXIT` or on any `error|traceback|passcode`. Re-arm it until `EXIT` appears. The phone's percentage runs behind the GB copied, so estimate the total size from the ratio of the two. The backup is usually larger than the phone's reported used storage. As a reference, a 256 GB iPhone 13 Pro Max made a 121 GB backup in 1 h 26 min over USB 2.
   - Done when the log ends in `EXIT 0`.

7. **Archive photos.** Run in the background:
   ```
   cd ~ && $VENV/bin/python <skill-dir>/photo-archive.py "$PHOTOS" > ~/photo-archive.log 2>&1; echo "EXIT $?" >> ~/photo-archive.log
   ```
   Done when the log shows `DONE` followed by `EXIT 0`. See "Photo archive" below.

8. **Eject.** Run `cd ~ && sync && udisksctl unmount -b /dev/<partition>`. It reports "target is busy" while a shell is still inside the disk. Done when it prints "Unmounted".

## Backups mirror the phone

An iPhone backup is a mirror of the phone's current state, not a history. An incremental update adds anything new since the last run, but it also drops anything deleted from the phone in the meantime. To keep an old state, first copy `$DEST` to `iPhone-Backup-<date>`. Each copy costs the full backup size again.

## Photo archive

`photo-archive.py DEST` copies the camera roll to `DEST/YYYY/MM/IMG_xxxx.HEIC` as plain files that open anywhere: every album folder under `/DCIM` (photos taken on this phone) plus `/PhotoData/CPLAssets` (iCloud Photos synced from other devices). Folders and mtimes come from when each file was created on the phone, which is the capture time for camera shots and the save time for saved images.

- It is **add-only**: it copies only files missing from `DEST/.archived.txt`, and it never deletes or overwrites. Photos deleted from the phone stay in the archive.
- It prints `copied N` every 100 files, and `DONE copied=...` at the end. Speed is about 150–250 files, or 1–1.8 GB, per minute over USB 2; a first run of 20,000 files takes about 1.5 h.
- If it stops (phone unplugged or locked for long), rerun the same command: it picks up where it left off without duplicating files.
- `test_photo_archive.py` checks this logic against a fake phone: `python3 <skill-dir>/test_photo_archive.py`.
- It skips `.AAE` edit sidecars and archives originals. Edits made in Photos.app are not included.
- It only sees photos stored on the phone. With iCloud Photos set to "Optimize iPhone Storage", the originals live only in iCloud; switch to "Download and Keep Originals" first.

## Getting photos out of the encrypted backup

The backup's files are hashed and encrypted, so they can't be browsed. Decrypt the camera roll into plain files with:

```
$VENV/bin/python <skill-dir>/extract-photos.py "$DEST/<UDID>" <output-dir>
```

It prompts for the password, so the user runs it in their own terminal. The same library, [`iphone_backup_decrypt`](https://github.com/jsharkey13/iphone_backup_decrypt), also extracts messages, WhatsApp, notes and contacts (`RelativePath.*` with `extract_file`, `RelativePathsLike.*` with `extract_files`). To restore the whole backup to a new iPhone, use `pymobiledevice3 backup2 restore`, or copy the UDID folder into Finder's or iTunes' backup folder.
