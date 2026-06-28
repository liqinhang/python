"""
贪吃蛇大作战 — 具身智能实体定义
================================
门、钥匙、单向通道、移动陷阱、高级食物。
"""

import random
import config as cfg


# ============================================================
# 钥匙
# ============================================================
class Key:
    """可拾取钥匙，收入背包后用于解锁同色门。"""

    def __init__(self, x: int, y: int, color: str):
        self.pos = (x, y)
        self.color = color  # "blue" / "red" / "yellow"

    def __repr__(self):
        return f"Key({self.pos}, {self.color})"


# ============================================================
# 门
# ============================================================
class Door:
    """
    彩色门，无对应钥匙时不可通行。
    蛇携带匹配钥匙后自动解锁。
    """

    def __init__(self, x: int, y: int, color: str):
        self.pos = (x, y)
        self.color = color
        self.is_open = False

    def try_unlock(self, inventory: dict[str, int]) -> bool:
        """检查背包中是否有匹配钥匙，有则解锁。"""
        if inventory.get(self.color, 0) > 0:
            inventory[self.color] -= 1
            self.is_open = True
            return True
        return False

    def __repr__(self):
        return f"Door({self.pos}, {self.color}, open={self.is_open})"


# ============================================================
# 单向通道
# ============================================================
class OneWayPassage:
    """
    单向通道：只能从指定方向进入，强制沿通道方向移动。
    entry_direction: (dx, dy)，蛇必须从这个方向进入格子。
    exit_direction: (dx, dy)，蛇进入后强制沿此方向离开。
    例如：向右单向通道 → entry=(0,1) 从下方进入, exit=(1,0) 强制右移。
    """

    def __init__(self, x: int, y: int, entry_direction: tuple[int, int]):
        self.pos = (x, y)
        self.entry = entry_direction  # 允许进入的方向
        # 通道强制移动方向 = 进入方向（沿通道方向推过去）
        self.push = entry_direction

    def can_enter_from(self, prev_pos: tuple[int, int]) -> bool:
        """检查蛇是否从允许的方向进入。"""
        dx = self.pos[0] - prev_pos[0]
        dy = self.pos[1] - prev_pos[1]
        return (dx, dy) == self.entry

    def __repr__(self):
        return f"OneWay({self.pos}, entry={self.entry})"


# ============================================================
# 移动陷阱
# ============================================================
class MovingTrap:
    """
    沿预设路径巡逻的陷阱，触碰即死。
    """

    def __init__(self, path: list[tuple[int, int]], move_interval: int = 3):
        """
        Args:
            path: 巡逻路径点列表 [(x1,y1), (x2,y2), ...]
            move_interval: 每多少帧移动一步
        """
        self.path = path
        self.path_index = 0
        self.move_interval = move_interval
        self._tick_counter = 0
        self._forward = True  # 巡逻方向（来回巡逻）

    @property
    def pos(self) -> tuple[int, int]:
        return self.path[self.path_index]

    def update(self) -> None:
        """每帧调用，按间隔移动。"""
        self._tick_counter += 1
        if self._tick_counter >= self.move_interval:
            self._tick_counter = 0
            self._move_one_step()

    def _move_one_step(self) -> None:
        """沿路径移动一步（来回巡逻）。"""
        if self._forward:
            if self.path_index < len(self.path) - 1:
                self.path_index += 1
            else:
                self._forward = False
                self.path_index -= 1
        else:
            if self.path_index > 0:
                self.path_index -= 1
            else:
                self._forward = True
                self.path_index += 1

    def predict_positions(self, steps_ahead: int) -> list[tuple[int, int]]:
        """
        预测未来 N 步的位置（用于 AI 避障）。
        注意：这是一个近似预测，假设陷阱沿当前方向继续移动。
        """
        positions = []
        idx = self.path_index
        forward = self._forward
        for _ in range(steps_ahead):
            if forward:
                if idx < len(self.path) - 1:
                    idx += 1
                else:
                    forward = False
                    idx -= 1
            else:
                if idx > 0:
                    idx -= 1
                else:
                    forward = True
                    idx += 1
            positions.append(self.path[idx])
        return positions

    def occupies(self, x: int, y: int) -> bool:
        """检查陷阱是否占据某格子。"""
        return self.pos == (x, y)

    def __repr__(self):
        return f"Trap(path={self.path}, at={self.pos})"


# ============================================================
# 高级食物
# ============================================================
class PremiumFood:
    """高价值食物（3 分），通常放置在门后。"""

    def __init__(self, x: int, y: int):
        self.pos = (x, y)
        self.value = 3

    def __repr__(self):
        return f"PremiumFood({self.pos})"


# ============================================================
# 实体生成工具
# ============================================================
def generate_entities(
    level: int,
    occupied: set[tuple[int, int]],
) -> tuple[list[Key], list[Door], list[OneWayPassage],
           list[MovingTrap], list[PremiumFood]]:
    """
    根据关卡等级生成实体。

    Args:
        level: 当前关卡 (1-based)。
        occupied: 已被占用的格子集合（蛇身+障碍物）。

    Returns:
        (keys, doors, passages, traps, premium_foods)
    """
    config = _get_level_config(level)
    available = [
        (x, y) for x in range(cfg.COLS) for y in range(cfg.ROWS)
        if (x, y) not in occupied
    ]

    keys = _spawn_keys(config["keys"], available, occupied)
    occupied.update(k.pos for k in keys)

    doors = _spawn_doors(config["doors"], keys, available, occupied)
    occupied.update(d.pos for d in doors)

    premium = _spawn_premium(config["premium"], doors, available, occupied)
    occupied.update(p.pos for p in premium)

    passages = _spawn_passages(config["passages"], available, occupied)
    occupied.update(p.pos for p in passages)

    traps = _spawn_traps(config["traps"], available, occupied)
    for t in traps:
        for pt in t.path:
            occupied.add(pt)

    return keys, doors, passages, traps, premium


def _get_level_config(level: int) -> dict:
    """获取某关卡的实体数量配置。"""
    if level <= 1:
        return {"keys": 0, "doors": 0, "traps": 0, "passages": 0, "premium": 0}
    elif level == 2:
        return {"keys": 0, "doors": 0, "traps": 1, "passages": 0, "premium": 0}
    elif level == 3:
        return {"keys": 1, "doors": 1, "traps": 0, "passages": 0, "premium": 1}
    elif level == 4:
        return {"keys": 1, "doors": 1, "traps": 1, "passages": 0, "premium": 1}
    elif level == 5:
        return {"keys": 2, "doors": 2, "traps": 1, "passages": 1, "premium": 2}
    else:
        # level 6+ 逐步增加
        extra = (level - 5) // 2
        return {
            "keys": min(3, 2 + extra),
            "doors": min(3, 2 + extra),
            "traps": min(3, 1 + extra),
            "passages": min(2, 1 + extra // 2),
            "premium": min(3, 2 + extra),
        }


def _spawn_keys(count: int, available: list, occupied: set) -> list[Key]:
    """生成钥匙，每种颜色最多一把。"""
    colors = ["blue", "red", "yellow"][:count]
    keys = []
    avail = [p for p in available if p not in occupied]
    for color in colors:
        if avail:
            pos = random.choice(avail)
            keys.append(Key(pos[0], pos[1], color))
            avail.remove(pos)
    return keys


def _spawn_doors(count: int, keys: list[Key], available: list,
                 occupied: set) -> list[Door]:
    """生成门，颜色与已有的钥匙匹配。"""
    if not keys:
        return []
    doors = []
    avail = [p for p in available if p not in occupied]
    for key in keys[:count]:
        # 门放在地图边缘附近，形成"屏障"效果
        candidates = [p for p in avail
                      if _is_near_edge(p) and not _is_too_close(p, key.pos)]
        if not candidates:
            candidates = [p for p in avail if not _is_too_close(p, key.pos)]
        if candidates:
            pos = random.choice(candidates)
            doors.append(Door(pos[0], pos[1], key.color))
            avail.remove(pos)
    return doors


def _spawn_premium(count: int, doors: list[Door], available: list,
                   occupied: set) -> list[PremiumFood]:
    """生成高级食物，尽量放在门后方。"""
    premium = []
    avail = [p for p in available if p not in occupied]
    for door in doors[:count]:
        # 放在门附近（模拟"门后"）
        candidates = _get_behind_door(door, avail)
        if not candidates:
            candidates = avail
        if candidates:
            pos = random.choice(candidates)
            premium.append(PremiumFood(pos[0], pos[1]))
            if pos in avail:
                avail.remove(pos)
    # 如果 premium 数量不足，随机补充
    while len(premium) < count and avail:
        pos = random.choice(avail)
        premium.append(PremiumFood(pos[0], pos[1]))
        avail.remove(pos)
    return premium


def _spawn_passages(count: int, available: list,
                    occupied: set) -> list[OneWayPassage]:
    """生成单向通道。"""
    passages = []
    avail = [p for p in available if p not in occupied]
    directions = list(cfg.DIRECTIONS)
    for _ in range(count):
        if not avail:
            break
        pos = random.choice(avail)
        entry = random.choice(directions)
        passages.append(OneWayPassage(pos[0], pos[1], entry))
        avail.remove(pos)
    return passages


def _spawn_traps(count: int, available: list,
                 occupied: set) -> list[MovingTrap]:
    """生成移动陷阱（含巡逻路径）。"""
    traps = []
    avail = [p for p in available if p not in occupied]
    # 陷阱路径上的点也暂时标记为不可用
    used = set()

    for _ in range(count):
        if not avail:
            break
        start = random.choice(avail)
        # 生成长度 3~6 的水平或垂直巡逻路径
        path = _generate_patrol_path(start, avail, used)
        if path and len(path) >= 2:
            traps.append(MovingTrap(path, move_interval=random.randint(2, 4)))
            for pt in path:
                used.add(pt)
                if pt in avail:
                    avail.remove(pt)
    return traps


def _generate_patrol_path(start: tuple, avail: list, used: set
                          ) -> list[tuple[int, int]]:
    """生成一条水平或垂直的短路径。"""
    horizontal = random.choice([True, False])
    length = random.randint(3, 6)
    path = [start]

    for step in range(1, length):
        if horizontal:
            candidates = [
                (start[0] + step, start[1]),
                (start[0] - step, start[1]),
            ]
        else:
            candidates = [
                (start[0], start[1] + step),
                (start[0], start[1] - step),
            ]

        # 两个方向各尝试
        found = False
        random.shuffle(candidates)
        for c in candidates:
            if (0 <= c[0] < cfg.COLS and 0 <= c[1] < cfg.ROWS
                    and c in avail and c not in used
                    and abs(c[0] - start[0]) + abs(c[1] - start[1]) == step):
                # 检查中间点也可用
                path.append(c)
                found = True
                break
        if not found:
            break

    # 保证路径至少 2 个点
    return path if len(path) >= 2 else []


# ============================================================
# 辅助函数
# ============================================================
def _is_near_edge(pos: tuple[int, int]) -> bool:
    """判断某点是否靠近地图边缘（3 格内）。"""
    x, y = pos
    margin = 3
    return (x <= margin or x >= cfg.COLS - 1 - margin or
            y <= margin or y >= cfg.ROWS - 1 - margin)


def _is_too_close(pos1: tuple[int, int], pos2: tuple[int, int],
                  min_dist: int = 5) -> bool:
    """两个位置是否太近（曼哈顿距离）。"""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1]) < min_dist


def _get_behind_door(door: Door, candidates: list) -> list[tuple[int, int]]:
    """获取门'后方'的候选位置（门的对角方向）。"""
    # 简单策略：距离门 1~3 格的位置
    behind = []
    for pos in candidates:
        dist = abs(pos[0] - door.pos[0]) + abs(pos[1] - door.pos[1])
        if 1 <= dist <= 4 and pos != door.pos:
            behind.append(pos)
    return behind if behind else candidates
