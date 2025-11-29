import tkinter as tk
from tkinter import ttk
import json
import os
import sys
import webbrowser
import time  # [NEW] 클릭 시간 계산용
import random  # 랜덤 재생용

class TermMarquee:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TermMarquee")
        self.root.focus_force()

        # 경로 설정
        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        # 초기 변수
        self.terms = []
        self.config = {}
        self.current_index = 0  # (예전 순차 재생용, 호환 유지)
        self.timer_id = None
        self.drawer_open = False
        self.drawer_width = 240  # 설정창 너비 확장 (시인성 향상)
        self.is_paused = False 
        self.font_scale = 1.0
        self.help_expanded = False  # 사용법이 펼쳐져 있는지 여부 (기본값: 닫힘)
        self.shuffled_indices = []
        self.shuffle_pos = 0
        self.last_index = 0  # 마지막으로 표시한 용어 인덱스
        
        # 스마트 클릭 변수
        self.click_start_time = 0
        self.click_start_pos = (0, 0)
        
        # 테마 정의
        self.themes = {
            "Yellow": {"bg": "#fff7d1", "header": "#e3d8a3", "fg": "#000000"},
            "Pink":   {"bg": "#fccce4", "header": "#e3a8c3", "fg": "#000000"},
            "Green":  {"bg": "#ccffcc", "header": "#a8e3a8", "fg": "#000000"},
            "Blue":   {"bg": "#cceeff", "header": "#a8cee3", "fg": "#000000"},
            "Purple": {"bg": "#e6ccff", "header": "#c3a8e3", "fg": "#000000"},
            "Grey":   {"bg": "#f2f2f2", "header": "#d9d9d9", "fg": "#000000"},
            "Dark":   {"bg": "#333333", "header": "#222222", "fg": "#ffffff"}
        }

        self.load_config()
        self.load_terms()
        self.setup_ui()
        
        # 첫 용어 로드
        self.update_term()
        
        # 첫 용어에 맞게 창 크기 자동 조정
        self.root.update_idletasks()  # UI 업데이트 대기
        self.adjust_window_to_content()
        
        self.root.mainloop()

    def load_config(self):
        config_path = os.path.join(self.base_path, 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception:
            self.config = {
                "theme_name": "Yellow",
                "interval_seconds": 10,
                "width": 600,
                "height": 300
            }
        
        if self.config.get("theme_name") not in self.themes:
            self.config["theme_name"] = "Yellow"

    def save_config(self):
        config_path = os.path.join(self.base_path, 'config.json')
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Config save error: {e}")

    def load_terms(self):
        terms_path = os.path.join(self.base_path, 'terms.json')
        try:
            with open(terms_path, 'r', encoding='utf-8') as f:
                self.terms = json.load(f)
        except Exception:
            self.terms = [{"term": "Error", "desc": "terms.json 확인 필요"}]

    def setup_ui(self):
        self.root.overrideredirect(True) 
        self.root.attributes('-topmost', True)
        
        # 초기 창 크기는 임시로 설정 (나중에 adjust_window_to_content에서 조정됨)
        w = self.config.get('width', 600)
        h = self.config.get('height', 300)
        self.root.geometry(f"{w}x{h}+200+200")
        
        current_theme = self.themes[self.config['theme_name']]
        self.root.configure(bg="#888888")

        self.container = tk.Frame(self.root, bg=current_theme['bg'])
        self.container.pack(fill='both', expand=True, padx=1, pady=1)

        # Drawer
        self.drawer_panel = tk.Frame(self.container, bg="#f9f9f9", width=0)

        # Main Panel
        self.main_panel = tk.Frame(self.container, bg=current_theme['bg'])
        self.main_panel.pack(side='right', fill='both', expand=True)

        # 헤더 (창 크기에 비례하여 조절)
        self.header = tk.Frame(self.main_panel, bg=current_theme['header'])
        self.header.pack(side='top', fill='x')
        self.header.pack_propagate(False)

        # 설정 아이콘 (초기 크기는 apply_responsive_header에서 설정됨)
        self.btn_settings = tk.Label(
            self.header,
            text="⚙",
            bg=current_theme['header'],
            fg="#555555",
            font=("Arial", 20),
            cursor="hand2"
        )
        self.btn_settings.pack(side='left', padx=10, pady=2)
        self.btn_settings.bind("<Button-1>", self.toggle_drawer)

        # 재생 버튼 (초기 크기는 apply_responsive_header에서 설정됨)
        # 일시정지(⏸)와 재생(▶) 아이콘 크기를 동일하게 맞추기 위해 동일한 폰트 크기 사용
        self.btn_play = tk.Label(
            self.header,
            text="⏸",
            bg=current_theme['header'],
            fg="#555555",
            font=("MS Gothic", 20, "bold"),  # 설정 아이콘과 동일한 크기로 조정
            cursor="hand2",
        )
        self.btn_play.pack(side='left', padx=(6, 0), pady=2)
        self.btn_play.bind("<Button-1>", self.toggle_play)

        # 닫기 아이콘 (초기 크기는 apply_responsive_header에서 설정됨)
        self.btn_close = tk.Label(
            self.header,
            text="✕",
            bg=current_theme['header'],
            fg="#555555",
            font=("Arial", 17),
            cursor="hand2"
        )
        self.btn_close.pack(side='right', padx=10, pady=2)
        self.btn_close.bind("<Button-1>", lambda e: self.root.destroy())

        self.header.bind("<Button-1>", self.start_move)
        self.header.bind("<B1-Motion>", self.do_move)

        # 중앙 콘텐츠 (헤더 아래에 배치, 타이틀 바 침범 방지)
        self.center_frame = tk.Frame(self.main_panel, bg=current_theme['bg'])
        self.center_frame.pack(side='top', fill='both', expand=True, padx=5)
        
        # 콘텐츠 컨테이너 (위아래 동일한 패딩을 위해 중앙 배치)
        self.content_container = tk.Frame(self.center_frame, bg=current_theme['bg'])
        # rely=0.5: 헤더 아래 영역의 정중앙에 배치하여 위아래 패딩 동일하게
        self.content_container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.95) 

        # 용어 (Label로 변경 - 전체 표시 보장)
        self.term_label = tk.Label(
            self.content_container,
            text="",
            bg=current_theme['bg'],
            fg=current_theme['fg'],
            font=("Malgun Gothic", 14, "bold"),
            cursor="hand2",
            justify="center"
        )
        self.term_label.pack(pady=(0, 10))
        
        # 용어 영역 클릭 및 Hover 효과
        self.term_label.bind("<Button-1>", self.open_google_search)
        self.term_label.bind("<Enter>", self.on_term_enter)
        self.term_label.bind("<Leave>", self.on_term_leave)

        # 설명 (Text 위젯)
        self.desc_text = tk.Text(self.content_container, height=3, width=30,
                                 bg=current_theme['bg'], fg=current_theme['fg'],
                                 bd=0, highlightthickness=0, cursor="xterm")
        self.desc_text.tag_configure("center", justify='center')
        self.desc_text.pack(fill='both', expand=True)
        self.desc_text.bind("<Key>", lambda e: "break")
        # 설명 영역도 드래그 선택 방지
        self.desc_text.bind("<Button-1>", lambda e: "break")
        self.desc_text.bind("<B1-Motion>", lambda e: "break")
        # Text 위젯에도 클릭 애니메이션 추가
        self.add_click_animation(self.desc_text)

        self.root.bind_all("<Control-MouseWheel>", self.manual_zoom)

        # 리사이즈 그립
        self.grip = tk.Label(self.main_panel, text="⇲", font=("ui-icons", 12), bg=current_theme['bg'], fg="#aaaaaa", cursor="sizing")
        self.grip.place(relx=1.0, rely=1.0, anchor="se")
        self.grip.bind("<Button-1>", self.start_resize)
        self.grip.bind("<B1-Motion>", self.do_resize)

        self.setup_drawer_ui()
        self.main_panel.bind("<Configure>", self.on_resize_window)
        self.root.bind("<Configure>", self.on_root_resize)
        
        # 초기 타이틀 바 크기 설정 (모든 UI 구성 후)
        self.root.update_idletasks()
        self.apply_responsive_header()

        # 공통 버튼 피드백/애니메이션 효과 적용
        self.add_button_feedback(self.btn_settings, hover_bg="#d6c89a", active_bg="#c9bc8f")
        self.add_button_feedback(self.btn_play, hover_bg="#d6c89a", active_bg="#c9bc8f")
        self.add_button_feedback(self.btn_close, hover_bg="#d6c89a", active_bg="#c98f8f")
        self.add_button_feedback(self.term_label, hover_bg=current_theme['bg'], active_bg=current_theme['bg'])
        self.add_button_feedback(self.grip, hover_bg="#dddddd", active_bg="#cccccc")
        
        # 모든 클릭 가능한 위젯에 클릭 애니메이션 추가
        self.add_click_animation(self.btn_settings)
        self.add_click_animation(self.btn_play)
        self.add_click_animation(self.btn_close)
        self.add_click_animation(self.term_label)
        self.add_click_animation(self.grip)

    def setup_drawer_ui(self):
        bg_color = "#f9f9f9"
        
        # 제목 (상단 여백 축소)
        lbl_title = tk.Label(
            self.drawer_panel,
            text="설정",
            font=("Malgun Gothic", 12, "bold"),
            bg=bg_color,
            fg="#333333"
        )
        lbl_title.pack(pady=(10, 10))

        # 전환 시간 섹션 (간격 축소)
        time_section = tk.Frame(self.drawer_panel, bg=bg_color)
        time_section.pack(fill='x', padx=12, pady=(0, 10))
        
        lbl_time = tk.Label(
            time_section,
            text="전환 시간",
            font=("Malgun Gothic", 9, "bold"),
            bg=bg_color,
            fg="#555555"
        )
        lbl_time.pack(side='left')

        time_values = [str(i) for i in range(5, 65, 5)]
        self.combo_time = ttk.Combobox(
            time_section,
            values=time_values,
            state="readonly",
            width=8
        )
        self.combo_time.set(self.config['interval_seconds'])
        self.combo_time.pack(side='left', padx=(8, 0))
        self.combo_time.bind("<<ComboboxSelected>>", self.change_interval)

        # 테마 색상 섹션 (간격 축소)
        theme_section = tk.Frame(self.drawer_panel, bg=bg_color)
        theme_section.pack(fill='x', padx=12, pady=(0, 10))
        
        lbl_color = tk.Label(
            theme_section,
            text="테마 색상",
            font=("Malgun Gothic", 9, "bold"),
            bg=bg_color,
            fg="#555555"
        )
        lbl_color.pack(anchor="w", pady=(0, 6))

        color_frame = tk.Frame(theme_section, bg=bg_color)
        color_frame.pack(anchor="w")

        col = 0
        for name, colors in self.themes.items():
            btn = tk.Label(
                color_frame,
                text="  ",
                bg=colors['bg'],
                width=2,
                height=1,
                relief="solid",
                bd=1,
                cursor="hand2"
            )
            btn.grid(row=0, column=col, padx=2, pady=2)  # 모두 row=0에 배치하여 한 줄로
            btn.bind("<Button-1>", lambda e, n=name: self.change_theme(n))
            # 테마 칩에도 피드백 효과 적용
            self.add_button_feedback(btn, hover_bg=colors['header'], active_bg=colors['bg'])
            self.add_click_animation(btn)
            col += 1

        # 구분선 (간격 축소)
        tk.Frame(self.drawer_panel, height=1, bg="#dddddd").pack(fill='x', padx=12, pady=(6, 8))
        
        # 사용법 섹션
        help_section = tk.Frame(self.drawer_panel, bg=bg_color)
        help_section.pack(fill='both', expand=True, padx=12, pady=(0, 10))
        
        # 사용법 제목 (클릭 가능)
        help_title_frame = tk.Frame(help_section, bg=bg_color)
        help_title_frame.pack(anchor="w", fill='x', pady=(0, 4))
        
        help_title = tk.Label(
            help_title_frame,
            text="사용법",
            font=("Malgun Gothic", 12, "bold"),
            bg=bg_color,
            fg="#555555",
            cursor="hand2"
        )
        help_title.pack(side='left')
        
        # 클릭 아이콘 (▼/▶)
        self.help_icon = tk.Label(
            help_title_frame,
            text="▶",  # 기본값: 닫혀있으므로 ▶
            font=("Malgun Gothic", 10),
            bg=bg_color,
            fg="#888888",
            cursor="hand2"
        )
        self.help_icon.pack(side='left', padx=(6, 0))
        
        # 클릭 이벤트 바인딩
        help_title.bind("<Button-1>", self.toggle_help)
        self.help_icon.bind("<Button-1>", self.toggle_help)
        self.add_click_animation(help_title)
        self.add_click_animation(self.help_icon)
        
        # 사용법 내용 컨테이너 (기본값: 닫혀있으므로 생성만 하고 표시하지 않음)
        self.help_content = tk.Frame(help_section, bg=bg_color)
        # 초기에는 표시하지 않음 (help_expanded = False)
        
        # 사용법 항목들을 각각 별도 Label로 생성하여 줄 간격 조절
        help_items = [
            "• 상단 바 드래그: 창 이동",
            "• ⏸/▶: 일시정지/재생",
            "• ⚙: 설정 열기/닫기",
            "• 용어 클릭: 구글 검색",
            "• Ctrl+휠: 글자 크기",
            "• ⇲: 창 크기 조절"
        ]
        
        for item in help_items:
            lbl_item = tk.Label(
                self.help_content,
                text=item,
                font=("Malgun Gothic", 9),
                bg=bg_color,
                fg="#666666",
                anchor="w",
                justify="left"
            )
            lbl_item.pack(anchor="w", pady=(0, 3))  # 각 줄 사이에 3px 패딩
            self.add_click_animation(lbl_item)

    def toggle_drawer(self, event=None):
        current_w = self.root.winfo_width()
        current_h = self.root.winfo_height()

        if self.drawer_open:
            self.drawer_panel.pack_forget()
            new_w = current_w - self.drawer_width
            self.drawer_open = False
        else:
            self.drawer_panel.pack(side='left', fill='y')
            new_w = current_w + self.drawer_width
            self.drawer_open = True
            
        self.root.geometry(f"{new_w}x{current_h}")

    # 공통 버튼 피드백 + 간단한 애니메이션 (배경색 변화) 유틸
    def add_button_feedback(self, widget, hover_bg, active_bg):
        normal_bg = widget.cget("bg")

        def on_enter(e):
            widget.config(bg=hover_bg)

        def on_leave(e):
            widget.config(bg=normal_bg)

        def on_click_flash():
            widget.config(bg=active_bg)
            # 120ms 후 살짝 밝은 색으로 복구
            widget.after(120, lambda: widget.config(bg=hover_bg))

        def on_button(e):
            # 기존에 걸려 있던 클릭 동작은 그대로 두고, 시각 효과만 추가
            on_click_flash()

        widget.bind("<Enter>", on_enter, add="+")
        widget.bind("<Leave>", on_leave, add="+")
        widget.bind("<Button-1>", on_button, add="+")

    def add_click_animation(self, widget):
        """모든 위젯에 클릭 애니메이션 효과 추가"""
        def on_click(e):
            # 클릭 시 작은 이펙트 (약간 어둡게 → 원래대로)
            try:
                # 현재 배경색 저장
                current_bg = widget.cget("bg")
                
                # 어두운 색으로 변경
                widget.config(bg="#cccccc")
                
                # 100ms 후 원래 색으로 복구 (클로저 문제 해결을 위해 기본 인자 사용)
                def restore_bg(bg_color=current_bg):
                    try:
                        widget.config(bg=bg_color)
                    except:
                        pass
                
                widget.after(100, restore_bg)
            except:
                # bg 속성이 없거나 변경할 수 없는 위젯은 스킵
                pass
        
        widget.bind("<Button-1>", on_click, add="+")

    def toggle_help(self, event=None):
        """사용법 펼치기/접기"""
        if self.help_expanded:
            self.help_content.pack_forget()
            self.help_icon.config(text="▶")
            self.help_expanded = False
        else:
            self.help_content.pack(anchor="w", fill='x')
            self.help_icon.config(text="▼")
            self.help_expanded = True

    def toggle_play(self, event):
        if self.is_paused:
            self.is_paused = False
            self.btn_play.config(text="⏸") 
            self.update_term()
        else:
            self.is_paused = True
            self.btn_play.config(text="▶") 
            if self.timer_id:
                self.root.after_cancel(self.timer_id)

    def change_interval(self, event):
        val = int(self.combo_time.get())
        self.config['interval_seconds'] = val
        self.save_config()
        if not self.is_paused:
            self.update_term()
        
        # Combobox의 파란색 하이라이트 제거를 위해 포커스를 다른 곳으로 이동
        self.root.focus_set()

    def change_theme(self, theme_name):
        self.config['theme_name'] = theme_name
        self.save_config()
        t = self.themes[theme_name]
        
        self.container.config(bg=t['bg'])
        self.main_panel.config(bg=t['bg'])
        self.header.config(bg=t['header'])
        self.btn_settings.config(bg=t['header'])
        self.btn_play.config(bg=t['header'])
        self.btn_close.config(bg=t['header'])
        self.center_frame.config(bg=t['bg'])
        self.content_container.config(bg=t['bg'])
        
        self.term_label.config(bg=t['bg'], fg=t['fg'])
        self.desc_text.config(bg=t['bg'], fg=t['fg'])
        self.grip.config(bg=t['bg'])

    def manual_zoom(self, event):
        if event.delta > 0:
            self.font_scale += 0.1
        else:
            self.font_scale -= 0.1
        if self.font_scale < 0.5: self.font_scale = 0.5
        self.apply_responsive_font()

    def on_resize_window(self, event):
        if event.widget == self.main_panel:
            self.apply_responsive_font()
            self.apply_responsive_header()

    def on_root_resize(self, event):
        """루트 윈도우 크기 변경 시 타이틀 바 높이 조절"""
        if event.widget == self.root:
            self.apply_responsive_header()

    def apply_responsive_header(self):
        """타이틀 바 높이를 창 크기에 비례하여 조절"""
        height = self.root.winfo_height()
        if height <= 1: return
        
        # 창 높이의 9.6%로 설정 (기존 12%의 80%), 최소 28px, 최대 48px
        header_height = max(28, min(48, int(height * 0.096)))
        self.header.config(height=header_height)
        
        # 아이콘 크기도 타이틀 바 높이에 비례하여 조절 (80%로 축소)
        icon_size = max(11, min(18, int(header_height * 0.5)))
        play_icon_size = icon_size  # 일시정지와 재생 아이콘 크기를 동일하게
        close_icon_size = max(10, min(15, int(header_height * 0.42)))
        
        self.btn_settings.config(font=("Arial", icon_size))
        self.btn_play.config(font=("MS Gothic", play_icon_size, "bold"))
        self.btn_close.config(font=("Arial", close_icon_size))

    def apply_responsive_font(self):
        width = self.main_panel.winfo_width()
        if width <= 1: return

        base_size = int(width / 25)
        new_size = int(base_size * self.font_scale)
        if new_size < 10: new_size = 10
        
        self.term_label.configure(font=("Malgun Gothic", new_size, "bold"))
        self.desc_text.configure(font=("Malgun Gothic", new_size - 2))

    def adjust_window_to_content(self):
        """현재 표시된 용어와 설명에 맞게 창 크기를 자동 조정"""
        if not self.terms or not hasattr(self, 'term_label'):
            return
        
        # 현재 표시된 용어와 설명 가져오기
        current_term_text = self.term_label.cget("text")
        self.desc_text.config(state='normal')
        current_desc_text = self.desc_text.get("1.0", "end-1c")
        self.desc_text.config(state='disabled')
        
        if not current_term_text:
            return
        
        # 텍스트 크기 측정
        term_font = ("Malgun Gothic", 14, "bold")
        desc_font = ("Malgun Gothic", 12)
        
        # 임시 Label로 용어 너비 측정
        temp_label = tk.Label(self.root, text=current_term_text, font=term_font)
        temp_label.update_idletasks()
        term_width = temp_label.winfo_reqwidth()
        temp_label.destroy()
        
        # 설명 텍스트 너비 측정 (최대 너비 제한 고려)
        desc_lines = current_desc_text.split('\n')
        max_desc_width = 0
        for line in desc_lines:
            if line.strip():
                temp_label = tk.Label(self.root, text=line, font=desc_font)
                temp_label.update_idletasks()
                line_width = temp_label.winfo_reqwidth()
                max_desc_width = max(max_desc_width, line_width)
                temp_label.destroy()
        
        # 필요한 너비 계산 (패딩 포함)
        content_width = max(term_width, max_desc_width) + 100  # 좌우 패딩 50px씩
        min_width = 400
        max_width = 800
        window_width = max(min_width, min(max_width, content_width))
        
        # 필요한 높이 계산
        # 헤더 높이 (창 높이의 9.6%, 최소 28px, 최대 48px)
        estimated_header_height = 36  # 초기 추정값 (기존 45의 80%)
        # 용어 높이
        term_height = 30
        # 설명 높이 (줄 수에 따라)
        desc_line_count = len([line for line in desc_lines if line.strip()])
        desc_height = max(40, desc_line_count * 20) + 20  # 최소 40px, 줄당 20px
        # 위아래 패딩 (동일하게)
        padding = 40  # 위아래 각 40px
        
        content_height = term_height + desc_height + padding * 2
        window_height = estimated_header_height + content_height
        
        # 최소/최대 높이 제한
        min_height = 250
        max_height = 500
        window_height = max(min_height, min(max_height, window_height))
        
        # 창 크기 설정
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 설정 저장
        self.config['width'] = window_width
        self.config['height'] = window_height
        self.save_config()

    # --- [스마트 클릭 + Hover 구현] ---
    def on_text_down(self, event):
        # 클릭 시작 시간과 위치 기록
        self.click_start_time = time.time()
        self.click_start_pos = (event.x, event.y)
        # 드래그 선택 방지
        return "break"

    def on_text_up(self, event):
        # 1. 이동 거리 계산 (절댓값)
        dx = abs(event.x - self.click_start_pos[0])
        dy = abs(event.y - self.click_start_pos[1])
        # 2. 클릭 시간 계산
        dt = time.time() - self.click_start_time
        
        # 3. 판단: 조금 움직이고(5px 이하), 짧게 눌렀다면(0.3초 이하) => 단순 클릭(검색)
        if dx < 5 and dy < 5 and dt < 0.3:
            # 텍스트 위젯 특성상 클릭 시 커서가 이동하므로, 검색을 띄웁니다.
            self.open_google_search(event)
        
        # 그렇지 않으면(많이 움직였거나 길게 누름)도 선택은 막고 아무 동작도 하지 않음
        return "break"

    def on_term_enter(self, event):
        """용어 영역에 마우스를 올렸을 때: 손가락 커서 + 색상 강조"""
        self.term_label.config(cursor="hand2", fg="blue")

    def on_term_leave(self, event):
        """용어 영역에서 벗어났을 때: 원래 테마 색상 복구"""
        theme = self.themes[self.config['theme_name']]
        self.term_label.config(cursor="hand2", fg=theme['fg'])

    def open_google_search(self, event):
        term = self.terms[self.last_index]['term']
        webbrowser.open(f"https://www.google.com/search?q={term} 뜻")

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def start_resize(self, event):
        self.rx = event.x_root
        self.ry = event.y_root
        self.rw = self.root.winfo_width()
        self.rh = self.root.winfo_height()

    def do_resize(self, event):
        dx = event.x_root - self.rx
        dy = event.y_root - self.ry
        new_w = max(300, self.rw + dx)
        new_h = max(150, self.rh + dy)
        self.root.geometry(f"{new_w}x{new_h}")

    def update_term(self):
        if self.is_paused: return
        if not self.terms: return

        # 모든 용어를 한 번씩 소진할 때까지 중복 없이 랜덤 재생
        if not self.shuffled_indices or len(self.shuffled_indices) != len(self.terms) or self.shuffle_pos >= len(self.shuffled_indices):
            self.shuffled_indices = list(range(len(self.terms)))
            random.shuffle(self.shuffled_indices)
            self.shuffle_pos = 0

        idx = self.shuffled_indices[self.shuffle_pos]
        data = self.terms[idx]
        
        self.term_label.config(text=data['term'])
        
        self.desc_text.config(state='normal')
        self.desc_text.delete("1.0", "end")
        self.desc_text.insert("1.0", data['desc'], "center")

        # 마지막으로 사용한 인덱스 기록 (검색용)
        self.last_index = idx
        # 다음 위치로 이동
        self.shuffle_pos += 1

        if self.timer_id: self.root.after_cancel(self.timer_id)
        self.timer_id = self.root.after(self.config['interval_seconds'] * 1000, self.update_term)

if __name__ == "__main__":
    TermMarquee()