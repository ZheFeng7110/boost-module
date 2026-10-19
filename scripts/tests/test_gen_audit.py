"""Hand-written modules must not require nonexistent generated bundle TUs."""
import unittest
from unittest import mock

import gen_audit


class AuditSpecialModulesTests(unittest.TestCase):
    def test_linkage_audit_skips_special_modules(self):
        with mock.patch("sys.argv", ["gen_audit.py"]), \
                mock.patch.object(gen_audit.bc, "get_ci"), \
                mock.patch.object(gen_audit.bc, "TARGET_LIBS", ["atomic", "version"]), \
                mock.patch.object(gen_audit.bc, "headers_of", return_value=[]) as headers, \
                mock.patch.object(gen_audit, "audit_lib", return_value=(0, 0, 0, 0)) as audit:
            self.assertEqual(gen_audit.main(), 0)
        headers.assert_called_once_with("atomic")
        audit.assert_called_once_with("atomic", [], gen_audit.bc.AUDIT_DIR)

    def test_explicit_special_module_needs_no_bundle(self):
        with mock.patch("sys.argv", ["gen_audit.py", "--libs", "version"]), \
                mock.patch.object(gen_audit.bc, "get_ci"), \
                mock.patch.object(gen_audit, "audit_lib") as audit:
            self.assertEqual(gen_audit.main(), 0)
        audit.assert_not_called()

    def test_macro_audit_keeps_special_module_headers(self):
        with mock.patch("sys.argv", ["gen_audit.py", "--macros", "--libs", "version"]), \
                mock.patch.object(gen_audit.bc, "get_ci") as get_ci, \
                mock.patch.object(gen_audit, "macros_audit", return_value=0) as audit:
            self.assertEqual(gen_audit.main(), 0)
        get_ci.assert_not_called()
        audit.assert_called_once_with(["version"], gen_audit.bc.AUDIT_DIR)


if __name__ == "__main__":
    unittest.main()
