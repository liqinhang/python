"""
贪吃蛇大作战 — AI 自动寻路模块
==============================
BFS 基础寻路 + DSG 多步任务规划。
若有实体（门/钥匙/陷阱/高级食物）则优先使用 DSG 规划器，
否则回退到传统 BFS。
"""

from collections import deque
from typing import Optional

import config as cfg
from dsg import get_dsg_direction
from entities import Door, OneWayPassage, MovingTrap


# ================================================================
# 传统 BFS（用于无实体场景或回退）
# ================================================================
def bfs_find_path(
    snake_body: list[tuple[int, int]],
    food_pos: tuple[int, int],
    obstacles: list[tuple[int, int]],
) -> Optional[tuple[int, int]]:
    """BFS 搜索蛇头到食物的最短路径，返回下一步方向。"""
    if not snake_body:
        return None

    head = snake_body[0]
    cols, rows = cfg.COLS, cfg.ROWS
    blocked = set(snake_body[1:]) | set(obstacles)

    queue = deque([head])
    visited = {head}
    parent: dict[tuple[int, int], tuple[int, int]] = {}

    while queue:
        current = queue.popleft()
        if current == food_pos:
            return _backtrack(parent, head, food_pos)
        for dx, dy in cfg.DIRECTIONS:
            nx, ny = current[0] + dx, current[1] + dy
            neighbor = (nx, ny)
            if nx < 0 or nx >= cols or ny < 0 or ny >= rows:
                continue
            if neighbor in blocked:
                continue
            if neighbor in visited:
                continue
            visited.add(neighbor)
            parent[neighbor] = current
            queue.append(neighbor)

    return None


def _backtrack(
    parent: dict[tuple[int, int], tuple[int, int]],
    start: tuple[int, int],
    goal: tuple[int, int],
) -> Optional[tuple[int, int]]:
    """从 parent 字典回溯，返回第一步方向。"""
    if goal not in parent and start != goal:
        return None
    current = goal
    while parent.get(current) != start:
        current = parent[current]
        if current not in parent:
            return None
    return (current[0] - start[0], current[1] - start[1])


def fallback_move(
    snake_body: list[tuple[int, int]],
    obstacles: list[tuple[int, int]],
    current_direction: tuple[int, int],
) -> tuple[int, int]:
    """保底策略：选第一个安全方向，优先保持当前方向。"""
    if not snake_body:
        return current_direction
    head = snake_body[0]
    blocked = set(snake_body[1:]) | set(obstacles)
    candidates = [current_direction] + [d for d in cfg.DIRECTIONS
                                         if d != current_direction]
    for dx, dy in candidates:
        nx, ny = head[0] + dx, head[1] + dy
        if (0 <= nx < cfg.COLS and 0 <= ny < cfg.ROWS
                and (nx, ny) not in blocked):
            return (dx, dy)
    return current_direction


# ================================================================
# 基础 AI 入口（向后兼容，用于无实体场景）
# ================================================================
def get_ai_direction(
    snake_body: list[tuple[int, int]],
    food_pos: tuple[int, int],
    obstacles: list[tuple[int, int]],
    current_direction: tuple[int, int],
) -> tuple[int, int]:
    """基础 AI 决策：BFS → 保底。"""
    bfs_result = bfs_find_path(snake_body, food_pos, obstacles)
    if bfs_result is not None:
        return bfs_result
    return fallback_move(snake_body, obstacles, current_direction)


# ================================================================
# 增强 AI 入口（具身智能，支持所有实体类型）
# ================================================================
def get_ai_direction_enhanced(
    snake_body: list[tuple[int, int]],
    food_pos: tuple[int, int],
    obstacles: list[tuple[int, int]],
    doors: list[Door],
    passages: list[OneWayPassage],
    traps: list[MovingTrap],
    premium_foods: list[tuple[int, int]],
    keys_on_map: list[tuple[int, int]],
    inventory: dict[str, int],
    current_direction: tuple[int, int],
) -> tuple[int, int]:
    """
    增强 AI 决策入口：
      1. 若有实体 → 使用 DSG 多步任务规划
      2. 若无实体 → 使用传统 BFS
      3. 全部失败 → 保底策略

    Returns:
        推荐移动方向 (dx, dy)。
    """
    has_entities = bool(doors or traps or premium_foods or keys_on_map)

    if has_entities:
        # DSG 多步规划
        dsg_result = get_dsg_direction(
            snake_body=snake_body,
            food_pos=food_pos,
            obstacles=obstacles,
            doors=doors,
            passages=passages,
            traps=traps,
            premium_foods=premium_foods,
            keys_on_map=keys_on_map,
            inventory=inventory,
            current_direction=current_direction,
        )
        if dsg_result is not None:
            return dsg_result

    # 回退：传统 BFS
    bfs_result = bfs_find_path(snake_body, food_pos, obstacles)
    if bfs_result is not None:
        return bfs_result

    return fallback_move(snake_body, obstacles, current_direction)
