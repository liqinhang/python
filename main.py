"""
贪吃蛇大作战 — 游戏入口
========================
初始化 Pygame、生成音效、管理游戏状态机、调度所有模块。

操作说明：
  方向键  — 控制蛇的移动
  空格键  — 切换 手动/AI 模式
  P 键   — 暂停/继续
  Q 键   — 暂停时返回主菜单
  Esc    — 取消/返回
  Enter  — 确认/提交
  鼠标    — 菜单选择
"""

import sys
import numpy as np
import pygame

import config as cfg
from game import SnakeGame
from ai import get_ai_direction, get_ai_direction_enhanced
from ui import (
    Button,
    TextInput,
    draw_main_menu,
    draw_skin_select,
    draw_skin_preview,
    draw_game,
    draw_hud,
    draw_pause_overlay,
    draw_game_over,
    draw_leaderboard,
)
from network import submit_score, fetch_leaderboard


# ============================================================
# 音效生成（纯代码，无需外部文件）
# ============================================================
def _generate_beep(frequency: float, duration: float,
                   sample_rate: int = cfg.SAMPLE_RATE,
                   volume: float = 0.3) -> pygame.mixer.Sound:
    """生成一个正弦波音效。"""
    t = np.arange(0, duration, 1.0 / sample_rate)
    wave = np.sin(2.0 * np.pi * frequency * t) * volume * 32767
    wave = wave.astype(np.int16)
    stereo = np.column_stack([wave, wave])
    return pygame.sndarray.make_sound(stereo)


def _generate_chirp(freq_start: float, freq_end: float, duration: float,
                    sample_rate: int = cfg.SAMPLE_RATE,
                    volume: float = 0.35) -> pygame.mixer.Sound:
    """生成一个频率滑变的音效（用于死亡声）。"""
    t = np.arange(0, duration, 1.0 / sample_rate)
    # 频率从 freq_start 线性下降到 freq_end
    freq = freq_start + (freq_end - freq_start) * (t / duration)
    phase = 2.0 * np.pi * np.cumsum(freq) / sample_rate
    wave = np.sin(phase) * volume * 32767
    wave = wave.astype(np.int16)
    stereo = np.column_stack([wave, wave])
    return pygame.sndarray.make_sound(stereo)


def create_sounds() -> tuple[pygame.mixer.Sound, pygame.mixer.Sound]:
    """生成吃食物和死亡音效，返回 (eat_sound, die_sound)。"""
    eat_sound = _generate_beep(
        frequency=cfg.EAT_FREQ,
        duration=cfg.EAT_DURATION,
        volume=cfg.EAT_VOLUME,
    )
    die_sound = _generate_chirp(
        freq_start=cfg.DIE_FREQ_START,
        freq_end=cfg.DIE_FREQ_END,
        duration=cfg.DIE_DURATION,
        volume=cfg.DIE_VOLUME,
    )
    return eat_sound, die_sound


# ============================================================
# 游戏主类
# ============================================================
class GameApp:
    """管理整个游戏的状态机和主循环。"""

    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=cfg.SAMPLE_RATE, size=-16, channels=2)

        self.screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        pygame.display.set_caption("贪吃蛇大作战")
        self.clock = pygame.time.Clock()

        # 音效
        self.eat_sound, self.die_sound = create_sounds()

        # 游戏引擎
        self.game = SnakeGame()

        # 状态
        self.state = cfg.STATE_MAIN_MENU
        self.current_skin = cfg.DEFAULT_SKIN

        # UI 元素（按需初始化）
        self.menu_buttons: dict[str, Button] = {}
        self.skin_buttons: dict[str, Button] = {}
        self.skin_back_btn: Button | None = None
        self.skin_preview_colors: dict = {}
        self.leaderboard_data: list[dict] | None = None
        self.text_input: TextInput | None = None
        self.submission_status = ""  # "" / "success" / "fail"
        self.back_button: Button | None = None

        # 帧时间
        self.last_tick_time = 0
        self.frame_dt_ms = 0

        # 游戏结束处理标志（避免每帧重复提交）
        self._game_over_processed = False

    # ============================================================
    # 主循环
    # ============================================================
    def run(self) -> None:
        """主循环入口。"""
        running = True
        while running:
            self.frame_dt_ms = self.clock.tick(cfg.MAX_SPEED * 2)
            events = pygame.event.get()

            # ---- 全局事件 ----
            for event in events:
                if event.type == pygame.QUIT:
                    running = False

            # ---- 状态分发 ----
            if self.state == cfg.STATE_MAIN_MENU:
                self._handle_main_menu(events)
            elif self.state == cfg.STATE_SKIN_SELECT:
                self._handle_skin_select(events)
            elif self.state == cfg.STATE_PLAYING:
                self._handle_playing(events)
            elif self.state == cfg.STATE_GAME_OVER:
                self._handle_game_over(events)
            elif self.state == cfg.STATE_LEADERBOARD:
                self._handle_leaderboard(events)

            pygame.display.flip()

        pygame.quit()
        sys.exit()

    # ============================================================
    # 主菜单
    # ============================================================
    def _handle_main_menu(self, events: list[pygame.event.Event]) -> None:
        """处理主菜单事件和绘制。"""
        # 每帧重新绘制菜单（按钮也重新创建以便 hover 响应）
        self.menu_buttons = draw_main_menu(self.screen, self.current_skin)

        mouse_pos = pygame.mouse.get_pos()
        for btn in self.menu_buttons.values():
            btn.update(mouse_pos)
            btn.draw(self.screen)

        for event in events:
            if self.menu_buttons["start"].is_clicked(event):
                self.game.reset()
                self.state = cfg.STATE_PLAYING
                self._game_over_processed = False
                self.last_tick_time = pygame.time.get_ticks()
            elif self.menu_buttons["skin"].is_clicked(event):
                self.state = cfg.STATE_SKIN_SELECT
            elif self.menu_buttons["leaderboard"].is_clicked(event):
                self.leaderboard_data = fetch_leaderboard()
                self._init_back_button()
                self.state = cfg.STATE_LEADERBOARD
            elif self.menu_buttons["quit"].is_clicked(event):
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.game.reset()
                    self.state = cfg.STATE_PLAYING
                    self._game_over_processed = False
                    self.last_tick_time = pygame.time.get_ticks()

    # ============================================================
    # 皮肤选择
    # ============================================================
    def _handle_skin_select(self, events: list[pygame.event.Event]) -> None:
        """处理皮肤选择界面。"""
        skin_buttons, back_btn, preview_colors = draw_skin_select(
            self.screen, self.current_skin
        )
        self.skin_buttons = skin_buttons
        self.skin_back_btn = back_btn
        self.skin_preview_colors = preview_colors

        mouse_pos = pygame.mouse.get_pos()
        for btn in skin_buttons.values():
            btn.update(mouse_pos)
            btn.draw(self.screen)
        back_btn.update(mouse_pos)
        back_btn.draw(self.screen)

        # 皮肤预览色块
        draw_skin_preview(self.screen, cfg.SCREEN_WIDTH // 2 - 180, 420, preview_colors.get(self.current_skin, {}))

        for event in events:
            for key, btn in skin_buttons.items():
                if btn.is_clicked(event):
                    self.current_skin = key
            if back_btn.is_clicked(event):
                self.state = cfg.STATE_MAIN_MENU
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = cfg.STATE_MAIN_MENU
                # 数字键快速选择皮肤
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    idx = event.key - pygame.K_1
                    if idx < len(cfg.SKIN_KEYS):
                        self.current_skin = cfg.SKIN_KEYS[idx]

    # ============================================================
    # 游戏进行中
    # ============================================================
    def _handle_playing(self, events: list[pygame.event.Event]) -> None:
        """处理游戏进行中的事件和逻辑更新。"""
        now = pygame.time.get_ticks()
        tick_interval = 1000 // self.game.speed

        # 先处理键盘事件
        for event in events:
            if event.type == pygame.KEYDOWN:
                # 暂停
                if event.key == pygame.K_p:
                    self.game.is_paused = not self.game.is_paused
                # 暂停状态下 Q 返回主菜单
                elif event.key == pygame.K_q and self.game.is_paused:
                    self.state = cfg.STATE_MAIN_MENU
                # AI 切换
                elif event.key == pygame.K_SPACE and not self.game.is_paused:
                    self.game.is_ai_mode = not self.game.is_ai_mode
                # 手动方向控制
                elif not self.game.is_ai_mode and not self.game.is_paused:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.game.change_direction(cfg.UP)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.game.change_direction(cfg.DOWN)
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        self.game.change_direction(cfg.LEFT)
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        self.game.change_direction(cfg.RIGHT)

        # 绘制
        draw_game(self.screen, self.game, self.current_skin)
        draw_hud(self.screen, self.game, self.current_skin)

        if self.game.is_paused:
            draw_pause_overlay(self.screen)
            return  # 暂停时不走逻辑 tick

        # 逻辑 tick（按速度帧率执行）
        if now - self.last_tick_time >= tick_interval:
            self.last_tick_time = now

            # 更新移动陷阱（每帧都更新，不限于 tick）
            self.game.update_moving_traps()

            # 生成当前关卡实体（新关卡时触发一次）
            self.game.spawn_entities_for_level()

            # AI 决策
            if self.game.is_ai_mode:
                ai_dir = get_ai_direction_enhanced(
                    snake_body=self.game.snake_body,
                    food_pos=self.game.food_pos,
                    obstacles=self.game.obstacles,
                    doors=self.game.doors,
                    passages=self.game.one_way_passages,
                    traps=self.game.moving_traps,
                    premium_foods=self.game.get_all_premium_positions(),
                    keys_on_map=self.game.get_all_key_positions(),
                    inventory=self.game.inventory,
                    current_direction=self.game.direction,
                )
                self.game.change_direction(ai_dir)

            # 移动
            self.game.move_snake()

            # 音效
            if self.game.just_ate:
                self.eat_sound.play()
            if self.game.just_died:
                self.die_sound.play()

            # 检查游戏结束
            if self.game.is_game_over:
                self.game.save_high_score()
                self.state = cfg.STATE_GAME_OVER
                self._game_over_processed = False
                self.submission_status = ""
                self.text_input = TextInput(
                    cfg.SCREEN_WIDTH // 2 - 150,
                    240,
                    300, 42,
                )
                self.leaderboard_data = None

    # ============================================================
    # 游戏结束
    # ============================================================
    def _handle_game_over(self, events: list[pygame.event.Event]) -> None:
        """处理游戏结束界面。"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                result = self.text_input.handle_event(event)  # type: ignore
                if result == "submit":
                    self._do_submit()
                elif result == "cancel":
                    self.state = cfg.STATE_MAIN_MENU
            self.text_input.update(self.frame_dt_ms)  # type: ignore

        draw_game_over(
            self.screen,
            self.game.score,
            self.game.high_score,
            self.game.is_won,
            self.text_input,  # type: ignore
            self.leaderboard_data,
            self.submission_status,
        )

    def _do_submit(self) -> None:
        """提交分数到服务器。"""
        name = self.text_input.text.strip()  # type: ignore
        if not name:
            return
        result = submit_score(name, self.game.score)
        if result is not None:
            self.leaderboard_data = result.get("leaderboard", [])
            self.submission_status = "success"
        else:
            self.submission_status = "fail"

    # ============================================================
    # 排行榜
    # ============================================================
    def _init_back_button(self) -> None:
        """初始化排行榜返回按钮。"""
        self.back_button = Button(
            cfg.SCREEN_WIDTH // 2 - 130,
            cfg.SCREEN_HEIGHT - 70,
            260, 45,
            "<< 返回主菜单",
            font_size=22,
            base_color=(30, 30, 50),
            hover_color=(60, 60, 100),
        )

    def _handle_leaderboard(self, events: list[pygame.event.Event]) -> None:
        """处理排行榜界面。"""
        if not self.back_button:
            self._init_back_button()

        mouse_pos = pygame.mouse.get_pos()
        self.back_button.update(mouse_pos)  # type: ignore
        draw_leaderboard(self.screen, self.leaderboard_data, self.back_button)  # type: ignore

        for event in events:
            if self.back_button.is_clicked(event):  # type: ignore
                self.state = cfg.STATE_MAIN_MENU
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = cfg.STATE_MAIN_MENU


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    app = GameApp()
    app.run()
