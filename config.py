"""
贪吃蛇大作战 — 全局配置与常量
==============================
屏幕参数、网格系统、皮肤定义、颜色、音效参数、服务器地址等。
"""

# ============================================================
# 屏幕与网格
# ============================================================
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GRID_SIZE = 20                      # 每个格子的像素边长
COLS = SCREEN_WIDTH // GRID_SIZE    # 40
ROWS = SCREEN_HEIGHT // GRID_SIZE   # 30
TOTAL_CELLS = COLS * ROWS           # 1200（用于判断胜利条件）
HUD_HEIGHT = 40                     # 顶部信息栏高度（从网格区域上方扣除）

# ============================================================
# 四个方向（网格坐标系：x 向右, y 向下）
# ============================================================
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
DIRECTIONS = [UP, DOWN, LEFT, RIGHT]

# ============================================================
# 颜色常量 (RGB)
# ============================================================
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
LIGHT_GRAY = (180, 180, 180)
DARK_GRAY = (40, 40, 40)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
BLUE = (50, 100, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (160, 50, 200)

# 霓虹色系
NEON_GREEN = (0, 255, 100)
NEON_PINK = (255, 0, 150)
NEON_BLUE = (0, 200, 255)

# 皮肤色系
DEEP_BLUE = (20, 60, 180)
FIRE_RED = (255, 80, 0)
GOLD = (255, 215, 0)

# 半透明色（用于遮罩）
OVERLAY_BG = (0, 0, 0, 180)  # RGBA，但 pygame surface 的 alpha 需要特殊处理

# ============================================================
# 皮肤定义
# ============================================================
SKINS = {
    "classic": {
        "name": "经典",
        "head": GREEN,
        "body": (34, 139, 34),       # 森林绿
        "food": RED,
        "obstacle": GRAY,
        "obstacle_border": DARK_GRAY,
        "bg": BLACK,
        "grid": (20, 20, 20),
        "hud_bg": (15, 15, 15),
        "hud_text": WHITE,
    },
    "neon": {
        "name": "霓虹",
        "head": NEON_GREEN,
        "body": (0, 180, 80),
        "food": NEON_PINK,
        "obstacle": (100, 0, 100),
        "obstacle_border": (180, 0, 180),
        "bg": (10, 0, 20),
        "grid": (30, 0, 40),
        "hud_bg": (15, 0, 25),
        "hud_text": NEON_GREEN,
    },
    "deepsea": {
        "name": "深海",
        "head": (255, 200, 50),      # 金黄色鱼头
        "body": DEEP_BLUE,
        "food": GOLD,
        "obstacle": (40, 40, 100),
        "obstacle_border": (80, 80, 160),
        "bg": (5, 10, 30),
        "grid": (15, 20, 50),
        "hud_bg": (8, 13, 35),
        "hud_text": (200, 220, 255),
    },
    "flame": {
        "name": "烈焰",
        "head": (255, 255, 100),     # 亮黄蛇头
        "body": FIRE_RED,
        "food": GOLD,
        "obstacle": (80, 20, 20),
        "obstacle_border": (140, 40, 40),
        "bg": (30, 5, 5),
        "grid": (50, 15, 15),
        "hud_bg": (35, 8, 8),
        "hud_text": (255, 200, 150),
    },
}

SKIN_KEYS = list(SKINS.keys())       # 方便索引
DEFAULT_SKIN = "classic"

# ============================================================
# 实体颜色（门 / 钥匙 / 陷阱 / 高级食物 / 单向通道）
# ============================================================
KEY_COLORS = {
    "blue": (50, 100, 255),
    "red": (255, 50, 50),
    "yellow": (255, 215, 0),
}
DOOR_COLORS = KEY_COLORS
TRAP_COLOR = (255, 30, 30)
TRAP_GLOW_COLOR = (255, 100, 100)
PREMIUM_FOOD_COLOR = (255, 215, 0)
PREMIUM_FOOD_GLOW = (255, 255, 150)
ONE_WAY_COLOR = (100, 200, 255)
INVENTORY_COLORS = KEY_COLORS  # HUD 背包显示用

# ============================================================
# 游戏参数
# ============================================================
INITIAL_SPEED = 8                    # 初始帧率（每秒移动次数）
MIN_SPEED = 5
MAX_SPEED = 30
SPEED_INCREMENT = 2                  # 每次升级增加的速度
SCORE_PER_LEVEL = 5                  # 每吃几个食物升一级
MAX_OBSTACLES = 25                   # 障碍物数量上限
INITIAL_SNAKE_LENGTH = 3             # 蛇的初始长度

# 输入限制
MAX_NAME_LENGTH = 12

# ============================================================
# 音效参数
# ============================================================
SAMPLE_RATE = 44100
EAT_FREQ = 880
EAT_DURATION = 0.08
EAT_VOLUME = 0.3
DIE_FREQ_START = 300
DIE_FREQ_END = 80
DIE_DURATION = 0.4
DIE_VOLUME = 0.35

# ============================================================
# 网络
# ============================================================
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
REQUEST_TIMEOUT = 3                  # 网络请求超时（秒）

# ============================================================
# 游戏状态枚举
# ============================================================
STATE_MAIN_MENU = "main_menu"
STATE_SKIN_SELECT = "skin_select"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_GAME_OVER = "game_over"
STATE_LEADERBOARD = "leaderboard"
