# GitHub Release Process (runbook)

> Applies to releases of any version; independent of a specific release.
> Version naming: `b<boost version>w<wrapper version>`; below, `<tag>` denotes the tag name
> of the release being published (e.g. `b1.91.0w0.0.0-preview`, `b1.91.0w0.0.0`).
> `<version>` refers to the same string, used for the release notes file name and the
> CHANGELOG entry.

## 0. Prerequisites (release bar)

- [ ] All four CI legs (windows-clang-msvc / linux-gcc / linux-llvm / macos-llvm-arm64)
      green for the commit to be released; both A/B gate groups pass.
- [ ] `uv run scripts/gen_features.py --check` passes (zero drift between the features
      block and features.lst).
- [ ] `uv run scripts/reapply_hand_edits.py` re-runs idempotently with zero changes
      (all vendored patches replay cleanly).
- [ ] Count review: `src/*.cppm` = module count, `scripts/features.lst` = feature count,
      `[features].default` = default closure, all consistent with the numbers in the
      CHANGELOG / release notes.
- [ ] `docs/release_notes/<version>.md` is ready (contents / known limitations /
      issue-reporting guidance), and `CHANGELOG.md` has the corresponding version entry.
- [ ] The user has confirmed that tagging may proceed.

## 1. Tag-build Drill in a Clean Checkout (mandatory before tagging)

Once a tag is set it points to an immutable snapshot; simulate "consumer clones and builds"
in a temporary directory first:

```bash
git clone <repo-url> "$TEMP/boost-module-release-drill"
cd "$TEMP/boost-module-release-drill"
git checkout <commit to release>

# Full local-leg (llvm/msvc defaults) verification
mcpp build
mcpp test                 # default-set smoke all green
mcpp run -p default_usage # examples
```

Any failure → go back to the development branch, fix, and re-run the drill.
**Never tag a broken state.**

## 2. Tagging

```bash
# On the development branch, at the commit to be released
git tag -a <tag> -m "<one-line release note, e.g. Boost X.Y.Z C++23 named modules wrapper vX.Y.Z>"
git push origin <tag>
```

- Always use an **annotated tag** (carries tagger / date / message).
- The tag name must match the release notes file name and the CHANGELOG entry exactly.
- Mistakenly created but unpushed tag: `git tag -d <tag>`; pushed tags are in principle
  **never deleted or rewritten** — to retract, publish a new version and mark the old one
  deprecated in the release notes.

## 3. Creating the GitHub Release

```bash
gh release create <tag> \
  --title "<tag>" \
  --notes-file docs/release_notes/<version>.md \
  --prerelease          # mandatory for previews; drop for stable releases
```

- The body reuses `docs/release_notes/<version>.md` directly (wording may be tweaked in the
  GitHub UI afterwards, but the in-repo file remains authoritative).
- **No binary attachments**: this project is a source package; consumers get it via git dep
  / (in the future) the mcpp package index; Source code (zip/tar.gz) is generated
  automatically by GitHub.
- Release page topic labels (if available): `cpp` `cpp23` `boost` `modules`.

## 4. Post-release Wrap-up

- [ ] Release page visible, notes render correctly, tag commit is correct.
- [ ] Consumer probe: a temporary project with a `git = ... tag = <tag>` dependency
      declaration goes through build+run (at least the default set of the three
      configurations in architecture.md §2.1).
- [ ] `CHANGELOG.md` and `docs/release_notes/` match what was actually released
      (if wording was changed in the GitHub UI, sync it back to the in-repo files).
- [ ] Update the example tag in the development-branch README / architecture.md to the new
      tag (only if the next release is still a preview; a stable release instead proceeds
      with the T3 registry integration).
- [ ] Check off the corresponding items in related plan documents (if any).

## 5. Preview vs. Stable Release Differences

| Item | Preview | Stable |
|---|---|---|
| `--prerelease` | yes | no |
| tag suffix | `-preview` | none (e.g. `b1.91.0w0.0.0`) |
| mcpp package index (T3) | not published | boost.lua integration + registry consumption probe mandatory |
| Known-limitation disclosure | full list | reduced to still-valid entries |
