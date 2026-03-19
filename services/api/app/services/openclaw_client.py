from __future__ import annotations

import asyncio
import json
import os
import signal
import time
from collections.abc import Mapping
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.domain.schemas import AgentRunRequest, AgentRunResponse
from app.settings import Settings

ROLE_TO_SKILL: Mapping[str, tuple[str, str]] = {
    "principal_investigator": (
        "guideclaw-principal-investigator",
        "请使用 guideclaw-principal-investigator 技能，围绕当前 GUIDECLAW_PROJECT_ID 对应项目总结所处阶段、当前进展与下一步建议。如果项目信息不足，要明确指出空缺，不要引用历史示例项目。你负责调度，不负责亲自做外部文献检索。",
    ),
    "literature_assistant": (
        "guideclaw-literature-assistant",
        "请使用 guideclaw-literature-assistant 技能，围绕当前 GUIDECLAW_PROJECT_ID 对应项目梳理文献现状、关键方法和证据。若环境里存在 ACCESS_KEY，请优先使用 bohrium-paper-search、bohrium-pdf-parser、bohrium-knowledge-base 与 web-search；若当前项目暂无文献卡或知识源，请明确说明缺失。",
    ),
    "gap_analyst": (
        "guideclaw-gap-analyst",
        "请使用 guideclaw-gap-analyst 技能，围绕当前 GUIDECLAW_PROJECT_ID 对应项目比较研究缺口，并指出最值得优先推进的一项。若缺口卡为空，请明确说明不能下结论。",
    ),
    "study_designer": (
        "guideclaw-study-designer",
        "请使用 guideclaw-study-designer 技能，围绕当前 GUIDECLAW_PROJECT_ID 对应项目整理成一版可执行的研究方案。若当前任务已经明确是论文复现或复现实验规划，可进一步使用 proposal-agent；若方案卡为空，请优先指出需要补哪些前置输入。",
    ),
    "meeting_secretary": (
        "guideclaw-meeting-secretary",
        "请使用 guideclaw-meeting-secretary 技能，围绕当前 GUIDECLAW_PROJECT_ID 对应项目输出结论、待办和下一步推进顺序。若纪要卡为空，请只输出缺失项和建议补充的讨论材料。",
    ),
}


def _build_session_id(project_id: str, role: str) -> str:
    safe_project_id = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in project_id)
    safe_role = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in role)
    return f"guideclaw-{safe_project_id}-{safe_role}-{uuid4().hex[:8]}"


def _extract_json_block(output: str) -> dict:
    lines = output.splitlines()
    for index, line in enumerate(lines):
        if line.lstrip().startswith("{"):
            candidate = "\n".join(lines[index:])
            return json.loads(candidate)
    raise ValueError("no JSON payload found in OpenClaw output")


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _cleanup_openclaw_session_locks(settings: Settings) -> None:
    profile_root = Path.home() / f".openclaw-{settings.guideclaw_openclaw_profile}"
    session_dir = profile_root / "agents" / settings.guideclaw_openclaw_agent / "sessions"
    if not session_dir.exists():
        return

    for lock_path in session_dir.glob("*.lock"):
        pid: int | None = None
        try:
            payload = json.loads(lock_path.read_text(encoding="utf-8"))
            raw_pid = payload.get("pid")
            if isinstance(raw_pid, int):
                pid = raw_pid
        except Exception:
            pid = None

        if pid and _process_exists(pid):
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass

            deadline = time.time() + 2
            while time.time() < deadline and _process_exists(pid):
                time.sleep(0.1)

            if _process_exists(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass

        if not pid or not _process_exists(pid):
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass


def _sync_openclaw_model_profile(settings: Settings) -> None:
    profile_root = Path.home() / f".openclaw-{settings.guideclaw_openclaw_profile}"
    config_path = profile_root / "openclaw.json"
    agent_models_path = profile_root / "agents" / settings.guideclaw_openclaw_agent / "agent" / "models.json"

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        config = {}

    config.setdefault("auth", {}).setdefault("profiles", {})
    config.setdefault("models", {})["mode"] = "merge"
    providers = config["models"].setdefault("providers", {})
    providers["minimax"] = {
        "baseUrl": settings.minimax_base_url,
        "apiKey": "${MINIMAX_API_KEY}",
        "api": "openai-completions",
        "models": [
            {
                "id": settings.minimax_model,
                "name": settings.minimax_model,
                "reasoning": True,
                "input": ["text"],
                "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                "contextWindow": 1000000,
                "maxTokens": 64000,
            }
        ],
    }

    defaults = config.setdefault("agents", {}).setdefault("defaults", {})
    defaults.setdefault("model", {})["primary"] = f"minimax/{settings.minimax_model}"
    defaults["models"] = {
        f"minimax/{settings.minimax_model}": {
            "alias": settings.minimax_model,
        }
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    try:
        agent_models = json.loads(agent_models_path.read_text(encoding="utf-8"))
    except Exception:
        agent_models = {}
    agent_models["providers"] = {
        "minimax": {
            "baseUrl": settings.minimax_base_url,
            "api": "openai-completions",
            "authHeader": True,
            "models": [
                {
                    "id": settings.minimax_model,
                    "name": settings.minimax_model,
                    "reasoning": True,
                    "input": ["text"],
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                    "contextWindow": 1000000,
                    "maxTokens": 64000,
                }
            ],
            "apiKey": "MINIMAX_API_KEY",
        }
    }
    agent_models_path.parent.mkdir(parents=True, exist_ok=True)
    agent_models_path.write_text(json.dumps(agent_models, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def run_openclaw_role(
    settings: Settings,
    project_id: str,
    payload: AgentRunRequest,
) -> AgentRunResponse:
    # 当前接入模式不是常驻 OpenClaw 服务，而是由 FastAPI 按需拉起 CLI 执行一轮 agent turn。
    skill, default_prompt = ROLE_TO_SKILL[payload.role]
    prompt = payload.prompt_override or default_prompt

    env = os.environ.copy()
    env["GUIDECLAW_API_BASE_URL"] = settings.guideclaw_api_base_url
    env["GUIDECLAW_PROJECT_ID"] = project_id

    # OpenClaw 当前会把角色运行复用到同一个主 session；若上一轮异常退出，残留 lock 会导致后续全部超时。
    _cleanup_openclaw_session_locks(settings)
    _sync_openclaw_model_profile(settings)

    if settings.bohrium_access_key:
        env["BOHRIUM_ACCESS_KEY"] = settings.bohrium_access_key
        env["ACCESS_KEY"] = settings.bohrium_access_key

    if settings.minimax_api_key:
        env["MINIMAX_API_KEY"] = settings.minimax_api_key
    if settings.minimax_model:
        env["MINIMAX_MODEL"] = settings.minimax_model
    if settings.minimax_base_url:
        env["MINIMAX_BASE_URL"] = settings.minimax_base_url

    process = await asyncio.create_subprocess_exec(
        settings.guideclaw_openclaw_binary,
        "--profile",
        settings.guideclaw_openclaw_profile,
        "agent",
        "--agent",
        settings.guideclaw_openclaw_agent,
        "--session-id",
        _build_session_id(project_id, payload.role),
        "--local",
        "--json",
        "-m",
        prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
    except TimeoutError as exc:
        process.kill()
        _cleanup_openclaw_session_locks(settings)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="OpenClaw execution timed out",
        ) from exc

    stdout_text = stdout.decode("utf-8", errors="replace").strip()
    stderr_text = stderr.decode("utf-8", errors="replace").strip()

    if process.returncode != 0:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "OpenClaw execution failed",
                "stderr": stderr_text,
                "stdout": stdout_text,
            },
        )

    try:
        result = _extract_json_block(stdout_text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "OpenClaw returned non-JSON output",
                "stderr": stderr_text,
                "stdout": stdout_text,
            },
        ) from exc

    payloads = result.get("payloads") or []
    first_payload = payloads[0] if payloads else {}
    meta = result.get("meta") or {}
    agent_meta = meta.get("agentMeta") or {}

    return AgentRunResponse(
        project_id=project_id,
        role=payload.role,
        skill=skill,
        model=agent_meta.get("model"),
        session_id=agent_meta.get("sessionId"),
        duration_ms=meta.get("durationMs"),
        content=first_payload.get("text", "").strip(),
    )
