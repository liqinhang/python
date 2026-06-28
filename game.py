"""
贪吃蛇大作战 — 核心游戏逻辑
============================
SnakeGame 类负责：蛇身管理、食物/障碍物/实体生成、
碰撞检测、移动逻辑、背包系统、本地最高分。
"""

import random
import json
import os

import config as cfg
from entities import (
    Key, Door, OneWayPassage, MovingTrap, PremiumFood,
    generate_entities,
)


class SnakeGame:
    """贪吃蛇核心游戏引擎（含具身智能实体）。"""

    def __init__(self):
        # 蛇与基本状态
        self.snake_body: list[tuple[int, int]] = []
        self.direction: tuple[int, int] = cfg.RIGHT
        self.next_direction: tuple[int, int] = cfg.RIGHT
        self.food_pos: tuple[int, int] = (0, 0)
        self.obstacles: list[tuple[int, int]] = []

        # 具身智能实体
        self.keys_on_map: list[Key] = []
        self.doors: list[Door] = []
        self.one_way_passages: list[OneWayPassage] = []
        self.moving_traps: list[MovingTrap] = []
        self.premium_foods: list[PremiumFood] = []

        # 背包（钥匙库存）
        self.inventory: dict[str, int] = {"blue": 0, "red": 0, "yellow": 0}

        # 游戏状态
        self.score: int = 0
        self.speed: int = cfg.INITIAL_SPEED
        self.is_ai_mode: bool = False
        self.is_paused: bool = False
        self.is_game_over: bool = False
        self.is_won: bool = False
        self.high_score: int = 0
        self.just_ate: bool = False
        self.just_died: bool = False
        self.just_got_key: bool = False    # 本帧拿到钥匙（触发 UI 反馈）
        self.just_unlocked: bool = False   # 本帧开门
        self.level: int = 1
        self.move_count: int = 0

        self._entities_spawned_for_level: int = 0

        self.load_high_score()

    # ================================================================
    # 重置
    # ================================================================
    def reset(self) -> None:
        """重置游戏到初始状态。"""
        center_x = cfg.COLS // 2
        center_y = cfg.ROWS // 2
        self.snake_body = [
            (center_x, center_y),
            (center_x - 1, center_y),
            (center_x - 2, center_y),
        ]
        self.direction = cfg.RIGHT
        self.next_direction = cfg.RIGHT
        self.obstacles.clear()
        self.keys_on_map.clear()
        self.doors.clear()
        self.one_way_passages.clear()
        self.moving_traps.clear()
        self.premium_foods.clear()
        self.inventory = {"blue": 0, "red": 0, "yellow": 0}
        self.score = 0
        self.speed = cfg.INITIAL_SPEED
        self.is_ai_mode = False
        self.is_paused = False
        self.is_game_over = False
        self.is_won = False
        self.just_ate = False
        self.just_died = False
        self.just_got_key = False
        self.just_unlocked = False
        self.level = 1
        self.move_count = 0
        self._entities_spawned_for_level = 0
        self.generate_food()

    # ================================================================
    # 实体生成
    # ================================================================
    def spawn_entities_for_level(self) -> None:
        """根据当前关卡生成实体（仅在新关卡时调用一次）。"""
        if self._entities_spawned_for_level >= self.level:
            return

        occupied = (set(self.snake_body) | set(self.obstacles)
                    | {self.food_pos})
        occupied.update(k.pos for k in self.keys_on_map)
        occupied.update(d.pos for d in self.doors)
        occupied.update(p.pos for p in self.one_way_passages)
        occupied.update(p.pos for p in self.premium_foods)

        keys, doors, passages, traps, premium = generate_entities(
            self.level, occupied
        )
        self.keys_on_map.extend(keys)
        self.doors.extend(doors)
        self.one_way_passages.extend(passages)
        self.moving_traps.extend(traps)
        self.premium_foods.extend(premium)
        self._entities_spawned_for_level = self.level

    # ================================================================
    # 食物 / 障碍物生成（避开实体）
    # ================================================================
    def generate_food(self) -> None:
        """在安全位置生成食物（避开蛇身、障碍物和所有实体）。"""
        occupied = self._all_occupied_cells()
        available = [
            (x, y) for x in range(cfg.COLS) for y in range(cfg.ROWS)
            if (x, y) not in occupied
        ]
        if available:
            self.food_pos = random.choice(available)
        else:
            self.food_pos = (-1, -1)

    def generate_obstacle(self) -> None:
        """在安全位置生成障碍物。"""
        if len(self.obstacles) >= cfg.MAX_OBSTACLES:
            return
        occupied = self._all_occupied_cells()
        occupied.add(self.food_pos)
        available = [
            (x, y) for x in range(cfg.COLS) for y in range(cfg.ROWS)
            if (x, y) not in occupied
        ]
        if available:
            self.obstacles.append(random.choice(available))

    def _all_occupied_cells(self) -> set[tuple[int, int]]:
        """返回所有被占用的格子（蛇+障碍物+实体）。"""
        occupied = set(self.snake_body) | set(self.obstacles)
        for k in self.keys_on_map:
            occupied.add(k.pos)
        for d in self.doors:
            if not d.is_open:
                occupied.add(d.pos)
        for p in self.one_way_passages:
            occupied.add(p.pos)
        for t in self.moving_traps:
            occupied.add(t.pos)
            occupied.update(t.path)  # 巡逻路径也避开
        for pf in self.premium_foods:
            occupied.add(pf.pos)
        return occupied

    # ================================================================
    # 蛇移动（扩展：实体交互）
    # ================================================================
    def update_moving_traps(self) -> None:
        """更新所有移动陷阱的位置。"""
        for trap in self.moving_traps:
            trap.update()

    def move_snake(self) -> None:
        """执行一帧移动：实体交互 + 吃食物 + 碰撞检测 + 升级。"""
        self.just_ate = False
        self.just_died = False
        self.just_got_key = False
        self.just_unlocked = False

        self.direction = self.next_direction

        head_x, head_y = self.snake_body[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        # ---- 碰撞检测 ----
        if self._check_collision(new_head):
            self.is_game_over = True
            self.just_died = True
            return

        # ---- 实体交互检测（在插入新蛇头之前） ----
        # 单向通道：检查是否从正确方向进入
        passage = self._get_passage_at(new_head)
        if passage and not passage.can_enter_from(self.snake_body[0]):
            # 从错误方向进入 → 撞墙
            self.is_game_over = True
            self.just_died = True
            return

        # 移动陷阱检测（在移动后检查）
        for trap in self.moving_traps:
            if trap.occupies(new_head[0], new_head[1]):
                self.is_game_over = True
                self.just_died = True
                return

        # ---- 插入新蛇头 ----
        self.snake_body.insert(0, new_head)

        # ---- 拾取钥匙 ----
        key = self._get_key_at(new_head)
        if key:
            self.inventory[key.color] += 1
            self.keys_on_map.remove(key)
            self.just_got_key = True

        # ---- 解锁门 ----
        door = self._get_door_at(new_head)
        if door:
            if door.try_unlock(self.inventory):
                door.is_open = True
                self.just_unlocked = True
                # 已开的门不再阻挡，但保留在地图上（视觉上消失）
                # 注意：蛇可以穿过已开的门
            else:
                # 门未开且无钥匙 → 不应该走到这里（碰撞检测会拦截）
                # 但作为保护，回退
                self.snake_body.pop(0)
                self.is_game_over = True
                self.just_died = True
                return

        # ---- 吃食物 ----
        ate_something = False
        points = 0

        if new_head == self.food_pos:
            ate_something = True
            points = 1
            self.food_pos = (-1, -1)

        # 高级食物
        pf = self._get_premium_food_at(new_head)
        if pf:
            ate_something = True
            points = pf.value
            self.premium_foods.remove(pf)

        if ate_something:
            self.just_ate = True
            self.score += points
            self.move_count += 1

            # 升级判断
            if self.score % cfg.SCORE_PER_LEVEL == 0 and self.score > 0:
                old_level = self.level
                self.level = self.score // cfg.SCORE_PER_LEVEL + 1
                if self.level > old_level:
                    self.speed = min(cfg.MAX_SPEED,
                                     self.speed + cfg.SPEED_INCREMENT)
                    self.generate_obstacle()

            self.generate_food()
            if self.food_pos == (-1, -1):
                # 检查是否还有 premium food
                if not self.premium_foods:
                    self.is_won = True
                    self.is_game_over = True
                    return
        else:
            self.snake_body.pop()
            self.move_count += 1

    # ================================================================
    # 碰撞检测（扩展：门、陷阱、单向通道）
    # ================================================================
    def _check_collision(self, head: tuple[int, int]) -> bool:
        """检查蛇头是否撞到墙壁、自身、障碍物、关闭的门。"""
        x, y = head

        if x < 0 or x >= cfg.COLS or y < 0 or y >= cfg.ROWS:
            return True

        if head in self.snake_body[:-1]:
            return True

        if head in self.obstacles:
            return True

        # 关闭的门 = 不可通行
        for door in self.doors:
            if not door.is_open and door.pos == head:
                # 如果有钥匙，不算碰撞（蛇可以进入并解锁）
                if self.inventory.get(door.color, 0) > 0:
                    return False
                return True

        return False

    # ================================================================
    # 实体查询工具
    # ================================================================
    def _get_key_at(self, pos: tuple[int, int]) -> Key | None:
        for k in self.keys_on_map:
            if k.pos == pos:
                return k
        return None

    def _get_door_at(self, pos: tuple[int, int]) -> Door | None:
        for d in self.doors:
            if d.pos == pos and not d.is_open:
                return d
        return None

    def _get_passage_at(self, pos: tuple[int, int]) -> OneWayPassage | None:
        for p in self.one_way_passages:
            if p.pos == pos:
                return p
        return None

    def _get_premium_food_at(self, pos: tuple[int, int]) -> PremiumFood | None:
        for pf in self.premium_foods:
            if pf.pos == pos:
                return pf
        return None

    # ================================================================
    # 方向 / 胜利 / 分数
    # ================================================================
    def change_direction(self, new_dir: tuple[int, int]) -> None:
        """设置新的移动方向，禁止 180° 掉头。"""
        if (new_dir[0] + self.direction[0] == 0 and
                new_dir[1] + self.direction[1] == 0):
            return
        self.next_direction = new_dir

    def check_win(self) -> bool:
        """蛇身长度占据所有格子即胜利。"""
        return len(self.snake_body) == cfg.TOTAL_CELLS

    def load_high_score(self) -> None:
        path = self._score_file_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.high_score = data.get("high_score", 0)
            except (json.JSONDecodeError, KeyError):
                self.high_score = 0

    def save_high_score(self) -> None:
        if self.score > self.high_score:
            self.high_score = self.score
            path = self._score_file_path()
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"high_score": self.high_score}, f, ensure_ascii=False)

    @staticmethod
    def _score_file_path() -> str:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "scores_local.json")

    def get_occupied_cells(self) -> set:
        """返回所有不可通行的格子集合（供 AI 用）。"""
        occupied = set(self.snake_body[1:]) | set(self.obstacles)
        for d in self.doors:
            if not d.is_open and self.inventory.get(d.color, 0) == 0:
                occupied.add(d.pos)
        for t in self.moving_traps:
            occupied.add(t.pos)
        return occupied

    def get_all_premium_positions(self) -> list[tuple[int, int]]:
        return [pf.pos for pf in self.premium_foods]

    def get_all_key_positions(self) -> list[tuple[int, int]]:
        return [k.pos for k in self.keys_on_map]
