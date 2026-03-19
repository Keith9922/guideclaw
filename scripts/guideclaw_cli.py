#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def api_base_url() -> str:
    return os.environ.get("GUIDECLAW_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def request_json(method: str, path: str) -> dict | list | str:
    request = urllib.request.Request(
        f"{api_base_url()}{path}",
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"API request failed: {exc.code} {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"API request failed: {exc}") from exc


def cmd_health(_: argparse.Namespace) -> None:
    print(json.dumps(request_json("GET", "/health"), ensure_ascii=False, indent=2))


def cmd_project(args: argparse.Namespace) -> None:
    print(json.dumps(request_json("GET", f"/projects/{args.project_id}"), ensure_ascii=False, indent=2))


def cmd_artifacts(args: argparse.Namespace) -> None:
    print(json.dumps(request_json("GET", f"/projects/{args.project_id}/artifacts"), ensure_ascii=False, indent=2))


def cmd_state(args: argparse.Namespace) -> None:
    print(json.dumps(request_json("GET", f"/projects/{args.project_id}/state"), ensure_ascii=False, indent=2))


def cmd_tasks(args: argparse.Namespace) -> None:
    print(json.dumps(request_json("GET", f"/projects/{args.project_id}/tasks"), ensure_ascii=False, indent=2))


def cmd_summary(args: argparse.Namespace) -> None:
    print(
        json.dumps(
            request_json("POST", f"/projects/{args.project_id}/llm-summary"),
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_knowledge_sources(args: argparse.Namespace) -> None:
    print(
        json.dumps(
            request_json("GET", f"/projects/{args.project_id}/knowledge-sources"),
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_knowledge_search(args: argparse.Namespace) -> None:
    query = urllib.parse.quote(args.query)
    print(
        json.dumps(
            request_json("GET", f"/projects/{args.project_id}/knowledge-search?q={query}"),
            ensure_ascii=False,
            indent=2,
        )
    )


def add_project_id_argument(parser: argparse.ArgumentParser) -> None:
    env_project_id = os.environ.get("GUIDECLAW_PROJECT_ID")
    parser.add_argument(
        "--project-id",
        default=env_project_id,
        required=env_project_id is None,
        help="GuideClaw 项目 ID。也可以通过 GUIDECLAW_PROJECT_ID 环境变量提供。",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GuideClaw local CLI bridge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser("health", help="Check GuideClaw API health")
    health.set_defaults(func=cmd_health)

    project = subparsers.add_parser("project", help="Fetch project metadata")
    add_project_id_argument(project)
    project.set_defaults(func=cmd_project)

    artifacts = subparsers.add_parser("artifacts", help="Fetch project artifacts")
    add_project_id_argument(artifacts)
    artifacts.set_defaults(func=cmd_artifacts)

    state = subparsers.add_parser("state", help="Fetch project research state")
    add_project_id_argument(state)
    state.set_defaults(func=cmd_state)

    tasks = subparsers.add_parser("tasks", help="Fetch agent tasks")
    add_project_id_argument(tasks)
    tasks.set_defaults(func=cmd_tasks)

    summary = subparsers.add_parser("summary", help="Generate OpenRouter-backed project summary")
    add_project_id_argument(summary)
    summary.set_defaults(func=cmd_summary)

    knowledge_sources = subparsers.add_parser("knowledge-sources", help="Fetch project knowledge sources")
    add_project_id_argument(knowledge_sources)
    knowledge_sources.set_defaults(func=cmd_knowledge_sources)

    knowledge_search = subparsers.add_parser("knowledge-search", help="Search project knowledge sources")
    add_project_id_argument(knowledge_search)
    knowledge_search.add_argument("query", help="Knowledge search query")
    knowledge_search.set_defaults(func=cmd_knowledge_search)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
