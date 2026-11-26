import json
import os
import sys
import time
import glob
import tkinter as tk
from tkinter import ttk, messagebox

# Resolve paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
CONFIG_PATH = os.path.join(PROJECT_ROOT, ".agents", "orca-config.json")
BRAIN_DIR = os.path.expanduser(r"~\.gemini\antigravity\brain")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    tmp_path = f"{CONFIG_PATH}.tmp.{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    for _ in range(5):
        try:
            os.replace(tmp_path, CONFIG_PATH)
            return True
        except PermissionError:
            time.sleep(0.05)
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return True
    except Exception:
        return False

def update_dashboards(new_scope, new_tier, new_5h):
    # Search for all orca_dashboard.md in brain directory
    dashboards = glob.glob(os.path.join(BRAIN_DIR, "*", "orca_dashboard.md"))
    for db_path in dashboards:
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Replace Worker default tier
            # Replace alertScope
            import re
            content = re.sub(
                r"(\*\*Worker \(서브에이전트\)\*\* \| `)[^`]+(`)",
                rf"\g<1>gemini-4-{new_tier}\g<2>",
                content
            )
            content = re.sub(
                r"(\*\*알림 범위 \(`alertScope`\)\*\*: `)[^`]+(`)",
                rf"\g<1>{new_scope}\g<2>",
                content
            )
            content = re.sub(
                r"(\*\*5시간 임계치\*\*: `)[^`]+(`)",
                rf"\g<1>{new_5h:.1f}%\g<2>",
                content
            )
            with open(db_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass

class OrcaSettingsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ORCA Quick Settings")
        self.root.geometry("440x500")
        self.root.resizable(False, False)

        # Style & Colors (Dark Modern Theme)
        self.bg_color = "#181825"
        self.card_color = "#1e1e2e"
        self.text_color = "#cdd6f4"
        self.accent_color = "#89b4fa"
        self.success_color = "#a6e3a1"
        self.muted_color = "#6c7086"

        self.root.configure(bg=self.bg_color)

        self.config = load_config()

        self.setup_ui()

    def setup_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg=self.bg_color)
        header_frame.pack(fill="x", padx=20, pady=(16, 10))

        title = tk.Label(header_frame, text="🧭 ORCA Quick Settings", font=("Segoe UI", 14, "bold"),
                         fg=self.text_color, bg=self.bg_color)
        title.pack(anchor="w")

        coord_text = f"Coordinator: {self.config.get('coordinatorModel', 'gemini-3.8-flash-high')} (고속 접수)"
        sub = tk.Label(header_frame, text=coord_text, font=("Segoe UI", 9),
                       fg=self.muted_color, bg=self.bg_color)
        sub.pack(anchor="w", pady=(2, 0))

        # Card 1: Alert Scope
        card1 = tk.LabelFrame(self.root, text=" 🔔 쿼터 알림 범위 (alertScope) ", font=("Segoe UI", 10, "bold"),
                              fg=self.accent_color, bg=self.card_color, relief="flat", padx=12, pady=8)
        card1.pack(fill="x", padx=16, pady=6)

        current_scope = self.config.get("quotaMonitoring", {}).get("alertSettings", {}).get("alertScope", "low_only")
        self.scope_var = tk.StringVar(value=current_scope)

        r1 = tk.Radiobutton(card1, text="low_only : 쿼터 부족(25% 이하) 시에만 조용히 경고 (권장)",
                            variable=self.scope_var, value="low_only",
                            font=("Segoe UI", 9), fg=self.text_color, bg=self.card_color,
                            selectcolor=self.bg_color, activebackground=self.card_color,
                            activeforeground=self.text_color)
        r1.pack(anchor="w", pady=2)

        r2 = tk.Radiobutton(card1, text="all : 모든 주요 작업 완료 후 쿼터 현황 리포트 출력",
                            variable=self.scope_var, value="all",
                            font=("Segoe UI", 9), fg=self.text_color, bg=self.card_color,
                            selectcolor=self.bg_color, activebackground=self.card_color,
                            activeforeground=self.text_color)
        r2.pack(anchor="w", pady=2)

        # Card 2: Default Worker Tier
        card2 = tk.LabelFrame(self.root, text=" ⚡ 기본 서브에이전트 작업 티어 (defaultTier) ", font=("Segoe UI", 10, "bold"),
                              fg=self.accent_color, bg=self.card_color, relief="flat", padx=12, pady=8)
        card2.pack(fill="x", padx=16, pady=6)

        current_tier = self.config.get("defaultTier", "hydrogen-high")
        self.tier_var = tk.StringVar(value=current_tier)

        tiers = [
            ("hydrogen-high", "hydrogen-high (권장/균형 : 복합 구현 및 테스트)"),
            ("hydrogen-low", "hydrogen-low (경량 : 단순 스크립팅/빠른 수정)"),
            ("neon-high", "neon-high (Neon 플래그십 : 범용 개발)"),
            ("neon-low", "neon-low (Neon 경량 : 초고속 수정)"),
            ("carbon-high", "carbon-high (고난도 : 심층 아키텍처/동시성)")
        ]

        for val, label in tiers:
            rb = tk.Radiobutton(card2, text=label, variable=self.tier_var, value=val,
                                font=("Segoe UI", 9), fg=self.text_color, bg=self.card_color,
                                selectcolor=self.bg_color, activebackground=self.card_color,
                                activeforeground=self.text_color)
            rb.pack(anchor="w", pady=1)

        # Card 3: 5h Threshold
        card3 = tk.LabelFrame(self.root, text=" ⚠️ 5시간 쿼터 경고 임계치 ", font=("Segoe UI", 10, "bold"),
                              fg=self.accent_color, bg=self.card_color, relief="flat", padx=12, pady=8)
        card3.pack(fill="x", padx=16, pady=6)

        curr_thresh = self.config.get("quotaMonitoring", {}).get("alertSettings", {}).get("fiveHourThresholdPercent", 25.0)
        self.thresh_var = tk.StringVar(value=str(int(curr_thresh)))

        thresh_frame = tk.Frame(card3, bg=self.card_color)
        thresh_frame.pack(anchor="w")

        tk.Label(thresh_frame, text="남은 쿼터 기준:", font=("Segoe UI", 9), fg=self.text_color, bg=self.card_color).pack(side="left")

        for val in ["25", "20", "15", "10"]:
            rb = tk.Radiobutton(thresh_frame, text=f"{val}%", variable=self.thresh_var, value=val,
                                font=("Segoe UI", 9), fg=self.text_color, bg=self.card_color,
                                selectcolor=self.bg_color, activebackground=self.card_color,
                                activeforeground=self.text_color)
            rb.pack(side="left", padx=6)

        # Status readout label
        self.status_label = tk.Label(self.root, text="", font=("Segoe UI", 9), fg=self.success_color, bg=self.bg_color)
        self.status_label.pack(pady=(4, 0))

        # Bottom Buttons
        btn_frame = tk.Frame(self.root, bg=self.bg_color)
        btn_frame.pack(fill="x", padx=16, pady=(10, 16))

        save_btn = tk.Button(btn_frame, text="💾 설정 저장 및 대시보드 갱신", font=("Segoe UI", 10, "bold"),
                             fg="#11111b", bg=self.accent_color, activebackground="#b4befe",
                             relief="flat", padx=12, pady=6, command=self.on_save, cursor="hand2")
        save_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        close_btn = tk.Button(btn_frame, text="닫기", font=("Segoe UI", 10),
                              fg=self.text_color, bg=self.card_color, activebackground="#313244",
                              relief="flat", padx=12, pady=6, command=self.root.destroy, cursor="hand2")
        close_btn.pack(side="right", padx=(6, 0))

    def on_save(self):
        new_scope = self.scope_var.get()
        new_tier = self.tier_var.get()
        try:
            new_5h = float(self.thresh_var.get())
        except ValueError:
            new_5h = 25.0

        # Update dict
        self.config["defaultTier"] = new_tier
        if "quotaMonitoring" not in self.config:
            self.config["quotaMonitoring"] = {}
        if "alertSettings" not in self.config["quotaMonitoring"]:
            self.config["quotaMonitoring"]["alertSettings"] = {}

        self.config["quotaMonitoring"]["alertSettings"]["alertScope"] = new_scope
        self.config["quotaMonitoring"]["alertSettings"]["fiveHourThresholdPercent"] = new_5h
        if "agents" in self.config["quotaMonitoring"]["alertSettings"]:
            if "antigravity_5h" in self.config["quotaMonitoring"]["alertSettings"]["agents"]:
                self.config["quotaMonitoring"]["alertSettings"]["agents"]["antigravity_5h"]["threshold"] = new_5h

        if "thresholds" not in self.config["quotaMonitoring"]:
            self.config["quotaMonitoring"]["thresholds"] = {}
        self.config["quotaMonitoring"]["thresholds"]["fiveHourLimitPercent"] = new_5h

        success = save_config(self.config)
        if success:
            update_dashboards(new_scope, new_tier, new_5h)
            self.status_label.config(text="✓ 설정이 성공적으로 저장되고 대시보드가 갱신되었습니다!")
            self.root.after(700, self.root.destroy)
        else:
            messagebox.showerror("오류", "설정 파일을 저장하는 중 오류가 발생했습니다.")

def main():
    root = tk.Tk()
    app = OrcaSettingsApp(root)
    # Center on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.mainloop()

if __name__ == "__main__":
    main()
