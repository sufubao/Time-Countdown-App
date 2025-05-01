import tkinter as tk
import tkinter.ttk as ttk # Import themed widgets
import time
import random
import pygame.mixer
import threading
import sys

class CountdownApp:
    def __init__(self, root):
        self.root = root
        root.title("倒计时")

        # --- 美化配色方案 ---
        self.bg_color = "#2b2b2b"       # 深炭灰色背景
        self.fg_main_high = "#90ee90"   # 浅绿色 (开始时)
        self.fg_main_medium = "#ffd700" # 金黄色 (中期)
        self.fg_main_low = "#ff6347"    # 番茄红 (后期)
        self.fg_end = "#dc143c"         # 深红色 (结束)
        self.fg_rest = "#add8e6"        # 浅蓝色 (请休息)
        self.fg_button = "#000000"      # !!! 修改这里为黑色按钮文本 !!!
        self.bg_button = "#ffffff"      # 白色按钮背景，与黑色文本搭配
        self.bg_button_active = "#cccccc" # 按钮按下颜色 (浅灰色)


        # 设置窗口大小和背景颜色
        root.geometry("600x400")
        root.configure(bg=self.bg_color)
        root.resizable(False, False) # 禁止调整窗口大小

        # --- 初始化 Pygame Mixer ---
        self.sound_available = False
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.sound_available = True
            # print("Pygame mixer initialized successfully.")
        except Exception as e:
            print(f"无法初始化 Pygame mixer: {e}")
            print("提示音将不起作用。请确保您的系统支持音频播放。")
            self.sound_available = False

        # --- 加载声音文件 ---
        self.sounds = {}
        if self.sound_available:
            sound_files = {
                'start': 'start.mp3',
                'info': 'info.mp3',
                'succ': 'succ.mp3'
            }
            for name, filename in sound_files.items():
                try:
                    self.sounds[name] = pygame.mixer.Sound(filename)
                    # print(f"成功加载声音: {filename}")
                except pygame.error as e:
                    print(f"无法加载声音文件 '{filename}': {e}")
                    self.sounds[name] = None
            if not all(self.sounds.get(name) for name in ['start', 'info', 'succ']):
                 print("部分或全部必需的声音文件未能加载，提示音将部分或全部不起作用。")


        # --- 配置主倒计时 ---
        self.total_duration_seconds = 90 * 60  # 90分钟转为秒
        self.main_time_left = self.total_duration_seconds
        self.main_running = False # Wait for button click

        # --- 配置小倒计时 ---
        self.small_min_seconds = 3 * 60  # 3分钟
        self.small_max_seconds = 5 * 60  # 5分钟
        self.small_time_left = 0
        self.small_phase = "waiting_to_start" # Possible phases: "waiting_to_start", "random", "ten_second", "finished"

        # --- GUI 元素 ---
        # 主倒计时标签
        self.main_label = tk.Label(
            root,
            text=self.format_time(self.main_time_left),
            font=("Consolas", 80, "bold"), # 使用数字风格字体，加大加粗
            bg=self.bg_color, # 与窗口背景一致
            fg=self.fg_main_high # 初始颜色
        )
        self.main_label.pack(pady=(50, 10)) # 顶部和底部留白

        # 请休息提示标签 (初始隐藏)
        self.rest_label = tk.Label(
            root,
            text="请休息", # 默认文本
            font=("Helvetica", 36, "bold"), # 稍大加粗，醒目
            bg=self.bg_color, # 与窗口背景一致
            fg=self.fg_rest
        )
        self.rest_label.pack_forget() # 初始隐藏

        # --- ttk Button ---
        style = ttk.Style()
        # 可以尝试不同的主题，看哪个基础样式更好看 (可选)
        # style.theme_use('clam') # 'clam', 'alt', 'default', 'classic'

        # 配置自定义按钮样式
        style.configure("TButton",
                        font=("Helvetica", 18),
                        padding=[20, 10], # 内部填充 [宽, 高]
                        borderwidth=0,
                        relief="flat",
                        background=self.bg_button,    # 使用白色背景
                        foreground=self.fg_button,    # !!! 使用黑色文本 !!!
                        focusthickness=0 # 移除焦点虚线
                        )
        # 配置按钮按下时的样式
        style.map("TButton",
                  background=[('active', self.bg_button_active)], # 按下时变浅灰
                  foreground=[('active', self.fg_button)]         # !!! 按下时文本仍为黑色 !!!
                  )

        self.start_button = ttk.Button( # 使用 ttk.Button
            root,
            text="开始倒计时",
            command=self.start_countdown,
            style="TButton" # 应用样式
        )
        self.start_button.pack(pady=20)

        # --- 初始状态设置 ---
        # Nothing runs until the button is clicked

    def format_time(self, seconds):
        """将秒数格式化为 MM:SS 格式"""
        if seconds < 0:
            seconds = 0 # Prevent negative display
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02}:{seconds:02}"

    def play_sound(self, sound_name):
        """播放指定名称的提示音"""
        if not self.sound_available:
            return

        sound_obj = self.sounds.get(sound_name)
        if sound_obj:
            try:
                sound_obj.play()
            except Exception as e:
                 print(f"播放声音 '{sound_name}' 时出错: {e}")


    def start_countdown(self):
        """开始主倒计时和小倒计时循环"""
        if self.main_running:
            return # Already started

        self.main_running = True
        self.start_button.config(state=tk.DISABLED) # 禁用开始按钮

        self.play_sound('start') # 播放开始音效

        print("倒计时已开始。")
        # 启动主更新循环
        self.update_all_timers()


    def update_all_timers(self):
        """每秒更新主倒计时并管理小倒计时状态"""
        if not self.main_running:
            # 主倒计时已结束或未开始
            if self.small_phase == "ten_second":
                 self.rest_label.pack_forget()
            return

        # --- 更新主倒计时 ---
        self.main_time_left -= 1
        self.main_label.config(text=self.format_time(self.main_time_left))

        # --- 根据剩余时间更新主倒计时颜色 ---
        if self.total_duration_seconds > 0: # Avoid division by zero
            remaining_percentage = (self.main_time_left / self.total_duration_seconds) * 100
            if remaining_percentage > 10: # 剩余时间大于总时长的10%
                self.main_label.config(fg=self.fg_main_high)
            elif remaining_percentage > 1: # 剩余时间在总时长的10%到1%之间
                 self.main_label.config(fg=self.fg_main_medium)
            else: # 剩余时间小于等于总时长的1%
                 self.main_label.config(fg=self.fg_main_low)


        # --- 管理小倒计时 ---
        self.manage_small_countdown()


        # --- 检查主倒计时是否结束 ---
        if self.main_time_left <= 0:
            self.main_running = False
            self.main_label.config(text="结束！", fg=self.fg_end) # 结束时变红色
            if self.small_phase == "ten_second": # Hide rest label if it was showing
                 self.rest_label.pack_forget()
            self.play_sound('succ') # 播放成功音效
            print("主倒计时结束。")
            # Optional: Clean up mixer - can cause issues if sounds are still playing
            # pygame.mixer.quit()
        else:
            self.root.after(1000, self.update_all_timers)


    def manage_small_countdown(self):
        """根据当前阶段管理小倒计时状态和播放声音"""

        if not self.main_running:
             self.small_phase = "finished" # Set phase to finished
             self.rest_label.pack_forget() # Ensure rest label is hidden
             return

        if self.small_phase == "waiting_to_start":
            self.rest_label.pack_forget() # Ensure hidden
            # Determine new random duration and enter random phase
            random_duration = random.randint(self.small_min_seconds, self.small_max_seconds)
            self.small_time_left = random_duration
            self.small_phase = "random"
            # print(f"小倒计时新的随机阶段开始，时长: {random_duration} 秒")
            self.play_sound('start') # 小倒计时随机阶段开始播放 start 音效


        elif self.small_phase == "random":
            if self.small_time_left > 0:
                self.small_time_left -= 1
            else:
                # 随机倒计时阶段结束
                # print("小倒计时随机阶段结束，播放 info 提示音并进入10秒倒计时。")
                self.play_sound('info') # 随机阶段结束播放 info 音效
                self.small_time_left = 10 # 进入10秒倒计时
                self.small_phase = "ten_second"
                self.rest_label.pack(pady=10) # Show "请休息"


        elif self.small_phase == "ten_second":
            if self.small_time_left > 0:
                 self.small_time_left -= 1
            else:
                # 10秒倒计时阶段结束
                # print("10秒倒计时结束，播放 info 提示音并等待开始新的随机倒计时。")
                self.play_sound('info') # 10秒阶段结束播放 info 音效
                self.small_phase = "waiting_to_start" # 回到等待状态，下一循环会启动新的随机倒计时
                self.rest_label.pack_forget() # Hide "请休息"


# --- 运行应用 ---
if __name__ == "__main__":
    root = tk.Tk()
    app = CountdownApp(root)
    root.mainloop()

    # Optional: Explicitly quit mixer on program exit
    # try:
    #    pygame.mixer.quit()
    # except Exception:
    #    pass