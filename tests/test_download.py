import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import refresh


def response(body, content_type='application/zip'):
    stream = io.BytesIO(body)
    stream.headers = {'Content-Type': content_type}
    stream.status = 200
    return stream


def archive():
    body = io.BytesIO()
    with zipfile.ZipFile(body, 'w') as z:
        z.writestr('data.csv', 'year,value\n2026,42\n')
    return body.getvalue()


class DownloadTests(unittest.TestCase):
    def test_error_page_is_retried_and_only_valid_zip_is_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / '2026.zip'
            opener = Mock(side_effect=[response(b'<html>temporary failure</html>', 'text/html'), response(archive())])
            sleep = Mock()
            refresh.download_archive('https://example.org/data.zip', path, opener, sleep)
            self.assertTrue(zipfile.is_zipfile(path))
            self.assertEqual(opener.call_count, 2)
            sleep.assert_called_once_with(5)
            self.assertFalse(path.with_suffix('.part').exists())

    def test_repeated_bad_download_keeps_previous_archive_and_reports_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / '2026.zip'
            before = archive(); path.write_bytes(before)
            opener = Mock(side_effect=[response(b'error', 'text/html'), response(b'error', 'text/html')])
            with self.assertRaisesRegex(OSError, 'HTTP 200, Content-Type text/html, 5 bytes'):
                refresh.download_archive('https://example.org/data.zip', path, opener, Mock())
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(path.with_suffix('.part').exists())

    def test_rejections_and_unpublished_year_are_not_retried(self):
        for code in (403, 404, 429):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as tmp:
                opener = Mock(side_effect=HTTPError('https://example.org/data.zip', code, 'Rejected', {}, None))
                sleep = Mock()
                with self.assertRaises(HTTPError):
                    refresh.download_archive('https://example.org/data.zip', Path(tmp) / '2026.zip', opener, sleep)
                self.assertEqual(opener.call_count, 1); sleep.assert_not_called()

    def test_timeout_can_recover_and_truncated_zip_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / '2026.zip'
            opener = Mock(side_effect=[TimeoutError('timed out'), response(archive())])
            refresh.download_archive('https://example.org/data.zip', path, opener, Mock())
            self.assertTrue(zipfile.is_zipfile(path))
            path.write_bytes(archive()[:20])
            with self.assertRaises(ValueError): refresh.validate_zip(path)

    def test_failed_refresh_never_changes_published_edition(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); old = folder / 'edition.json'; old.write_text('{"retrieved":"2026-11-01"}')
            with patch.object(refresh, 'download_archive', side_effect=OSError('invalid ZIP')):
                with self.assertRaises(OSError): refresh.refresh(folder)
            self.assertEqual(old.read_text(), '{"retrieved":"2026-11-01"}')
