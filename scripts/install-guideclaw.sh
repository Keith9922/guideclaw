#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
API_ENV_EXAMPLE="$ROOT_DIR/services/api/.env.example"
API_ENV_LOCAL="$ROOT_DIR/services/api/.env.local"
OPENCLAW_ENV_EXAMPLE="$ROOT_DIR/openclaw/openclaw.env.example"
OPENCLAW_ENV_LOCAL="$ROOT_DIR/openclaw/.env.local"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[GuideClaw] 缺少依赖：$1" >&2
    exit 1
  fi
}

write_from_example() {
  local source_file="$1"
  local target_file="$2"
  if [[ ! -f "$target_file" ]]; then
    cp "$source_file" "$target_file"
  fi
}

replace_or_append() {
  local file="$1"
  local key="$2"
  local value="$3"
  if grep -q "^${key}=" "$file"; then
    perl -0pi -e "s#^${key}=.*#${key}=${value}#m" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >>"$file"
  fi
}

require_cmd python3
require_cmd pnpm
require_cmd openclaw

mkdir -p "$ROOT_DIR/data/uploads" "$ROOT_DIR/data/samples"

write_from_example "$API_ENV_EXAMPLE" "$API_ENV_LOCAL"
write_from_example "$OPENCLAW_ENV_EXAMPLE" "$OPENCLAW_ENV_LOCAL"

replace_or_append "$API_ENV_LOCAL" "GUIDECLAW_API_BASE_URL" "http://127.0.0.1:8000"
replace_or_append "$API_ENV_LOCAL" "GUIDECLAW_DATABASE_PATH" "$ROOT_DIR/data/guideclaw.db"
replace_or_append "$API_ENV_LOCAL" "OPENROUTER_MODEL" "openrouter/free"

replace_or_append "$OPENCLAW_ENV_LOCAL" "WORKSPACE_ROOT" "$ROOT_DIR"
replace_or_append "$OPENCLAW_ENV_LOCAL" "GUIDECLAW_API_BASE_URL" "http://127.0.0.1:8000"
replace_or_append "$OPENCLAW_ENV_LOCAL" "OPENROUTER_MODEL" "openrouter/free"

cat <<EOF

[GuideClaw] 一键接入准备完成。

已经生成：
- $API_ENV_LOCAL
- $OPENCLAW_ENV_LOCAL

默认基座模型：
- openrouter/free

下一步只需要：

1. 在 $API_ENV_LOCAL 中填入：
   - OPENROUTER_API_KEY
   - 如需文献技能，再填 BOHRIUM_ACCESS_KEY

2. 安装后端依赖并启动 API：
   cd "$ROOT_DIR/services/api"
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

3. 启动前端：
   cd "$ROOT_DIR"
   pnpm install
   pnpm --filter @guideclaw/web dev

4. 检查 OpenClaw 工作区 skills：
   source "$OPENCLAW_ENV_LOCAL"
   GUIDECLAW_API_BASE_URL=http://127.0.0.1:8000 openclaw --profile guideclaw skills list

EOF
