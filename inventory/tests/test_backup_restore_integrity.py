"""Restore failure boundaries, using real test-DB commits and temporary media."""
import json
import tempfile
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import management
from django.db import connection, DatabaseError
from django.test import TransactionTestCase, RequestFactory

from inventory.models import Category
from inventory.utils import media_restore
from inventory.views.system import backup


class BackupRestoreIntegrityTests(TransactionTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.media = self.root / 'media'
        self.media.mkdir()
        (self.media / 'current.txt').write_text('current media')
        self.snapshot = self.root / 'backups' / 'snapshot'
        (self.snapshot / 'media').mkdir(parents=True)
        (self.snapshot / 'media' / 'restored.txt').write_text('snapshot media')
        (self.root / 'temp').mkdir()
        self.user = User.objects.create_superuser('restore-admin', 'restore@example.com', 'secret')
        management.call_command(
            'dumpdata', '--exclude', 'auth.permission', '--exclude', 'contenttypes',
            '--exclude', 'sessions.session', '--output', str(self.snapshot / 'db.json'), verbosity=0,
        )
        (self.snapshot / 'backup_info.json').write_text(json.dumps({
            'includes_media': True, 'created_at': '2026-09-11T10:00:00', 'created_by': self.user.username,
        }))
        self.extra = Category.objects.create(name='post-snapshot')
        override = self.settings(
            BACKUP_ROOT=str(self.root / 'backups'), TEMP_DIR=str(self.root / 'temp'), MEDIA_ROOT=str(self.media),
        )
        override.enable()
        self.addCleanup(override.disable)

    def restore(self):
        request = RequestFactory().post('/system/backup/restore/snapshot/', {
            'confirm_restore': 'on', 'restore_media': 'on',
        })
        request.user = self.user
        request.session = {}
        request._messages = FallbackStorage(request)
        return backup.restore_backup(request, 'snapshot')

    def assert_original_state(self):
        self.assertTrue(Category.objects.filter(pk=self.extra.pk).exists())
        self.assertEqual((self.media / 'current.txt').read_text(), 'current media')
        self.assertFalse((self.media / 'restored.txt').exists())

    def test_success_restores_database_and_media_from_real_form(self):
        self.assertEqual(self.restore().status_code, 302)
        self.assertFalse(Category.objects.filter(pk=self.extra.pk).exists())
        self.assertEqual((self.media / 'restored.txt').read_text(), 'snapshot media')
        self.assertFalse((self.media / 'current.txt').exists())
        self.assertEqual(list((self.root / 'temp').iterdir()), [])

    def test_stage_failure_leaves_live_database_and_files_unchanged(self):
        with mock.patch.object(media_restore.shutil, 'copytree', side_effect=OSError('disk full')):
            self.assertEqual(self.restore().status_code, 200)
        self.assert_original_state()

    def test_live_copy_failure_rolls_back_database_and_files(self):
        original = media_restore.replace_contents
        def fail_snapshot(source, destination):
            if Path(source).name == 'snapshot':
                (Path(destination) / 'current.txt').unlink()
                raise OSError('disk full while replacing live files')
            return original(source, destination)
        with mock.patch.object(media_restore, 'replace_contents', side_effect=fail_snapshot):
            self.assertEqual(self.restore().status_code, 200)
        self.assert_original_state()

    def test_commit_failure_restores_original_media(self):
        with mock.patch.object(connection, 'commit', side_effect=DatabaseError('commit failed')):
            self.assertEqual(self.restore().status_code, 200)
        self.assert_original_state()

    def test_failed_rollback_keeps_the_only_recovery_copy(self):
        original = media_restore.replace_contents
        def fail_rollback(source, destination):
            if Path(source).name == 'original':
                raise OSError('rollback disk error')
            return original(source, destination)
        with mock.patch.object(connection, 'commit', side_effect=DatabaseError('commit failed')), \
                mock.patch.object(media_restore, 'replace_contents', side_effect=fail_rollback):
            self.assertEqual(self.restore().status_code, 200)
        self.assertTrue(Category.objects.filter(pk=self.extra.pk).exists())
        copies = list((self.root / 'temp').glob('media-restore-*/original/current.txt'))
        self.assertEqual(len(copies), 1)
        self.assertEqual(copies[0].read_text(), 'current media')

    def test_cleanup_failure_never_reverts_committed_media(self):
        original = media_restore.shutil.rmtree
        def fail_workspace(path, *args, **kwargs):
            if Path(path).name.startswith('media-restore-'):
                raise OSError('cleanup failed')
            return original(path, *args, **kwargs)
        with mock.patch.object(media_restore.shutil, 'rmtree', side_effect=fail_workspace):
            self.assertEqual(self.restore().status_code, 302)
        self.assertFalse(Category.objects.filter(pk=self.extra.pk).exists())
        self.assertEqual((self.media / 'restored.txt').read_text(), 'snapshot media')

    def test_missing_snapshot_media_does_not_restore_only_database(self):
        (self.snapshot / 'media' / 'restored.txt').unlink()
        (self.snapshot / 'media').rmdir()
        self.assertEqual(self.restore().status_code, 200)
        self.assert_original_state()
