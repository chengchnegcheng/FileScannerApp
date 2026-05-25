import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.path_utils import (
    get_app_data_dir,
    get_project_root,
    get_resource_path,
    normalize_directory_path,
)


class PathUtilsTests(unittest.TestCase):
    def test_project_root_points_to_repository_root(self):
        project_root = get_project_root()

        self.assertEqual(project_root.name, "FileScannerApp")
        self.assertTrue((project_root / "app.py").exists())

    def test_resource_path_resolves_from_project_root(self):
        resource_path = get_resource_path("resources/icons/folder.png")

        self.assertEqual(resource_path.name, "folder.png")
        self.assertTrue(resource_path.exists())

    def test_app_data_dir_prefers_user_writable_location(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"LOCALAPPDATA": temp_dir}, clear=False):
                app_data_dir = get_app_data_dir("FileScannerApp")

        self.assertEqual(app_data_dir, Path(temp_dir) / "FileScannerApp")

    def test_normalize_directory_path_preserves_unc_and_fixes_separators(self):
        mixed_path = "//172.16.51.56/project backup\\30667"

        normalized = normalize_directory_path(mixed_path)

        self.assertEqual(normalized, r"\\172.16.51.56\project backup\30667")

    def test_normalize_directory_path_merges_unc_slash_variants(self):
        variants = [
            r"\\172.16.51.56\project backup",
            "//172.16.51.56/project backup",
            r"\\172.16.51.56/project backup",
            r"\\172.16.51.56\project backup\\",
            "//172.16.51.56/project backup/",
        ]
        expected = r"\\172.16.51.56\project backup"

        normalized = {normalize_directory_path(path) for path in variants}

        self.assertEqual(normalized, {expected})

    def test_normalize_directory_path_keeps_drive_root(self):
        self.assertEqual(normalize_directory_path("C:\\"), "C:\\")
        self.assertEqual(normalize_directory_path("C:\\folder\\\\"), "C:\\folder")


if __name__ == "__main__":
    unittest.main()
