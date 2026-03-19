#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "OpenClaw 接入检查"
echo "工作区: ${ROOT_DIR}"

status=0

if command -v openclaw >/dev/null 2>&1; then
  echo "openclaw: 已安装"
  openclaw --version || status=1
else
  echo "openclaw: 未安装"
  status=1
fi

echo "运行模式: FastAPI 常驻 + OpenClaw CLI 按需执行"

if [[ -d "${ROOT_DIR}/skills" ]]; then
  echo "skills/: 已存在"
else
  echo "skills/: 缺失"
  status=1
fi

for dir in \
  "${ROOT_DIR}/skills/guideclaw-principal-investigator" \
  "${ROOT_DIR}/skills/guideclaw-literature-assistant" \
  "${ROOT_DIR}/skills/guideclaw-gap-analyst" \
  "${ROOT_DIR}/skills/guideclaw-study-designer" \
  "${ROOT_DIR}/skills/guideclaw-meeting-secretary" \
  "${ROOT_DIR}/skills/bohrium-paper-search" \
  "${ROOT_DIR}/skills/bohrium-pdf-parser" \
  "${ROOT_DIR}/skills/bohrium-knowledge-base" \
  "${ROOT_DIR}/skills/web-search" \
  "${ROOT_DIR}/skills/proposal-agent" \
  "${ROOT_DIR}/skills/preparation-agent" \
  "${ROOT_DIR}/openclaw"
do
  if [[ -d "${dir}" ]]; then
    echo "$(basename "${dir}"): 已存在"
  else
    echo "$(basename "${dir}"): 缺失"
    status=1
  fi
done

if [[ -f "${ROOT_DIR}/openclaw/openclaw.config.template.yml" ]]; then
  echo "openclaw 配置模板: 已存在"
else
  echo "openclaw 配置模板: 缺失"
  status=1
fi

if [[ -f "${ROOT_DIR}/openclaw/openclaw.env.example" ]]; then
  echo "openclaw 环境示例: 已存在"
else
  echo "openclaw 环境示例: 缺失"
  status=1
fi

if command -v openclaw >/dev/null 2>&1; then
  echo "workspace skills readiness:"
  export GUIDECLAW_API_BASE_URL="${GUIDECLAW_API_BASE_URL:-http://127.0.0.1:8000}"
  if [[ -n "${BOHRIUM_ACCESS_KEY:-}" && -z "${ACCESS_KEY:-}" ]]; then
    export ACCESS_KEY="${BOHRIUM_ACCESS_KEY}"
  fi
  if openclaw --profile guideclaw skills list 2>/dev/null | grep -q "openclaw-workspace"; then
    openclaw --profile guideclaw skills list | grep "openclaw-workspace" || true
  else
    echo "未检测到 openclaw-workspace skills 输出"
    status=1
  fi
fi

exit "${status}"
