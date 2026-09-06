#!/usr/bin/env python3
"""Re-apply hand edits that scripts/gen_exports.py --emit-cppm overwrites.

Run after ANY full regeneration:

    uv run scripts/gen_exports.py --emit-cppm
    uv run scripts/reapply_hand_edits.py

Idempotent: each patch is applied only when its anchor is still present
(regeneration restores the anchor). See the M3 doc §3/§5 and the M4 doc §7.

Known costs (M3 §8): .inc platform guards and the .cppm hand-edits below.

Also replays the vendored header patches under deps/boost/ (M5/M11/M12),
which scripts/import_boost.py wipes on re-vendoring (rollup doc §3.7#1).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def patch(rel, old, new, *, required=True):
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    if new in s:
        print(f"  skip   {rel} (already applied)")
        return False
    n = s.count(old)
    if n == 1:
        p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")
        print(f"  patched {rel}")
        return True
    if n == 0:
        if not required:
            print(f"  skip   {rel} (anchor not present, not required)")
            return False
        raise SystemExit(f"{rel}: anchor not found\n  anchor: {old[:80]!r}")
    raise SystemExit(f"{rel}: expected 1 anchor, found {n}\n  anchor: {old[:80]!r}")


def restore_from_git(rel):
    r = subprocess.run(["git", "checkout", "--", rel], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode == 0:
        print(f"  restored {rel} (from git, M3 final form)")
    else:
        print(f"  git checkout failed for {rel}: {r.stderr[:200]}", file=sys.stderr)


def guard_entity_lines(rel, cond, names):
    """Wrap each `  using boost::...;` line whose entity appears in `names`
    (as a ::-delimited segment) in `#if cond` / `#endif`. Idempotent — a line
    already sitting between a #if/#endif pair is left alone.

    M6: the committed .inc files are a mingw-flavor snapshot, so Windows-only
    entities (guarded by #if defined(_WIN32) in the upstream headers) must not
    be exported on POSIX. This mirrors the upstream header condition in the
    module surface instead of hard-coding per-platform .inc files.
    """
    import re
    p = ROOT / rel
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    out = []
    changed = 0
    for i, line in enumerate(lines):
        prev_is_if = bool(out) and out[-1].lstrip().startswith("#if ")
        next_is_endif = (i + 1 < len(lines)) and lines[i + 1].lstrip().startswith("#endif")
        if prev_is_if or next_is_endif:
            out.append(line)
            continue
        stripped = line.strip()
        m = re.fullmatch(r"using boost::([A-Za-z0-9_:]+);", stripped)
        if m is None:
            out.append(line)
            continue
        segments = m.group(1).split("::")
        if any(seg in names for seg in segments):
            out.append(f"#if {cond}\n")
            out.append(line)
            out.append("#endif\n")
            changed += 1
        else:
            out.append(line)
    if changed:
        p.write_text("".join(out), encoding="utf-8", newline="\n")
        print(f"  guarded {changed} entity line(s) in {rel}")


def ensure_file(rel, content):
    """Create a vendored file that is an addition, not an upstream patch
    (no-op when already present)."""
    p = ROOT / rel
    if p.exists():
        print(f"  skip   {rel} (already present)")
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8", newline="\n")
    print(f"  created {rel}")


def reapply_vendored_patches():
    """Replay the hand edits inside deps/boost/ (rollup doc §3.7#1).

    scripts/import_boost.py wipes deps/boost/ and re-extracts pristine
    upstream files; the vendored patches below (M5 B', M9, M11, M12 and the
    M11 CI fix — 22 patched files + 1 added file) would otherwise be
    silently lost. Every patch anchors on the pristine upstream text, which
    regeneration restores, so the replay is idempotent. Anchors were
    verified to reproduce the committed vendored state byte-for-byte when
    replayed from the import commit (abef08a6).
    """
    print("reapplying vendored patches (deps/boost)...")

    # M11 (M11 §6)
    patch("deps/boost/boost/archive/iterators/remove_whitespace.hpp",
          "#undef iswspace\n"
          "#endif\n"
          "\n"
          "namespace { // anonymous\n"
          "\n"
          "template<class CharType>\n"
          "struct remove_whitespace_predicate;\n",
          "#undef iswspace\n"
          "#endif\n"
          "\n"
          "namespace boost { // M11: was anonymous — TU-local exposure breaks gcc module builds (see M11 design doc §6); moved into boost::archive::iterators::detail\n"
          "namespace archive {\n"
          "namespace iterators {\n"
          "namespace detail {\n"
          "\n"
          "template<class CharType>\n"
          "struct remove_whitespace_predicate;\n")
    patch("deps/boost/boost/archive/iterators/remove_whitespace.hpp",
          "};\n"
          "#endif\n"
          "\n"
          "} // namespace anonymous\n"
          "\n"
          "/////////1/////////2/////////3/////////4/////////5/////////6/////////7/////////8\n"
          "// convert base64 file data (including whitespace and padding) to binary\n",
          "};\n"
          "#endif\n"
          "\n"
          "} } } } // namespace detail, iterators, archive, boost\n"
          "\n"
          "/////////1/////////2/////////3/////////4/////////5/////////6/////////7/////////8\n"
          "// convert base64 file data (including whitespace and padding) to binary\n")
    patch("deps/boost/boost/archive/iterators/remove_whitespace.hpp",
          "template<class Base>\n"
          "class remove_whitespace :\n"
          "    public filter_iterator<\n"
          "        remove_whitespace_predicate<\n"
          "            typename boost::iterator_value<Base>::type\n"
          "            //typename Base::value_type\n"
          "        >,\n",
          "template<class Base>\n"
          "class remove_whitespace :\n"
          "    public filter_iterator<\n"
          "        detail::remove_whitespace_predicate<\n"
          "            typename boost::iterator_value<Base>::type\n"
          "            //typename Base::value_type\n"
          "        >,\n")
    patch("deps/boost/boost/archive/iterators/remove_whitespace.hpp",
          "{\n"
          "    friend class boost::iterator_core_access;\n"
          "    typedef filter_iterator<\n"
          "        remove_whitespace_predicate<\n"
          "            typename boost::iterator_value<Base>::type\n"
          "            //typename Base::value_type\n"
          "        >,\n",
          "{\n"
          "    friend class boost::iterator_core_access;\n"
          "    typedef filter_iterator<\n"
          "        detail::remove_whitespace_predicate<\n"
          "            typename boost::iterator_value<Base>::type\n"
          "            //typename Base::value_type\n"
          "        >,\n")

    # M11 CI fix (CI fix commit)
    patch("deps/boost/boost/asio/detail/call_stack.hpp",
          "};\n"
          "\n"
          "template <typename Key, typename Value>\n"
          "tss_ptr<typename call_stack<Key, Value>::context>\n"
          "call_stack<Key, Value>::top_;\n"
          "\n"
          "} // namespace detail\n",
          "};\n"
          "\n"
          "template <typename Key, typename Value>\n"
          "inline tss_ptr<typename call_stack<Key, Value>::context>\n"
          "call_stack<Key, Value>::top_;\n"
          "\n"
          "} // namespace detail\n")

    # M11 CI fix (CI fix commit)
    patch("deps/boost/boost/asio/detail/keyword_tss_ptr.hpp",
          "};\n"
          "\n"
          "template <typename T>\n"
          "BOOST_ASIO_THREAD_KEYWORD T* keyword_tss_ptr<T>::value_;\n"
          "\n"
          "} // namespace detail\n"
          "BOOST_ASIO_INLINE_NAMESPACE_END\n",
          "};\n"
          "\n"
          "template <typename T>\n"
          "inline BOOST_ASIO_THREAD_KEYWORD T* keyword_tss_ptr<T>::value_;\n"
          "\n"
          "} // namespace detail\n"
          "BOOST_ASIO_INLINE_NAMESPACE_END\n")

    # M12 (M12 §6)
    patch("deps/boost/boost/asio/prefer.hpp",
          "namespace boost {\n"
          "namespace asio {\n"
          "BOOST_ASIO_INLINE_NAMESPACE_BEGIN\n"
          "namespace {\n"
          "\n"
          "static constexpr const BOOST_ASIO_VERSIONED_NAME(prefer_fn)::impl&\n"
          "  prefer = BOOST_ASIO_VERSIONED_NAME(prefer_fn)::static_instance<>::instance;\n"
          "\n"
          "} // namespace\n"
          "\n"
          "typedef BOOST_ASIO_VERSIONED_NAME(prefer_fn)::impl prefer_t;\n"
          "\n"
          "template <typename T, typename... Properties>\n",
          "namespace boost {\n"
          "namespace asio {\n"
          "BOOST_ASIO_INLINE_NAMESPACE_BEGIN\n"
          "// boost-module M12 vendor patch: anonymous namespace -> inline variable.\n"
          "// The TU-local prefer object is referenced from the module face; when the\n"
          "// boost.asio CMI and a consumer GMF (beast/cobalt/process) both carry the\n"
          "// _GLOBAL__N_1 copy, gcc emits the same-mangled symbol twice (M11 §7.4\n"
          "// print_helper family). A named inline constexpr keeps the spelling and\n"
          "// merges the definitions.\n"
          "inline constexpr const BOOST_ASIO_VERSIONED_NAME(prefer_fn)::impl&\n"
          "  prefer = BOOST_ASIO_VERSIONED_NAME(prefer_fn)::static_instance<>::instance;\n"
          "\n"
          "typedef BOOST_ASIO_VERSIONED_NAME(prefer_fn)::impl prefer_t;\n"
          "\n"
          "template <typename T, typename... Properties>\n")

    # M12 (M12 §6)
    patch("deps/boost/boost/asio/query.hpp",
          "namespace boost {\n"
          "namespace asio {\n"
          "BOOST_ASIO_INLINE_NAMESPACE_BEGIN\n"
          "namespace {\n"
          "\n"
          "static constexpr const BOOST_ASIO_VERSIONED_NAME(query_fn)::impl&\n"
          "  query = BOOST_ASIO_VERSIONED_NAME(query_fn)::static_instance<>::instance;\n"
          "\n"
          "} // namespace\n"
          "\n"
          "typedef BOOST_ASIO_VERSIONED_NAME(query_fn)::impl query_t;\n"
          "\n"
          "template <typename T, typename Property>\n",
          "namespace boost {\n"
          "namespace asio {\n"
          "BOOST_ASIO_INLINE_NAMESPACE_BEGIN\n"
          "// boost-module M12 vendor patch: anonymous namespace -> inline variable.\n"
          "// The TU-local query object is referenced from the module face; when the\n"
          "// boost.asio CMI and a consumer GMF (beast/cobalt/process) both carry the\n"
          "// _GLOBAL__N_1 copy, gcc emits the same-mangled symbol twice (M11 §7.4\n"
          "// print_helper family). A named inline constexpr keeps the spelling and\n"
          "// merges the definitions.\n"
          "inline constexpr const BOOST_ASIO_VERSIONED_NAME(query_fn)::impl&\n"
          "  query = BOOST_ASIO_VERSIONED_NAME(query_fn)::static_instance<>::instance;\n"
          "\n"
          "typedef BOOST_ASIO_VERSIONED_NAME(query_fn)::impl query_t;\n"
          "\n"
          "template <typename T, typename Property>\n")

    # M12 (M12 §6)
    patch("deps/boost/boost/asio/require.hpp",
          "namespace boost {\n"
          "namespace asio {\n"
          "BOOST_ASIO_INLINE_NAMESPACE_BEGIN\n"
          "namespace {\n"
          "\n"
          "static constexpr const BOOST_ASIO_VERSIONED_NAME(require_fn)::impl&\n"
          "  require = BOOST_ASIO_VERSIONED_NAME(require_fn)::static_instance<>::instance;\n"
          "\n"
          "} // namespace\n"
          "\n"
          "typedef BOOST_ASIO_VERSIONED_NAME(require_fn)::impl require_t;\n"
          "\n"
          "template <typename T, typename... Properties>\n",
          "namespace boost {\n"
          "namespace asio {\n"
          "BOOST_ASIO_INLINE_NAMESPACE_BEGIN\n"
          "// boost-module M12 vendor patch: anonymous namespace -> inline variable.\n"
          "// The TU-local require object is referenced from the module face; when the\n"
          "// boost.asio CMI and a consumer GMF (beast/cobalt/process) both carry the\n"
          "// _GLOBAL__N_1 copy, gcc emits the same-mangled symbol twice (M11 §7.4\n"
          "// print_helper family). A named inline constexpr keeps the spelling and\n"
          "// merges the definitions.\n"
          "inline constexpr const BOOST_ASIO_VERSIONED_NAME(require_fn)::impl&\n"
          "  require = BOOST_ASIO_VERSIONED_NAME(require_fn)::static_instance<>::instance;\n"
          "\n"
          "typedef BOOST_ASIO_VERSIONED_NAME(require_fn)::impl require_t;\n"
          "\n"
          "template <typename T, typename... Properties>\n")

    # M12 (M12 §6)
    patch("deps/boost/boost/asio/require_concept.hpp",
          "namespace boost {\n"
          "namespace asio {\n"
          "BOOST_ASIO_INLINE_NAMESPACE_BEGIN\n"
          "namespace {\n"
          "\n"
          "static constexpr const BOOST_ASIO_VERSIONED_NAME(require_concept_fn)::impl&\n"
          "  require_concept = BOOST_ASIO_VERSIONED_NAME(\n"
          "    require_concept_fn)::static_instance<>::instance;\n"
          "\n"
          "} // namespace\n"
          "\n"
          "typedef BOOST_ASIO_VERSIONED_NAME(require_concept_fn)::impl require_concept_t;\n"
          "\n"
          "template <typename T, typename Property>\n",
          "namespace boost {\n"
          "namespace asio {\n"
          "BOOST_ASIO_INLINE_NAMESPACE_BEGIN\n"
          "// boost-module M12 vendor patch: anonymous namespace -> inline variable.\n"
          "// The TU-local require_concept object is referenced from the module face; when the\n"
          "// boost.asio CMI and a consumer GMF (beast/cobalt/process) both carry the\n"
          "// _GLOBAL__N_1 copy, gcc emits the same-mangled symbol twice (M11 §7.4\n"
          "// print_helper family). A named inline constexpr keeps the spelling and\n"
          "// merges the definitions.\n"
          "inline constexpr const BOOST_ASIO_VERSIONED_NAME(require_concept_fn)::impl&\n"
          "  require_concept = BOOST_ASIO_VERSIONED_NAME(\n"
          "    require_concept_fn)::static_instance<>::instance;\n"
          "\n"
          "typedef BOOST_ASIO_VERSIONED_NAME(require_concept_fn)::impl require_concept_t;\n"
          "\n"
          "template <typename T, typename Property>\n")

    # M12 (M12 §6)
    patch("deps/boost/boost/beast/core/detail/static_const.hpp",
          "template<typename T>\n"
          "constexpr T static_const<T>::value;\n"
          "\n"
          "#define BOOST_BEAST_INLINE_VARIABLE(name, type) \\\n"
          "    namespace \\\n"
          "    { \\\n"
          "        constexpr auto& name = \\\n"
          "            ::boost::beast::detail::static_const<type>::value; \\\n"
          "    }\n"
          "\n"
          "} // detail\n"
          "} // beast\n",
          "template<typename T>\n"
          "constexpr T static_const<T>::value;\n"
          "\n"
          "// boost-module M12 vendor patch: anonymous namespace -> inline constexpr.\n"
          "// The TU-local variable is referenced from the module face; when a beast CMI\n"
          "// and a consumer GMF (mqtt5 etc.) both carry the _GLOBAL__N_1 copy, gcc emits\n"
          "// the same-mangled symbol twice (M11 §7.4 print_helper family). An inline\n"
          "// constexpr variable keeps the spelling and merges the definitions.\n"
          "#define BOOST_BEAST_INLINE_VARIABLE(name, type) \\\n"
          "    inline constexpr auto& name = \\\n"
          "        ::boost::beast::detail::static_const<type>::value;\n"
          "\n"
          "} // detail\n"
          "} // beast\n")

    # M11 (M11 §6.9)
    patch("deps/boost/boost/io/detail/buffer_fill.hpp",
          "    std::size_t size)\n"
          "{\n"
          "    charT fill[] = { ch, ch, ch, ch, ch, ch, ch, ch };\n"
          "    enum {\n"
          "        chunk = sizeof fill / sizeof(charT)\n"
          "    };\n"
          "    for (; size > chunk; size -= chunk) {\n"
          "        if (static_cast<std::size_t>(buf.sputn(fill, chunk)) != chunk) {\n"
          "            return false;\n",
          "    std::size_t size)\n"
          "{\n"
          "    charT fill[] = { ch, ch, ch, ch, ch, ch, ch, ch };\n"
          "    // M11 vendored edit (gcc C++23 modules): the unnamed enum inside this\n"
          "    // inline template failed to stream consistently across CMIs that include\n"
          "    // this header from different module faces (boost.utility via\n"
          "    // utility/string_view.hpp, boost.filesystem/wave via filesystem/path.hpp →\n"
          "    // io/quoted.hpp) — gcc hard-errors \"definition of enum ... does not match\"\n"
          "    // when a consumer TU loads both pendings. A constexpr local is\n"
          "    // behavior-identical and streams fine. Replay after re-running\n"
          "    // import_boost (see M11 doc §6.9).\n"
          "    constexpr std::size_t chunk = sizeof fill / sizeof(charT);\n"
          "    for (; size > chunk; size -= chunk) {\n"
          "        if (static_cast<std::size_t>(buf.sputn(fill, chunk)) != chunk) {\n"
          "            return false;\n")

    # M12 (M12 §6)
    patch("deps/boost/boost/mqtt5/detail/async_traits.hpp",
          "\n"
          "// tls handshake\n"
          "\n"
          "constexpr auto handshake_handler_t = [](error_code) {};\n"
          "\n"
          "template <typename T>\n"
          "using tls_handshake_t = typename T::handshake_type;\n",
          "\n"
          "// tls handshake\n"
          "\n"
          "// boost-module M12 vendor patch: lambda closure types are TU-local, so the\n"
          "// exported *_sig detection aliases \"expose TU-local entity\" on gcc. Named\n"
          "// struct tags keep the detection role (decltype(X) == the tag type) with\n"
          "// external linkage.\n"
          "struct handshake_handler_t {\n"
          "  void operator()(error_code) const {}\n"
          "};\n"
          "\n"
          "template <typename T>\n"
          "using tls_handshake_t = typename T::handshake_type;\n")
    patch("deps/boost/boost/mqtt5/detail/async_traits.hpp",
          "template <typename T>\n"
          "constexpr bool has_tls_handshake = boost::is_detected<\n"
          "    async_tls_handshake_sig, T, tls_handshake_type_of<T>,\n"
          "    decltype(handshake_handler_t)\n"
          ">::value;\n"
          "\n"
          "// websocket handshake\n",
          "template <typename T>\n"
          "constexpr bool has_tls_handshake = boost::is_detected<\n"
          "    async_tls_handshake_sig, T, tls_handshake_type_of<T>,\n"
          "    handshake_handler_t\n"
          ">::value;\n"
          "\n"
          "// websocket handshake\n")
    patch("deps/boost/boost/mqtt5/detail/async_traits.hpp",
          "constexpr bool has_ws_handshake = boost::is_detected<\n"
          "    async_ws_handshake_sig, T,\n"
          "    std::string_view, std::string_view,\n"
          "    decltype(handshake_handler_t)\n"
          ">::value;\n"
          "\n"
          "// next layer\n",
          "constexpr bool has_ws_handshake = boost::is_detected<\n"
          "    async_ws_handshake_sig, T,\n"
          "    std::string_view, std::string_view,\n"
          "    handshake_handler_t\n"
          ">::value;\n"
          "\n"
          "// next layer\n")
    patch("deps/boost/boost/mqtt5/detail/async_traits.hpp",
          "    std::declval<T&>().async_write(std::declval<Ts>()...)\n"
          ");\n"
          "\n"
          "constexpr auto write_handler_t = [](error_code, size_t) {};\n"
          "\n"
          "template <typename T, typename B>\n"
          "constexpr bool has_async_write = boost::is_detected<\n"
          "    async_write_sig, T, B, decltype(write_handler_t)\n"
          ">::value;\n"
          "\n"
          "template <\n",
          "    std::declval<T&>().async_write(std::declval<Ts>()...)\n"
          ");\n"
          "\n"
          "struct write_handler_t {\n"
          "  void operator()(error_code, std::size_t) const {}\n"
          "};\n"
          "\n"
          "template <typename T, typename B>\n"
          "constexpr bool has_async_write = boost::is_detected<\n"
          "    async_write_sig, T, B, write_handler_t\n"
          ">::value;\n"
          "\n"
          "template <\n")

    # M12 (M12 §6)
    patch("deps/boost/boost/numeric/ublas/operation/size.hpp",
          "\n"
          "namespace boost { namespace numeric { namespace ublas {\n"
          "\n"
          "namespace detail { namespace /*<unnamed>*/ {\n"
          "\n"
          "/// Define a \\c has_size_type trait class.\n"
          "BOOST_MPL_HAS_XXX_TRAIT_DEF(size_type)\n",
          "\n"
          "namespace boost { namespace numeric { namespace ublas {\n"
          "\n"
          "// boost-module M12 vendor patch: unnamed -> named namespace. The trait\n"
          "// templates here (has_size_type/vector_size_type/matrix_size_type/\n"
          "// size_by_*_impl) appear in the return types of the exported function\n"
          "// templates size()/... — an anonymous namespace makes them TU-local and\n"
          "// gcc hard-errors \"exposes TU-local entity\" on the module face.\n"
          "namespace detail {\n"
          "\n"
          "/// Define a \\c has_size_type trait class.\n"
          "BOOST_MPL_HAS_XXX_TRAIT_DEF(size_type)\n")
    patch("deps/boost/boost/numeric/ublas/operation/size.hpp",
          "    // Empty\n"
          "};\n"
          "\n"
          "}} // Namespace detail::<unnamed>\n"
          "\n"
          "\n"
          "/**\n",
          "    // Empty\n"
          "};\n"
          "\n"
          "} // Namespace detail\n"
          "\n"
          "\n"
          "/**\n")

    # M12 (M12 §6)
    patch("deps/boost/boost/parameter/name.hpp",
          "\n"
          "#include <boost/parameter/keyword.hpp>\n"
          "\n"
          "#define BOOST_PARAMETER_NAME_KEYWORD(tag_namespace, tag, name)               \\\n"
          "    namespace                                                                \\\n"
          "    {                                                                        \\\n"
          "        ::boost::parameter::keyword<tag_namespace::tag> const& name          \\\n"
          "            = ::boost::parameter::keyword<tag_namespace::tag>::instance;     \\\n"
          "    }\n"
          "/**/\n"
          "\n"
          "#define BOOST_PARAMETER_BASIC_NAME(tag_namespace, tag, qualifier, name)      \\\n",
          "\n"
          "#include <boost/parameter/keyword.hpp>\n"
          "\n"
          "// boost-module M12 vendor patch: anonymous namespace -> inline constexpr.\n"
          "// The TU-local keyword objects are referenced from module faces (e.g. BGL\n"
          "// keywords in boost.graph); when a module CMI and a consumer GMF both carry\n"
          "// the _GLOBAL__N_1 copy, gcc emits the same-mangled symbol twice (M11 §7.4\n"
          "// print_helper family). An inline constexpr reference keeps the spelling and\n"
          "// merges the definitions.\n"
          "#define BOOST_PARAMETER_NAME_KEYWORD(tag_namespace, tag, name)               \\\n"
          "    inline constexpr ::boost::parameter::keyword<tag_namespace::tag> const& name \\\n"
          "        = ::boost::parameter::keyword<tag_namespace::tag>::instance;\n"
          "/**/\n"
          "\n"
          "#define BOOST_PARAMETER_BASIC_NAME(tag_namespace, tag, qualifier, name)      \\\n")

    # M12 (M12 §6)
    patch("deps/boost/boost/parameter/nested_keyword.hpp",
          "            >::instance;                                                     \\\n"
          "        typedef BOOST_PP_CAT(name, _)<> name;                                \\\n"
          "    }                                                                        \\\n"
          "    namespace                                                                \\\n"
          "    {                                                                        \\\n"
          "        ::boost::parameter::keyword<tag_namespace::name> const& name         \\\n"
          "            = ::boost::parameter::keyword<tag_namespace::name>::instance;    \\\n"
          "    }\n"
          "/**/\n"
          "#else   // !defined(BOOST_PARAMETER_CAN_USE_MP11)\n"
          "#define BOOST_PARAMETER_NESTED_KEYWORD_AUX(tag_namespace, q, name, alias)    \\\n",
          "            >::instance;                                                     \\\n"
          "        typedef BOOST_PP_CAT(name, _)<> name;                                \\\n"
          "    }                                                                        \\\n"
          "    /* boost-module M12 vendor patch: anonymous namespace -> inline constexpr */ \\\n"
          "    /* (gcc same-mangled symbol collision, M11 doc 7.4 family; named inline) */ \\\n"
          "    /* merges the definitions; spelling and semantics are unchanged.          */ \\\n"
          "        inline constexpr ::boost::parameter::keyword<tag_namespace::name> const& name         \\\n"
          "            = ::boost::parameter::keyword<tag_namespace::name>::instance;    \\\n"
          "/**/\n"
          "#else   // !defined(BOOST_PARAMETER_CAN_USE_MP11)\n"
          "#define BOOST_PARAMETER_NESTED_KEYWORD_AUX(tag_namespace, q, name, alias)    \\\n")
    patch("deps/boost/boost/parameter/nested_keyword.hpp",
          "            >::instance;                                                     \\\n"
          "        typedef BOOST_PP_CAT(name, _)<> name;                                \\\n"
          "    }                                                                        \\\n"
          "    namespace                                                                \\\n"
          "    {                                                                        \\\n"
          "        ::boost::parameter::keyword<tag_namespace::name> const& name         \\\n"
          "            = ::boost::parameter::keyword<tag_namespace::name>::instance;    \\\n"
          "    }\n"
          "/**/\n"
          "#endif  // BOOST_PARAMETER_CAN_USE_MP11\n"
          "\n",
          "            >::instance;                                                     \\\n"
          "        typedef BOOST_PP_CAT(name, _)<> name;                                \\\n"
          "    }                                                                        \\\n"
          "    /* boost-module M12 vendor patch: anonymous namespace -> inline constexpr */ \\\n"
          "    /* (gcc same-mangled symbol collision, M11 doc 7.4 family; named inline) */ \\\n"
          "    /* merges the definitions; spelling and semantics are unchanged.          */ \\\n"
          "        inline constexpr ::boost::parameter::keyword<tag_namespace::name> const& name         \\\n"
          "            = ::boost::parameter::keyword<tag_namespace::name>::instance;    \\\n"
          "/**/\n"
          "#endif  // BOOST_PARAMETER_CAN_USE_MP11\n"
          "\n")

    # M5 B' (M5 §6)
    patch("deps/boost/boost/regex/v5/mem_block_cache.hpp",
          "     ::operator delete(ptr);\n"
          "   }\n"
          "\n"
          "   static mem_block_cache& instance()\n"
          "   {\n"
          "      static mem_block_cache block_cache = { { {nullptr} } };\n"
          "      return block_cache;\n"
          "   }\n"
          "};\n"
          "\n"
          "\n"
          "#else /* lock-based implementation */\n"
          "\n",
          "     ::operator delete(ptr);\n"
          "   }\n"
          "\n"
          "   static mem_block_cache& instance();\n"
          "};\n"
          "\n"
          "// boost-module (M5 B'): 原为 instance() 函数内 static — gcc 模块管线在消费者 TU 以强符号\n"
          "// 发射函数内 static (非 COMDAT), 与 regex 库 TU 定义多重定义; 改命名空间作用域内部链接\n"
          "// 对象, 每 TU 独立持有 (纯缓存, 语义等价)。instance() 定义移出类 (类内体看不到其后声明)。\n"
          "static mem_block_cache block_cache = { { {nullptr} } };\n"
          "\n"
          "inline mem_block_cache& mem_block_cache::instance()\n"
          "{\n"
          "   return block_cache;\n"
          "}\n"
          "\n"
          "\n"
          "#else /* lock-based implementation */\n"
          "\n")
    patch("deps/boost/boost/regex/v5/mem_block_cache.hpp",
          "         ++cached_blocks;\n"
          "      }\n"
          "   }\n"
          "   static mem_block_cache& instance()\n"
          "   {\n"
          "      static mem_block_cache block_cache;\n"
          "      return block_cache;\n"
          "   }\n"
          "};\n"
          "#endif\n"
          "#endif\n"
          "\n",
          "         ++cached_blocks;\n"
          "      }\n"
          "   }\n"
          "   static mem_block_cache& instance();\n"
          "};\n"
          "\n"
          "// boost-module (M5 B'): 同 lock-free 版本注释 (见上), 每 TU 独立持有。\n"
          "static mem_block_cache block_cache;\n"
          "\n"
          "inline mem_block_cache& mem_block_cache::instance()\n"
          "{\n"
          "   return block_cache;\n"
          "}\n"
          "#endif\n"
          "#endif\n"
          "\n")

    # M5 B' (M5 §6)
    patch("deps/boost/boost/regex/v5/regex_traits_defaults.hpp",
          "   return ((n >= (sizeof(messages) / sizeof(messages[1]))) ? \"\" : messages[n]);\n"
          "}\n"
          "\n"
          "inline const char*  get_default_error_string(regex_constants::error_type n)\n"
          "{\n"
          "   static const char* const s_default_error_messages[] = {\n"
          "      \"Success\",                                                            /* REG_NOERROR 0 error_ok */\n"
          "      \"No match\",                                                           /* REG_NOMATCH 1 error_no_match */\n"
          "      \"Invalid regular expression.\",                                        /* REG_BADPAT 2 error_bad_pattern */\n"
          "      \"Invalid collation character.\",                                       /* REG_ECOLLATE 3 error_collate */\n"
          "      \"Invalid character class name, collating name, or character range.\",  /* REG_ECTYPE 4 error_ctype */\n"
          "      \"Invalid or unterminated escape sequence.\",                           /* REG_EESCAPE 5 error_escape */\n"
          "      \"Invalid back reference: specified capturing group does not exist.\",  /* REG_ESUBREG 6 error_backref */\n"
          "      \"Unmatched [ or [^ in character class declaration.\",                  /* REG_EBRACK 7 error_brack */\n"
          "      \"Unmatched marking parenthesis ( or \\\\(.\",                            /* REG_EPAREN 8 error_paren */\n"
          "      \"Unmatched quantified repeat operator { or \\\\{.\",                     /* REG_EBRACE 9 error_brace */\n"
          "      \"Invalid content of repeat range.\",                                   /* REG_BADBR 10 error_badbrace */\n"
          "      \"Invalid range end in character class\",                               /* REG_ERANGE 11 error_range */\n"
          "      \"Out of memory.\",                                                     /* REG_ESPACE 12 error_space NOT USED */\n"
          "      \"Invalid preceding regular expression prior to repetition operator.\", /* REG_BADRPT 13 error_badrepeat */\n"
          "      \"Premature end of regular expression\",                                /* REG_EEND 14 error_end NOT USED */\n"
          "      \"Regular expression is too large.\",                                   /* REG_ESIZE 15 error_size NOT USED */\n"
          "      \"Unmatched ) or \\\\)\",                                                 /* REG_ERPAREN 16 error_right_paren NOT USED */\n"
          "      \"Empty regular expression.\",                                          /* REG_EMPTY 17 error_empty */\n"
          "      \"The complexity of matching the regular expression exceeded predefined bounds.  \"\n"
          "      \"Try refactoring the regular expression to make each choice made by the state machine unambiguous.  \"\n"
          "      \"This exception is thrown to prevent \\\"eternal\\\" matches that take an \"\n"
          "      \"indefinite period time to locate.\",                                  /* REG_ECOMPLEXITY 18 error_complexity */\n"
          "      \"Ran out of stack space trying to match the regular expression.\",     /* REG_ESTACK 19 error_stack */\n"
          "      \"Invalid or unterminated Perl (?...) sequence.\",                      /* REG_E_PERL 20 error_perl */\n"
          "      \"Unknown error.\",                                                     /* REG_E_UNKNOWN 21 error_unknown */\n"
          "   };\n"
          "\n"
          "   return (n > ::boost::regex_constants::error_unknown) ? s_default_error_messages[::boost::regex_constants::error_unknown] : s_default_error_messages[n];\n"
          "}\n"
          "\n"
          "inline regex_constants::syntax_type  get_default_syntax_type(char c)\n",
          "   return ((n >= (sizeof(messages) / sizeof(messages[1]))) ? \"\" : messages[n]);\n"
          "}\n"
          "\n"
          "// boost-module (M5 B'): 原为 get_default_error_string 函数内 static — gcc 模块管线在\n"
          "// 消费者 TU 以强符号发射函数内 static (非 COMDAT), 与 regex 库 TU 定义多重定义;\n"
          "// 改命名空间作用域内部链接数组, 每 TU 独立持有 (const 表, 语义等价)。\n"
          "static const char* const s_default_error_messages[] = {\n"
          "   \"Success\",                                                            /* REG_NOERROR 0 error_ok */\n"
          "   \"No match\",                                                           /* REG_NOMATCH 1 error_no_match */\n"
          "   \"Invalid regular expression.\",                                        /* REG_BADPAT 2 error_bad_pattern */\n"
          "   \"Invalid collation character.\",                                       /* REG_ECOLLATE 3 error_collate */\n"
          "   \"Invalid character class name, collating name, or character range.\",  /* REG_ECTYPE 4 error_ctype */\n"
          "   \"Invalid or unterminated escape sequence.\",                           /* REG_EESCAPE 5 error_escape */\n"
          "   \"Invalid back reference: specified capturing group does not exist.\",  /* REG_ESUBREG 6 error_backref */\n"
          "   \"Unmatched [ or [^ in character class declaration.\",                  /* REG_EBRACK 7 error_brack */\n"
          "   \"Unmatched marking parenthesis ( or \\\\(.\",                            /* REG_EPAREN 8 error_paren */\n"
          "   \"Unmatched quantified repeat operator { or \\\\{.\",                     /* REG_EBRACE 9 error_brace */\n"
          "   \"Invalid content of repeat range.\",                                   /* REG_BADBR 10 error_badbrace */\n"
          "   \"Invalid range end in character class\",                               /* REG_ERANGE 11 error_range */\n"
          "   \"Out of memory.\",                                                     /* REG_ESPACE 12 error_space NOT USED */\n"
          "   \"Invalid preceding regular expression prior to repetition operator.\", /* REG_BADRPT 13 error_badrepeat */\n"
          "   \"Premature end of regular expression\",                                /* REG_EEND 14 error_end NOT USED */\n"
          "   \"Regular expression is too large.\",                                   /* REG_ESIZE 15 error_size NOT USED */\n"
          "   \"Unmatched ) or \\\\)\",                                                 /* REG_ERPAREN 16 error_right_paren NOT USED */\n"
          "   \"Empty regular expression.\",                                          /* REG_EMPTY 17 error_empty */\n"
          "   \"The complexity of matching the regular expression exceeded predefined bounds.  \"\n"
          "   \"Try refactoring the regular expression to make each choice made by the state machine unambiguous.  \"\n"
          "   \"This exception is thrown to prevent \\\"eternal\\\" matches that take an \"\n"
          "   \"indefinite period time to locate.\",                                  /* REG_ECOMPLEXITY 18 error_complexity */\n"
          "   \"Ran out of stack space trying to match the regular expression.\",     /* REG_ESTACK 19 error_stack */\n"
          "   \"Invalid or unterminated Perl (?...) sequence.\",                      /* REG_E_PERL 20 error_perl */\n"
          "   \"Unknown error.\",                                                     /* REG_E_UNKNOWN 21 error_unknown */\n"
          "};\n"
          "\n"
          "inline const char*  get_default_error_string(regex_constants::error_type n)\n"
          "{\n"
          "   return ((n >= (sizeof(s_default_error_messages) / sizeof(s_default_error_messages[1]))) ? \"\" : s_default_error_messages[n]);\n"
          "}\n"
          "\n"
          "inline regex_constants::syntax_type  get_default_syntax_type(char c)\n")
    patch("deps/boost/boost/regex/v5/regex_traits_defaults.hpp",
          "//\n"
          "// get a default collating element:\n"
          "//\n"
          "inline std::string  lookup_default_collate_name(const std::string& name)\n"
          "{\n"
          "   //\n"
          "   // these are the POSIX collating names:\n"
          "   //\n"
          "   static const char* def_coll_names[] = {\n"
          "   \"NUL\", \"SOH\", \"STX\", \"ETX\", \"EOT\", \"ENQ\", \"ACK\", \"alert\", \"backspace\", \"tab\", \"newline\",\n"
          "   \"vertical-tab\", \"form-feed\", \"carriage-return\", \"SO\", \"SI\", \"DLE\", \"DC1\", \"DC2\", \"DC3\", \"DC4\", \"NAK\",\n"
          "   \"SYN\", \"ETB\", \"CAN\", \"EM\", \"SUB\", \"ESC\", \"IS4\", \"IS3\", \"IS2\", \"IS1\", \"space\", \"exclamation-mark\",\n"
          "   \"quotation-mark\", \"number-sign\", \"dollar-sign\", \"percent-sign\", \"ampersand\", \"apostrophe\",\n"
          "   \"left-parenthesis\", \"right-parenthesis\", \"asterisk\", \"plus-sign\", \"comma\", \"hyphen\",\n"
          "   \"period\", \"slash\", \"zero\", \"one\", \"two\", \"three\", \"four\", \"five\", \"six\", \"seven\", \"eight\", \"nine\",\n"
          "   \"colon\", \"semicolon\", \"less-than-sign\", \"equals-sign\", \"greater-than-sign\",\n"
          "   \"question-mark\", \"commercial-at\", \"A\", \"B\", \"C\", \"D\", \"E\", \"F\", \"G\", \"H\", \"I\", \"J\", \"K\", \"L\", \"M\", \"N\", \"O\", \"P\",\n"
          "   \"Q\", \"R\", \"S\", \"T\", \"U\", \"V\", \"W\", \"X\", \"Y\", \"Z\", \"left-square-bracket\", \"backslash\",\n"
          "   \"right-square-bracket\", \"circumflex\", \"underscore\", \"grave-accent\", \"a\", \"b\", \"c\", \"d\", \"e\", \"f\",\n"
          "   \"g\", \"h\", \"i\", \"j\", \"k\", \"l\", \"m\", \"n\", \"o\", \"p\", \"q\", \"r\", \"s\", \"t\", \"u\", \"v\", \"w\", \"x\", \"y\", \"z\", \"left-curly-bracket\",\n"
          "   \"vertical-line\", \"right-curly-bracket\", \"tilde\", \"DEL\", \"\",\n"
          "   };\n"
          "\n"
          "   // these multi-character collating elements\n"
          "   // should keep most Western-European locales\n"
          "   // happy - we should really localise these a\n"
          "   // little more - but this will have to do for\n"
          "   // now:\n"
          "\n"
          "   static const char* def_multi_coll[] = {\n"
          "      \"ae\",\n"
          "      \"Ae\",\n"
          "      \"AE\",\n"
          "      \"ch\",\n"
          "      \"Ch\",\n"
          "      \"CH\",\n"
          "      \"ll\",\n"
          "      \"Ll\",\n"
          "      \"LL\",\n"
          "      \"ss\",\n"
          "      \"Ss\",\n"
          "      \"SS\",\n"
          "      \"nj\",\n"
          "      \"Nj\",\n"
          "      \"NJ\",\n"
          "      \"dz\",\n"
          "      \"Dz\",\n"
          "      \"DZ\",\n"
          "      \"lj\",\n"
          "      \"Lj\",\n"
          "      \"LJ\",\n"
          "      \"\",\n"
          "   };\n"
          "\n"
          "   unsigned int i = 0;\n"
          "   while (*def_coll_names[i])\n"
          "   {\n",
          "//\n"
          "// get a default collating element:\n"
          "//\n"
          "// boost-module (M5 B'): 原为 lookup_default_collate_name 函数内 static — 与\n"
          "// get_default_error_string 同因 (见上), 改命名空间作用域内部链接, 每 TU 独立持有。\n"
          "static const char* def_coll_names[] = {\n"
          "\"NUL\", \"SOH\", \"STX\", \"ETX\", \"EOT\", \"ENQ\", \"ACK\", \"alert\", \"backspace\", \"tab\", \"newline\",\n"
          "\"vertical-tab\", \"form-feed\", \"carriage-return\", \"SO\", \"SI\", \"DLE\", \"DC1\", \"DC2\", \"DC3\", \"DC4\", \"NAK\",\n"
          "\"SYN\", \"ETB\", \"CAN\", \"EM\", \"SUB\", \"ESC\", \"IS4\", \"IS3\", \"IS2\", \"IS1\", \"space\", \"exclamation-mark\",\n"
          "\"quotation-mark\", \"number-sign\", \"dollar-sign\", \"percent-sign\", \"ampersand\", \"apostrophe\",\n"
          "\"left-parenthesis\", \"right-parenthesis\", \"asterisk\", \"plus-sign\", \"comma\", \"hyphen\",\n"
          "\"period\", \"slash\", \"zero\", \"one\", \"two\", \"three\", \"four\", \"five\", \"six\", \"seven\", \"eight\", \"nine\",\n"
          "\"colon\", \"semicolon\", \"less-than-sign\", \"equals-sign\", \"greater-than-sign\",\n"
          "\"question-mark\", \"commercial-at\", \"A\", \"B\", \"C\", \"D\", \"E\", \"F\", \"G\", \"H\", \"I\", \"J\", \"K\", \"L\", \"M\", \"N\", \"O\", \"P\",\n"
          "\"Q\", \"R\", \"S\", \"T\", \"U\", \"V\", \"W\", \"X\", \"Y\", \"Z\", \"left-square-bracket\", \"backslash\",\n"
          "\"right-square-bracket\", \"circumflex\", \"underscore\", \"grave-accent\", \"a\", \"b\", \"c\", \"d\", \"e\", \"f\",\n"
          "\"g\", \"h\", \"i\", \"j\", \"k\", \"l\", \"m\", \"n\", \"o\", \"p\", \"q\", \"r\", \"s\", \"t\", \"u\", \"v\", \"w\", \"x\", \"y\", \"z\", \"left-curly-bracket\",\n"
          "\"vertical-line\", \"right-curly-bracket\", \"tilde\", \"DEL\", \"\",\n"
          "};\n"
          "\n"
          "// these multi-character collating elements\n"
          "// should keep most Western-European locales\n"
          "// happy - we should really localise these a\n"
          "// little more - but this will have to do for\n"
          "// now:\n"
          "\n"
          "static const char* def_multi_coll[] = {\n"
          "   \"ae\",\n"
          "   \"Ae\",\n"
          "   \"AE\",\n"
          "   \"ch\",\n"
          "   \"Ch\",\n"
          "   \"CH\",\n"
          "   \"ll\",\n"
          "   \"Ll\",\n"
          "   \"LL\",\n"
          "   \"ss\",\n"
          "   \"Ss\",\n"
          "   \"SS\",\n"
          "   \"nj\",\n"
          "   \"Nj\",\n"
          "   \"NJ\",\n"
          "   \"dz\",\n"
          "   \"Dz\",\n"
          "   \"DZ\",\n"
          "   \"lj\",\n"
          "   \"Lj\",\n"
          "   \"LJ\",\n"
          "   \"\",\n"
          "};\n"
          "\n"
          "inline std::string  lookup_default_collate_name(const std::string& name)\n"
          "{\n"
          "   unsigned int i = 0;\n"
          "   while (*def_coll_names[i])\n"
          "   {\n")
    patch("deps/boost/boost/regex/v5/regex_traits_defaults.hpp",
          "#endif\n"
          "   }\n"
          "};\n"
          "template <class charT>\n"
          "int get_default_class_id(const charT* p1, const charT* p2)\n"
          "{\n"
          "   static const charT data[73] = {\n"
          "      'a', 'l', 'n', 'u', 'm',\n"
          "      'a', 'l', 'p', 'h', 'a',\n"
          "      'b', 'l', 'a', 'n', 'k',\n"
          "      'c', 'n', 't', 'r', 'l',\n"
          "      'd', 'i', 'g', 'i', 't',\n"
          "      'g', 'r', 'a', 'p', 'h',\n"
          "      'l', 'o', 'w', 'e', 'r',\n"
          "      'p', 'r', 'i', 'n', 't',\n"
          "      'p', 'u', 'n', 'c', 't',\n"
          "      's', 'p', 'a', 'c', 'e',\n"
          "      'u', 'n', 'i', 'c', 'o', 'd', 'e',\n"
          "      'u', 'p', 'p', 'e', 'r',\n"
          "      'v',\n"
          "      'w', 'o', 'r', 'd',\n"
          "      'x', 'd', 'i', 'g', 'i', 't',\n"
          "   };\n"
          "\n"
          "   static const character_pointer_range<charT> ranges[21] =\n"
          "   {\n"
          "      {data+0, data+5,}, // alnum\n"
          "      {data+5, data+10,}, // alpha\n"
          "      {data+10, data+15,}, // blank\n"
          "      {data+15, data+20,}, // cntrl\n"
          "      {data+20, data+21,}, // d\n"
          "      {data+20, data+25,}, // digit\n"
          "      {data+25, data+30,}, // graph\n"
          "      {data+29, data+30,}, // h\n"
          "      {data+30, data+31,}, // l\n"
          "      {data+30, data+35,}, // lower\n"
          "      {data+35, data+40,}, // print\n"
          "      {data+40, data+45,}, // punct\n"
          "      {data+45, data+46,}, // s\n"
          "      {data+45, data+50,}, // space\n"
          "      {data+57, data+58,}, // u\n"
          "      {data+50, data+57,}, // unicode\n"
          "      {data+57, data+62,}, // upper\n"
          "      {data+62, data+63,}, // v\n"
          "      {data+63, data+64,}, // w\n"
          "      {data+63, data+67,}, // word\n"
          "      {data+67, data+73,}, // xdigit\n"
          "   };\n"
          "   const character_pointer_range<charT>* ranges_begin = ranges;\n"
          "   const character_pointer_range<charT>* ranges_end = ranges + (sizeof(ranges)/sizeof(ranges[0]));\n"
          "\n"
          "   character_pointer_range<charT> t = { p1, p2, };\n"
          "   const character_pointer_range<charT>* p = std::lower_bound(ranges_begin, ranges_end, t);\n"
          "   if((p != ranges_end) && (t == *p))\n"
          "      return static_cast<int>(p - ranges);\n"
          "   return -1;\n"
          "}\n"
          "\n",
          "#endif\n"
          "   }\n"
          "};\n"
          "// boost-module (M5 B'): 原为 get_default_class_id 函数内 static — 与 get_default_error_string\n"
          "// 同因 (gcc 模块管线在消费者 TU 强符号发射函数内 static); 数据改到类模板静态成员。\n"
          "template <class charT>\n"
          "struct default_class_id_data\n"
          "{\n"
          "   static const charT data[73];\n"
          "   static const character_pointer_range<charT> ranges[21];\n"
          "};\n"
          "template <class charT>\n"
          "const charT default_class_id_data<charT>::data[73] = {\n"
          "   'a', 'l', 'n', 'u', 'm',\n"
          "   'a', 'l', 'p', 'h', 'a',\n"
          "   'b', 'l', 'a', 'n', 'k',\n"
          "   'c', 'n', 't', 'r', 'l',\n"
          "   'd', 'i', 'g', 'i', 't',\n"
          "   'g', 'r', 'a', 'p', 'h',\n"
          "   'l', 'o', 'w', 'e', 'r',\n"
          "   'p', 'r', 'i', 'n', 't',\n"
          "   'p', 'u', 'n', 'c', 't',\n"
          "   's', 'p', 'a', 'c', 'e',\n"
          "   'u', 'n', 'i', 'c', 'o', 'd', 'e',\n"
          "   'u', 'p', 'p', 'e', 'r',\n"
          "   'v',\n"
          "   'w', 'o', 'r', 'd',\n"
          "   'x', 'd', 'i', 'g', 'i', 't',\n"
          "};\n"
          "\n"
          "template <class charT>\n"
          "const character_pointer_range<charT> default_class_id_data<charT>::ranges[21] =\n"
          "{\n"
          "   {default_class_id_data<charT>::data+0, default_class_id_data<charT>::data+5,}, // alnum\n"
          "   {default_class_id_data<charT>::data+5, default_class_id_data<charT>::data+10,}, // alpha\n"
          "   {default_class_id_data<charT>::data+10, default_class_id_data<charT>::data+15,}, // blank\n"
          "   {default_class_id_data<charT>::data+15, default_class_id_data<charT>::data+20,}, // cntrl\n"
          "   {default_class_id_data<charT>::data+20, default_class_id_data<charT>::data+21,}, // d\n"
          "   {default_class_id_data<charT>::data+20, default_class_id_data<charT>::data+25,}, // digit\n"
          "   {default_class_id_data<charT>::data+25, default_class_id_data<charT>::data+30,}, // graph\n"
          "   {default_class_id_data<charT>::data+29, default_class_id_data<charT>::data+30,}, // h\n"
          "   {default_class_id_data<charT>::data+30, default_class_id_data<charT>::data+31,}, // l\n"
          "   {default_class_id_data<charT>::data+30, default_class_id_data<charT>::data+35,}, // lower\n"
          "   {default_class_id_data<charT>::data+35, default_class_id_data<charT>::data+40,}, // print\n"
          "   {default_class_id_data<charT>::data+40, default_class_id_data<charT>::data+45,}, // punct\n"
          "   {default_class_id_data<charT>::data+45, default_class_id_data<charT>::data+46,}, // s\n"
          "   {default_class_id_data<charT>::data+45, default_class_id_data<charT>::data+50,}, // space\n"
          "   {default_class_id_data<charT>::data+57, default_class_id_data<charT>::data+58,}, // u\n"
          "   {default_class_id_data<charT>::data+50, default_class_id_data<charT>::data+57,}, // unicode\n"
          "   {default_class_id_data<charT>::data+57, default_class_id_data<charT>::data+62,}, // upper\n"
          "   {default_class_id_data<charT>::data+62, default_class_id_data<charT>::data+63,}, // v\n"
          "   {default_class_id_data<charT>::data+63, default_class_id_data<charT>::data+64,}, // w\n"
          "   {default_class_id_data<charT>::data+63, default_class_id_data<charT>::data+67,}, // word\n"
          "   {default_class_id_data<charT>::data+67, default_class_id_data<charT>::data+73,}, // xdigit\n"
          "};\n"
          "\n"
          "template <class charT>\n"
          "int get_default_class_id(const charT* p1, const charT* p2)\n"
          "{\n"
          "   const character_pointer_range<charT>* ranges_begin = default_class_id_data<charT>::ranges;\n"
          "   const character_pointer_range<charT>* ranges_end = ranges_begin + (sizeof(default_class_id_data<charT>::ranges)/sizeof(default_class_id_data<charT>::ranges[0]));\n"
          "\n"
          "   character_pointer_range<charT> t = { p1, p2, };\n"
          "   const character_pointer_range<charT>* p = std::lower_bound(ranges_begin, ranges_end, t);\n"
          "   if((p != ranges_end) && (t == *p))\n"
          "      return static_cast<int>(p - default_class_id_data<charT>::ranges);\n"
          "   return -1;\n"
          "}\n"
          "\n")

    # M9 fix (M9 doc)
    patch("deps/boost/boost/safe_numerics/exception.hpp",
          "namespace boost {\n"
          "namespace safe_numerics {\n"
          "\n"
          "const class : public std::error_category {\n"
          "public:\n"
          "    virtual const char* name() const noexcept{\n"
          "        return \"safe numerics error\";\n",
          "namespace boost {\n"
          "namespace safe_numerics {\n"
          "\n"
          "// M9: named the class (was anonymous) — an anonymous class type is TU-local,\n"
          "// so safe_numerics_error_category and make_error_code were TU-local exposures,\n"
          "// which gcc 16 rejects in a module GMF ([basic.link]). Naming the type removes\n"
          "// TU-locality; behavior is unchanged. Re-apply if re-vendoring (import_boost.py).\n"
          "const class safe_numerics_error_category_t : public std::error_category {\n"
          "public:\n"
          "    virtual const char* name() const noexcept{\n"
          "        return \"safe numerics error\";\n")

    # M5 B' (M5 §6)
    patch("deps/boost/boost/system/detail/error_category_impl.hpp",
          "namespace system\n"
          "{\n"
          "\n"
          "inline void error_category::init_stdcat() const\n"
          "{\n"
          "    static_assert( sizeof( stdcat_ ) >= sizeof( boost::system::detail::std_category ), \"sizeof(stdcat_) is not enough for std_category\" );\n"
          "\n"
          "#if defined(BOOST_MSVC) && BOOST_MSVC < 1900\n"
          "    // no alignof\n"
          "#else\n"
          "\n"
          "    static_assert( alignof( decltype(stdcat_align_) ) >= alignof( boost::system::detail::std_category ), \"alignof(stdcat_) is not enough for std_category\" );\n"
          "\n"
          "#endif\n"
          "\n"
          "    // detail::mutex has a constexpr default constructor,\n"
          "    // and therefore guarantees static initialization, on\n"
          "    // everything except VS 2013 (msvc-12.0)\n"
          "\n"
          "    static system::detail::mutex mx_;\n"
          "\n"
          "    system::detail::lock_guard<system::detail::mutex> lk( mx_ );\n"
          "\n"
          "    if( sc_init_.load( std::memory_order_acquire ) == 0 )\n"
          "    {\n"
          "        ::new( static_cast<void*>( stdcat_ ) ) boost::system::detail::std_category( this, system::detail::id_wrapper<0>() );\n"
          "        sc_init_.store( 1, std::memory_order_release );\n"
          "    }\n"
          "}\n"
          "\n"
          "#if defined( BOOST_GCC ) && BOOST_GCC >= 40800 && BOOST_GCC < 70000\n"
          "#pragma GCC diagnostic push\n"
          "#pragma GCC diagnostic ignored \"-Wstrict-aliasing\"\n"
          "#endif\n"
          "\n"
          "inline BOOST_NOINLINE error_category::operator std::error_category const& () const\n"
          "{\n"
          "    if( id_ == detail::generic_category_id )\n"
          "    {\n"
          "// This condition must be the same as the one in error_condition.hpp\n"
          "#if defined(BOOST_SYSTEM_AVOID_STD_GENERIC_CATEGORY)\n"
          "\n"
          "        static const boost::system::detail::std_category generic_instance( this, system::detail::id_wrapper<0x1F4D3>() );\n"
          "        return generic_instance;\n"
          "\n"
          "#else\n"
          "\n"
          "        return std::generic_category();\n"
          "\n"
          "#endif\n"
          "    }\n"
          "\n"
          "    if( id_ == detail::system_category_id )\n"
          "    {\n"
          "// This condition must be the same as the one in error_code.hpp\n"
          "#if defined(BOOST_SYSTEM_AVOID_STD_SYSTEM_CATEGORY)\n"
          "\n"
          "        static const boost::system::detail::std_category system_instance( this, system::detail::id_wrapper<0x1F4D7>() );\n"
          "        return system_instance;\n"
          "\n"
          "#else\n"
          "\n"
          "        return std::system_category();\n"
          "\n"
          "#endif\n"
          "    }\n"
          "\n"
          "    if( sc_init_.load( std::memory_order_acquire ) == 0 )\n"
          "    {\n"
          "        init_stdcat();\n"
          "    }\n"
          "\n"
          "    return *static_cast<boost::system::detail::std_category const*>( static_cast<void const*>( stdcat_ ) );\n"
          "}\n"
          "\n"
          "#if defined( BOOST_GCC ) && BOOST_GCC >= 40800 && BOOST_GCC < 70000\n"
          "#pragma GCC diagnostic pop\n"
          "#endif\n"
          "\n"
          "} // namespace system\n"
          "} // namespace boost\n",
          "namespace system\n"
          "{\n"
          "\n"
          "// boost-module (M5 B'): init_stdcat() 与 operator std::error_category const& () const\n"
          "// 的定义移入 src/boost_system_extras.cpp — 函数内 static (mutex / std_category 实例) 在\n"
          "// gcc 模块管线消费者 TU 以强符号发射 → 多重定义; 移出头部后消费者只调用外部定义,\n"
          "// 函数内 static 只在库 TU 单份存在 (语义不变)。\n"
          "\n"
          "} // namespace system\n"
          "} // namespace boost\n")

    # M5 B' (M5 §6)
    patch("deps/boost/boost/system/detail/error_code.hpp",
          "bool operator==( const error_code & code, const error_condition & condition ) noexcept;\n"
          "std::size_t hash_value( error_code const & ec );\n"
          "\n"
          "class error_code\n"
          "{\n"
          "private:\n",
          "bool operator==( const error_code & code, const error_condition & condition ) noexcept;\n"
          "std::size_t hash_value( error_code const & ec );\n"
          "\n"
          "// boost-module (M5 B'): 原为 error_code::location() 函数内 static — gcc 模块管线在消费者\n"
          "// TU 以强符号发射函数内 static (非 COMDAT), 与库 TU 多重定义; 改命名空间作用域内部链接\n"
          "// constexpr (空 source_location, 每 TU 独立持有, 语义等价)。\n"
          "static constexpr source_location default_location = source_location();\n"
          "\n"
          "class error_code\n"
          "{\n"
          "private:\n")
    patch("deps/boost/boost/system/detail/error_code.hpp",
          "\n"
          "    source_location const & location() const noexcept\n"
          "    {\n"
          "        BOOST_STATIC_CONSTEXPR source_location loc;\n"
          "        return lc_flags_ >= 4? *reinterpret_cast<source_location const*>( lc_flags_ &~ static_cast<boost::uintptr_t>( 1 ) ): loc;\n"
          "    }\n"
          "\n"
          "    // relationals:\n",
          "\n"
          "    source_location const & location() const noexcept\n"
          "    {\n"
          "        return lc_flags_ >= 4? *reinterpret_cast<source_location const*>( lc_flags_ &~ static_cast<boost::uintptr_t>( 1 ) ): default_location;\n"
          "    }\n"
          "\n"
          "    // relationals:\n")

    # M11 (M11 §7.4)
    patch("deps/boost/boost/test/tools/detail/print_helper.hpp",
          "    template <class T> struct static_const { static const T value; };\n"
          "    template <class T> const T static_const<T>::value = T();\n"
          "\n"
          "    namespace {\n"
          "        static const impl::boost_test_print_type_impl& boost_test_print_type =\n"
          "            static_const<impl::boost_test_print_type_impl>::value;\n"
          "    }\n"
          "\n"
          "\n"
          "// ************************************************************************** //\n",
          "    template <class T> struct static_const { static const T value; };\n"
          "    template <class T> const T static_const<T>::value = T();\n"
          "\n"
          "    // M11 vendored edit (gcc C++23 modules): the print helper reference lived\n"
          "    // in an anonymous namespace, making it TU-local; when the header is both\n"
          "    // included in a consumer TU and reachable through the boost.test CMI, gcc\n"
          "    // emits both copies under the same _GLOBAL__N_1 mangle and the assembler\n"
          "    // hard-errors \"symbol ... already defined\" (test_utf). An inline variable\n"
          "    // at namespace scope keeps the lookup spelling at the using-site below\n"
          "    // while being ODR-safe. Replay after re-running import_boost\n"
          "    // (see M11 doc §6.9).\n"
          "    inline const impl::boost_test_print_type_impl& boost_test_print_type =\n"
          "        static_const<impl::boost_test_print_type_impl>::value;\n"
          "\n"
          "\n"
          "// ************************************************************************** //\n")

    # M11 (M11 §7.4)
    patch("deps/boost/boost/test/utils/basic_cstring/basic_cstring.hpp",
          "\n"
          "//____________________________________________________________________________//\n"
          "\n"
          "template<typename CharT>\n"
          "CharT basic_cstring<CharT>::null = 0;\n"
          "\n"
          "//____________________________________________________________________________//\n"
          "\n",
          "\n"
          "//____________________________________________________________________________//\n"
          "\n"
          "// M11 vendored edit (gcc C++23 modules): the plain template static-data-member\n"
          "// definition is emitted both by the boost.test module TU (via its CMI) and by\n"
          "// include-side consumer TUs; the copies don't dedupe and the link hard-errors\n"
          "// \"duplicate symbol: boost::unit_test::basic_cstring<...>::null\" (test_utf).\n"
          "// An inline-variable definition merges them. Replay after re-running\n"
          "// import_boost (see M11 doc §6.9).\n"
          "template<typename CharT>\n"
          "inline CharT basic_cstring<CharT>::null = 0;\n"
          "\n"
          "//____________________________________________________________________________//\n"
          "\n")

    # M11 (M11 §6.9)
    patch("deps/boost/boost/test/utils/iterator/token_iterator.hpp",
          "// **************                  modifiers                   ************** //\n"
          "// ************************************************************************** //\n"
          "\n"
          "namespace {\n"
          "nfp::keyword<struct dropped_delimeters_t >           dropped_delimeters;\n"
          "nfp::keyword<struct kept_delimeters_t >              kept_delimeters;\n"
          "nfp::typed_keyword<bool,struct keep_empty_tokens_t > keep_empty_tokens;\n"
          "nfp::typed_keyword<std::size_t,struct max_tokens_t > max_tokens;\n"
          "}\n"
          "\n"
          "// ************************************************************************** //\n"
          "// **************             token_iterator_base              ************** //\n",
          "// **************                  modifiers                   ************** //\n"
          "// ************************************************************************** //\n"
          "\n"
          "// M11 vendored edit (gcc C++23 modules): the token keywords lived in an\n"
          "// anonymous namespace (TU-local), and token_iterator_base's modifier handling\n"
          "// exposed them from the test module surface. Named namespace with inline\n"
          "// variables + using-directive keeps the unqualified-lookup behavior. Replay\n"
          "// after re-running import_boost (see M11 doc §6.9).\n"
          "namespace token_iterator_detail {\n"
          "inline nfp::keyword<struct dropped_delimeters_t >           dropped_delimeters;\n"
          "inline nfp::keyword<struct kept_delimeters_t >              kept_delimeters;\n"
          "inline nfp::typed_keyword<bool,struct keep_empty_tokens_t > keep_empty_tokens;\n"
          "inline nfp::typed_keyword<std::size_t,struct max_tokens_t > max_tokens;\n"
          "}\n"
          "using namespace token_iterator_detail;\n"
          "\n"
          "// ************************************************************************** //\n"
          "// **************             token_iterator_base              ************** //\n")

    # M11 (M11 §6.9)
    patch("deps/boost/boost/test/utils/runtime/modifier.hpp",
          "// **************         environment variable modifiers       ************** //\n"
          "// ************************************************************************** //\n"
          "\n"
          "namespace {\n"
          "\n"
          "#ifdef BOOST_TEST_CLA_NEW_API\n"
          "auto const& description     = unit_test::static_constant<nfp::typed_keyword<cstring,struct description_t>>::value;\n"
          "auto const& help            = unit_test::static_constant<nfp::typed_keyword<cstring,struct help_t>>::value;\n"
          "auto const& env_var         = unit_test::static_constant<nfp::typed_keyword<cstring,struct env_var_t>>::value;\n"
          "auto const& end_of_params   = unit_test::static_constant<nfp::typed_keyword<cstring,struct end_of_params_t>>::value;\n"
          "auto const& negation_prefix = unit_test::static_constant<nfp::typed_keyword<cstring,struct neg_prefix_t>>::value;\n"
          "auto const& value_hint      = unit_test::static_constant<nfp::typed_keyword<cstring,struct value_hint_t>>::value;\n"
          "auto const& optional_value  = unit_test::static_constant<nfp::keyword<struct optional_value_t>>::value;\n"
          "auto const& default_value   = unit_test::static_constant<nfp::keyword<struct default_value_t>>::value;\n"
          "auto const& callback        = unit_test::static_constant<nfp::keyword<struct callback_t>>::value;\n"
          "\n"
          "template<typename EnumType>\n"
          "using enum_values = unit_test::static_constant<\n",
          "// **************         environment variable modifiers       ************** //\n"
          "// ************************************************************************** //\n"
          "\n"
          "// M11 vendored edit (gcc C++23 modules): the keyword objects lived in an\n"
          "// anonymous namespace, which made them and their tag types TU-local; the\n"
          "// test module surface hard-errors \"exposes TU-local entity\" when runtime\n"
          "// templates (parameter.hpp, argument_factory.hpp, cla/parser.hpp) reference\n"
          "// them. A named namespace with inline variables + a using-directive keeps\n"
          "// the unqualified-lookup behavior. Replay after re-running import_boost\n"
          "// (see M11 doc §6.9).\n"
          "namespace runtime_detail {\n"
          "\n"
          "#ifdef BOOST_TEST_CLA_NEW_API\n"
          "inline auto const& description     = unit_test::static_constant<nfp::typed_keyword<cstring,struct description_t>>::value;\n"
          "inline auto const& help            = unit_test::static_constant<nfp::typed_keyword<cstring,struct help_t>>::value;\n"
          "inline auto const& env_var         = unit_test::static_constant<nfp::typed_keyword<cstring,struct env_var_t>>::value;\n"
          "inline auto const& end_of_params   = unit_test::static_constant<nfp::typed_keyword<cstring,struct end_of_params_t>>::value;\n"
          "inline auto const& negation_prefix = unit_test::static_constant<nfp::typed_keyword<cstring,struct neg_prefix_t>>::value;\n"
          "inline auto const& value_hint      = unit_test::static_constant<nfp::typed_keyword<cstring,struct value_hint_t>>::value;\n"
          "inline auto const& optional_value  = unit_test::static_constant<nfp::keyword<struct optional_value_t>>::value;\n"
          "inline auto const& default_value   = unit_test::static_constant<nfp::keyword<struct default_value_t>>::value;\n"
          "inline auto const& callback        = unit_test::static_constant<nfp::keyword<struct callback_t>>::value;\n"
          "\n"
          "template<typename EnumType>\n"
          "using enum_values = unit_test::static_constant<\n")
    patch("deps/boost/boost/test/utils/runtime/modifier.hpp",
          "\n"
          "#else\n"
          "\n"
          "nfp::typed_keyword<cstring,struct description_t> description;\n"
          "nfp::typed_keyword<cstring,struct help_t> help;\n"
          "nfp::typed_keyword<cstring,struct env_var_t> env_var;\n"
          "nfp::typed_keyword<cstring,struct end_of_params_t> end_of_params;\n"
          "nfp::typed_keyword<cstring,struct neg_prefix_t> negation_prefix;\n"
          "nfp::typed_keyword<cstring,struct value_hint_t> value_hint;\n"
          "nfp::keyword<struct optional_value_t> optional_value;\n"
          "nfp::keyword<struct default_value_t> default_value;\n"
          "nfp::keyword<struct callback_t> callback;\n"
          "\n"
          "template<typename EnumType>\n"
          "struct enum_values_list {\n",
          "\n"
          "#else\n"
          "\n"
          "inline nfp::typed_keyword<cstring,struct description_t> description;\n"
          "inline nfp::typed_keyword<cstring,struct help_t> help;\n"
          "inline nfp::typed_keyword<cstring,struct env_var_t> env_var;\n"
          "inline nfp::typed_keyword<cstring,struct end_of_params_t> end_of_params;\n"
          "inline nfp::typed_keyword<cstring,struct neg_prefix_t> negation_prefix;\n"
          "inline nfp::typed_keyword<cstring,struct value_hint_t> value_hint;\n"
          "inline nfp::keyword<struct optional_value_t> optional_value;\n"
          "inline nfp::keyword<struct default_value_t> default_value;\n"
          "inline nfp::keyword<struct callback_t> callback;\n"
          "\n"
          "template<typename EnumType>\n"
          "struct enum_values_list {\n")
    patch("deps/boost/boost/test/utils/runtime/modifier.hpp",
          "\n"
          "#endif\n"
          "\n"
          "} // local namespace\n"
          "\n"
          "} // namespace runtime\n"
          "} // namespace boost\n",
          "\n"
          "#endif\n"
          "\n"
          "} // namespace runtime_detail\n"
          "using namespace runtime_detail;\n"
          "\n"
          "} // namespace runtime\n"
          "} // namespace boost\n")

    # M11 (M11 §6.4): new vendored file (mc.exe stub), not an upstream patch
    ensure_file("deps/boost/libs/log/src/windows/simple_event_log.h",
          "/*\n"
          " *          Copyright Andrey Semashev 2007 - 2015.\n"
          " * Distributed under the Boost Software License, Version 1.0.\n"
          " *    (See accompanying file LICENSE_1_0.txt or copy at\n"
          " *          http://www.boost.org/LICENSE_1_0.txt)\n"
          " */\n"
          "\n"
          "/*\n"
          " * M11: hand-written replacement for the mc.exe-generated header. Upstream\n"
          " * builds it from simple_event_log.mc at configure/build time (see\n"
          " * libs/log/CMakeLists.txt); the vendored tree has no build-time code\n"
          " * generation, so the constants (which only need to be self-consistent event\n"
          " * IDs passed to ReportEvent) are defined here directly, mirroring the .mc\n"
          " * MessageId/Severity layout.\n"
          " */\n"
          "\n"
          "#pragma once\n"
          "\n"
          "#define BOOST_LOG_SEVERITY_DEBUG   0x00000000L\n"
          "#define BOOST_LOG_SEVERITY_INFO    0x00000001L\n"
          "#define BOOST_LOG_SEVERITY_WARNING 0x00000002L\n"
          "#define BOOST_LOG_SEVERITY_ERROR   0x00000003L\n"
          "\n"
          "#define BOOST_LOG_MSG_DEBUG   ((DWORD)0x01000100L)\n"
          "#define BOOST_LOG_MSG_INFO    ((DWORD)0x01000101L)\n"
          "#define BOOST_LOG_MSG_WARNING ((DWORD)0x01000102L)\n"
          "#define BOOST_LOG_MSG_ERROR   ((DWORD)0x01000103L)\n")


def main():
    print("reapplying hand edits...")

    # ---- vendored header patches under deps/boost/ (rollup doc §3.7#1):
    # import_boost.py re-vendoring wipes them; replay before the .inc/.cppm
    # pass below ----
    reapply_vendored_patches()

    # ---- .cppm (M3 §3 + M4 §7) ----
    patch("src/core.cppm",
          "export module boost.core;\n\n#include \"gen_exports/core.inc\"",
          "export module boost.core;\n\n"
          "// 对象宏 re-homing (M3): 宏无法跨模块导出。上游 <boost/version.hpp> 的对象宏\n"
          "// 以 boost:: 命名空间 constexpr 重置于此 (拼写保持): 消费者 import 后可用\n"
          "// boost::BOOST_VERSION。值须与 deps/boost/boost/version.hpp 一致 — tests/macros.cpp\n"
          "// 在旁路头 (include/boost-module/macros.hpp) 参与下交叉校验。\n"
          "// 注意: 同一 TU 中若定义了同名宏 (include <boost-module/macros.hpp>), 宏展开会\n"
          "// 吞掉 boost::BOOST_VERSION 拼写 (→ boost::109100), 两种拼写互斥, 二选一。\n"
          "export namespace boost {\n"
          "  constexpr int BOOST_VERSION = 109100;\n"
          "  constexpr const char* BOOST_LIB_VERSION = \"1_91\";\n"
          "}\n\n"
          "#include \"gen_exports/core.inc\"",
          required=False)  # git restore below covers it
    patch("src/json.cppm",
          "module;\n#include <boost/json/debug_printers.hpp>\n#include <boost/json/src.hpp>",
          "module;\n// M4: 定义移入库 TU src/src.cpp, GMF 不再 include src.hpp (防双定义) — 2026-08-11-m4-compiled-libs.md §4\n"
          "#include <boost/json/debug_printers.hpp>\n#include <boost/json.hpp>",
          required=False)
    patch("src/stacktrace.cppm",
          "module;\n#include <boost/stacktrace.hpp>",
          "module;\n// M4: BOOST_STACKTRACE_LINK 切到外链模式, 定义来自 libs/stacktrace/src/basic.cpp — 2026-08-11-m4-compiled-libs.md §3\n"
          "#define BOOST_STACKTRACE_LINK\n#include <boost/stacktrace.hpp>")
    # scope.cppm: no `export import boost.core;` — gcc 16.1.0 ICEs when this
    # GMF include set (unique_fd.hpp etc.) re-exports boost.core (M3 §3.2).
    patch("src/scope.cppm",
          "export module boost.scope;\n\nexport import boost.core;\n",
          "export module boost.scope;\n\n"
          "// NB: no `export import boost.core;` — gcc 16.1.0 ICEs (Segmentation fault at\n"
          "// the export-module line) when this GMF include set (which pulls\n"
          "// unique_fd.hpp, whose entities depend on boost.core) is combined with\n"
          "// re-exporting boost.core. scope.inc carries no boost::core:: entities (they\n"
          "// are claimed by boost.core itself), so consumers import boost.core on their\n"
          "// own. (Clang has no such issue; tracked as a gcc bug for M6 CI.)\n")

    # M9: winapi.cppm — boost/winapi/* headers are Windows-only (basic_types.hpp
    # #errors "Win32 functions not available" off-Windows). The winapi module
    # is in the default closure (system/thread imply it + `export import
    # boost.winapi;`), so on POSIX it must compile as a valid empty module.
    # Guards mirror basic_types.hpp. Three patches: open the GMF guard at the
    # first include, close it before `export module`, and guard the .inc.
    patch("src/winapi.cppm",
          "module;\n#include <boost/winapi/bcrypt.hpp>",
          "module;\n"
          "// M9 platform guard: boost/winapi/* #error off-Windows (basic_types.hpp).\n"
          "#if defined(_WIN32) || defined(__CYGWIN__)\n"
          "#include <boost/winapi/bcrypt.hpp>")
    patch("src/winapi.cppm",
          "#include <boost/winapi/waitable_timer.hpp>\n\nexport module boost.winapi;",
          "#include <boost/winapi/waitable_timer.hpp>\n#endif\n\nexport module boost.winapi;")
    patch("src/winapi.cppm",
          '#include "gen_exports/winapi.inc"\n',
          '#if defined(_WIN32) || defined(__CYGWIN__)\n'
          '#include "gen_exports/winapi.inc"\n'
          '#endif\n')

    # M9: safe_numerics.cppm — checked_result_operations.hpp calls std::terminate
    # without including <exception>; on libstdc++/libc++ <cassert> does not
    # transitively pull <exception> (it does on MSVC STL), so the GMF compile
    # fails on POSIX. Add the missing include upfront.
    patch("src/safe_numerics.cppm",
          "module;\n#include <boost/safe_numerics/automatic.hpp>",
          "module;\n"
          "// M9: checked_result_operations.hpp uses std::terminate without <exception>;\n"
          "// libstdc++/libc++ <cassert> doesn't transitively include it (MSVC STL does).\n"
          "#include <exception>\n"
          "#include <boost/safe_numerics/automatic.hpp>")

    # ---- .inc platform guards (M3 §5) ----
    # M9: int128_type/uint128_type are declared in boost/config/suffix.hpp, so
    # with boost.config as a module they moved from core.inc to config.inc.
    patch("src/gen_exports/config.inc",
          "  using boost::int128_type;",
          "#if defined(BOOST_HAS_INT128)\n  // M3 hand-guard (M9: moved to config.inc): suffix.hpp defines int128_type only where BOOST_HAS_INT128.\n  using boost::int128_type;\n#endif")
    patch("src/gen_exports/config.inc",
          "  using boost::uint128_type;",
          "#if defined(BOOST_HAS_INT128)\n  // M3 hand-guard (M9: moved to config.inc): suffix.hpp defines uint128_type only where BOOST_HAS_INT128.\n  using boost::uint128_type;\n#endif")
    patch("src/gen_exports/core.inc",
          "  using boost::core::detail::copysign_impl;",
          "#if defined(__GNUC__)\n  // M3 hand-guard: boost/core/cmath.hpp defines copysign_impl only on gcc-like compilers.\n  using boost::core::detail::copysign_impl;\n#endif")
    # M6 platform guards: snapshot = mingw flavor; Windows-only entities are absent
    # on POSIX (or live in a different namespace), so the module TU must not export
    # them there. Guards mirror the upstream header conditions.
    patch("src/gen_exports/core.inc",
          "  using boost::core::detail::sp_thread_sleep;\n  using boost::core::detail::sp_thread_yield;",
          "#if defined(_WIN32) || defined(__WIN32__) || defined(__CYGWIN__)\n"
          "  // M6 platform guard: sp_thread_sleep/yield live in boost::core::detail only on Windows;\n"
          "  // on POSIX (nanosleep/sched_yield branch of the header) they are declared in boost::core.\n"
          "  using boost::core::detail::sp_thread_sleep;\n"
          "  using boost::core::detail::sp_thread_yield;\n"
          "#else\n"
          "  using boost::core::sp_thread_sleep;\n"
          "  using boost::core::sp_thread_yield;\n"
          "#endif")
    patch("src/gen_exports/system.inc",
          "  using boost::system::detail::is_value_convertible_to;\n"
          "  using boost::system::detail::local_free;\n"
          "  using boost::system::detail::lock_guard;\n"
          "  using boost::system::detail::message_cp_win32;\n"
          "  using boost::system::detail::reference_to_temporary;",
          "  using boost::system::detail::is_value_convertible_to;\n"
          "#if defined(BOOST_WINDOWS_API)\n"
          "  // M6 platform guard: snapshot = mingw flavor; these boost/system/detail entities\n"
          "  // exist only under BOOST_WINDOWS_API (system_category_message_win32.hpp / condition).\n"
          "  using boost::system::detail::local_free;\n"
          "  using boost::system::detail::message_cp_win32;\n"
          "#endif\n"
          "  using boost::system::detail::lock_guard;\n"
          "  using boost::system::detail::reference_to_temporary;")
    patch("src/gen_exports/system.inc",
          "  using boost::system::detail::system_cat_holder;\n"
          "  using boost::system::detail::system_category_condition_win32;\n"
          "  using boost::system::detail::system_category_message_win32;\n"
          "  using boost::system::detail::system_error_category;\n"
          "  using boost::system::detail::system_error_category_message;\n"
          "  using boost::system::detail::unknown_message_win32;",
          "  using boost::system::detail::system_cat_holder;\n"
          "#if defined(BOOST_WINDOWS_API)\n"
          "  // M6 platform guard: as above.\n"
          "  using boost::system::detail::system_category_condition_win32;\n"
          "  using boost::system::detail::system_category_message_win32;\n"
          "#endif\n"
          "  using boost::system::detail::system_error_category;\n"
          "  using boost::system::detail::system_error_category_message;\n"
          "#if defined(BOOST_WINDOWS_API)\n"
          "  // M6 platform guard: as above.\n"
          "  using boost::system::detail::unknown_message_win32;\n"
          "#endif")
    patch("src/gen_exports/system.inc",
          "export namespace boost { namespace system { namespace windows_error {\n"
          "  using boost::system::windows_error::make_error_code;",
          "#if defined(BOOST_WINDOWS_API)\n"
          "export namespace boost { namespace system { namespace windows_error {\n"
          "  using boost::system::windows_error::make_error_code;")
    patch("src/gen_exports/system.inc",
          "  using boost::system::windows_error::windows_error_code::wrong_disk;\n}}}\n\nexport namespace boost { namespace variant2 {",
          "  using boost::system::windows_error::windows_error_code::wrong_disk;\n}}}\n#endif\n\nexport namespace boost { namespace variant2 {")

    # M6: program_options winmain splitter — <boost/program_options/winmain.hpp>
    # is pulled into the GMF only on Windows.
    patch("src/gen_exports/program_options.inc",
          "  using boost::program_options::split_winmain;",
          "#if defined(_WIN32)\n  // M6 platform guard: winmain.hpp (split_winmain) is Windows-only.\n  using boost::program_options::split_winmain;\n#endif")

    # M7c: gcc 16.1.0 module consumers emit a partial vtable for clone_impl<T>
    # (virtual base clone_base) whose thunk slots stay undefined — gcc never
    # emits the thunks in a module consumer TU (ELF link: undefined reference
    # to the virtual/non-virtual thunks, cf. linux-gcc CI). extern-template
    # declarations visible through the module interface suppress the consumer's
    # implicit instantiation; the complete vtable + thunks come from the
    # explicit instantiation in src/boost_thread_extras.cpp.
    patch("src/gen_exports/thread.inc",
          "  using boost::broken_promise;\n"
          "  using boost::call_once;",
          "  using boost::broken_promise;\n"
          "  // M7c: gcc 16.1.0 module consumers emit a partial vtable for clone_impl<T>\n"
          "  // (virtual base clone_base) whose thunk slots stay undefined — gcc never\n"
          "  // emits the thunks in a module consumer TU. These extern-template\n"
          "  // declarations suppress the consumer's implicit instantiation; the complete\n"
          "  // vtable + thunks come from the explicit instantiation in\n"
          "  // src/boost_thread_extras.cpp (same pattern as boost_system_extras.cpp).\n"
          "  extern template class boost::exception_detail::clone_impl<boost::broken_promise>;\n"
          "  extern template class boost::exception_detail::clone_impl<boost::unknown_exception>;\n"
          "  extern template class boost::exception_detail::clone_impl<boost::exception_detail::std_exception_ptr_wrapper>;\n"
          "  using boost::call_once;")

    # M9: leaf — same gcc 16.1.0 consumer-thunk bug as thread's clone_impl
    # (M7c), for leaf::detail::exception<bad_result> (multi-base
    # exception_base/error_id → non-virtual thunks). extern template in the
    # module interface + explicit instantiation in src/boost_leaf_extras.cpp.
    patch("src/gen_exports/leaf.inc",
          "  using boost::leaf::detail::exception;\n"
          "  using boost::leaf::detail::exception_base;",
          "  using boost::leaf::detail::exception;\n"
          "  // M9: gcc 16.1.0 module consumers emit a partial vtable for\n"
          "  // exception<bad_result> (multi-base exception_base/error_id) whose\n"
          "  // non-virtual thunks stay undefined — gcc never emits them in a module\n"
          "  // consumer TU. This extern template suppresses the consumer's implicit\n"
          "  // instantiation; the complete vtable + thunks come from the explicit\n"
          "  // instantiation in src/boost_leaf_extras.cpp (same pattern as thread's\n"
          "  // clone_impl, cf. M7c).\n"
          "  extern template class boost::leaf::detail::exception<boost::leaf::bad_result>;\n"
          "  using boost::leaf::detail::exception_base;")

    # M7: url module — grammar/detail/charset.hpp defines find_if_pred /
    # find_if_not_pred only under BOOST_URL_USE_SSE2 (x86 + SSE2); the mingw
    # x86_64 snapshot carried them, but macOS arm64 (no __SSE2__) fails.
    patch("src/gen_exports/url.inc",
          "  using boost::urls::grammar::detail::find_if_not_pred;\n"
          "  using boost::urls::grammar::detail::find_if_pred;",
          "#if defined(BOOST_URL_USE_SSE2)\n"
          "  // M7 platform guard: charset.hpp defines the *_pred SSE2 helpers only under\n"
          "  // BOOST_URL_USE_SSE2 (x86 with SSE2); absent on arm64 (e.g. macOS).\n"
          "  using boost::urls::grammar::detail::find_if_not_pred;\n"
          "  using boost::urls::grammar::detail::find_if_pred;\n"
          "#endif")

    # M9: decimal — the mingw snapshot carries 128-bit / 80-bit-long-double
    # entities that the MSVC ABI never declares (BOOST_DECIMAL_HAS_INT128 is
    # off under _MSC_VER, and MSVC long double is 53-bit so the
    # LDBL_MANT_DIG==64 branch is absent). Guards mirror the upstream header
    # conditions in decimal/detail/config.hpp / bit_layouts.hpp.
    patch("src/gen_exports/decimal.inc",
          "  using boost::decimal::detail::builtin_int128_t;\n"
          "  using boost::decimal::detail::builtin_uint128_t;",
          "#if defined(BOOST_DECIMAL_HAS_INT128)\n"
          "  // M9 platform guard: config.hpp defines the __int128 typedefs only where\n"
          "  // BOOST_DECIMAL_HAS_INT128 (off under the MSVC ABI).\n"
          "  using boost::decimal::detail::builtin_int128_t;\n"
          "  using boost::decimal::detail::builtin_uint128_t;\n"
          "#endif")
    patch("src/gen_exports/decimal.inc",
          "  using boost::decimal::detail::ieee754_binary80;",
          "#if LDBL_MANT_DIG == 64 && LDBL_MAX_EXP == 16384\n"
          "  // M9 platform guard: bit_layouts.hpp defines ieee754_binary80 only for 80-bit\n"
          "  // long double (x86-64 gcc/mingw); MSVC long double is 53-bit.\n"
          "  using boost::decimal::detail::ieee754_binary80;\n"
          "#endif")
    patch("src/gen_exports/decimal.inc",
          "  using boost::decimal::detail::impl::builtin_128_pow10;",
          "#if defined(BOOST_DECIMAL_HAS_INT128)\n"
          "  // M9 platform guard: power_tables.hpp defines builtin_128_pow10 only under\n"
          "  // BOOST_DECIMAL_HAS_INT128.\n"
          "  using boost::decimal::detail::impl::builtin_128_pow10;\n"
          "#endif")

    # M9: per-lib MSVC-flavor guards — the mingw snapshot carries entities
    # that the MSVC ABI never declares (compiler-specific branches). Guards
    # mirror the upstream header conditions.
    # dll: the itanium demangling parser (dll/detail/demangling/itanium.hpp)
    # is selected only outside _MSC_VER (ctor_dtor.hpp).
    patch("src/gen_exports/dll.inc",
          "  using boost::dll::detail::parser::arg_list;\n"
          "  using boost::dll::detail::parser::const_rule;\n"
          "  using boost::dll::detail::parser::const_rule_impl;\n"
          "  using boost::dll::detail::parser::dummy;\n"
          "  using boost::dll::detail::parser::parse_type;\n"
          "  using boost::dll::detail::parser::parse_type_helper;\n"
          "  using boost::dll::detail::parser::pure_type;\n"
          "  using boost::dll::detail::parser::reference_rule;\n"
          "  using boost::dll::detail::parser::reference_rule_impl;\n"
          "  using boost::dll::detail::parser::type_name;\n"
          "  using boost::dll::detail::parser::volatile_rule;\n"
          "  using boost::dll::detail::parser::volatile_rule_impl;",
          "#if !defined(_MSC_VER)\n"
          "  // M9 platform guard: the itanium demangling parser (demangling/itanium.hpp)\n"
          "  // is selected only outside _MSC_VER (dll/detail/ctor_dtor.hpp).\n"
          "  using boost::dll::detail::parser::arg_list;\n"
          "  using boost::dll::detail::parser::const_rule;\n"
          "  using boost::dll::detail::parser::const_rule_impl;\n"
          "  using boost::dll::detail::parser::dummy;\n"
          "  using boost::dll::detail::parser::parse_type;\n"
          "  using boost::dll::detail::parser::parse_type_helper;\n"
          "  using boost::dll::detail::parser::pure_type;\n"
          "  using boost::dll::detail::parser::reference_rule;\n"
          "  using boost::dll::detail::parser::reference_rule_impl;\n"
          "  using boost::dll::detail::parser::type_name;\n"
          "  using boost::dll::detail::parser::volatile_rule;\n"
          "  using boost::dll::detail::parser::volatile_rule_impl;\n"
          "#endif")
    # functional / poly_collection: gcc-preprocessed mpl vector/map aux headers
    # (BOOST_MPL_CFG_COMPILER_DIR=gcc, set under __GNUC__ — same pattern as the
    # M3 variant.inc guards).
    patch("src/gen_exports/functional.inc",
          "  using boost::mpl::v_at_impl;\n"
          "  using boost::mpl::v_item;\n"
          "  using boost::mpl::v_iter;\n"
          "  using boost::mpl::v_mask;",
          "#if defined(__GNUC__)\n"
          "  // M9 platform guard: gcc-preprocessed mpl vector headers only.\n"
          "  using boost::mpl::v_at_impl;\n"
          "  using boost::mpl::v_item;\n"
          "#endif\n"
          "  using boost::mpl::v_iter;\n"
          "#if defined(__GNUC__)\n"
          "  using boost::mpl::v_mask;\n"
          "#endif")
    patch("src/gen_exports/poly_collection.inc",
          "  using boost::mpl::item_by_order_impl;",
          "#if defined(__GNUC__)\n"
          "  // M9 platform guard: gcc-preprocessed mpl map headers only.\n"
          "  using boost::mpl::item_by_order_impl;\n"
          "#endif")
    # intrusive: builtin_clz_dispatch — the __GNUC__ branch of the BSR
    # intrinsic chain (intrusive/detail/math.hpp).
    patch("src/gen_exports/intrusive.inc",
          "  using boost::intrusive::detail::builtin_clz_dispatch;",
          "#if defined(__GNUC__)\n"
          "  // M9 platform guard: math.hpp defines builtin_clz_dispatch only in the\n"
          "  // __GNUC__ branch of the BSR intrinsic chain.\n"
          "  using boost::intrusive::detail::builtin_clz_dispatch;\n"
          "#endif")
    # dll: demangle_symbol is part of the itanium demangling surface (only
    # outside _MSC_VER).
    patch("src/gen_exports/dll.inc",
          "  using boost::dll::experimental::demangle_symbol;",
          "#if !defined(_MSC_VER)\n"
          "  // M9 platform guard: demangle_symbol comes from demangling/itanium.hpp.\n"
          "  using boost::dll::experimental::demangle_symbol;\n"
          "#endif")
    # range: `using std::random_shuffle;` — std::random_shuffle was removed in
    # C++17; only libstdc++ still ships it (mingw gate passes), MSVC STL and
    # libc++ do not.
    patch("src/gen_exports/range.inc",
          "  using std::random_shuffle;",
          "#if defined(__GLIBCXX__)\n"
          "  // M9 platform guard: std::random_shuffle was removed in C++17; only\n"
          "  // libstdc++ (mingw/linux-gcc) still provides it.\n"
          "  using std::random_shuffle;\n"
          "#endif")
    # thread: boost::make_signed/make_unsigned reach the thread GMF only via
    # atomic/detail/type_traits/make_signed.hpp, which pulls
    # boost/type_traits/make_signed.hpp only under BOOST_HAS_INT128 (under the
    # MSVC ABI it uses std::make_signed instead).
    # M11: boost.atomic may now claim them — best-effort.
    patch("src/gen_exports/thread.inc",
          "  using boost::make_signed;\n"
          "  using boost::make_strict_lock;",
          "#if defined(BOOST_HAS_INT128)\n"
          "  // M9 platform guard: boost::make_signed is declared only where\n"
          "  // BOOST_HAS_INT128 (atomic/detail/type_traits/make_signed.hpp); under the\n"
          "  // MSVC ABI the atomic headers use std::make_signed instead.\n"
          "  using boost::make_signed;\n"
          "#endif\n"
          "  using boost::make_strict_lock;",
          required=False)
    patch("src/gen_exports/thread.inc",
          "  using boost::make_unsigned;\n"
          "  using boost::memory_order;",
          "#if defined(BOOST_HAS_INT128)\n"
          "  using boost::make_unsigned;\n"
          "#endif\n"
          "  using boost::memory_order;",
          required=False)

    # M11: math — float80_t / float_fast80_t / float_least80_t are the
    # cstdfloat long-double typedefs (cstdfloat_types.hpp), declared only for
    # 80-bit long double (same condition family as the M9 decimal guard).
    for name in ["float80_t", "float_fast80_t", "float_least80_t"]:
        patch("src/gen_exports/math.inc",
              f"  using boost::{name};",
              f"#if LDBL_MANT_DIG == 64 && LDBL_MAX_EXP == 16384\n"
              f"  // M11 platform guard: cstdfloat_types.hpp declares the 80-bit long-double\n"
              f"  // typedefs only where long double really is 80-bit; MSVC long double is 53-bit.\n"
              f"  using boost::{name};\n"
              f"#endif")
    # M11 CI fix (POSIX llvm legs): the statistics parallel impls exist only
    # under BOOST_MATH_EXEC_COMPATIBLE (tools/config.hpp: requires
    # BOOST_MATH_NO_CXX17_HDR_EXECUTION to stay undefined — libc++ provides
    # <execution> without __cpp_lib_execution, so the macro is absent there),
    # while the MSVC/libstdc++ snapshot faces define it. Guard the three
    # affected using-lines with the exact upstream condition.
    for name in ["chatterjee_correlation_par_impl",
                 "correlation_coefficient_parallel_impl",
                 "means_and_covariance_parallel_impl"]:
        patch("src/gen_exports/math.inc",
              f"  using boost::math::statistics::detail::{name};",
              f"#if defined(BOOST_MATH_EXEC_COMPATIBLE)\n"
              f"  // M11 CI platform guard: statistics {name} is defined only under\n"
              f"  // BOOST_MATH_EXEC_COMPATIBLE (chatterjee_correlation.hpp /\n"
              f"  // bivariate_statistics.hpp); libc++ lacks __cpp_lib_execution.\n"
              f"  using boost::math::statistics::detail::{name};\n"
              f"#endif")
    # M11: iostreams — codecvt_impl exists only on the libstdc++/older-dinkumware
    # workaround paths (detail/codecvt_helper.hpp); MSVC STL declares neither.
    patch("src/gen_exports/iostreams.inc",
          "  using boost::iostreams::detail::codecvt_impl;",
          "#if defined(BOOST_IOSTREAMS_NO_PRIMARY_CODECVT_DEFINITION) || \\\n"
          "    defined(BOOST_IOSTREAMS_EMPTY_PRIMARY_CODECVT_DEFINITION) || \\\n"
          "    defined(BOOST_IOSTREAMS_NO_LOCALE)\n"
          "  // M11 platform guard: detail/codecvt_helper.hpp declares codecvt_impl only\n"
          "  // on these std::codecvt workaround paths (libstdc++ mingw snapshot); the\n"
          "  // MSVC STL takes none of them.\n"
          "  using boost::iostreams::detail::codecvt_impl;\n"
          "#endif")
    # M11: process — asio selects posix_thread when BOOST_ASIO_HAS_PTHREADS
    # (asio/detail/thread.hpp checks pthreads BEFORE windows; mingw-gcc defines
    # it via boost config's BOOST_HAS_PTHREADS). The MSVC flavor uses win_thread
    # and never declares posix_thread.
    # M12: boost.asio is a module of its own and claims all boost/asio/** files
    # (first-wins) — posix_thread moved to asio.inc; best-effort here.
    patch("src/gen_exports/process.inc",
          "  using boost::asio::detail::posix_thread;",
          "#if defined(BOOST_ASIO_HAS_PTHREADS)\n"
          "  // M11 platform guard: asio/detail/thread.hpp includes posix_thread.hpp only\n"
          "  // under BOOST_ASIO_HAS_PTHREADS (mingw snapshot); the MSVC flavor takes\n"
          "  // win_thread.\n"
          "  using boost::asio::detail::posix_thread;\n"
          "#endif",
          required=False)
    # M11 CI fix (POSIX legs): the process GMF includes ten windows-only headers
    # (v1/windows.hpp, v2/windows/*, windows/* launchers) — boost/winapi
    # basic_types.hpp #errors off-Windows, same reason as the M9 winapi.cppm
    # guard. The remaining GMF includes self-guard per-platform upstream.
    patch("src/process.cppm",
          "#include <boost/process/v1/extend.hpp>\n"
          "#include <boost/process/v1/windows.hpp>\n"
          "#include <boost/process/v2/windows/show_window.hpp>\n"
          "#include <boost/process/v2/windows/with_logon_launcher.hpp>\n"
          "#include <boost/process/v2/windows/with_token_launcher.hpp>\n"
          "#include <boost/process/windows/as_user_launcher.hpp>\n"
          "#include <boost/process/windows/creation_flags.hpp>\n"
          "#include <boost/process/windows/default_launcher.hpp>\n"
          "#include <boost/process/windows/show_window.hpp>\n"
          "#include <boost/process/windows/with_logon_launcher.hpp>\n"
          "#include <boost/process/windows/with_token_launcher.hpp>\n",
          "#include <boost/process/v1/extend.hpp>\n"
          "// M11 platform guard: v1/v2 windows launchers are Windows-only headers\n"
          "// (boost/winapi basic_types.hpp #errors off-Windows); M9 winapi.cppm\n"
          "// convention. POSIX face = platform-neutral + posix-self-guarded surface.\n"
          "#if defined(_WIN32) || defined(__CYGWIN__)\n"
          "#include <boost/process/v1/windows.hpp>\n"
          "#include <boost/process/v2/windows/show_window.hpp>\n"
          "#include <boost/process/v2/windows/with_logon_launcher.hpp>\n"
          "#include <boost/process/v2/windows/with_token_launcher.hpp>\n"
          "#include <boost/process/windows/as_user_launcher.hpp>\n"
          "#include <boost/process/windows/creation_flags.hpp>\n"
          "#include <boost/process/windows/default_launcher.hpp>\n"
          "#include <boost/process/windows/show_window.hpp>\n"
          "#include <boost/process/windows/with_logon_launcher.hpp>\n"
          "#include <boost/process/windows/with_token_launcher.hpp>\n"
          "#endif\n")
    # M11 CI fix (POSIX legs), second step: the mingw snapshot's GMF reached the
    # v2 core (basic_process) and the launcher detail helpers only through the
    # windows launcher chain; on POSIX include the cross-platform core and the
    # posix default launcher explicitly so the shared-surface `using` lines
    # resolve.
    patch("src/process.cppm",
          "#include <boost/process/windows/with_token_launcher.hpp>\n"
          "#endif\n\nexport module boost.process;",
          "#include <boost/process/windows/with_token_launcher.hpp>\n"
          "#endif\n"
          "// M11 platform guard (POSIX): the mingw snapshot's GMF reached the v2\n"
          "// core (basic_process) and the launcher detail helpers only through the\n"
          "// windows launcher chain; on POSIX include the cross-platform core and\n"
          "// the posix default launcher explicitly so the shared-surface `using`\n"
          "// lines resolve.\n"
          "#if !defined(_WIN32) && !defined(__CYGWIN__)\n"
          "#include <boost/process/v2/process.hpp>\n"
          "#include <boost/process/v2/posix/default_launcher.hpp>\n"
          "#endif\n\nexport module boost.process;")
    # M11 CI fix (POSIX legs): windows-only entities in process.inc — the
    # windows-flavored snapshot exports them, but their headers are only pulled
    # by the windows GMF branches above. Conditions mirror upstream:
    # asio windows services under BOOST_ASIO_WINDOWS (= _WIN32), process
    # v1/v2 windows detail under BOOST_WINDOWS_API (= _WIN32).
    # M12: win_object_handle_service is owned by boost.asio now (first-wins,
    # asio/detail/object_handle.hpp) — best-effort here.
    patch("src/gen_exports/process.inc",
          "  using boost::asio::detail::win_object_handle_service;",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: win_object_handle_service is the asio windows\n"
          "  // branch (BOOST_ASIO_WINDOWS); POSIX asio never declares it.\n"
          "  using boost::asio::detail::win_object_handle_service;\n"
          "#endif",
          required=False)
    patch("src/gen_exports/process.inc",
          "export namespace boost { namespace asio { namespace windows {\n"
          "  using boost::asio::windows::basic_object_handle;\n"
          "  using boost::asio::windows::basic_overlapped_handle;\n"
          "  using boost::asio::windows::basic_stream_handle;\n"
          "  using boost::asio::windows::object_handle;\n"
          "  using boost::asio::windows::stream_handle;\n"
          "}}}",
          "#if defined(_WIN32)\n"
          "export namespace boost { namespace asio { namespace windows {\n"
          "  // M11 platform guard: asio/windows/* handle types are Windows-only\n"
          "  // (BOOST_ASIO_WINDOWS); POSIX asio never declares them.\n"
          "  using boost::asio::windows::basic_object_handle;\n"
          "  using boost::asio::windows::basic_overlapped_handle;\n"
          "  using boost::asio::windows::basic_stream_handle;\n"
          "  using boost::asio::windows::object_handle;\n"
          "  using boost::asio::windows::stream_handle;\n"
          "}}}\n"
          "#endif",
          required=False)
    patch("src/gen_exports/process.inc",
          "export namespace boost { namespace process { namespace v1 { namespace detail { namespace windows {\n"
          "  using boost::process::v1::detail::windows::apply_out_handles;",
          "#if defined(_WIN32)\n"
          "export namespace boost { namespace process { namespace v1 { namespace detail { namespace windows {\n"
          "  // M11 platform guard: v1 detail windows impls (incl. the NT workaround\n"
          "  // block below) are declared only by the windows GMF branches.\n"
          "  using boost::process::v1::detail::windows::apply_out_handles;")
    patch("src/gen_exports/process.inc",
          "  using boost::process::v1::detail::windows::workaround::set_information_job_object;\n"
          "}}}}}}\n",
          "  using boost::process::v1::detail::windows::workaround::set_information_job_object;\n"
          "}}}}}}\n"
          "#endif\n")
    patch("src/gen_exports/process.inc",
          "  using boost::process::v2::detail::basic_process_handle_win;",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: basic_process_handle_win is the windows variant\n"
          "  // (detail/process_handle_windows.hpp); POSIX takes process_handle_fd.\n"
          "  using boost::process::v2::detail::basic_process_handle_win;\n"
          "#endif")
    patch("src/gen_exports/process.inc",
          "  using boost::process::v2::detail::open_process_;",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: open_process_ lives in detail/process_handle_windows.hpp.\n"
          "  using boost::process::v2::detail::open_process_;\n"
          "#endif")
    # M11 CI fix (POSIX legs): the process_handle_windows detail helpers have no
    # fd-variant counterparts (basic_process_handle_fd implements them inline);
    # is_exec_type is in detail/environment_win.hpp. All Windows-only.
    for name in ["check_handle_", "check_pid_", "check_running_", "get_exit_code_",
                 "interrupt_", "request_exit_", "resume_", "suspend_",
                 "terminate_", "terminate_if_running_"]:
        patch("src/gen_exports/process.inc",
              f"  using boost::process::v2::detail::{name};",
              f"#if defined(_WIN32)\n  // M11 platform guard: {name} lives in detail/process_handle_windows.hpp (no fd-variant counterpart).\n  using boost::process::v2::detail::{name};\n#endif")
    patch("src/gen_exports/process.inc",
          "  using boost::process::v2::environment::detail::is_exec_type;",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: is_exec_type lives in detail/environment_win.hpp;\n"
          "  // POSIX environment detail does not declare it.\n"
          "  using boost::process::v2::environment::detail::is_exec_type;\n"
          "#endif")
    # M11 CI fix (POSIX legs): the generic-launcher initializer machinery
    # (probe/invoke/has_* + all_are_initializers/is_initializer + base/derived)
    # is flat in boost::process::v2::detail on Windows (windows/default_launcher.hpp)
    # but nested under v2::posix::detail with a different name set on POSIX
    # (fork-based launchers have no initializer-probe support), so these shared
    # .inc lines only resolve on Windows.
    for name in ["all_are_initializers", "base", "derived",
                 "has_on_error", "has_on_setup", "has_on_success",
                 "invoke_on_error", "invoke_on_setup", "invoke_on_success",
                 "is_initializer", "on_error", "on_setup", "on_success",
                 "probe_on_error", "probe_on_setup", "probe_on_success"]:
        patch("src/gen_exports/process.inc",
              f"  using boost::process::v2::detail::{name};",
              f"#if defined(_WIN32)\n  // M11 platform guard: {name} is the windows generic-launcher machinery (flat v2::detail); POSIX nests a different set under v2::posix::detail.\n  using boost::process::v2::detail::{name};\n#endif")
    patch("src/gen_exports/process.inc",
          "export namespace boost { namespace process { namespace v2 { namespace windows {\n"
          "  using boost::process::v2::windows::as_user_launcher;\n"
          "  using boost::process::v2::windows::default_launcher;\n"
          "  using boost::process::v2::windows::process_creation_flags;\n"
          "  using boost::process::v2::windows::process_show_window;\n"
          "  using boost::process::v2::windows::with_logon_launcher;\n"
          "  using boost::process::v2::windows::with_token_launcher;\n"
          "}}}}",
          "#if defined(_WIN32)\n"
          "export namespace boost { namespace process { namespace v2 { namespace windows {\n"
          "  // M11 platform guard: v2 windows launchers are Windows-only headers.\n"
          "  using boost::process::v2::windows::as_user_launcher;\n"
          "  using boost::process::v2::windows::default_launcher;\n"
          "  using boost::process::v2::windows::process_creation_flags;\n"
          "  using boost::process::v2::windows::process_show_window;\n"
          "  using boost::process::v2::windows::with_logon_launcher;\n"
          "  using boost::process::v2::windows::with_token_launcher;\n"
          "}}}}\n"
          "#endif")

    # M11: graph — graph's bundle transitively pulls multiprecision/proto/
    # serialization interop headers; their directive-expansion/injection
    # leaks export entities that the MSVC ABI never declares (BOOST_HAS_INT128
    # is off under the clang-msvc flavor; proto's extended-template matching is
    # gcc-specific). Guards mirror the upstream header conditions.
    for name in ["int128_type", "uint128_type"]:
        patch("src/gen_exports/graph.inc",
              f"  using boost::multiprecision::{name};",
              f"#if defined(BOOST_HAS_INT128)\n  // M11 platform guard: standalone_config.hpp declares multiprecision::{name} only under BOOST_HAS_INT128 (off under the clang-msvc flavor).\n  using boost::multiprecision::{name};\n#endif",
              required=False)  # M12: entity owned by boost.multiprecision now
    for name in ["template_arity", "template_arity_helper", "template_arity_impl2"]:
        patch("src/gen_exports/graph.inc",
              f"  using boost::proto::detail::{name};",
              f"#if defined(BOOST_PROTO_EXTENDED_TEMPLATE_PARAMETERS_MATCHING)\n  // M11 platform guard: proto/detail/template_arity.hpp declares {name} only under\n  // BOOST_PROTO_EXTENDED_TEMPLATE_PARAMETERS_MATCHING (gcc extended-template matching).\n  using boost::proto::detail::{name};\n#endif")
    for name in ["divide_subtract", "divide_unsigned_helper"]:
        patch("src/gen_exports/graph.inc",
              f"  using boost::multiprecision::backends::{name};",
              f"#if defined(BOOST_HAS_INT128)\n  // M11 platform guard: the cpp_int divide helpers take double_limb_type (= __int128)\n  // and are declared only under BOOST_HAS_INT128 (off under the clang-msvc flavor).\n  using boost::multiprecision::backends::{name};\n#endif",
              required=False)  # M12: entity owned by boost.multiprecision now
    for name in ["divide_subtract", "int128_type", "uint128_type"]:
        patch("src/gen_exports/graph.inc",
              f"  using boost::serialization::cpp_int_detail::{name};",
              f"#if defined(BOOST_HAS_INT128)\n  // M11 platform guard: the cpp_int interop surface exists only under BOOST_HAS_INT128\n  // (multiprecision detail; off under the clang-msvc flavor).\n  using boost::serialization::cpp_int_detail::{name};\n#endif",
              required=False)  # M12: entity owned by boost.multiprecision now
    # M11 CI fix (macos-llvm leg): addcarry_limb / subborrow_limb live in
    # boost/multiprecision/cpp_int/intel_intrinsics.hpp under the
    # BOOST_MP_HAS_IMMINTRIN_H gate. On macOS arm64 (clang) the macro is unset
    # (no __builtin_ia32_addcarryx_u64, BOOST_GCC not defined), so the symbols
    # are not declared; the mingw-snapshot .inc (parsed on Linux x86_64 where
    # the macro is set) still emits `using ...::addcarry_limb;` and the macOS
    # module compile then errors "no member named 'addcarry_limb' in namespace
    # 'boost::multiprecision::detail'". Mirror the upstream macro exactly.
    patch("src/gen_exports/graph.inc",
          "  using boost::multiprecision::detail::addcarry_limb;\n  using boost::multiprecision::detail::arg_type;",
          "#if defined(BOOST_MP_HAS_IMMINTRIN_H)\n"
          "  // M11 platform guard: cpp_int/intel_intrinsics.hpp declares addcarry_limb\n"
          "  // only under BOOST_MP_HAS_IMMINTRIN_H (the adc intrinsics dispatch — clang on\n"
          "  // macOS arm64 unsets the macro because __builtin_ia32_addcarryx_u64 is a\n"
          "  // gcc-only builtin and BOOST_GCC is not defined).\n"
          "  using boost::multiprecision::detail::addcarry_limb;\n"
          "#endif\n"
          "  using boost::multiprecision::detail::arg_type;",
          required=False)  # M12: entity owned by boost.multiprecision now
    patch("src/gen_exports/graph.inc",
          "  using boost::multiprecision::detail::subborrow_limb;\n  using boost::multiprecision::detail::subtract_immediates;",
          "#if defined(BOOST_MP_HAS_IMMINTRIN_H)\n"
          "  // M11 platform guard: cpp_int/intel_intrinsics.hpp declares subborrow_limb\n"
          "  // only under BOOST_MP_HAS_IMMINTRIN_H (see addcarry_limb guard for rationale).\n"
          "  using boost::multiprecision::detail::subborrow_limb;\n"
          "#endif\n"
          "  using boost::multiprecision::detail::subtract_immediates;",
          required=False)  # M12: entity owned by boost.multiprecision now
    # M12 CI fix (macos-llvm leg): multiprecision.inc itself now emits the bare
    # addcarry_limb / subborrow_limb using-lines (M12 moved the entity from the
    # graph face to boost.multiprecision) — apply the same
    # BOOST_MP_HAS_IMMINTRIN_H guards there (see the graph.inc rationale above).
    patch("src/gen_exports/multiprecision.inc",
          "  using boost::multiprecision::detail::addcarry_limb;\n  using boost::multiprecision::detail::arg_type;",
          "#if defined(BOOST_MP_HAS_IMMINTRIN_H)\n"
          "  // M11 platform guard: cpp_int/intel_intrinsics.hpp declares addcarry_limb\n"
          "  // only under BOOST_MP_HAS_IMMINTRIN_H (the adc intrinsics dispatch — clang on\n"
          "  // macOS arm64 unsets the macro because __builtin_ia32_addcarryx_u64 is a\n"
          "  // gcc-only builtin and BOOST_GCC is not defined).\n"
          "  using boost::multiprecision::detail::addcarry_limb;\n"
          "#endif\n"
          "  using boost::multiprecision::detail::arg_type;")
    patch("src/gen_exports/multiprecision.inc",
          "  using boost::multiprecision::detail::subborrow_limb;\n  using boost::multiprecision::detail::subtract_immediates;",
          "#if defined(BOOST_MP_HAS_IMMINTRIN_H)\n"
          "  // M11 platform guard: cpp_int/intel_intrinsics.hpp declares subborrow_limb\n"
          "  // only under BOOST_MP_HAS_IMMINTRIN_H (see addcarry_limb guard for rationale).\n"
          "  using boost::multiprecision::detail::subborrow_limb;\n"
          "#endif\n"
          "  using boost::multiprecision::detail::subtract_immediates;")

    # M11: charconv — the mingw snapshot exports entities the MSVC ABI never
    # declares (mirrors the M9 decimal guards):
    # ieee754_binary80: bit_layouts.hpp defines it only for 80-bit long double
    # (MSVC long double is 53-bit); to_chars128: to_chars_integer_impl.hpp
    # declares it only under BOOST_CHARCONV_HAS_INT128.
    patch("src/gen_exports/charconv.inc",
          "  using boost::charconv::detail::ieee754_binary80;",
          "#if LDBL_MANT_DIG == 64 && LDBL_MAX_EXP == 16384\n"
          "  // M11 platform guard: bit_layouts.hpp defines ieee754_binary80 only for\n"
          "  // 80-bit long double (x86-64 gcc/mingw); MSVC long double is 53-bit.\n"
          "  using boost::charconv::detail::ieee754_binary80;\n"
          "#endif")
    patch("src/gen_exports/charconv.inc",
          "  using boost::charconv::detail::to_chars128;\n",
          "#if defined(BOOST_CHARCONV_HAS_INT128)\n"
          "  // M11 platform guard: to_chars128 exists only under BOOST_CHARCONV_HAS_INT128\n"
          "  // (to_chars_integer_impl.hpp).\n"
          "  using boost::charconv::detail::to_chars128;\n"
          "#endif\n")

    # M9: pfr — clang_wrapper_t is the clang-only NTTP wrapper
    # (core_name20_static.hpp #ifdef __clang__ branch; gcc takes the #else
    # make_clang_wrapper that returns arg directly). fields_count_dispatch_impl
    # exists only under the C++26 reflection / structured-bindings branches
    # (fields_count.hpp), which the C++23 CI compilers don't activate.
    patch("src/gen_exports/pfr.inc",
          "  using boost::pfr::detail::clang_wrapper_t;",
          "#if defined(__clang__)\n"
          "  // M9 platform guard: clang_wrapper_t is the clang-only NTTP wrapper\n"
          "  // (core_name20_static.hpp #ifdef __clang__ branch).\n"
          "  using boost::pfr::detail::clang_wrapper_t;\n"
          "#endif")
    patch("src/gen_exports/pfr.inc",
          "  using boost::pfr::detail::fields_count_dispatch_impl;",
          "#if BOOST_PFR_USE_CPP26_REFLECTION || BOOST_PFR_USE_CPP26\n"
          "  // M9 platform guard: fields_count_dispatch_impl exists only under the\n"
          "  // C++26 reflection / structured-bindings branches (fields_count.hpp).\n"
          "  using boost::pfr::detail::fields_count_dispatch_impl;\n"
          "#endif")

    # M9: uuid — the SIMD/x86 from_chars/to_chars entities live in
    # from_chars_x86.hpp / to_chars_x86.hpp / uuid_x86.ipp / simd_vector.hpp,
    # all included under BOOST_UUID_USE_SSE2 (config.hpp: __GNUC__ && __SSE2__,
    # or MSVC _M_X64). Absent on macOS arm64 (no __SSE2__).
    # M11: iostreams — boost/iostreams/filter/regex.hpp is curated out of the
    # module GMF (its boost::regex dependency trips the gcc 16.1 module
    # abi-tag streaming bug in cpp_regex_traits); drop the GMF include and the
    # regex filter exports. Best-effort: a regen from the curated libs.json
    # produces neither.
    patch("src/iostreams.cppm",
          "#include <boost/iostreams/filter/regex.hpp>\n",
          "// M11: filter/regex.hpp curated out of the GMF — the cpp_regex_traits\n"
          "// abi-tag streaming bug (gcc 16.1); consumers include it themselves.\n",
          required=False)
    patch("src/iostreams.cppm",
          "export import boost.regex;\n",
          "// M11: stale boost.regex import removed with filter/{regex,grep}.hpp\n"
          "// curation (gcc 16.1 cpp_regex_traits abi-tag streaming bug).\n",
          required=False)
    for name in ["basic_regex_filter", "regex_filter", "wregex_filter"]:
        patch("src/gen_exports/iostreams.inc",
              f"  using boost::iostreams::{name};\n",
              f"  // M11: {name} dropped — declared only via filter/regex.hpp (curated\n"
              f"  // out of the module GMF; gcc 16.1 abi-tag streaming bug).\n",
              required=False)
    # C1 (2026-09-06): test.cppm / gen_exports/test.inc are gone (boost.test
    # downgraded to compiled include-only, feature renamed
    # unit_test_framework) — the M11 test-module curation anchors above the
    # data/test_case.hpp patch were removed with them. The vendored test
    # header patches (print_helper / basic_cstring / modifier /
    # token_iterator) stay: they benefit BOTH consumption forms (compiled
    # framework TUs and the included/* aggregate).
    # M11: io — boost/io/ostream_put.hpp is curated out of the io module GMF:
    # its function-local unnamed enum (buffer_fill) streamed from two module
    # CMIs (boost.io + boost.utility via string_view) mismatches on gcc 16.1.
    # Nothing from it appears in io.inc.
    # M11: graph — multiprecision detail unmentionable placeholders have no
    # external linkage; gcc refuses the export.
    for name in ["unmentionable", "unmentionable_type"]:
        patch("src/gen_exports/graph.inc",
              f"  using boost::multiprecision::detail::{name};\n",
              f"  // M11: {name} dropped — no external linkage (multiprecision detail\n"
              f"  // placeholder); gcc refuses the export.\n",
              required=False)
    # M11: io — boost/io/ostream_put.hpp is curated out of the io module GMF:
    # its function-local unnamed enum (buffer_fill) streamed from two module
    # CMIs (boost.io + boost.utility via string_view) mismatches on gcc 16.1.
    # Nothing from it appears in io.inc. NB: runs after the git restores below
    # in file order? No — placed after them via main() ordering: keep it here
    # only if the restore list does not include io.cppm (it does not).
    patch("src/io.cppm",
          "#include <boost/io/ostream_put.hpp>\n",
          "// M11: ostream_put.hpp curated out of the io module GMF — its\n"
          "// buffer_fill enum mismatches between the boost.io/boost.utility CMIs\n"
          "// on gcc 16.1; consumers include the header themselves.\n",
          required=False)
    for name in ["basic_grep_filter", "grep_filter", "wgrep_filter"]:
        patch("src/gen_exports/iostreams.inc",
              f"  using boost::iostreams::{name};\n",
              f"  // M11: {name} dropped — declared only via filter/grep.hpp (curated\n"
              f"  // out of the module GMF; same gcc 16.1 regex traits bug).\n",
              required=False)
    # M11: utility — boost/utility/string_ref.hpp (deprecated upstream) pulls
    # boost/io/detail/buffer_fill.hpp whose unnamed enum mismatches between the
    # boost.io and boost.utility BMIs on gcc 16.1. Curated out of the module
    # GMF; drop the include and the string_ref exports.
    patch("src/utility.cppm",
          "#include <boost/utility/string_ref.hpp>\n",
          "// M11: string_ref.hpp curated out of the GMF — its buffer_fill enum\n"
          "// mismatches between the boost.io/boost.utility BMIs on gcc 16.1;\n"
          "// consumers include the deprecated header themselves.\n",
          required=False)
    for name in ["basic_string_ref", "string_ref", "u16string_ref",
                 "u32string_ref", "wstring_ref"]:
        patch("src/gen_exports/utility.inc",
              f"  using boost::{name};\n",
              f"  // M11: {name} dropped — declared only via string_ref.hpp (curated out of\n"
              f"  // the module GMF; gcc 16.1 buffer_fill enum mismatch).\n",
              required=False)
    patch("src/gen_exports/utility.inc",
          "  using boost::detail::string_ref_traits_eq;\n",
          "  // M11: string_ref_traits_eq dropped — string_ref.hpp curated out of the GMF.\n",
          required=False)
    # C1 (2026-09-06): the remaining M11 test-module anchors (minimal.hpp /
    # utils/timer.hpp / boost::detail::execution_monitor family) were removed
    # together with src/test.cppm — see the note above.

    # M11: atomic — the mingw snapshot exports boost::is_integral/is_signed/
    # make_signed/make_unsigned (atomic/detail/type_traits/*.hpp use the
    # Boost.TypeTraits versions only under BOOST_HAS_INT128; the MSVC ABI takes
    # the std:: versions and never declares the boost:: ones) plus the
    # gcc-only backends (convert_memory_order_to_gcc, *_gcc_atomic,
    # *_gcc_x86 — same conditions as the M4/M7 thread.inc guards).
    patch("src/gen_exports/atomic.inc",
          "  using boost::is_integral;\n"
          "  using boost::is_signed;",
          "#if defined(BOOST_HAS_INT128)\n"
          "  // M11 platform guard: atomic/detail/type_traits/is_integral.hpp (and\n"
          "  // is_signed) pull the boost:: trait only under BOOST_HAS_INT128 (libstdc++\n"
          "  // __int128 workaround); the MSVC ABI takes the std:: trait instead.\n"
          "  using boost::is_integral;\n"
          "  using boost::is_signed;\n"
          "#endif")
    patch("src/gen_exports/atomic.inc",
          "  using boost::make_signed;\n"
          "  using boost::make_unsigned;\n"
          "  using boost::memory_order;\n"
          "  using boost::memory_order_acq_rel;",
          "#if defined(BOOST_HAS_INT128)\n"
          "  // M11 platform guard: atomic/detail/type_traits/make_signed.hpp — as above.\n"
          "  using boost::make_signed;\n"
          "  using boost::make_unsigned;\n"
          "#endif\n"
          "  using boost::memory_order;\n"
          "  using boost::memory_order_acq_rel;")
    for name in ["convert_memory_order_to_gcc",
                 "core_operations_gcc_atomic",
                 "fence_operations_gcc_atomic"]:
        patch("src/gen_exports/atomic.inc",
              f"  using boost::atomics::detail::{name};",
              f"#if defined(__GNUC__)\n  // M11 platform guard: gcc-only branch of boost/atomic (snapshot = mingw flavor).\n  using boost::atomics::detail::{name};\n#endif")
    for name in ["core_arch_operations_gcc_x86",
                 "core_arch_operations_gcc_x86_base",
                 "fence_arch_operations_gcc_x86"]:
        patch("src/gen_exports/atomic.inc",
              f"  using boost::atomics::detail::{name};",
              f"#if defined(__GNUC__) && (defined(__i386__) || defined(__x86_64__))\n  // M11 platform guard: gcc_x86 backend of boost/atomic (platform.hpp); x86 only.\n  using boost::atomics::detail::{name};\n#endif")
    # M11: wait_operations_windows lives in wait_ops_windows.hpp, which
    # platform.hpp includes only under BOOST_WINDOWS (wait backend = windows);
    # POSIX takes futex/darwin_ulock/generic and never declares it. Same entity
    # the M6 thread.inc guard carried before it migrated to atomic.inc.
    patch("src/gen_exports/atomic.inc",
          "  using boost::atomics::detail::wait_operations_windows;",
          "#if defined(BOOST_WINDOWS)\n"
          "  // M11 platform guard: wait_ops_windows.hpp (wait backend = windows,\n"
          "  // platform.hpp BOOST_WINDOWS); POSIX uses futex/darwin_ulock/generic.\n"
          "  using boost::atomics::detail::wait_operations_windows;\n"
          "#endif")
    # M11: container — win_critical_section lives in the non-pthread branch of
    # container/detail/thread_mutex.hpp (POSIX takes the BOOST_HAS_PTHREADS
    # pthread_mutex branch), and the whole boost::container_winapi block
    # (DWORD_/BOOL_/::SleepEx) is declared only under the
    # _WIN32/__WIN32__/WIN32 spin-lock-yield branch of container/detail/mutex.hpp.
    patch("src/gen_exports/container.inc",
          "  using boost::container::dtl::win_critical_section;\n",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: win_critical_section is the non-pthread branch\n"
          "  // of container/detail/thread_mutex.hpp; POSIX uses pthread_mutex.\n"
          "  using boost::container::dtl::win_critical_section;\n"
          "#endif\n")
    patch("src/gen_exports/container.inc",
          "export namespace boost { namespace container_winapi {\n"
          "  using ::SleepEx;\n"
          "  using boost::container_winapi::BOOL_;\n"
          "  using boost::container_winapi::DWORD_;\n"
          "}}",
          "#if defined(_WIN32)\n"
          "export namespace boost { namespace container_winapi {\n"
          "  // M11 platform guard: container_winapi DWORD_/BOOL_/SleepEx are\n"
          "  // declared only in the _WIN32 branch of container/detail/mutex.hpp.\n"
          "  using ::SleepEx;\n"
          "  using boost::container_winapi::BOOL_;\n"
          "  using boost::container_winapi::DWORD_;\n"
          "}}\n"
          "#endif")
    # M11: date_time — time_from_ftime (date_time/filetime_functions.hpp) and
    # posix_time::from_ftime (posix_time/conversion.hpp) exist only under
    # BOOST_HAS_FTIME (win32 FILETIME); same entities the M6 thread.inc guard
    # carried before them.
    guard_entity_lines("src/gen_exports/date_time.inc", "defined(_WIN32)", [
        "time_from_ftime",
        "from_ftime",
    ])
    # M11 CI fix (POSIX legs): nowide — the mingw snapshot's GMF reached
    # cstdio/stackstring/convert entities only through windows-flavored
    # transitive includes; add the cross-platform headers explicitly. The
    # console machinery and detail::stat are BOOST_WINDOWS branches upstream
    # (POSIX nowide uses std:: streams and ::stat directly) — guard those.
    patch("src/nowide.cppm",
          "#include <boost/nowide/iostream.hpp>\n#include <boost/nowide/quoted.hpp>",
          "#include <boost/nowide/iostream.hpp>\n"
          "// M11 platform guard (POSIX): cstdio/stackstring/convert were reached\n"
          "// only via windows-flavored transitive includes in the mingw snapshot;\n"
          "// include the cross-platform headers explicitly so the shared-surface\n"
          "// `using` lines resolve.\n"
          "#include <boost/nowide/cstdio.hpp>\n"
          "#include <boost/nowide/stackstring.hpp>\n"
          "#include <boost/nowide/convert.hpp>\n"
          "#include <boost/nowide/quoted.hpp>")
    for name in ["console_input_buffer", "console_output_buffer"]:
        patch("src/gen_exports/nowide.inc",
              f"  using boost::nowide::detail::{name};",
              f"#if defined(_WIN32)\n  // M11 platform guard: {name} is the windows console machinery (detail/console_buffer.hpp); POSIX nowide uses std:: streams directly.\n  using boost::nowide::detail::{name};\n#endif")
    for name in ["winconsole_istream", "winconsole_ostream"]:
        patch("src/gen_exports/nowide.inc",
              f"  using boost::nowide::detail::{name};",
              f"#if defined(_WIN32)\n  // M11 platform guard: {name} is the windows console stream branch of iostream.hpp; POSIX takes std:: streams directly.\n  using boost::nowide::detail::{name};\n#endif")
    patch("src/gen_exports/nowide.inc",
          "  using boost::nowide::detail::stat;",
          "#if defined(_WIN32)\n"
          "  // M11 platform guard: detail::stat is the BOOST_WINDOWS branch of\n"
          "  // stat.hpp; POSIX exposes ::stat via a using-declaration instead.\n"
          "  using boost::nowide::detail::stat;\n"
          "#endif")
    # C1 (2026-09-06): the log module anchors (strip_log_version_namespace,
    # src/log.cppm POSIX GMF guards, src/gen_exports/log.inc platform guards)
    # are gone with src/log.cppm — boost.log is compiled include-only now
    # (LIBS_COMPILED_INCLUDE_ONLY), consumers #include <boost/log/...> and
    # link the feature's library TUs. The simple_event_log.h vendored stub
    # below stays: the windows log TUs still need it.
    # M11 CI fix (POSIX legs): cobalt — the mingw snapshot's GMF reached the
    # asio reactor / hash_map detail headers only through windows-flavored
    # chains (cobalt on POSIX selects epoll, so select_reactor.hpp et al. were
    # never included); include the cross-platform headers explicitly so the
    # shared-surface `using` lines resolve on POSIX (they are redundant but
    # harmless on Windows).
    patch("src/cobalt.cppm",
          "#include <boost/cobalt.hpp>\n#include <boost/cobalt/composition.hpp>",
          "#include <boost/cobalt.hpp>\n"
          "// M11 platform guard (POSIX): asio reactor/hash_map details were only\n"
          "// reached through windows-flavored chains in the mingw snapshot (POSIX\n"
          "// cobalt selects the epoll reactor); include them explicitly so the\n"
          "// shared-surface `using` lines resolve.\n"
          "#include <boost/asio/detail/hash_map.hpp>\n"
          "#include <boost/asio/detail/null_reactor.hpp>\n"
          "#include <boost/asio/detail/select_reactor.hpp>\n"
          "#include <boost/cobalt/composition.hpp>",
          required=False)
    # M11 CI fix (POSIX legs) 2/2: fd_set_adapter / reactor_op_queue /
    # socket_select_interrupter are per-OS-selected headers with no outer
    # platform guard; null_reactor.hpp and select_reactor.hpp self-guard empty
    # on the epoll/kqueue paths (their entities are guarded _WIN32 in the
    # .inc instead).
    patch("src/cobalt.cppm",
          "#include <boost/asio/detail/select_reactor.hpp>\n#include <boost/cobalt/composition.hpp>",
          "#include <boost/asio/detail/select_reactor.hpp>\n"
          "// fd_set_adapter / reactor_op_queue / socket_select_interrupter are\n"
          "// per-OS-selected headers with no outer platform guard; the reactor\n"
          "// headers above self-guard empty on the epoll/kqueue paths (their\n"
          "// entities are guarded _WIN32 in the .inc instead).\n"
          "#include <boost/asio/detail/fd_set_adapter.hpp>\n"
          "#include <boost/asio/detail/reactor_op_queue.hpp>\n"
          "#include <boost/asio/detail/socket_select_interrupter.hpp>\n"
          "#include <boost/cobalt/composition.hpp>",
          required=False)
    # Windows-only asio surface: IOCP/file backends, winsock init, APC, and the
    # win_* detail family (asio/detail/config.hpp BOOST_ASIO_HAS_FILE is
    # windows-random-access-handle / io_uring only; the posix signal blocker
    # replaces null_signal_blocker).
    guard_entity_lines("src/gen_exports/cobalt.inc", "defined(BOOST_ASIO_HAS_FILE)", [
        "basic_file",
        "basic_random_access_file",
        "basic_stream_file",
        "file_base",
    ])
    guard_entity_lines("src/gen_exports/cobalt.inc", "defined(_WIN32)", [
        "apc_function",
        "null_reactor",
        "select_reactor",
        "null_signal_blocker",
        "socket_select_interrupter",
        "win_event",
        "win_fd_set_adapter",
        "win_global",
        "win_global_impl",
        "win_iocp_file_service",
        "win_iocp_handle_read_op",
        "win_iocp_handle_service",
        "win_iocp_handle_write_op",
        "win_iocp_io_context",
        "win_iocp_null_buffers_op",
        "win_iocp_operation",
        "win_iocp_overlapped_ptr",
        "win_iocp_serial_port_service",
        "win_iocp_socket_accept_op",
        "win_iocp_socket_connect_op",
        "win_iocp_socket_connect_op_base",
        "win_iocp_socket_move_accept_op",
        "win_iocp_socket_recv_op",
        "win_iocp_socket_recvfrom_op",
        "win_iocp_socket_recvmsg_op",
        "win_iocp_socket_send_op",
        "win_iocp_socket_service",
        "win_iocp_socket_service_base",
        "win_iocp_thread_info",
        "win_iocp_wait_op",
        "win_mutex",
        "win_static_mutex",
        "win_thread",
        "win_thread_base",
        "win_thread_function",
        "winsock_init",
        "winsock_init_base",
        "win_iocp_overlapped_op",
        "win_object_handle_service",
        "basic_object_handle",
        "basic_overlapped_handle",
        "basic_random_access_handle",
        "basic_stream_handle",
        "object_handle",
        "overlapped_handle",
        "overlapped_ptr",
        "random_access_handle",
        "stream_handle",
        "complete_iocp_accept",
        "complete_iocp_connect",
        "complete_iocp_recv",
        "complete_iocp_recvfrom",
        "complete_iocp_recvmsg",
        "complete_iocp_send",
        "msghdr",
    ])
    # C1 (2026-09-06): the log.inc _WIN32 guard blocks (is_debugger_present,
    # event-log sinks, spirit decode_utf16) are gone with gen_exports/log.inc —
    # see the note above.

    guard_entity_lines("src/gen_exports/uuid.inc", "defined(BOOST_UUID_USE_SSE2)", [
        "compare",
        "countr_zero_nz",
        "from_chars_simd",
        "from_chars_simd_char_constants",
        "from_chars_simd_constants",
        "from_chars_simd_core",
        "from_chars_simd_load_traits",
        "simd_vector",
        "simd_vector128",
        "simd_vector256",
        "simd_vector512",
        "to_chars_simd",
        "to_chars_simd_char_constants",
        "to_chars_simd_constants",
        "to_chars_simd_core",
    ])

    # M9: signals2 — critical_section / critical_section_debug /
    # rtl_critical_section live in lwm_win32_cs.hpp, included only under
    # BOOST_HAS_WINTHREADS (mutex.hpp selector); POSIX takes lwm_pthreads.hpp.
    guard_entity_lines("src/gen_exports/signals2.inc", "defined(BOOST_HAS_WINTHREADS)", [
        "critical_section",
        "critical_section_debug",
        "rtl_critical_section",
    ])

    # M9: safe_numerics — the TU-local anonymous-class error_category singleton
    # (exception.hpp) is fixed at the vendored header (class named
    # safe_numerics_error_category_t); make_error_code is exported on all
    # platforms. No .inc guard needed.

    # M9: dll — last_error_code lives in detail/windows/path_from_handle.hpp
    # (no POSIX equivalent); the POSIX GMF never includes it.
    patch("src/gen_exports/dll.inc",
          "  using boost::dll::detail::last_error_code;",
          "#if defined(_WIN32)\n"
          "  // M9 platform guard: last_error_code is in detail/windows/\n"
          "  // path_from_handle.hpp (no POSIX counterpart).\n"
          "  using boost::dll::detail::last_error_code;\n"
          "#endif")

    # M9: bloom — m128ix2 lives in detail/fast_multiblock32_sse2.hpp, included
    # only under BOOST_BLOOM_SSE2 (detail/sse2.hpp: __SSE2__ && x86). Absent on
    # macOS arm64 (no __SSE2__; NEON branch active instead).
    patch("src/gen_exports/bloom.inc",
          "  using boost::bloom::detail::m128ix2;",
          "#if defined(BOOST_BLOOM_SSE2)\n"
          "  // M9 platform guard: m128ix2 is the SSE2 branch of fast_multiblock32\n"
          "  // (detail/sse2.hpp, __SSE2__); absent on arm64 (NEON branch).\n"
          "  using boost::bloom::detail::m128ix2;\n"
          "#endif")

    # M12: hana — the ext::boost adapter tags (tuple_tag, fusion::*_tag,
    # mpl::*_tag) sit in namespaces named `boost` nested inside boost::hana::ext.
    # The generated qualified using-lines (`using boost::hana::ext::boost::...;`)
    # resolve `boost` to the innermost shadowing namespace (hana::ext::boost) and
    # fail with "'hana' is not a class, namespace, or enumeration". Root-qualify
    # them with a leading `::` so the using-declaration resolves from the global
    # scope (the injected name in hana::ext::boost is unchanged).
    patch("src/gen_exports/hana.inc",
          "  using boost::hana::ext::boost::tuple_tag;\n}}}}",
          "  using ::boost::hana::ext::boost::tuple_tag;\n}}}}")
    patch("src/gen_exports/hana.inc",
          "  using boost::hana::ext::boost::fusion::deque_tag;\n"
          "  using boost::hana::ext::boost::fusion::list_tag;\n"
          "  using boost::hana::ext::boost::fusion::tuple_tag;\n"
          "  using boost::hana::ext::boost::fusion::vector_tag;",
          "  using ::boost::hana::ext::boost::fusion::deque_tag;\n"
          "  using ::boost::hana::ext::boost::fusion::list_tag;\n"
          "  using ::boost::hana::ext::boost::fusion::tuple_tag;\n"
          "  using ::boost::hana::ext::boost::fusion::vector_tag;")
    patch("src/gen_exports/hana.inc",
          "  using boost::hana::ext::boost::mpl::integral_c_tag;\n"
          "  using boost::hana::ext::boost::mpl::list_tag;\n"
          "  using boost::hana::ext::boost::mpl::vector_tag;",
          "  using ::boost::hana::ext::boost::mpl::integral_c_tag;\n"
          "  using ::boost::hana::ext::boost::mpl::list_tag;\n"
          "  using ::boost::hana::ext::boost::mpl::vector_tag;")
    # Same shadowing from inside hana::ext::std: unqualified `boost` lookup
    # walks out to hana::ext, which has a member namespace `boost`.
    patch("src/gen_exports/hana.inc",
          "  using boost::hana::ext::std::array_tag;\n"
          "  using boost::hana::ext::std::integer_sequence_tag;\n"
          "  using boost::hana::ext::std::integral_constant_tag;\n"
          "  using boost::hana::ext::std::pair_tag;\n"
          "  using boost::hana::ext::std::ratio_tag;\n"
          "  using boost::hana::ext::std::tuple_tag;\n"
          "  using boost::hana::ext::std::vector_tag;",
          "  using ::boost::hana::ext::std::array_tag;\n"
          "  using ::boost::hana::ext::std::integer_sequence_tag;\n"
          "  using ::boost::hana::ext::std::integral_constant_tag;\n"
          "  using ::boost::hana::ext::std::pair_tag;\n"
          "  using ::boost::hana::ext::std::ratio_tag;\n"
          "  using ::boost::hana::ext::std::tuple_tag;\n"
          "  using ::boost::hana::ext::std::vector_tag;")

    # M12: multiprecision — the mingw snapshot carries entities the MSVC ABI
    # never declares (mirrors the M11 graph.inc guards):
    #  - int128_type/uint128_type: detail/standalone_config.hpp defines them only
    #    under BOOST_HAS_INT128 (off under the clang-msvc flavor);
    #  - backends::divide_subtract/divide_unsigned_helper: the synthetic-
    #    double_limb_type division branch of cpp_int/misc.hpp (taken only where
    #    double_limb_type is __int128, i.e. BOOST_HAS_INT128);
    #  - serialization::cpp_int_detail::divide_subtract/int128_type/uint128_type:
    #    serialize.hpp's `using namespace boost::multiprecision(::backends)`
    #    exposes exactly the multiprecision/backends entities above into
    #    cpp_int_detail, so they are absent on the same condition.
    patch("src/gen_exports/multiprecision.inc",
          "  using boost::multiprecision::int128_type;",
          "#if defined(BOOST_HAS_INT128)\n"
          "  // M12 platform guard: detail/standalone_config.hpp defines int128_type only\n"
          "  // under BOOST_HAS_INT128 (off under the clang-msvc flavor).\n"
          "  using boost::multiprecision::int128_type;\n"
          "#endif")
    patch("src/gen_exports/multiprecision.inc",
          "  using boost::multiprecision::uint128_type;",
          "#if defined(BOOST_HAS_INT128)\n"
          "  // M12 platform guard: as above (uint128_type).\n"
          "  using boost::multiprecision::uint128_type;\n"
          "#endif")
    patch("src/gen_exports/multiprecision.inc",
          "  using boost::multiprecision::backends::divide_subtract;",
          "#if defined(BOOST_HAS_INT128)\n"
          "  // M12 platform guard: divide_subtract is the synthetic-double_limb_type\n"
          "  // division branch of cpp_int/misc.hpp (BOOST_HAS_INT128 only).\n"
          "  using boost::multiprecision::backends::divide_subtract;\n"
          "#endif")
    patch("src/gen_exports/multiprecision.inc",
          "  using boost::multiprecision::backends::divide_unsigned_helper;",
          "#if defined(BOOST_HAS_INT128)\n"
          "  // M12 platform guard: as above (divide_unsigned_helper).\n"
          "  using boost::multiprecision::backends::divide_unsigned_helper;\n"
          "#endif")
    for name in ["divide_subtract", "int128_type", "uint128_type"]:
        patch("src/gen_exports/multiprecision.inc",
              f"  using boost::serialization::cpp_int_detail::{name};",
              f"#if defined(BOOST_HAS_INT128)\n"
              f"  // M12 platform guard: serialize.hpp's `using namespace\n"
              f"  // boost::multiprecision(::backends)` exposes the {name} entity into\n"
              f"  // cpp_int_detail — present only under BOOST_HAS_INT128.\n"
              f"  using boost::serialization::cpp_int_detail::{name};\n"
              f"#endif")

    # M12: qvm — vec_traits_gnuc_impl lives in vec_traits_gnuc.hpp, included
    # (unconditionally, from lite.hpp) only for its content — the header
    # self-guards with `#if defined(__GNUC__) && defined(__SSE2__)`; the MSVC
    # flavor never declares the impl.
    patch("src/gen_exports/qvm.inc",
          "  using boost::qvm::qvm_detail::vec_traits_gnuc_impl;",
          "#if defined(__GNUC__) && defined(__SSE2__)\n"
          "  // M12 platform guard: vec_traits_gnuc.hpp declares vec_traits_gnuc_impl\n"
          "  // only under __GNUC__ && __SSE2__ (gcc vector_size ext_vector_traits).\n"
          "  using boost::qvm::qvm_detail::vec_traits_gnuc_impl;\n"
          "#endif")

    # M12: interprocess — the mingw snapshot's GMF carries Windows-only
    # headers and faces that POSIX never declares:
    #  - managed_windows_shared_memory.hpp #errors off-Windows (it pulls
    #    windows_shared_memory.hpp / detail/win32_api.hpp); guard the GMF
    #    include (M9 winapi.cppm pattern);
    #  - the whole boost::interprocess::winapi block (win32_api.hpp) and
    #    boost::ipwinapiext (registry/virtual-memory extensions) are
    #    Windows-only;
    #  - scattered windows_shared_memory/ipcdetail::winapi_* entities.
    patch("src/interprocess.cppm",
          "#include <boost/interprocess/managed_windows_shared_memory.hpp>\n",
          "#if defined(_WIN32) || defined(__CYGWIN__)\n"
          "// M12 platform guard: managed_windows_shared_memory.hpp pulls\n"
          "// windows_shared_memory.hpp / detail/win32_api.hpp, which #error off-Windows\n"
          "// (M9 winapi.cppm convention).\n"
          "#include <boost/interprocess/managed_windows_shared_memory.hpp>\n"
          "#endif\n")
    patch("src/gen_exports/interprocess.inc",
          "export namespace boost { namespace interprocess { namespace winapi {\n"
          "  using boost::interprocess::winapi::NtClose_t;",
          "#if defined(_WIN32)\n"
          "export namespace boost { namespace interprocess { namespace winapi {\n"
          "  // M12 platform guard: the interprocess::winapi surface (detail/win32_api.hpp)\n"
          "  // is Windows-only; POSIX interprocess never declares it.\n"
          "  using boost::interprocess::winapi::NtClose_t;")
    patch("src/gen_exports/interprocess.inc",
          "  using boost::interprocess::winapi::write_file;\n}}}",
          "  using boost::interprocess::winapi::write_file;\n}}}\n#endif")
    patch("src/gen_exports/interprocess.inc",
          "export namespace boost { namespace ipwinapiext {\n"
          "  using boost::ipwinapiext::CreateThread;",
          "#if defined(_WIN32)\n"
          "export namespace boost { namespace ipwinapiext {\n"
          "  // M12 platform guard: registry / virtual-memory extension surface —\n"
          "  // Windows-only (win32_api.hpp chain).\n"
          "  using boost::ipwinapiext::CreateThread;")
    patch("src/gen_exports/interprocess.inc",
          "  using boost::ipwinapiext::VirtualUnlock;\n}}",
          "  using boost::ipwinapiext::VirtualUnlock;\n}}\n#endif")
    guard_entity_lines("src/gen_exports/interprocess.inc", "defined(_WIN32)", [
        "basic_managed_windows_shared_memory",
        "managed_windows_shared_memory",
        "windows_shared_memory",
        "wmanaged_windows_shared_memory",
        "do_winapi_wait",
        "winapi_mutex_functions",
        "winapi_mutex_wrapper",
        "winapi_semaphore_functions",
        "winapi_semaphore_wrapper",
        "winapi_wrapper_timed_wait_for_single_object",
        "winapi_wrapper_try_wait_for_single_object",
        "winapi_wrapper_wait_for_single_object",
        "windows_bootstamp",
        "windows_intermodule_singleton",
        "windows_semaphore_based_map",
        # second round (gcc/musl cross check): the mingw snapshot declares
        # these in ipcdetail only — POSIX interprocess selects different
        # implementations (shm/spin/windows file traits are the windows
        # branches of the platform selectors).
        "file_time_to_microseconds",
        "get_bootstamp",
        "get_temporary_wpath",
        "intermodule_singleton_common",
        "intermodule_singleton_impl",
        "mapping_handle_from_shm_handle",
        "os_file_traits",
        "ref_count_ptr",
        "shm_named_mutex",
        "shm_named_semaphore",
        "spin_condition",
        "spin_mutex",
        "spin_recursive_mutex",
        "spin_semaphore",
        "unrestricted_permissions_holder",
        "wshmem_open_or_create",
        "get_map_base_name",
        "get_map_name",
        "get_map_size",
        "get_pid_creation_time_str",
        "thread_safe_global_map_dependant",
        "mutex_traits",
    ])

    guard_entity_lines("src/gen_exports/process.inc", "defined(_WIN32)", [
        "stream_handle",
    ])
    # M12: asio — BOOST_ASIO_HAS_FILE-gated file surface (windows-random-
    # access-handle / io_uring only; same guard family as the M11 cobalt.inc
    # file guards) and the internal-linkage unmentionable placeholders
    # (same drop as the M11 graph.inc ones).
    guard_entity_lines("src/gen_exports/asio.inc", "defined(BOOST_ASIO_HAS_FILE)", [
        "basic_file",
        "basic_random_access_file",
        "basic_stream_file",
        "file_base",
        "random_access_file",
        "stream_file",
    ])
    # Windows-only asio detail surface in the asio module face itself — the
    # same guard list the M11 cobalt.inc guards carry (IOCP/file backends,
    # winsock init, APC, win_* family, and the select-reactor machinery that
    # POSIX asio does not instantiate; null_reactor/select_reactor et al.
    # self-guard empty on the epoll/kqueue paths).
    guard_entity_lines("src/gen_exports/asio.inc", "defined(_WIN32)", [
        "apc_function",
        "calculate_hash_value",
        "random_access_handle",
        "stream_handle",
        "fd_set_adapter",
        "hash_map",
        "null_reactor",
        "select_reactor",
        "null_signal_blocker",
        "socket_select_interrupter",
        "reactor_op_queue",
        "win_event",
        "win_fd_set_adapter",
        "win_global",
        "win_global_impl",
        "win_iocp_file_service",
        "win_iocp_handle_read_op",
        "win_iocp_handle_service",
        "win_iocp_handle_write_op",
        "win_iocp_io_context",
        "win_iocp_null_buffers_op",
        "win_iocp_operation",
        "win_iocp_overlapped_ptr",
        "win_iocp_serial_port_service",
        "win_iocp_socket_accept_op",
        "win_iocp_socket_connect_op",
        "win_iocp_socket_connect_op_base",
        "win_iocp_socket_move_accept_op",
        "win_iocp_socket_recv_op",
        "win_iocp_socket_recvfrom_op",
        "win_iocp_socket_recvmsg_op",
        "win_iocp_socket_send_op",
        "win_iocp_socket_service",
        "win_iocp_socket_service_base",
        "win_iocp_thread_info",
        "win_iocp_wait_op",
        "win_iocp_overlapped_op",
        "win_object_handle_service",
        "win_mutex",
        "win_static_mutex",
        "win_thread",
        "win_thread_base",
        "win_thread_function",
        "winsock_init",
        "winsock_init_base",
        "basic_object_handle",
        "basic_overlapped_handle",
        "basic_random_access_handle",
        "basic_stream_handle",
        "object_handle",
        "overlapped_handle",
        "overlapped_ptr",
        "complete_iocp_accept",
        "complete_iocp_connect",
        "complete_iocp_recv",
        "complete_iocp_recvfrom",
        "complete_iocp_recvmsg",
        "complete_iocp_send",
        "msghdr",
    ])
    for name in ["unmentionable", "unmentionable_type"]:
        patch("src/gen_exports/multiprecision.inc",
              f"  using boost::multiprecision::detail::{name};\n",
              f"  // M12: {name} dropped — no external linkage (multiprecision detail\n"
              f"  // placeholder); gcc refuses the export.\n",
              required=False)

    # M12: beast — the mingw snapshot's face carries the win32 file backend
    # (beast::file_win32, detail::win32_* helpers, http::detail win32 overwrite
    # operators) that POSIX beast never declares (it takes file_posix).
    guard_entity_lines("src/gen_exports/beast.inc", "defined(_WIN32)", [
        "file_win32",
        "set_file_pointer_ex",
        "win32_unicode_path",
        "highPart",
        "lowPart",
        "make_win32_error",
        "null_lambda",
        "run_write_some_win32_op",
        "write_some_win32_op",
        "basic_dstream",
        "dstream_buf",
    ])

    # M9: align — detail::alignment_of is config-selected by
    # boost/align/alignment_of.hpp: `using std::alignment_of;` (cxx11 branch)
    # on x86/clang-msvc, but a real `struct alignment_of` on the
    # BOOST_CLANG && !__x86_64__ branch (macOS arm64, and 32-bit unix gcc).
    # The generated snapshot (mingw → cxx11) emits `using std::alignment_of;`
    # in the module purview, which conflicts with the struct the macOS GMF
    # declares. The detail name is NOT needed by the exported surface — the
    # public boost::alignment::alignment_of inherits from it via the GMF and
    # consumers instantiate it fine (verified gcc/clang, struct and cxx11
    # paths) — so drop the export line.
    patch("src/gen_exports/align.inc",
          "  using std::add_lvalue_reference;\n  using std::alignment_of;\n  using std::false_type;\n",
          "  using std::add_lvalue_reference;\n  using std::false_type;\n")

    # M9: parser — parse_int/parse_real live in an `inline namespace
    # BOOST_PARSER_NUMERIC_NS` (std_charconv | boost_charconv | spirit_parsers,
    # selected by numeric.hpp at include time). The mingw snapshot used
    # std_charconv, so the .inc qualified the entities as
    # numeric::std_charconv::parse_int. On toolchains where a different branch
    # is active (e.g. libc++ without __cpp_lib_to_chars), the std_charconv
    # namespace doesn't exist. Use the inline-namespace-agnostic path
    # (numeric::parse_int) which resolves on every branch.
    patch("src/gen_exports/parser.inc",
          "export namespace boost { namespace parser { namespace detail { namespace numeric { namespace std_charconv {\n"
          "  using boost::parser::detail::numeric::std_charconv::parse_int;\n"
          "  using boost::parser::detail::numeric::std_charconv::parse_real;\n"
          "}}}}}",
          "export namespace boost { namespace parser { namespace detail { namespace numeric {\n"
          "  using boost::parser::detail::numeric::parse_int;\n"
          "  using boost::parser::detail::numeric::parse_real;\n"
          "}}}}")

    # M9: flyweight — the generator leaked the entire transitive surface of
    # boost.container / boost.interprocess(.winapi) / boost.intrusive /
    # boost.move_detail / boost.mpl / boost.parameter / boost.multi_index into
    # flyweight.inc (932 entities). Those namespaces are internal dependencies
    # whose availability is platform-dependent (interprocess.winapi is Windows-
    # only; container option types are macro-generated, declared only on the
    # mingw snapshot include path). The committed form is hand-trimmed to
    # flyweight's own surface (boost::flyweight + boost::flyweights::*); restore
    # it after regeneration. Mirrors the algorithm.inc convention.
    restore_from_git("src/gen_exports/flyweight.inc")

    # M6: thread module — mingw snapshot exports Windows-only entities (win32
    # thread primitives + boost.winapi) that the POSIX GMF include set never
    # declares. Guard the entirely-windows namespace blocks wholesale, and the
    # scattered Windows-only entities via guard_entity_lines.
    patch("src/gen_exports/thread.inc",
          "export namespace boost { namespace detail { namespace win32 {\n"
          "  using boost::detail::win32::create_anonymous_event;",
          "#if defined(_WIN32)\n"
          "export namespace boost { namespace detail { namespace win32 {\n"
          "  using boost::detail::win32::create_anonymous_event;")
    patch("src/gen_exports/thread.inc",
          "  using boost::detail::win32::system_info;\n"
          "  using boost::detail::win32::ticks_type;\n"
          "}}}\n\nexport namespace boost { namespace detail { namespace win32 { namespace detail {",
          "  using boost::detail::win32::system_info;\n"
          "  using boost::detail::win32::ticks_type;\n"
          "}}}\n#endif\n\nexport namespace boost { namespace detail { namespace win32 { namespace detail {")
    patch("src/gen_exports/thread.inc",
          "  using boost::detail::win32::detail::gettickcount64_t;\n"
          "}}}}\n\nexport namespace boost { namespace exception_detail {",
          "#if defined(_WIN32)\n"
          "  using boost::detail::win32::detail::gettickcount64_t;\n"
          "#endif\n"
          "}}}}\n\nexport namespace boost { namespace exception_detail {")
    guard_entity_lines("src/gen_exports/thread.inc", "defined(_WIN32)", [
        # boost block — intrusive_ptr is pulled in only via win32 thread headers
        "intrusive_ptr",
        # atomics::detail — wait_operations_windows (win32 branch of boost/atomic)
        "wait_operations_windows",
        # date_time / posix_time — FILETIME helpers (win32 only)
        "time_from_ftime",
        "from_ftime",
        # this_thread — interruptible_wait / non_interruptible_wait (win32 API wait)
        "interruptible_wait",
        "non_interruptible_wait",
        # boost::detail — win32 thread primitives (once / mutex / interlocked / tss)
        "allocate_raw_heap_memory",
        "free_raw_heap_memory",
        "basic_condition_variable",
        "basic_cv_list_entry",
        "basic_recursive_mutex",
        "basic_recursive_mutex_impl",
        "basic_recursive_timed_mutex",
        "basic_timed_mutex",
        "commit_once_region",
        "create_once_event",
        "enter_once_region",
        "rollback_once_region",
        "int_to_string",
        "interlocked_read_acquire",
        "interlocked_write_release",
        "intrusive_ptr_add_ref",
        "intrusive_ptr_release",
        "name_once_mutex",
        "once_action",
        "once_char_type",
        "once_context",
        "open_once_event",
        "underlying_mutex",
    ])
    patch("src/gen_exports/mp11.inc",
          "  using boost::mp11::detail::mpmf_unwrap;\n  using boost::mp11::detail::mpmf_wrap;",
          "#if !defined(__GNUC__)\n  // M3 hand-guard: mp_map_find.hpp (gcc bug 120161 workaround) defines mpmf_* only outside gcc.\n"
          "  using boost::mp11::detail::mpmf_unwrap;\n  using boost::mp11::detail::mpmf_wrap;\n#endif")
    patch("src/gen_exports/tuple.inc",
          "  using boost::tuples::detail::ignore_t;",
          "#if !defined(__GNUC__)\n  // M3 hand-guard: ignore_t is a member-pointer typedef; gcc treats it as internal linkage.\n  using boost::tuples::detail::ignore_t;\n#endif")
    # M4: thread.inc atomics — mingw snapshot carries gcc-only boost/atomic
    # entities (convert_memory_order_to_gcc, core_arch_operations_gcc_x86*,
    # core_operations_gcc_atomic, fence_arch_operations_gcc_x86,
    # fence_operations_gcc_atomic); absent under the MSVC ABI.
    # M11: with boost.atomic as a module these entities are claimed by it
    # (first-wins) and migrate out of thread.inc — anchors may be gone, so
    # the guards are best-effort (required=False).
    for name in ["convert_memory_order_to_gcc",
                 "core_operations_gcc_atomic",
                 "fence_operations_gcc_atomic"]:
        patch("src/gen_exports/thread.inc",
              f"  using boost::atomics::detail::{name};",
              f"#if defined(__GNUC__)\n  // M4 platform guard: gcc-only branch of boost/atomic (snapshot = mingw flavor).\n  using boost::atomics::detail::{name};\n#endif",
              required=False)
    # M7: the *_gcc_x86 backend classes need the same condition as the
    # boost/atomic gcc_x86 backend (platform.hpp: __GNUC__ && x86 arch). Plain
    # __GNUC__ broke macOS arm64 (clang defines __GNUC__, but the gcc_aarch64
    # backend applies); bare __i386__/__x86_64__ would wrongly export them
    # under the MSVC ABI (clang-cl defines no __GNUC__).
    # M11: entities may migrate to boost.atomic — best-effort.
    for name in ["core_arch_operations_gcc_x86",
                 "core_arch_operations_gcc_x86_base",
                 "fence_arch_operations_gcc_x86"]:
        patch("src/gen_exports/thread.inc",
              f"  using boost::atomics::detail::{name};",
              f"#if defined(__GNUC__) && (defined(__i386__) || defined(__x86_64__))\n  // M7 platform guard: gcc_x86 backend of boost/atomic (platform.hpp) exists only on x86; __GNUC__ is defined by clang too, so it broke macOS arm64 (gcc_aarch64 backend).\n  using boost::atomics::detail::{name};\n#endif",
              required=False)
    patch("src/gen_exports/variant.inc",
          "  using boost::mpl::aux::arity_helper;\n  using boost::mpl::aux::arity_tag;",
          "#if defined(__GNUC__)\n  // M3 hand-guard: gcc-preprocessed mpl headers only (BOOST_MPL_CFG_COMPILER_DIR=gcc).\n"
          "  using boost::mpl::aux::arity_helper;\n  using boost::mpl::aux::arity_tag;\n#endif")
    patch("src/gen_exports/variant.inc",
          "  using boost::mpl::aux::max_arity;",
          "#if defined(__GNUC__)\n  // M3 hand-guard: as above (max_arity).\n  using boost::mpl::aux::max_arity;\n#endif")
    patch("src/gen_exports/variant.inc",
          "  using boost::mpl::aux::nested_type_wknd;",
          "#if defined(__GNUC__)\n  // M3 hand-guard: as above (nested_type_wknd).\n  using boost::mpl::aux::nested_type_wknd;\n#endif")
    patch("src/gen_exports/variant.inc",
          "  using boost::mpl::aux::template_arity_impl;",
          "#if defined(__GNUC__)\n  // M3 hand-guard: as above (template_arity_impl).\n  using boost::mpl::aux::template_arity_impl;\n#endif")

    # M9: heap's container templates (d_ary_heap etc.) instantiate the intrusive
    # placement new (`::new(p, boost_move_new_t()) T`) in the consumer TU, where
    # the global operator new overload from move/detail/placement_new.hpp (a GMF
    # include) is not visible. M0 rule: re-export the global operator new
    # overloads from the module purview.
    patch("src/heap.cppm",
          '#include "gen_exports/heap.inc"',
          "// M9: heap's container templates (d_ary_heap etc.) instantiate the intrusive\n"
          "// placement new (`::new(p, boost_move_new_t()) T`) in the consumer TU, where\n"
          "// the global operator new overload from move/detail/placement_new.hpp (a GMF\n"
          "// include) is not visible. M0 rule: re-export the global operator new\n"
          "// overloads from the module purview.\n"
          "export using ::operator new;\n\n"
          '#include "gen_exports/heap.inc"',
          required=False)

    # ---- algorithm: M3 workaround (string.hpp GFM + *regex entity pruning) ----
    # algorithm.inc is regenerated with string_regex.hpp in the GFM; the M3
    # gcc abi-tag workaround keeps string.hpp instead, so the generated inc
    # (which lists the *regex entities) cannot compile in the module TU.
    # The committed M3 form is the source of truth; regenerate-free.
    restore_from_git("src/gen_exports/algorithm.inc")
    restore_from_git("src/gen_exports/algorithm.deps")
    restore_from_git("src/algorithm.cppm")  # M3 GFM (string.hpp) + no boost.regex import

    # ---- M3 libs whose .cppm are unchanged (regen only rewrites the header
    # comment): keep the M3 "final form" convention. Their .inc/.deps ARE
    # regenerated (entity ownership may shift between runs). scope_exit left
    # the list in C1 (2026-09-06): boost.scope_exit is include-only now. ----
    for rel in ["any", "container_hash", "core", "endian", "io", "iterator",
                "mp11", "optional", "range", "rational", "scope",
                "static_string", "tuple", "type_traits", "variant", "variant2"]:
        restore_from_git(f"src/{rel}.cppm")

    # M11: io — boost/io/ostream_put.hpp is curated out of the io module GMF:
    # its function-local unnamed enum (buffer_fill) streamed from two module
    # CMIs (boost.io + boost.utility via string_view) mismatches on gcc 16.1.
    # Nothing from it appears in io.inc. NB: io.cppm is git-restored above, so
    # this patch must run after the restores.
    patch("src/io.cppm",
          "#include <boost/io/ostream_put.hpp>\n",
          "// M11: ostream_put.hpp curated out of the io module GMF — its\n"
          "// buffer_fill enum mismatches between the boost.io/boost.utility CMIs\n"
          "// on gcc 16.1; consumers include the header themselves.\n",
          required=False)
    patch("src/gen_exports/io.inc",
          "  using boost::io::ostream_put;\n",
          "  // M11: ostream_put dropped — declared only via io/ostream_put.hpp (curated\n"
          "  // out of the module GMF; gcc 16.1 buffer_fill enum mismatch).\n",
          required=False)

    print("done.")


if __name__ == "__main__":
    main()
