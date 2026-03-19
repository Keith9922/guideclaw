from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.projects import router as projects_router
from app.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="引路虾 API",
    version="0.1.0",
    description="引路虾后端 API，负责项目持久化、多 Agent 调查工作流和 OpenClaw 执行接入。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.guideclaw_allowed_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "environment": settings.guideclaw_env,
        "project_bootstrap_mode": "user_created_only",
        "storage": {
            "mode": "sqlite",
            "database_path": str(settings.guideclaw_database_path),
        },
        "openrouter": {
            "base_url": settings.openrouter_base_url,
            "api_key_configured": bool(settings.openrouter_api_key),
            "model_configured": bool(settings.openrouter_model),
            "ready": settings.openrouter_ready,
        },
        "bohrium": {
            "base_url": settings.bohrium_openapi_base_url,
            "access_key_configured": bool(settings.bohrium_access_key),
            "ready": settings.bohrium_ready,
            "installed_workspace_skills": [
                "bohrium-paper-search",
                "bohrium-pdf-parser",
                "bohrium-knowledge-base",
                "web-search",
                "proposal-agent",
                "preparation-agent",
            ],
            "demo_primary_roles": {
                "literature_assistant": [
                    "bohrium-paper-search",
                    "bohrium-pdf-parser",
                    "bohrium-knowledge-base",
                    "web-search",
                ],
                "study_designer": [
                    "proposal-agent",
                ],
            },
        },
        "openclaw": {
            "integration_mode": "cli_on_demand",
            "binary": settings.guideclaw_openclaw_binary,
            "profile": settings.guideclaw_openclaw_profile,
            "agent": settings.guideclaw_openclaw_agent,
            "channel_server": False,
            "call_path": "web -> fastapi -> openclaw cli --local --json -> response stream",
            "workspace_skills_require_api_env": True,
        },
    }
