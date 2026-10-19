"""Committed generator outputs must use LF, including on Windows."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import gen_exports


class ExportNewlineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        original_open = Path.open

        def windows_open(path, mode="r", buffering=-1, encoding=None,
                         errors=None, newline=None):
            # Emulate Windows text output on every test runner. Explicit LF
            # must bypass the platform's default CRLF translation.
            if "w" in mode and "b" not in mode and newline is None:
                newline = "\r\n"
            return original_open(path, mode, buffering, encoding, errors, newline)

        patcher = mock.patch.object(Path, "open", windows_open)
        patcher.start()
        self.addCleanup(patcher.stop)

    def assert_lf(self, rel):
        data = (self.root / rel).read_bytes()
        self.assertIn(b"\n", data)
        self.assertNotIn(b"\r", data)
        return data

    def test_export_and_dependency_files(self):
        records = {
            "own": {"home": "example", "usr": "own",
                    "qname": "boost::example", "ns": ["boost"]},
        }
        self.assertEqual(gen_exports.emit_inc(
            "example", records, self.root, False, {}, extra_deps=["core"]),
            (1, ["core"]))
        self.assertIn(b"  using boost::example;\n",
                      self.assert_lf("src/gen_exports/example.inc"))
        self.assertEqual(self.assert_lf("src/gen_exports/example.deps"),
                         b"boost.core\n")

    def test_cppm_file(self):
        (self.root / "src").mkdir()
        gen_exports.emit_cppm("example", self.root, gfm_headers=[])
        self.assertIn(b"export module boost.example;\n",
                      self.assert_lf("src/example.cppm"))

    def test_body_dependency_merge(self):
        deps = self.root / "src/gen_exports"
        deps.mkdir(parents=True)
        (deps / "example.deps").write_bytes(b"boost.core\n")
        added = gen_exports.merge_body_edges(
            self.root, ["example"], {"example": {"system": ["reference"]}})
        self.assertEqual(added, {"example": {"system": 1}})
        self.assertEqual(self.assert_lf("src/gen_exports/example.deps"),
                         b"boost.core\nboost.system\n")

    def test_scanned_metadata(self):
        output = self.root / "libs.json"
        with mock.patch.object(gen_exports.bc, "LIBS_JSON", output), \
                mock.patch.object(gen_exports.bc, "scan_libs_json",
                                  return_value={"example": ["example.hpp"]}), \
                mock.patch("sys.argv", ["gen_exports.py", "--scan"]):
            self.assertEqual(gen_exports.main(), 0)
        self.assert_lf("libs.json")


if __name__ == "__main__":
    unittest.main()
