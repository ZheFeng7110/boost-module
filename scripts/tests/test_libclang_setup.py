"""Regression tests for selecting the AST parser, not just the clang++ gate."""
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import boost_common as bc
import gen_exports


class LibclangSetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ci = types.ModuleType("clang.cindex")
        self.ci.Config = mock.Mock(library_file=None, library_path=None)
        self.ci.Index = mock.Mock()
        clang = types.ModuleType("clang")
        clang.cindex = self.ci
        patcher = mock.patch.dict(sys.modules, {
            "clang": clang, "clang.cindex": self.ci,
        })
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.dict(os.environ, {}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def file(self, rel):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return path

    def test_explicit_library_file_wins(self):
        library = self.file("custom/libclang.so")
        os.environ["LIBCLANG_PATH"] = str(library)
        os.environ["LLVM_PATH"] = str(self.root / "other-llvm")
        with mock.patch("shutil.which") as which:
            self.assertIs(bc.load_libclang(), self.ci)
        self.ci.Config.set_library_file.assert_called_once_with(str(library))
        self.ci.Index.create.assert_not_called()
        which.assert_not_called()

    def test_explicit_library_directory(self):
        library = self.file("custom/libclang.dylib")
        os.environ["LIBCLANG_PATH"] = str(library.parent)
        bc.load_libclang()
        self.ci.Config.set_library_file.assert_called_once_with(str(library))

    def test_llvm_path_accepts_installation_prefix(self):
        library = self.file("llvm/lib/libclang.so.23.1.3")
        os.environ["LLVM_PATH"] = str(self.root / "llvm")
        bc.load_libclang()
        self.ci.Config.set_library_file.assert_called_once_with(str(library))

    def test_windows_prefix_uses_bin(self):
        library = self.file("llvm/bin/libclang.dll")
        os.environ["LLVM_PATH"] = str(self.root / "llvm")
        bc.load_libclang()
        self.ci.Config.set_library_file.assert_called_once_with(str(library))

    def test_invalid_prefix_does_not_fall_back_to_wheel(self):
        os.environ["LLVM_PATH"] = str(self.root)
        with self.assertRaisesRegex(RuntimeError, "libclang not found under"):
            bc.load_libclang()
        self.ci.Index.create.assert_not_called()

    def test_cxx_library_precedes_bundled_libclang(self):
        driver = self.file("llvm/bin/clang++")
        library = self.file("llvm/lib/libclang.so")
        os.environ["CXX"] = str(driver)
        with mock.patch("shutil.which", return_value=str(driver)) as which:
            bc.load_libclang()
        which.assert_called_once_with(str(driver))
        self.ci.Config.set_library_file.assert_called_once_with(str(library))
        self.ci.Index.create.assert_not_called()

    def test_path_driver_symlink_resolves_to_full_installation(self):
        driver = self.file("llvm/bin/clang++")
        library = self.file("llvm/lib/libclang.dylib")
        shim = self.root / "clang++"
        try:
            shim.symlink_to(driver)
        except OSError:
            self.skipTest("symlink creation is not available")
        with mock.patch("shutil.which", return_value=str(shim)) as which:
            bc.load_libclang()
        which.assert_called_once_with("clang++")
        self.ci.Config.set_library_file.assert_called_once_with(str(library))

    def test_not_confused_with_clang_cpp_or_compiler_rt(self):
        self.file("lib/libclang-cpp.so.23.1")
        self.file("lib/libclang_rt.asan.so")
        self.assertIsNone(bc._libclang_in_installation(self.root))

    def test_bundled_fallback_without_native_library(self):
        with mock.patch("shutil.which", return_value=None):
            bc.load_libclang()
        self.ci.Index.create.assert_called_once_with()
        self.ci.Config.set_library_file.assert_not_called()

    def test_missing_builtins_fail_before_generating_incomplete_ast(self):
        self.ci.Config.library_file = str(self.file("wheel/libclang.so"))
        with mock.patch.object(bc, "CLANG_ARGS", []):
            with self.assertRaisesRegex(RuntimeError, "builtin headers not found"):
                bc._append_resource_dir()

    def test_native_builtin_headers_are_found_once(self):
        self.ci.Config.library_file = str(self.file("llvm/lib/libclang.so.23"))
        header = self.file("llvm/lib/clang/23/include/stddef.h")
        with mock.patch.object(bc, "CLANG_ARGS", []):
            bc._append_resource_dir()
            bc._append_resource_dir()
            self.assertEqual(bc.CLANG_ARGS, ["-I" + str(header.parent)])

    def test_invalid_explicit_resource_dir_fails(self):
        os.environ["CLANG_RESOURCE_DIR"] = str(self.root)
        with self.assertRaisesRegex(RuntimeError, "does not contain clang builtin"):
            bc._append_resource_dir()

    def test_cache_key_includes_ast_parser_version(self):
        with mock.patch.object(bc, "libclang_version", return_value="clang 18"):
            old = gen_exports._skip_key("atomic", [], {}, ["atomic"], False, False)
        with mock.patch.object(bc, "libclang_version", return_value="clang 23"):
            new = gen_exports._skip_key("atomic", [], {}, ["atomic"], False, False)
        self.assertNotEqual(old, new)


if __name__ == "__main__":
    unittest.main()
