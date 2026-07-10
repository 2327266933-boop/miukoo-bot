from __future__ import annotations

import os
from typing import Any


def build_version_info() -> dict[str, Any]:
    commit_sha = os.getenv("RAILWAY_GIT_COMMIT_SHA", "")
    return {
        "status": "ok",
        "service": os.getenv("RAILWAY_SERVICE_NAME", ""),
        "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", ""),
        "git_branch": os.getenv("RAILWAY_GIT_BRANCH", ""),
        "git_commit_sha": commit_sha,
        "git_commit_short": commit_sha[:7] if commit_sha else "",
        "git_commit_message": os.getenv("RAILWAY_GIT_COMMIT_MESSAGE", ""),
    }


def format_version_info() -> str:
    info = build_version_info()
    lines = [
        "当前部署版本：",
        f"commit：{info['git_commit_short'] or '未知'}",
    ]
    if info["git_commit_message"]:
        lines.append(f"说明：{info['git_commit_message']}")
    if info["git_branch"]:
        lines.append(f"分支：{info['git_branch']}")
    if info["environment"]:
        lines.append(f"环境：{info['environment']}")
    return "\n".join(lines)
