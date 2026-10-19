"""Re-vendoring must reproduce the branch's hand-written log header exactly."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import reapply_hand_edits as edits


class ReapplyHandEditsTests(unittest.TestCase):
    def test_log_stub_matches_committed_snapshot(self):
        rel = "deps/boost/libs/log/src/windows/simple_event_log.h"
        expected = (edits.ROOT / rel).read_bytes()
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(edits, "ROOT", Path(tmp)), \
                mock.patch.object(edits, "VENDORED_PATCHES", []), \
                mock.patch.object(edits, "SRC_PATCHES", []), \
                mock.patch.object(edits, "patch"), \
                mock.patch.object(edits, "guard_entity_lines"), \
                mock.patch.object(edits, "restore_from_git"), \
                contextlib.redirect_stdout(io.StringIO()):
            edits.main()
            self.assertEqual((Path(tmp) / rel).read_bytes(), expected)
            edits.main()
            self.assertEqual((Path(tmp) / rel).read_bytes(), expected)


if __name__ == "__main__":
    unittest.main()
