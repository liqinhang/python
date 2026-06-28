"""
贪吃蛇大作战 — 网络客户端
==========================
使用 requests 库与 FastAPI 排行榜服务通信。
所有网络操作均包含异常处理，服务器不可用时返回 None 以保证游戏正常运行。
"""

from typing import Any

import requests

import config as cfg


def submit_score(name: str, score: int) -> dict[str, Any] | None:
    """
    上传分数到排行榜服务器。

    Args:
        name: 玩家昵称。
        score: 最终分数。

    Returns:
        服务器返回的 JSON（包含排行榜列表），失败则返回 None。
    """
    if not name.strip():
        return None
    try:
        resp = requests.post(
            f"{cfg.SERVER_URL}/upload",
            json={"name": name.strip(), "score": score},
            timeout=cfg.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


def fetch_leaderboard() -> list[dict[str, Any]] | None:
    """
    从服务器获取排行榜。

    Returns:
        排行榜条目列表，失败返回 None。
    """
    try:
        resp = requests.get(
            f"{cfg.SERVER_URL}/leaderboard",
            timeout=cfg.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("leaderboard", [])
    except requests.RequestException:
        return None
