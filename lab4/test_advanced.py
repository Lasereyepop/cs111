import os
import stat
import struct
import subprocess
import unittest


class Lab4AdvancedTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Build and execute the C program
        subprocess.run(["make"], capture_output=True)
        subprocess.run(["./ext2-create"], capture_output=True)

        # Capture dumpe2fs and fsck output for metadata testing
        p_dump = subprocess.run(
            ["dumpe2fs", "cs111-base.img"], capture_output=True, text=True
        )
        cls.dump_lines = p_dump.stdout

        p_fsck = subprocess.run(
            ["fsck.ext2", "-f", "-n", "cs111-base.img"], capture_output=True, text=True
        )
        cls.fsck_lines = p_fsck.stdout

        # Read raw image for bitmap/structural tests
        with open("cs111-base.img", "rb") as f:
            cls.img = f.read()

        # Mount the filesystem
        subprocess.run(["mkdir", "-p", "mnt"], capture_output=True)
        subprocess.run(["sudo", "mount", "-o", "loop", "cs111-base.img", "mnt"])

        # Cache file stat objects for the test methods
        cls.root_stat = os.lstat("mnt") if os.path.exists("mnt") else None
        cls.lf_stat = (
            os.lstat("mnt/lost+found") if os.path.exists("mnt/lost+found") else None
        )
        cls.hello_world_stat = (
            os.lstat("mnt/hello-world") if os.path.exists("mnt/hello-world") else None
        )
        cls.hello_stat = os.lstat("mnt/hello") if os.path.exists("mnt/hello") else None

    @classmethod
    def tearDownClass(cls):
        # Clean up the environment
        subprocess.run(["sudo", "umount", "mnt"])
        subprocess.run(["rmdir", "mnt"], capture_output=True)
        subprocess.run(["make", "clean"], capture_output=True)

    def test_fsck_clean(self):
        """Check if fsck.ext2 reports the filesystem as completely clean."""
        self.assertIn("13/128 files", self.fsck_lines)
        self.assertIn("24/1024 blocks", self.fsck_lines)

    def test_dumpe2fs_metadata(self):
        """Check if superblock and block group metadata match assignments specs."""
        self.assertIn("Inode count:              128", self.dump_lines)
        self.assertIn("Block count:              1024", self.dump_lines)
        self.assertIn("Free blocks:              1000", self.dump_lines)
        self.assertIn("Free inodes:              115", self.dump_lines)

    def test_root_directory_properties(self):
        """Test root directory type, ownership, and permissions."""
        self.assertIsNotNone(self.root_stat, "Root directory failed to mount.")
        self.assertTrue(
            stat.S_ISDIR(self.root_stat.st_mode), "Root is not a directory."
        )
        self.assertEqual(self.root_stat.st_uid, 0, "Root UID should be 0.")
        self.assertEqual(self.root_stat.st_gid, 0, "Root GID should be 0.")
        self.assertEqual(
            stat.S_IMODE(self.root_stat.st_mode),
            0o755,
            "Root permissions should be 755 (drwxr-xr-x).",
        )

    def test_lost_and_found_properties(self):
        """Test lost+found directory type, ownership, and permissions."""
        self.assertIsNotNone(self.lf_stat, "lost+found directory is missing.")
        self.assertTrue(
            stat.S_ISDIR(self.lf_stat.st_mode), "lost+found is not a directory."
        )
        self.assertEqual(self.lf_stat.st_uid, 0, "lost+found UID should be 0.")
        self.assertEqual(self.lf_stat.st_gid, 0, "lost+found GID should be 0.")
        self.assertEqual(
            stat.S_IMODE(self.lf_stat.st_mode),
            0o755,
            "lost+found permissions should be 755 (drwxr-xr-x).",
        )

    def test_hello_world_properties(self):
        """Test hello-world file type, ownership, permissions, size, and content."""
        self.assertIsNotNone(self.hello_world_stat, "hello-world file is missing.")
        self.assertTrue(
            stat.S_ISREG(self.hello_world_stat.st_mode),
            "hello-world is not a regular file.",
        )
        self.assertEqual(
            self.hello_world_stat.st_uid, 1000, "hello-world UID should be 1000."
        )
        self.assertEqual(
            self.hello_world_stat.st_gid, 1000, "hello-world GID should be 1000."
        )
        self.assertEqual(
            stat.S_IMODE(self.hello_world_stat.st_mode),
            0o644,
            "hello-world permissions should be 644 (-rw-r--r--).",
        )
        self.assertEqual(
            self.hello_world_stat.st_size,
            12,
            "hello-world size should be exactly 12 bytes.",
        )

        with open("mnt/hello-world") as f:
            self.assertEqual(
                f.read(), "Hello world\n", "hello-world file content is incorrect."
            )

    def test_hello_symlink_properties(self):
        """Test hello symlink type, target, ownership, permissions, and size."""
        self.assertIsNotNone(self.hello_stat, "hello symlink is missing.")
        self.assertTrue(
            stat.S_ISLNK(self.hello_stat.st_mode), "hello is not a symbolic link."
        )
        self.assertEqual(
            self.hello_stat.st_uid, 1000, "hello symlink UID should be 1000."
        )
        self.assertEqual(
            self.hello_stat.st_gid, 1000, "hello symlink GID should be 1000."
        )

        # A fast symlink stores the target string directly in the inode block area.
        # Its size is the length of the target string ("hello-world" = 11 characters).
        self.assertEqual(
            self.hello_stat.st_size, 11, "hello symlink size should be 11 bytes."
        )
        self.assertEqual(
            os.readlink("mnt/hello"),
            "hello-world",
            "hello symlink does not point to hello-world.",
        )


    def test_block_bitmap(self):
        """Blocks 0-23 used, 24-1023 free, bits 1024-8191 marked used."""
        BLOCK_SIZE = 1024
        bitmap = self.img[3 * BLOCK_SIZE : 4 * BLOCK_SIZE]
        for i in range(24):
            self.assertTrue(
                (bitmap[i // 8] >> (i % 8)) & 1,
                f"Block {i} should be marked used.",
            )
        for i in range(24, 1024):
            self.assertFalse(
                (bitmap[i // 8] >> (i % 8)) & 1,
                f"Block {i} should be marked free.",
            )
        for i in range(1024, BLOCK_SIZE * 8):
            self.assertTrue(
                (bitmap[i // 8] >> (i % 8)) & 1,
                f"Bit {i} (past end) should be marked used.",
            )

    def test_inode_bitmap(self):
        """Inodes 1-13 used, 14-128 free, bits 129-1024 marked used."""
        BLOCK_SIZE = 1024
        bitmap = self.img[4 * BLOCK_SIZE : 5 * BLOCK_SIZE]
        for i in range(13):
            self.assertTrue(
                (bitmap[i // 8] >> (i % 8)) & 1,
                f"Inode {i + 1} should be marked used.",
            )
        for i in range(13, 128):
            self.assertFalse(
                (bitmap[i // 8] >> (i % 8)) & 1,
                f"Inode {i + 1} should be marked free.",
            )
        for i in range(128, BLOCK_SIZE * 8):
            self.assertTrue(
                (bitmap[i // 8] >> (i % 8)) & 1,
                f"Bit {i} (past end) should be marked used.",
            )

    def test_root_dir_block_fills_1024_bytes(self):
        """All directory entries in the root dir block must sum to exactly 1024 bytes."""
        BLOCK_SIZE = 1024
        block = self.img[21 * BLOCK_SIZE : 22 * BLOCK_SIZE]
        offset = 0
        total = 0
        while offset < BLOCK_SIZE:
            rec_len = struct.unpack_from("<H", block, offset + 4)[0]
            self.assertGreater(rec_len, 0, "rec_len must be > 0")
            total += rec_len
            offset += rec_len
        self.assertEqual(total, BLOCK_SIZE, "Root dir entries must fill exactly 1024 bytes.")

    def test_lost_and_found_block_fills_1024_bytes(self):
        """All directory entries in the lost+found block must sum to exactly 1024 bytes."""
        BLOCK_SIZE = 1024
        block = self.img[22 * BLOCK_SIZE : 23 * BLOCK_SIZE]
        offset = 0
        total = 0
        while offset < BLOCK_SIZE:
            rec_len = struct.unpack_from("<H", block, offset + 4)[0]
            self.assertGreater(rec_len, 0, "rec_len must be > 0")
            total += rec_len
            offset += rec_len
        self.assertEqual(total, BLOCK_SIZE, "lost+found entries must fill exactly 1024 bytes.")

    def test_root_dotdot_points_to_root(self):
        """The '..' entry in the root directory must point to inode 2 (root itself)."""
        BLOCK_SIZE = 1024
        block = self.img[21 * BLOCK_SIZE : 22 * BLOCK_SIZE]
        # skip '.' entry
        rec_len_dot = struct.unpack_from("<H", block, 4)[0]
        dotdot_inode = struct.unpack_from("<I", block, rec_len_dot)[0]
        self.assertEqual(dotdot_inode, 2, "'..' in root dir must point to inode 2.")

    def test_root_inode_links_count(self):
        """Root inode (inode 2) must have i_links_count == 3."""
        BLOCK_SIZE = 1024
        INODE_SIZE = 128
        inode_table_offset = 5 * BLOCK_SIZE
        root_inode_offset = inode_table_offset + (2 - 1) * INODE_SIZE
        links_count = struct.unpack_from("<H", self.img, root_inode_offset + 26)[0]
        self.assertEqual(links_count, 3, "Root inode i_links_count should be 3.")


if __name__ == "__main__":
    unittest.main()
