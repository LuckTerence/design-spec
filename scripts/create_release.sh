#!/bin/bash
# create_release.sh — 在 GitHub 上为 design-spec 创建 Release 并将 new.zip 作为发布资产
# 使用方法：
#   1. 生成一个 GitHub Personal Access Token (classic)：
#       Settings → Developer settings → Personal access tokens → Tokens (classic)
#       ✅ 勾选 repo 权限
#   2. 运行： GH_TOKEN=ghp_xxx bash create_release.sh
#
# 或者先 export GH_TOKEN，再直接运行本脚本。

set -e

REPO="LuckTerence/design-spec"
TAG="v1.0.0"
ZIP_PATH="dist/new.zip"

if [ -z "$GH_TOKEN" ]; then
  echo "❌ 需要 GH_TOKEN 环境变量"
  echo ""
  echo "操作步骤："
  echo "  1. 打开 https://github.com/settings/tokens/new"
  echo "  2. 勾选 repo 权限（全选）"
  echo "  3. 生成 Token，复制"
  echo "  4. 运行："
  echo "       GH_TOKEN=你的token bash $0"
  exit 1
fi

# 验证 token
echo "🔍 验证 Token..."
gh auth login --with-token <<< "$GH_TOKEN" 2>/dev/null
echo "   ✅ Token 有效"

# 检查 we have the zip
if [ ! -f "$ZIP_PATH" ]; then
  echo "❌ 未找到 $ZIP_PATH，请先打包"
  echo "   运行： python3 /Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/builtin-skills/skill-creator/scripts/package_skill.py new dist"
  exit 1
fi

echo "📦 创建 Release $TAG ..."
gh release create "$TAG" \
  --repo "$REPO" \
  --title "v1.0.0 — Design Spec Generator 首发版" \
  --notes-file RELEASE_NOTES_v1.0.0.md \
  "$ZIP_PATH"

echo ""
echo "✅ Release 创建完成！"
echo "   https://github.com/$REPO/releases/tag/$TAG"
