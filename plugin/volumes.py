import pathlib
import os
import shutil
import typing
from plugin._log import logging


ROOT = pathlib.Path("/mnt")
USABLE_PATHS = os.getenv("USABLE_PATHS", "*").split(os.pathsep)
DRIVES = [p for path in USABLE_PATHS for p in (ROOT).glob(path)]


if not DRIVES:
    DRIVES = [ROOT / "drive"]


logging.debug("Environment: {%s}", ", ".join([f"{k}={v}" for k, v in os.environ.items()]))
logging.info("ROOT='%s'", str(ROOT))
logging.debug("Content of ROOT: %s", [str(f) for f in ROOT.glob("*")])
logging.info("USABLE_PATHS=%s", USABLE_PATHS)
logging.info("DRIVES=%s", [str(d) for d in DRIVES])


class DriveSelector:
    def __init__(self, drives: typing.Iterable[pathlib.Path | str] = DRIVES):
        self._drives = [pathlib.Path(path) for path in drives]
        assert self._drives, f"No drives provided"
        self._drives.sort()
    
    def select_drive_for_new_volume(self, name: str) -> pathlib.Path:
        ...

    def find_drive_of_volume(self, name: str) -> pathlib.Path:
        ...

    def all_volumes(self) -> typing.Iterable[tuple[pathlib.Path, str]]:
        for drive in self._drives:
            for path in drive.glob("*"):
                if path.is_dir():
                    yield drive, path.name


class FirstDriveSelector(DriveSelector):
    @property
    def _first_drive(self):
        return self._drives[0]

    def select_drive_for_new_volume(self, name: str) -> pathlib.Path:
        return self._first_drive
    
    def find_drive_of_volume(self, name: str) -> pathlib.Path:
        candidate = self._first_drive / name
        if candidate.exists():
            return self._first_drive
        return None
    

def create_volume(drive: pathlib.Path, name: str, mod: int = 0o777) -> pathlib.Path:
    candidate = drive / name
    if candidate.exists():
        return None
    candidate.mkdir()
    candidate.chmod(mod)
    return candidate


def remove_volume(drive: pathlib.Path, name: str) -> bool:
    candidate = drive / name
    if not candidate.exists():
        return False
    shutil.rmtree(candidate)
    if candidate.exists():
        raise RuntimeError(f"Failed to remove {candidate}")
    return True


def mount_info_path(drive: pathlib.Path, name: str, id: str) -> pathlib.Path:
    return drive / f"{name}-used-by-{id}.info" 


def mount_info(path: pathlib.Path) -> tuple[pathlib.Path, str, str]:
    name = path.name.split("-used-by-")[0]
    id = path.name.split("-used-by-")[1].split(".info")[0]
    return path.parent, name, id


def mount_volume(drive: pathlib.Path, name: str, id: str) -> bool:
    candidate = mount_info_path(drive, name, id)
    if candidate.exists():
        return False
    candidate.touch()
    return candidate.exists()


def unmount_volume(drive: pathlib.Path, name: str, id: str) -> bool:
    candidate = mount_info_path(drive, name, id)
    if not candidate.exists():
        return False
    candidate.unlink()
    return not candidate.exists()


def volume_mounts(drive: pathlib.Path, name: str) -> typing.Iterable[str]:
    for path in drive.glob(str(mount_info_path(drive, name, "*").name)):
        yield mount_info(path)[2]
