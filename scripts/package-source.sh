#!/usr/bin/env bash
# 打包发布源码：zip / tar.gz / 7z / tar.xz，并生成 sha256 校验文件
# 用法: package-source.sh [版本号] [输出目录]
#   版本号默认取自最新 git tag（去掉 v 前缀）

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VERSION="${1:-$(git describe --tags --abbrev=0 | sed 's/^v//')}"
OUT_DIR="${2:-$REPO_ROOT/target/dist}"
NAME="boost-module-v${VERSION}"

mkdir -p "$OUT_DIR"
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

# 导出 git 跟踪的文件（天然排除 .gitignore 忽略的内容），再手动排除指定路径
git archive --format=tar HEAD | tar -x -C "$STAGING"
rm -rf "$STAGING/.github" "$STAGING/.agents" "$STAGING/AGENTS.md"

STAGE_NAME="$NAME"
mv "$STAGING" "$REPO_ROOT/target/$STAGE_NAME"
trap 'rm -rf "$REPO_ROOT/target/$STAGE_NAME"' EXIT

# 极限压缩参数：
#   7z      -> -mx=9 -mfb=273 -md=1536m -ms=on
#   tar.xz  -> xz -9e
#   tar.gz  -> gzip -9（gzip 无更高等级）
cd "$REPO_ROOT/target"

echo "==> Creating $NAME.tar.gz"
tar -c "$STAGE_NAME" | gzip -9 > "$OUT_DIR/$NAME.tar.gz"

echo "==> Creating $NAME.tar.xz"
tar -c "$STAGE_NAME" | xz -9e -T0 > "$OUT_DIR/$NAME.tar.xz"

echo "==> Creating $NAME.zip"
zip -9 -q -r "$OUT_DIR/$NAME.zip" "$STAGE_NAME"

echo "==> Creating $NAME.7z"
7z a -mx=9 -mfb=273 -md=1536m -ms=on -bd -bso0 -bsp0 "$OUT_DIR/$NAME.7z" "$STAGE_NAME"

echo "==> Generating sha256"
(
  cd "$OUT_DIR"
  for f in "$NAME.zip" "$NAME.tar.gz" "$NAME.7z" "$NAME.tar.xz"; do
    sha256sum "$f" > "$f.sha256"
  done
)

echo "Done:"
ls -l "$OUT_DIR"/"$NAME".*
