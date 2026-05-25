import tempfile
import unittest
from pathlib import Path

from utils.backup_history import (
    MAX_BACKUP_HISTORY,
    create_backup_history_entry,
    format_history_item,
)
from utils.config_manager import ConfigManager


class BackupHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = ConfigManager(str(Path(self.temp_dir.name) / "config.json"))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_backup_history_keeps_latest_first_and_limits_count(self):
        for index in range(MAX_BACKUP_HISTORY + 3):
            self.config.add_backup_history(
                create_backup_history_entry(
                    dest_path=f"D:\\backup-{index}",
                    source_names=[f"src-{index}"],
                    status="success",
                )
            )

        history = self.config.get_backup_history()
        self.assertEqual(len(history), MAX_BACKUP_HISTORY)
        self.assertEqual(history[0].dest_path, f"D:\\backup-{MAX_BACKUP_HISTORY + 2}")

    def test_recent_directories_deduplicate_slash_variants(self):
        self.config.set_setting(
            "recent_directories",
            ["J:\\", "J:/", "H:\\", "H:/"],
        )

        directories = self.config.get_recent_directories()

        self.assertEqual(directories, ["J:\\", "H:\\"])

    def test_recent_directories_deduplicate_unc_slash_variants(self):
        self.config.set_setting(
            "recent_directories",
            [
                r"\\172.16.51.56\project backup",
                "//172.16.51.56/project backup",
                "\\\\172.16.51.56\\project backup\\\\",
            ],
        )

        directories = self.config.get_recent_directories()

        self.assertEqual(directories, [r"\\172.16.51.56\project backup"])

    def test_add_recent_directory_merges_slash_variants(self):
        self.config.add_recent_directory("J:\\")
        self.config.add_recent_directory("J:/")

        directories = self.config.get_recent_directories()

        self.assertEqual(directories, ["J:\\"])
        self.assertEqual(self.config.get_setting("last_directory"), "J:\\")

    def test_recent_backup_destinations_deduplicate_slash_variants(self):
        self.config.set_setting(
            "recent_backup_destinations",
            ["J:\\", "J:/", "H:\\", "H:/"],
        )

        destinations = self.config.get_recent_backup_destinations()

        self.assertEqual(destinations, ["J:\\", "H:\\"])

    def test_add_recent_backup_destination_merges_slash_variants(self):
        self.config.add_recent_backup_destination("J:\\")
        self.config.add_recent_backup_destination("J:/")

        destinations = self.config.get_recent_backup_destinations()

        self.assertEqual(destinations, ["J:\\"])
        self.assertEqual(self.config.get_setting("last_backup_destination"), "J:\\")

    def test_recent_backup_destinations_track_last_selection(self):
        self.config.add_recent_backup_destination(r"H:\archive")
        self.config.add_recent_backup_destination(r"D:\backup")

        destinations = self.config.get_recent_backup_destinations()

        self.assertEqual(destinations[0], r"D:\backup")
        self.assertEqual(self.config.get_setting("last_backup_destination"), r"D:\backup")

    def test_remove_backup_history_at_deletes_single_entry(self):
        self.config.add_backup_history(
            create_backup_history_entry(dest_path=r"D:\one", source_names=["a"], status="success")
        )
        self.config.add_backup_history(
            create_backup_history_entry(dest_path=r"D:\two", source_names=["b"], status="failed")
        )

        self.config.remove_backup_history_at(0)

        history = self.config.get_backup_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].dest_path, r"D:\one")

    def test_clear_backup_history_removes_all_entries(self):
        self.config.add_backup_history(
            create_backup_history_entry(dest_path=r"D:\one", source_names=["a"], status="success")
        )

        self.config.clear_backup_history()

        self.assertEqual(self.config.get_backup_history(), [])

    def test_format_history_item_contains_key_fields(self):
        entry = create_backup_history_entry(
            dest_path=r"H:\backup",
            source_names=["项目A", "项目B"],
            status="success",
            files_copied=12,
            bytes_copied=4096,
            duration_seconds=8.5,
        )

        text = format_history_item(entry)

        self.assertIn("成功", text)
        self.assertIn(r"H:\backup", text)
        self.assertIn("项目A", text)


if __name__ == "__main__":
    unittest.main()
