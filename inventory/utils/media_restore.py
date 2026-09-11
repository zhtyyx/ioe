"""Stage media changes and retain a recovery copy until database commit succeeds."""
import logging
import os
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def replace_contents(source, destination):
    """Keep MEDIA_ROOT itself in place (it can be a mounted Docker volume)."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for child in destination.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    for child in Path(source).iterdir():
        target = destination / child.name
        if child.is_dir():
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)


class MediaRestore:
    def __init__(self, source, destination, temp_dir):
        self.destination = Path(destination)
        self.workspace = None
        self.changed = False
        self.keep_recovery = False
        try:
            if not Path(source).is_dir():
                raise FileNotFoundError('备份媒体目录不存在')
            os.makedirs(temp_dir, exist_ok=True)
            self.workspace = Path(tempfile.mkdtemp(prefix='media-restore-', dir=temp_dir))
            self.staged = self.workspace / 'snapshot'
            self.original = self.workspace / 'original'
            shutil.copytree(source, self.staged)
            if self.destination.exists():
                shutil.copytree(self.destination, self.original)
            else:
                self.original.mkdir()
        except Exception:
            self.cleanup()
            raise

    def apply(self):
        self.changed = True
        replace_contents(self.staged, self.destination)

    def rollback(self):
        if not self.changed:
            return
        try:
            replace_contents(self.original, self.destination)
            self.changed = False
        except Exception:
            self.keep_recovery = True
            logger.exception('媒体回滚失败，恢复副本保留在 %s', self.original)
            raise

    def cleanup(self):
        if self.workspace and not self.keep_recovery:
            try:
                shutil.rmtree(self.workspace)
            except Exception:
                # A cleanup failure must never revert media after the DB commits.
                logger.warning('无法清理媒体恢复临时目录 %s', self.workspace, exc_info=True)
