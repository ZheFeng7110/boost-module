# GitHub Release Process (runbook)

> Applies to releases of any version; independent of a specific release.
> Version naming: six-segment numeric `v<boost version>.<wrapper version>`; below, `<tag>`
> denotes the tag name of the release being published (e.g. `v1.91.0.0.0.1`), and the release
> notes file is `docs/release_notes/<tag>.md` (v-prefixed, e.g. `v1.91.0.0.0.1.md`).
> `<version>` is the same string without the leading `v` (e.g. `1.91.0.0.0.1`), used for the
> CHANGELOG entry — and it is what `[package].version` / a consumer's `version = "..."` must
> carry.

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
- [ ] `docs/release_notes/<tag>.md` is ready (contents / known limitations /
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
- The tag name must match the release notes file name (both v-prefixed) exactly; the CHANGELOG
  entry uses the same version without the `v`.
- **Pushing the tag triggers the release workflow automatically** (see §3); make sure the
  notes file `docs/release_notes/<tag>.md` exists before pushing — the workflow fails if
  it is missing.
- Mistakenly created but unpushed tag: `git tag -d <tag>`; pushed tags are in principle
  **never deleted or rewritten** — to retract, publish a new version and mark the old one
  deprecated in the release notes.

## 3. Creating the GitHub Release

The GitHub Release is created **automatically** by the
[`.github/workflows/release.yml`](.github/workflows/release.yml) workflow as soon as a tag
is pushed: it extracts `docs/release_notes/<tag>.md` as the release body (**fails the run
if the file is missing**), runs `scripts/package-source.sh` to build the source archives
(`.zip` / `.tar.gz` / `.tar.xz` / `.7z` + `.sha256` checksums), and attaches them to a
release titled `Release <tag>`. Tags ending in `-preview` are published with the
prerelease flag set.

Monitor the workflow run (`Actions` tab, `Release` workflow). Manual creation is only the
fallback if the automation failed after the prerequisites were fixed:

```bash
bash scripts/package-source.sh
gh release create <tag> \
  --title "Release <tag>" \
  --notes-file docs/release_notes/<tag>.md \
  target/dist/* \
  --prerelease          # mandatory for previews; drop for stable releases
```

- The body reuses `docs/release_notes/<tag>.md` directly (wording may be tweaked in the
  GitHub UI afterwards, but the in-repo file remains authoritative).
- **No binary attachments**: the only assets are the source archives produced by
  `scripts/package-source.sh` (zip / tar.gz / tar.xz / 7z with sha256 files); consumers
  normally get the sources via git dep / (in the future) the mcpp package index. GitHub's
  auto-generated "Source code (zip/tar.gz)" links remain available alongside the archives.
- Release page topic labels (if available): `cpp` `cpp23` `boost` `modules`.

## 4. Post-release Wrap-up

- [ ] Release page visible, notes render correctly, tag commit is correct; the `Release`
      workflow ran green and the source archives (zip / tar.gz / tar.xz / 7z + sha256) are
      attached to the release.
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
| `--prerelease` | yes (set automatically by the workflow for `-preview` tags) | no |
| tag suffix | `-preview` | none (e.g. `v1.91.0.0.0.0`) |
| mcpp package index (T3) | not published | boost.lua integration + registry consumption probe mandatory |
| Known-limitation disclosure | full list | reduced to still-valid entries |
