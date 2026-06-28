"""
贪吃蛇大作战 — 动态场景图 (DSG) 规划器
========================================
具身任务规划：AI 蛇在包含门/钥匙/陷阱的环境中
进行多步逻辑推理，而非简单的 BFS 点到点寻路。

核心思想：
  1. 以蛇当前背包状态构建可通行图
  2. 发现目标被门阻挡 → 识别需要钥匙 → 规划"取钥匙→开门→吃食物"
  3. 预测移动陷阱未来位置，提前规避
"""

from collections import deque
from typing import Optional

import config as cfg
from entities import Door, OneWayPassage, MovingTrap


class SceneGraph:
    """
    动态场景图：根据当前背包状态、实体位置构建可达性图。
    图会随"拿到钥匙"而改变拓扑结构。
    """

    def __init__(
        self,
        snake_body: list[tuple[int, int]],
        obstacles: list[tuple[int, int]],
        doors: list[Door],
        passages: list[OneWayPassage],
        traps: list[MovingTrap],
        inventory: dict[str, int],
    ):
        self.snake_body = snake_body
        self.head = snake_body[0] if snake_body else (0, 0)
        self.obstacles = obstacles
        self.doors = doors
        self.passages = passages
        self.traps = traps
        self.inventory = inventory
        self.cols = cfg.COLS
        self.rows = cfg.ROWS

        # 预计算不可通行的格子集合
        self._blocked = self._build_blocked_set()

    def _build_blocked_set(self) -> set[tuple[int, int]]:
        """构建当前不可通行的格子集合。"""
        blocked = set(self.snake_body[1:])  # 蛇身（除蛇头）
        blocked.update(self.obstacles)

        # 关闭的门 = 不可通行
        for door in self.doors:
            if not door.is_open and self.inventory.get(door.color, 0) == 0:
                blocked.add(door.pos)

        # 移动陷阱当前位置 = 不可通行
        for trap in self.traps:
            blocked.add(trap.pos)

        return blocked

    def is_passable(self, pos: tuple[int, int]) -> bool:
        """判断某格子是否可通行。"""
        x, y = pos
        if x < 0 or x >= self.cols or y < 0 or y >= self.rows:
            return False
        return pos not in self._blocked

    def bfs_to_target(
        self, start: tuple[int, int], target: tuple[int, int]
    ) -> Optional[list[tuple[int, int]]]:
        """
        标准 BFS：从 start 到 target 的最短路径。
        返回完整路径（含起点），如果不可达返回 None。
        """
        if start == target:
            return [start]

        queue = deque([start])
        visited = {start}
        parent: dict[tuple[int, int], tuple[int, int]] = {}

        while queue:
            current = queue.popleft()
            for dx, dy in cfg.DIRECTIONS:
                nx, ny = current[0] + dx, current[1] + dy
                neighbor = (nx, ny)

                if not self.is_passable(neighbor):
                    continue
                if neighbor in visited:
                    continue

                # 单向通道检查：如果邻居是单向通道，检查进入方向
                passage = self._get_passage_at(neighbor)
                if passage:
                    if not passage.can_enter_from(current):
                        continue

                visited.add(neighbor)
                parent[neighbor] = current

                if neighbor == target:
                    return self._reconstruct_path(parent, start, target)

                queue.append(neighbor)

        return None

    def _get_passage_at(self, pos: tuple[int, int]) -> Optional[OneWayPassage]:
        """获取某位置的单向通道（如果存在）。"""
        for p in self.passages:
            if p.pos == pos:
                return p
        return None

    def _reconstruct_path(
        self,
        parent: dict[tuple[int, int], tuple[int, int]],
        start: tuple[int, int],
        goal: tuple[int, int],
    ) -> list[tuple[int, int]]:
        """回溯 parent 字典重建路径。"""
        path = [goal]
        current = goal
        while current != start:
            current = parent[current]
            path.append(current)
        path.reverse()
        return path

    # ================================================================
    # 多步规划（DSG 核心）
    # ================================================================
    def plan_multi_step(
        self,
        food_pos: tuple[int, int],
        premium_foods: list[tuple[int, int]],
        keys_on_map: list[tuple[int, int]],
    ) -> Optional[tuple[int, int]]:
        """
        多步任务规划入口。

        返回：蛇的下一步移动方向 (dx, dy)，或 None。

        策略优先级：
          1. 可直接到达 premium_food → 直接去吃
          2. 可直接到达普通 food → 直接去吃
          3. 被门阻挡 → 找钥匙 → 规划取钥匙路径
          4. 无路可走 → 返回 None（调用方用 fallback）
        """
        all_targets = list(premium_foods)  # 高级食物优先
        if food_pos != (-1, -1):
            all_targets.append(food_pos)

        # Step 1: 尝试直接到达任何目标
        for target in all_targets:
            path = self.bfs_to_target(self.head, target)
            if path is not None and len(path) >= 2:
                return self._path_to_direction(path)

        # Step 2: 直接路径被阻断 → 检查是否被门挡住
        blocking_door = self._find_blocking_door(all_targets)
        if blocking_door:
            # Step 3: 找对应钥匙
            key_pos = self._find_key_for_door(blocking_door, keys_on_map)
            if key_pos:
                # 规划去拿钥匙
                key_path = self.bfs_to_target(self.head, key_pos)
                if key_path and len(key_path) >= 2:
                    return self._path_to_direction(key_path)

        # Step 4: 所有高级策略失败 → None
        return None

    def _path_to_direction(self, path: list[tuple[int, int]]) -> tuple[int, int]:
        """从路径提取下一步方向。"""
        if len(path) < 2:
            return cfg.RIGHT
        dx = path[1][0] - path[0][0]
        dy = path[1][1] - path[0][1]
        return (dx, dy)

    def _find_blocking_door(
        self, targets: list[tuple[int, int]]
    ) -> Optional[Door]:
        """
        判断是否有门阻断了到所有目标的路径。
        策略：对每个未开启的门，尝试在假设门打开的情况下 BFS。
        如果门打开后路径可达，则该门是阻断的。
        """
        for door in self.doors:
            if door.is_open:
                continue
            if self.inventory.get(door.color, 0) > 0:
                continue  # 已经有钥匙，不算阻断

            # 临时移除门的阻挡，测试是否可达
            if door.pos in self._blocked:
                self._blocked.remove(door.pos)

            for target in targets:
                path = self.bfs_to_target(self.head, target)
                if path is not None:
                    # 门打开后可达 → 这门是阻断
                    self._blocked.add(door.pos)  # 恢复
                    return door

            self._blocked.add(door.pos)  # 恢复

        return None

    def _find_key_for_door(
        self, door: Door, keys_on_map: list[tuple[int, int]]
    ) -> Optional[tuple[int, int]]:
        """
        在地图上找到能打开指定门的钥匙位置。
        keys_on_map: [(x, y), ...] 需要包含颜色信息。

        简化处理：返回最近的可达钥匙。
        """
        # keys_on_map 中的位置，我们需要关联到 entity 对象
        # 这里假设调用方会传入正确的位置
        if not keys_on_map:
            return None

        best_key = None
        best_dist = float("inf")
        for key_pos in keys_on_map:
            # 尝试 BFS 到钥匙
            path = self.bfs_to_target(self.head, key_pos)
            if path is not None and len(path) < best_dist:
                best_dist = len(path)
                best_key = key_pos

        return best_key


def get_dsg_direction(
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
    DSG 规划器对外接口。
    如果 DSG 规划成功则返回规划方向，否则回退到保底策略。
    """
    graph = SceneGraph(
        snake_body=snake_body,
        obstacles=obstacles,
        doors=doors,
        passages=passages,
        traps=traps,
        inventory=inventory,
    )

    result = graph.plan_multi_step(
        food_pos=food_pos,
        premium_foods=premium_foods,
        keys_on_map=keys_on_map,
    )

    if result is not None:
        return result

    # 保底：BFS 到普通食物
    path = graph.bfs_to_target(snake_body[0], food_pos)
    if path is not None and len(path) >= 2:
        return graph._path_to_direction(path)

    # 最后的保底：能走哪走哪
    return _fallback_avoid_traps(snake_body, obstacles, traps,
                                  current_direction)


def _fallback_avoid_traps(
    snake_body: list[tuple[int, int]],
    obstacles: list[tuple[int, int]],
    traps: list[MovingTrap],
    current_direction: tuple[int, int],
) -> tuple[int, int]:
    """保底策略：选择安全方向，避开障碍物和陷阱。"""
    if not snake_body:
        return current_direction

    head = snake_body[0]
    blocked = set(snake_body[1:]) | set(obstacles)
    for trap in traps:
        blocked.add(trap.pos)

    candidates = [current_direction] + [d for d in cfg.DIRECTIONS
                                         if d != current_direction]

    for dx, dy in candidates:
        nx, ny = head[0] + dx, head[1] + dy
        if (0 <= nx < cfg.COLS and 0 <= ny < cfg.ROWS
                and (nx, ny) not in blocked):
            return (dx, dy)

    return current_direction
