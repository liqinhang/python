"""
贪吃蛇大作战 — 排行榜后端服务
==============================
FastAPI 微服务，提供分数上传和排行榜查询接口。
数据持久化到本地 JSON 文件，仅保留前 10 名。

启动方式：
    uvicorn server:app --reload --port 8000
"""

import json
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="贪吃蛇排行榜", version="1.0.0")

# 允许跨域请求（方便前端在不同端口访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据文件与 server.py 同目录
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scores.json")


def _load_scores() -> list[dict]:
    """从 JSON 文件加载排行榜数据。"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def _save_scores(scores: list[dict]) -> None:
    """将排行榜数据写入 JSON 文件。"""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)


@app.get("/")
def root():
    """健康检查。"""
    return {"message": "贪吃蛇排行榜服务运行中 🐍", "docs": "/docs"}


@app.get("/leaderboard")
def get_leaderboard():
    """获取排行榜（分数降序前 10 名）。"""
    scores = _load_scores()
    return {"leaderboard": scores[:10]}


@app.post("/upload")
def upload_score(data: dict):
    """
    上传新分数。
    请求体示例: {"name": "player1", "score": 42}
    返回更新后的排行榜。
    """
    name = data.get("name", "anonymous")
    score = data.get("score", 0)

    # 读取现有数据
    scores = _load_scores()

    # 追加新记录
    scores.append({"name": str(name), "score": int(score)})

    # 按分数降序排序，保留前 10
    scores = sorted(scores, key=lambda x: x["score"], reverse=True)[:10]

    # 持久化
    _save_scores(scores)

    return {"status": "ok", "leaderboard": scores}
