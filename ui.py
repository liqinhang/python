"""
贪吃蛇大作战 — 界面层
======================
所有画面的绘制、按钮交互、文字输入组件、HUD、排行榜展示。
纯 Pygame 原生绘制，零外部 UI 库依赖。
"""

from typing import Any
import pygame

import config as cfg


# ============================================================
# 字体缓存（避免反复创建字体对象）
# ============================================================
_font_cache: dict[tuple[str, int], pygame.font.Font] = {}


def _get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """获取系统默认中文字体（带缓存）。"""
    key = ("default", size, bold)
    if key not in _font_cache:
        font_name = _find_chinese_font()
        _font_cache[key] = pygame.font.Font(font_name, size)
        _font_cache[key].bold = bold
    return _font_cache[key]


def _find_chinese_font() -> str:
    """查找可用的中文字体文件路径。"""
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",       # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",      # 黑体
        "C:/Windows/Fonts/simsun.ttc",      # 宋体
        "C:/Windows/Fonts/simkai.ttf",      # 楷体
        "C:/Windows/Fonts/Deng.ttf",        # 等线
        None,  # 使用 pygame 默认字体（可能不含中文）
    ]
    import os
    for name in candidates:
        if name is None:
            return pygame.font.get_default_font()
        if os.path.exists(name):
            return name
    return pygame.font.get_default_font()


# ============================================================
# 颜色工具
# ============================================================
def _lerp_color(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """两颜色线性插值。"""
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


# ============================================================
# 按钮
# ============================================================
class Button:
    """通用按钮：矩形区域 + 文字 + 悬停/点击状态。"""

    def __init__(self, x: int, y: int, w: int, h: int, text: str,
                 font_size: int = 28,
                 base_color: tuple = cfg.DARK_GRAY,
                 hover_color: tuple = cfg.GRAY,
                 text_color: tuple = cfg.WHITE,
                 border_color: tuple = cfg.LIGHT_GRAY,
                 border_radius: int = 8):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font_size = font_size
        self.base_color = base_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.border_color = border_color
        self.border_radius = border_radius
        self.is_hovered = False

    def update(self, mouse_pos: tuple[int, int]) -> None:
        """根据鼠标位置更新悬停状态。"""
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, screen: pygame.Surface) -> None:
        """绘制按钮。"""
        color = self.hover_color if self.is_hovered else self.base_color
        # 按钮主体
        pygame.draw.rect(screen, color, self.rect, border_radius=self.border_radius)
        # 边框
        pygame.draw.rect(screen, self.border_color, self.rect, width=2, border_radius=self.border_radius)
        # 文字居中
        font = _get_font(self.font_size)
        text_surf = font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def is_clicked(self, event: pygame.event.Event) -> bool:
        """判断按钮是否被点击。"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.is_hovered
        return False


# ============================================================
# 文字输入组件
# ============================================================
class TextInput:
    """手写文字输入框，支持光标闪烁。"""

    def __init__(self, x: int, y: int, w: int, h: int,
                 max_length: int = cfg.MAX_NAME_LENGTH,
                 placeholder: str = "请输入昵称..."):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = ""
        self.max_length = max_length
        self.placeholder = placeholder
        self.active = True
        self._cursor_timer = 0
        self._cursor_visible = True
        self._blink_interval = 500  # ms

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """
        处理输入事件。返回 "submit" / "cancel" / None。
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                return "submit"
            elif event.key == pygame.K_ESCAPE:
                return "cancel"
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif len(self.text) < self.max_length:
                # 允许字母、数字、中文、下划线、空格
                if event.unicode.isprintable():
                    self.text += event.unicode
        return None

    def update(self, dt_ms: int) -> None:
        """更新光标闪烁计时器。"""
        self._cursor_timer += dt_ms
        if self._cursor_timer >= self._blink_interval:
            self._cursor_timer = 0
            self._cursor_visible = not self._cursor_visible

    def draw(self, screen: pygame.Surface) -> None:
        """绘制输入框。"""
        # 背景
        bg_color = (60, 60, 80) if self.active else (40, 40, 50)
        pygame.draw.rect(screen, bg_color, self.rect, border_radius=6)
        pygame.draw.rect(screen, cfg.LIGHT_GRAY, self.rect, width=2, border_radius=6)

        # 文字
        font = _get_font(24)
        display_text = self.text if self.text else self.placeholder
        text_color = cfg.WHITE if self.text else cfg.GRAY
        text_surf = font.render(display_text, True, text_color)
        text_rect = text_surf.get_rect(midleft=(self.rect.x + 12, self.rect.centery))
        screen.blit(text_surf, text_rect)

        # 光标
        if self.active and self._cursor_visible and self.text:
            cursor_x = text_rect.right + 2
            cursor_y = self.rect.y + 10
            cursor_h = self.rect.h - 20
            pygame.draw.line(screen, cfg.WHITE,
                             (cursor_x, cursor_y),
                             (cursor_x, cursor_y + cursor_h), width=2)


# ============================================================
# 主菜单
# ============================================================
def draw_main_menu(screen: pygame.Surface, current_skin_key: str = cfg.DEFAULT_SKIN) -> dict[str, Button]:
    """绘制主菜单，返回按钮字典。"""
    screen.fill((10, 10, 30))

    # 标题
    title_font = _get_font(48, bold=True)
    title_surf = title_font.render("贪吃蛇大作战", True, cfg.GREEN)
    title_rect = title_surf.get_rect(center=(cfg.SCREEN_WIDTH // 2, 100))
    screen.blit(title_surf, title_rect)

    # 副标题
    sub_font = _get_font(18)
    sub_surf = sub_font.render("Python 大作业 | Pygame + FastAPI", True, cfg.LIGHT_GRAY)
    sub_rect = sub_surf.get_rect(center=(cfg.SCREEN_WIDTH // 2, 150))
    screen.blit(sub_surf, sub_rect)

    # 按钮
    btn_w, btn_h = 260, 55
    btn_x = cfg.SCREEN_WIDTH // 2 - btn_w // 2
    spacing = 20

    buttons = {}
    labels = [
        ("start", "开始游戏"),
        ("skin", "选择皮肤"),
        ("leaderboard", "排行榜"),
        ("quit", "退出游戏"),
    ]
    for i, (key, label) in enumerate(labels):
        y = 210 + i * (btn_h + spacing)
        btn = Button(btn_x, y, btn_w, btn_h, label,
                     font_size=26,
                     base_color=(30, 40, 60),
                     hover_color=(50, 70, 110))
        buttons[key] = btn

    # -------- 操作说明 --------
    guide_font = _get_font(15)
    guide_color = (160, 170, 200)
    guide_lines = [
        ("[K]", "W A S D / 方向键 — 控制蛇的移动"),
        ("[AI]", "空格键 — 切换 手动 / AI 自动寻路 模式"),
        ("[P]", "P 键 — 暂停 / 继续游戏"),
    ]
    guide_start_y = 520
    for i, (icon, desc) in enumerate(guide_lines):
        line = f"{icon}  {desc}"
        guide_surf = guide_font.render(line, True, guide_color)
        guide_rect = guide_surf.get_rect(center=(cfg.SCREEN_WIDTH // 2, guide_start_y + i * 24))
        screen.blit(guide_surf, guide_rect)

    # 底部提示 — 显示当前皮肤名称
    skin_name = cfg.SKINS.get(current_skin_key, {}).get("name", "经典")
    hint_font = _get_font(13)
    hint_text = f"当前皮肤: {skin_name}"
    hint_surf = hint_font.render(hint_text, True, cfg.GRAY)
    hint_rect = hint_surf.get_rect(center=(cfg.SCREEN_WIDTH // 2, cfg.SCREEN_HEIGHT - 18))
    screen.blit(hint_surf, hint_rect)

    return buttons


# ============================================================
# 皮肤选择界面
# ============================================================
def draw_skin_select(
    screen: pygame.Surface,
    current_skin_key: str,
) -> tuple[dict[str, Button], Button, dict[str, tuple]]:
    """
    绘制皮肤选择画面。
    返回: (皮肤按钮字典, 返回按钮, {key: 预览颜色数据})
    """
    screen.fill((10, 10, 30))

    # 标题
    title_font = _get_font(36, bold=True)
    title_surf = title_font.render("选择皮肤", True, cfg.WHITE)
    title_rect = title_surf.get_rect(center=(cfg.SCREEN_WIDTH // 2, 50))
    screen.blit(title_surf, title_rect)

    skin_buttons = {}
    btn_w, btn_h = 280, 70
    btn_x = cfg.SCREEN_WIDTH // 2 - btn_w // 2
    preview_colors = {}

    for i, (key, skin) in enumerate(cfg.SKINS.items()):
        y = 110 + i * (btn_h + 18)
        is_current = (key == current_skin_key)
        label = f"{'> ' if is_current else ''}{skin['name']}"
        btn = Button(btn_x, y, btn_w, btn_h, label,
                     font_size=24,
                     base_color=skin["bg"],
                     hover_color=_lerp_color(skin["bg"], cfg.WHITE, 0.3),
                     text_color=skin["head"],
                     border_color=skin["head"] if is_current else skin["obstacle_border"])
        skin_buttons[key] = btn

        # 预览颜色数据（在按钮右侧画小方块）
        preview_colors[key] = {
            "head": skin["head"],
            "body": skin["body"],
            "food": skin["food"],
            "obstacle": skin["obstacle"],
            "bg": skin["bg"],
        }

    # 返回按钮
    back_btn = Button(cfg.SCREEN_WIDTH // 2 - btn_w // 2,
                      cfg.SCREEN_HEIGHT - 80,
                      btn_w, 50, "<< 返回主菜单",
                      font_size=22,
                      base_color=(50, 20, 20),
                      hover_color=(80, 40, 40))

    return skin_buttons, back_btn, preview_colors


def draw_skin_preview(screen: pygame.Surface, x: int, y: int,
                      colors: dict[str, tuple[int, int, int]]) -> None:
    """在指定位置绘制皮肤预览色块。"""
    labels = ["蛇头", "蛇身", "食物", "障碍"]
    color_keys = ["head", "body", "food", "obstacle"]
    swatch_size = 20
    font = _get_font(14)

    for i, (label, ck) in enumerate(zip(labels, color_keys)):
        ox = x + i * 90
        # 色块
        pygame.draw.rect(screen, colors[ck], (ox, y, swatch_size, swatch_size))
        pygame.draw.rect(screen, cfg.WHITE, (ox, y, swatch_size, swatch_size), width=1)
        # 标签
        txt = font.render(label, True, cfg.LIGHT_GRAY)
        screen.blit(txt, (ox + swatch_size + 5, y + 2))


# ============================================================
# 游戏画面绘制
# ============================================================
def draw_game(screen: pygame.Surface, game, skin_key: str) -> None:
    """绘制游戏网格区域：蛇、食物、障碍物、门、钥匙、陷阱、高级食物。"""
    skin = cfg.SKINS[skin_key]

    # 背景（网格区域从 HUD 下方开始）
    grid_rect = pygame.Rect(0, cfg.HUD_HEIGHT, cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT - cfg.HUD_HEIGHT)
    screen.fill(skin["bg"], grid_rect)

    # 网格线
    _draw_grid(screen, skin["grid"])

    # 单向通道
    for p in game.one_way_passages:
        _draw_one_way_passage(screen, p, skin)

    # 障碍物
    for ox, oy in game.obstacles:
        _draw_obstacle(screen, ox, oy, skin)

    # 关闭的门
    for door in game.doors:
        if not door.is_open:
            _draw_door(screen, door, skin)

    # 钥匙
    for key in game.keys_on_map:
        _draw_key(screen, key.pos[0], key.pos[1], key.color)

    # 移动陷阱
    for trap in game.moving_traps:
        _draw_moving_trap(screen, trap.pos[0], trap.pos[1])

    # 食物
    fx, fy = game.food_pos
    _draw_food(screen, fx, fy, skin)

    # 高级食物
    for pf in game.premium_foods:
        _draw_premium_food(screen, pf.pos[0], pf.pos[1])

    # 蛇身
    for i, (sx, sy) in enumerate(game.snake_body):
        is_head = (i == 0)
        _draw_snake_segment(screen, sx, sy, skin, is_head)


def _draw_grid(screen: pygame.Surface, color: tuple[int, int, int]) -> None:
    """绘制网格线。"""
    for x in range(0, cfg.SCREEN_WIDTH, cfg.GRID_SIZE):
        pygame.draw.line(screen, color,
                         (x, cfg.HUD_HEIGHT), (x, cfg.SCREEN_HEIGHT), 1)
    for y in range(cfg.HUD_HEIGHT, cfg.SCREEN_HEIGHT, cfg.GRID_SIZE):
        pygame.draw.line(screen, color,
                         (0, y), (cfg.SCREEN_WIDTH, y), 1)


def _draw_snake_segment(screen: pygame.Surface, gx: int, gy: int,
                        skin: dict, is_head: bool) -> None:
    """绘制蛇的一个身体段。"""
    px = gx * cfg.GRID_SIZE
    py = gy * cfg.GRID_SIZE + cfg.HUD_HEIGHT
    inner_margin = 1

    color = skin["head"] if is_head else skin["body"]
    rect = pygame.Rect(px + inner_margin, py + inner_margin,
                       cfg.GRID_SIZE - inner_margin * 2,
                       cfg.GRID_SIZE - inner_margin * 2)
    pygame.draw.rect(screen, color, rect, border_radius=4)

    # 蛇头画眼睛
    if is_head:
        eye_r = 3
        eye_color = cfg.BLACK
        center_x = px + cfg.GRID_SIZE // 2
        center_y = py + cfg.GRID_SIZE // 2
        # 两只眼睛
        pygame.draw.circle(screen, eye_color, (center_x - 4, center_y - 3), eye_r)
        pygame.draw.circle(screen, eye_color, (center_x + 4, center_y - 3), eye_r)


def _draw_food(screen: pygame.Surface, gx: int, gy: int,
               skin: dict) -> None:
    """绘制食物。"""
    px = gx * cfg.GRID_SIZE + cfg.GRID_SIZE // 2
    py = gy * cfg.GRID_SIZE + cfg.GRID_SIZE // 2 + cfg.HUD_HEIGHT
    radius = cfg.GRID_SIZE // 2 - 3

    # 主体
    pygame.draw.circle(screen, skin["food"], (px, py), radius)
    # 高光
    hl_r = max(2, radius // 3)
    pygame.draw.circle(screen, (255, 255, 255, 80), (px - 2, py - 2), hl_r)


def _draw_obstacle(screen: pygame.Surface, gx: int, gy: int,
                   skin: dict) -> None:
    """绘制障碍物（粗边框 + X 标记以区别于蛇身/食物）。"""
    px = gx * cfg.GRID_SIZE
    py = gy * cfg.GRID_SIZE + cfg.HUD_HEIGHT
    margin = 2

    rect = pygame.Rect(px + margin, py + margin,
                       cfg.GRID_SIZE - margin * 2,
                       cfg.GRID_SIZE - margin * 2)
    # 内部填充
    pygame.draw.rect(screen, skin["obstacle"], rect, border_radius=2)
    # 边框
    pygame.draw.rect(screen, skin["obstacle_border"], rect, width=2, border_radius=2)

    # X 标记
    inner = 5
    start_tl = (px + inner, py + inner)
    end_br = (px + cfg.GRID_SIZE - inner, py + cfg.GRID_SIZE - inner)
    start_tr = (px + cfg.GRID_SIZE - inner, py + inner)
    end_bl = (px + inner, py + cfg.GRID_SIZE - inner)
    pygame.draw.line(screen, skin["obstacle_border"], start_tl, end_br, 2)
    pygame.draw.line(screen, skin["obstacle_border"], start_tr, end_bl, 2)


# ============================================================
# 实体绘制函数
# ============================================================
def _draw_key(screen: pygame.Surface, gx: int, gy: int, color_key: str) -> None:
    """绘制钥匙（菱形）。"""
    color = cfg.KEY_COLORS.get(color_key, cfg.YELLOW)
    px = gx * cfg.GRID_SIZE + cfg.GRID_SIZE // 2
    py = gy * cfg.GRID_SIZE + cfg.GRID_SIZE // 2 + cfg.HUD_HEIGHT
    s = cfg.GRID_SIZE // 2 - 2
    # 菱形四点
    points = [(px, py - s), (px + s, py), (px, py + s), (px - s, py)]
    pygame.draw.polygon(screen, color, points)
    pygame.draw.polygon(screen, cfg.WHITE, points, width=1)
    # 钥匙孔（小圆）
    pygame.draw.circle(screen, (30, 30, 30), (px, py + s // 3), 2)


def _draw_door(screen: pygame.Surface, door, skin: dict) -> None:
    """绘制门（彩色粗线墙体 + 门锁标记）。"""
    x, y = door.pos
    color = cfg.DOOR_COLORS.get(door.color, cfg.GRAY)
    px = x * cfg.GRID_SIZE
    py = y * cfg.GRID_SIZE + cfg.HUD_HEIGHT
    margin = 1
    # 填充
    rect = pygame.Rect(px + margin, py + margin,
                       cfg.GRID_SIZE - margin * 2,
                       cfg.GRID_SIZE - margin * 2)
    pygame.draw.rect(screen, color, rect, border_radius=2)
    pygame.draw.rect(screen, cfg.WHITE, rect, width=2, border_radius=2)
    # 锁孔标记
    cx, cy = px + cfg.GRID_SIZE // 2, py + cfg.GRID_SIZE // 2
    pygame.draw.circle(screen, cfg.BLACK, (cx, cy), 3)
    pygame.draw.rect(screen, cfg.BLACK, (cx - 2, cy, 4, 4))


def _draw_one_way_passage(screen: pygame.Surface, passage, skin: dict) -> None:
    """绘制单向通道（方向箭头）。"""
    x, y = passage.pos
    px = x * cfg.GRID_SIZE
    py = y * cfg.GRID_SIZE + cfg.HUD_HEIGHT
    # 半透明底色
    s = pygame.Surface((cfg.GRID_SIZE, cfg.GRID_SIZE), pygame.SRCALPHA)
    s.fill((*cfg.ONE_WAY_COLOR, 80))
    screen.blit(s, (px, py))
    # 方向箭头
    cx, cy = px + cfg.GRID_SIZE // 2, py + cfg.GRID_SIZE // 2
    dx, dy = passage.entry
    arrow_len = cfg.GRID_SIZE // 3
    end_x = cx + dx * arrow_len
    end_y = cy + dy * arrow_len
    pygame.draw.line(screen, cfg.ONE_WAY_COLOR, (cx, cy), (end_x, end_y), 3)
    # 箭头尖
    if dx != 0:
        tip = [(end_x, end_y), (end_x - dx * 5, end_y - 4), (end_x - dx * 5, end_y + 4)]
    else:
        tip = [(end_x, end_y), (end_x - 4, end_y - dy * 5), (end_x + 4, end_y - dy * 5)]
    pygame.draw.polygon(screen, cfg.ONE_WAY_COLOR, tip)


def _draw_moving_trap(screen: pygame.Surface, gx: int, gy: int) -> None:
    """绘制移动陷阱（红色闪烁方块）。"""
    import time
    px = gx * cfg.GRID_SIZE
    py = gy * cfg.GRID_SIZE + cfg.HUD_HEIGHT
    # 闪烁效果
    t = time.time() if hasattr(time, 'time') else 0
    glow = abs(int(t * 3) % 2)  # 0 or 1, toggles
    color = cfg.TRAP_GLOW_COLOR if glow else cfg.TRAP_COLOR
    margin = 1
    rect = pygame.Rect(px + margin, py + margin,
                       cfg.GRID_SIZE - margin * 2,
                       cfg.GRID_SIZE - margin * 2)
    pygame.draw.rect(screen, color, rect, border_radius=3)
    pygame.draw.rect(screen, cfg.WHITE, rect, width=2, border_radius=3)
    # X 标记
    inner = 4
    pygame.draw.line(screen, cfg.WHITE, (px + inner, py + inner),
                     (px + cfg.GRID_SIZE - inner, py + cfg.GRID_SIZE - inner), 2)
    pygame.draw.line(screen, cfg.WHITE, (px + cfg.GRID_SIZE - inner, py + inner),
                     (px + inner, py + cfg.GRID_SIZE - inner), 2)


def _draw_premium_food(screen: pygame.Surface, gx: int, gy: int) -> None:
    """绘制高级食物（金色星形）。"""
    px = gx * cfg.GRID_SIZE + cfg.GRID_SIZE // 2
    py = gy * cfg.GRID_SIZE + cfg.GRID_SIZE // 2 + cfg.HUD_HEIGHT
    r_outer = cfg.GRID_SIZE // 2 - 2
    r_inner = r_outer // 2
    points = []
    import math
    for i in range(10):
        angle = math.pi / 2 - i * math.pi / 5
        r = r_outer if i % 2 == 0 else r_inner
        points.append((px + int(r * math.cos(angle)),
                       py - int(r * math.sin(angle))))
    pygame.draw.polygon(screen, cfg.PREMIUM_FOOD_COLOR, points)
    pygame.draw.polygon(screen, cfg.PREMIUM_FOOD_GLOW, points, width=1)


# ============================================================
# HUD 信息栏
# ============================================================
def draw_hud(screen: pygame.Surface, game, skin_key: str) -> None:
    """绘制顶部信息栏：分数、速度、模式、皮肤、背包。"""
    skin = cfg.SKINS[skin_key]
    hud_rect = pygame.Rect(0, 0, cfg.SCREEN_WIDTH, cfg.HUD_HEIGHT)
    pygame.draw.rect(screen, skin["hud_bg"], hud_rect)
    pygame.draw.line(screen, skin["grid"], (0, cfg.HUD_HEIGHT), (cfg.SCREEN_WIDTH, cfg.HUD_HEIGHT), 2)

    font = _get_font(16)
    mode_text = "[AI]" if game.is_ai_mode else "[手动]"

    # 背包描述文本
    inv_parts = []
    for color, count in game.inventory.items():
        if count > 0:
            color_names = {"blue": "蓝", "red": "红", "yellow": "黄"}
            inv_parts.append(f"{color_names.get(color, color)}:{count}")
    inv_text = "背包: " + (" ".join(inv_parts) if inv_parts else "-")

    items = [
        f"分数: {game.score}",
        f"关卡: {game.level}",
        f"速度: {game.speed}",
        f"模式: {mode_text}",
        inv_text,
        f"皮肤: {skin['name']}",
    ]

    spacing = cfg.SCREEN_WIDTH // len(items)
    for i, text in enumerate(items):
        color = skin["hud_text"]
        if "背包" in text:
            color = cfg.GOLD
        elif "皮肤" in text:
            color = skin["food"]
        surf = font.render(text, True, color)
        rect = surf.get_rect(midleft=(5 + i * spacing, cfg.HUD_HEIGHT // 2))
        screen.blit(surf, rect)


# ============================================================
# 暂停遮罩
# ============================================================
def draw_pause_overlay(screen: pygame.Surface) -> None:
    """绘制暂停半透明遮罩。"""
    overlay = pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))

    font = _get_font(42, bold=True)
    text1 = font.render("游戏暂停", True, cfg.WHITE)
    text1_rect = text1.get_rect(center=(cfg.SCREEN_WIDTH // 2, cfg.SCREEN_HEIGHT // 2 - 50))
    screen.blit(text1, text1_rect)

    font2 = _get_font(20)
    hints = [
        "P 键 — 继续游戏",
        "空格键 — 切换 手动 / AI 模式",
        "Q 键 — 返回主菜单",
    ]
    for i, hint in enumerate(hints):
        surf = font2.render(hint, True, cfg.LIGHT_GRAY)
        rect = surf.get_rect(center=(cfg.SCREEN_WIDTH // 2, cfg.SCREEN_HEIGHT // 2 + 10 + i * 28))
        screen.blit(surf, rect)


# ============================================================
# 游戏结束画面
# ============================================================
def draw_game_over(
    screen: pygame.Surface,
    score: int,
    high_score: int,
    is_won: bool,
    input_component: TextInput,
    leaderboard_data: list[dict] | None,
    submission_status: str,  # "" / "success" / "fail"
) -> None:
    """绘制游戏结束/结算画面。"""
    screen.fill((10, 10, 35))

    # 标题
    title_text = "*** 恭喜通关！***" if is_won else "游戏结束"
    title_color = cfg.GOLD if is_won else cfg.RED
    title_font = _get_font(40, bold=True)
    title_surf = title_font.render(title_text, True, title_color)
    title_rect = title_surf.get_rect(center=(cfg.SCREEN_WIDTH // 2, 55))
    screen.blit(title_surf, title_rect)

    # 分数信息
    info_font = _get_font(24)
    info_lines = [
        f"最终分数: {score}",
        f"历史最高: {high_score}",
    ]
    if score >= high_score and score > 0:
        info_lines.append("--- 新纪录！---")

    for i, line in enumerate(info_lines):
        color = cfg.GOLD if "新纪录" in line else cfg.WHITE
        surf = info_font.render(line, True, color)
        rect = surf.get_rect(center=(cfg.SCREEN_WIDTH // 2, 110 + i * 35))
        screen.blit(surf, rect)

    # 输入框
    input_y = 210
    prompt = _get_font(18).render("输入昵称上传分数:", True, cfg.LIGHT_GRAY)
    prompt_rect = prompt.get_rect(center=(cfg.SCREEN_WIDTH // 2, input_y - 20))
    screen.blit(prompt, prompt_rect)
    input_component.draw(screen)

    # 提交状态
    if submission_status == "success":
        status_text = "[OK] 分数已成功上传！"
        status_color = cfg.GREEN
    elif submission_status == "fail":
        status_text = "[X] 服务器连接失败，分数仅保存在本地"
        status_color = cfg.ORANGE
    else:
        status_text = ""
        status_color = cfg.WHITE

    if status_text:
        status_surf = _get_font(16).render(status_text, True, status_color)
        status_rect = status_surf.get_rect(center=(cfg.SCREEN_WIDTH // 2, input_y + 55))
        screen.blit(status_surf, status_rect)

    # 操作提示
    hint_font = _get_font(16)
    hints = [
        "Enter — 提交分数  |  Esc — 返回主菜单",
    ]
    for i, hint in enumerate(hints):
        hint_surf = hint_font.render(hint, True, cfg.GRAY)
        hint_rect = hint_surf.get_rect(center=(cfg.SCREEN_WIDTH // 2, cfg.SCREEN_HEIGHT - 30))
        screen.blit(hint_surf, hint_rect)


# ============================================================
# 排行榜界面
# ============================================================
def draw_leaderboard(
    screen: pygame.Surface,
    data: list[dict] | None,
    back_button: Button,
) -> None:
    """绘制排行榜界面。"""
    screen.fill((10, 10, 30))

    title_font = _get_font(36, bold=True)
    title_surf = title_font.render("排行榜", True, cfg.GOLD)
    title_rect = title_surf.get_rect(center=(cfg.SCREEN_WIDTH // 2, 45))
    screen.blit(title_surf, title_rect)

    font = _get_font(22)
    if data is None:
        # 加载失败
        err_surf = font.render("无法连接服务器，请确认后端已启动", True, cfg.ORANGE)
        err_rect = err_surf.get_rect(center=(cfg.SCREEN_WIDTH // 2, cfg.SCREEN_HEIGHT // 2 - 30))
        screen.blit(err_surf, err_rect)
    elif not data:
        empty_surf = font.render("暂无排行数据", True, cfg.GRAY)
        empty_rect = empty_surf.get_rect(center=(cfg.SCREEN_WIDTH // 2, cfg.SCREEN_HEIGHT // 2 - 30))
        screen.blit(empty_surf, empty_rect)
    else:
        # 表头
        header_font = _get_font(20)
        header_surf = header_font.render(f"{'排名':<6}{'昵称':<20}{'分数':>8}", True, cfg.LIGHT_GRAY)
        header_rect = header_surf.get_rect(center=(cfg.SCREEN_WIDTH // 2, 100))
        screen.blit(header_surf, header_rect)

        # 分隔线
        pygame.draw.line(screen, cfg.GRAY,
                         (cfg.SCREEN_WIDTH // 2 - 200, 125),
                         (cfg.SCREEN_WIDTH // 2 + 200, 125), 1)

        # 排行榜条目
        medals = ["1st", "2nd", "3rd"]
        for i, entry in enumerate(data):
            y = 140 + i * 40
            medal = medals[i] if i < 3 else f"{i+1:>2}."
            line = f"{medal}  {entry['name']:<16}  {entry['score']:>6}"
            color = cfg.GOLD if i == 0 else cfg.WHITE
            line_surf = font.render(line, True, color)
            line_rect = line_surf.get_rect(center=(cfg.SCREEN_WIDTH // 2, y))
            screen.blit(line_surf, line_rect)

    # 返回按钮
    back_button.draw(screen)
