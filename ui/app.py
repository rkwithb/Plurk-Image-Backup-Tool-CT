# Copyright (c) 2026 rkwithb (https://github.com/rkwithb)
# Licensed under CC BY-NC 4.0 (Non-Commercial Use Only)
# Disclaimer: Use at your own risk. The author is not responsible for any damages.

import sys
import threading
from pathlib import Path
from tkinter import filedialog

# Ensure project root is in sys.path so 'core' package can be found
# regardless of which directory the script is launched from
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import customtkinter as ctk

from core.processor import run_full_backup, ProcessStats
from core.exif_handler import is_exif_available

# ==========================================
# Theme & Appearance
# ==========================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ==========================================
# Colour palette — dark theme
# ==========================================
CLR_BG          = "#000000"   # main background
CLR_PANEL       = "#1a1a1a"   # subtle panel background
CLR_ACCENT      = "#ffffff"   # primary text / accent (light on dark)
CLR_ACCENT2     = "#818cf8"   # blue accent for progress bar
CLR_TEXT        = "#ffffff"   # primary text
CLR_SUBTEXT     = "#cccccc"   # secondary / hint text (grey stays grey)
CLR_SUCCESS     = "#16a34a"   # success green
CLR_WARN        = "#d97706"   # warning amber
CLR_ERROR       = "#dc2626"   # error red
CLR_BORDER      = "#ffffff"   # nav-style border (inverted)
CLR_DIVIDER     = "#ffffff"   # stat row divider lines (inverted)
CLR_ENTRY_BORDER = "#555555"
CLR_PROGRESS_BG  = "#2d2d2d"  # dark / "#e2e8f0" light
CLR_BTN_PRIMARY  = "#64748b"  # primary action button background
CLR_BTN_HOVER    = "#333333"  # primary action button hover
class FolderRow(ctk.CTkFrame):
    """
    Reusable row widget: label + path entry + browse button.
    """
    def __init__(self, master, label: str, default_path: str = "",
                 on_change=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_change = on_change

        self.columnconfigure(1, weight=1)

        # Label
        ctk.CTkLabel(
            self, text=label,
            text_color=CLR_SUBTEXT,
            font=ctk.CTkFont(family="monospace", size=12),
            width=140, anchor="w"
        ).grid(row=0, column=0, padx=(0, 8), sticky="w")

        # Path entry (editable)
        self._var = ctk.StringVar(value=default_path)
        self._entry = ctk.CTkEntry(
            self,
            textvariable=self._var,
            placeholder_text="請選擇噗浪備份資料夾...",
            font=ctk.CTkFont(size=14),
            fg_color=CLR_BG,
            border_color=CLR_ENTRY_BORDER,
            text_color=CLR_TEXT,
            height=34,
        )
        self._entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        # Browse button — minimal style matching Choose BG concept
        ctk.CTkButton(
            self, text="選擇",
            width=60, height=34,
            fg_color="transparent",
            hover_color=CLR_BTN_HOVER,
            border_color=CLR_ENTRY_BORDER,
            border_width=1,
            text_color=CLR_TEXT,
            font=ctk.CTkFont(size=14),
            command=self._browse,
        ).grid(row=0, column=2, sticky="e")

    def _browse(self):
        """Open folder picker dialog and update entry."""
        chosen = filedialog.askdirectory(title="選擇資料夾")
        if chosen:
            self._var.set(chosen)
            if self._on_change:
                self._on_change(chosen)  # notify parent of selection

    @property
    def path(self) -> Path:
        return Path(self._var.get())


class StatCard(ctk.CTkFrame):
    """
    Stat display card with subtle background and rounded corners.
    Top/bottom border lines are handled by the parent stats_wrapper.
    """
    def __init__(self, master, icon: str, label: str, color: str, **kwargs):
        # Light panel background with rounded corners
        super().__init__(master, fg_color=CLR_PANEL, corner_radius=10, **kwargs)

        self._var = ctk.StringVar(value="0")

        ctk.CTkLabel(
            self, text=icon,
            font=ctk.CTkFont(size=22),
        ).pack(pady=(12, 0))

        ctk.CTkLabel(
            self, textvariable=self._var,
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=color,
        ).pack()

        ctk.CTkLabel(
            self, text=label,
            font=ctk.CTkFont(size=11),
            text_color=CLR_SUBTEXT,
        ).pack(pady=(0, 12))

    def set(self, value: int):
        self._var.set(str(value))


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("噗浪圖片備份工具")
        self.geometry("720x680")
        self.minsize(640, 580)
        self.configure(fg_color=CLR_BG)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # log area expands

        # ── Header ──────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=CLR_PANEL, corner_radius=0, height=64)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="  噗浪圖片備份工具",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=CLR_TEXT,
        ).grid(row=0, column=0, pady=16, padx=24, sticky="w")

        ctk.CTkLabel(
            header,
            text="Plurk Image Backup Organizer",
            font=ctk.CTkFont(family="monospace", size=14),
            text_color=CLR_SUBTEXT,
        ).grid(row=0, column=1, pady=16, padx=24, sticky="e")

        # ── Settings Panel ───────────────────────────────────────
        panel = ctk.CTkFrame(self, fg_color=CLR_PANEL, corner_radius=12)
        panel.grid(row=1, column=0, sticky="ew", padx=20, pady=(16, 0))
        panel.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel, text="資料夾設定",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=CLR_ACCENT,
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))

        self._data_row = FolderRow(
            panel, "你的噗浪備份資料夾",
            on_change=self._on_data_dir_change,
        )
        self._data_row.grid(row=1, column=0, sticky="ew", padx=16, pady=4)

        ctk.CTkLabel(
            panel,
            text="　　請選擇噗浪備份的最上層資料夾（內含 data/plurks/ 與 data/responses/）",
            font=ctk.CTkFont(family="monospace", size=14),
            text_color=CLR_SUBTEXT,
            anchor="w",
        ).grid(row=2, column=0, sticky="w", padx=16, pady=(0, 4))

        # Readonly entry shows resolved output path — stretches with window width
        self._output_path_var = ctk.StringVar(value="圖檔存在（請先選擇你的噗浪備份資料夾）")
        ctk.CTkEntry(
            panel,
            textvariable=self._output_path_var,
            state="readonly",
            font=ctk.CTkFont(family="monospace", size=14),
            fg_color=CLR_BG,
            border_color=CLR_BG,
            text_color=CLR_TEXT,
            height=34,
        ).grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 4))

        # EXIF option
        exif_row = ctk.CTkFrame(panel, fg_color="transparent")
        exif_row.grid(row=4, column=0, sticky="w", padx=16, pady=(10, 14))

        self._exif_var = ctk.BooleanVar(value=False)
        self._exif_switch = ctk.CTkSwitch(
            exif_row,
            text="補寫 EXIF 圖片時間（僅限 JPG）",
            variable=self._exif_var,
            font=ctk.CTkFont(size=12),
            text_color=CLR_TEXT,
            progress_color=CLR_ACCENT2,
        )
        self._exif_switch.pack(side="left")

        if not is_exif_available():
            self._exif_switch.configure(state="disabled")
            ctk.CTkLabel(
                exif_row,
                text="  （未安裝 piexif）",
                font=ctk.CTkFont(size=11),
                text_color=CLR_WARN,
            ).pack(side="left")

        # ── Log Area ─────────────────────────────────────────────
        log_frame = ctk.CTkFrame(self, fg_color=CLR_PANEL, corner_radius=12)
        log_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(12, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)

        ctk.CTkLabel(
            log_frame, text="執行紀錄",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=CLR_ACCENT,
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))

        self._log_box = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="monospace", size=11),
            fg_color=CLR_BG,
            text_color=CLR_TEXT,
            border_color=CLR_ENTRY_BORDER,
            border_width=1,
            wrap="word",
            state="disabled",
        )
        self._log_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        # ── Progress Bar ─────────────────────────────────────────
        self._progress = ctk.CTkProgressBar(
            self,
            fg_color=CLR_PROGRESS_BG,
            progress_color=CLR_ACCENT2,
            height=6,
            corner_radius=3,
        )
        self._progress.grid(row=3, column=0, sticky="ew", padx=20, pady=(8, 0))
        self._progress.set(0)

        # ── Stat Cards with nav-style top/bottom border ──────────
        # Outer wrapper provides the top and bottom 1px black border
        stats_wrapper = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        stats_wrapper.grid(row=4, column=0, sticky="ew", padx=20, pady=(10, 0))
        stats_wrapper.columnconfigure(0, weight=1)

        # Top border line
        ctk.CTkFrame(
            stats_wrapper, fg_color=CLR_DIVIDER,
            height=1, corner_radius=0
        ).grid(row=0, column=0, sticky="ew")

        # Inner row holding 4 cards equally spaced
        stats_row = ctk.CTkFrame(stats_wrapper, fg_color="transparent", corner_radius=0)
        stats_row.grid(row=1, column=0, sticky="ew")
        for i in range(4):
            stats_row.columnconfigure(i, weight=1)

        self._card_dl   = StatCard(stats_row, "📥", "下載完成", CLR_SUCCESS)
        self._card_skip = StatCard(stats_row, "⏭️",  "略過已存在", CLR_SUBTEXT)
        self._card_exif = StatCard(stats_row, "🕒", "EXIF 更新", CLR_ACCENT2)
        self._card_fail = StatCard(stats_row, "❌", "下載失敗", CLR_ERROR)

        self._card_dl.grid  (row=0, column=0, sticky="ew", padx=(0, 6))
        self._card_skip.grid(row=0, column=1, sticky="ew", padx=3)
        self._card_exif.grid(row=0, column=2, sticky="ew", padx=3)
        self._card_fail.grid(row=0, column=3, sticky="ew", padx=(6, 0))

        # Bottom border line
        ctk.CTkFrame(
            stats_wrapper, fg_color=CLR_DIVIDER,
            height=1, corner_radius=0
        ).grid(row=2, column=0, sticky="ew")

        # ── Start Button ─────────────────────────────────────────
        self._start_btn = ctk.CTkButton(
            self,
            text="▶  開始備份",
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=CLR_BTN_PRIMARY,
            hover_color=CLR_BTN_HOVER,
            text_color="#ffffff",
            corner_radius=10,
            command=self._start,
        )
        self._start_btn.grid(row=5, column=0, sticky="ew", padx=20, pady=16)

    # ------------------------------------------------------------------
    # Input dir change callback
    # ------------------------------------------------------------------

    def _on_data_dir_change(self, chosen: str):
        """Update output path entry when user selects input dir."""
        output = Path(chosen) / "plurk_images_by_date"
        text=f"圖檔將儲存在：{output}"
        self._output_path_var.set(text)

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def _append_log(self, msg: str):
        """Append a line to the log textbox (thread-safe via after())."""
        def _write():
            self._log_box.configure(state="normal")
            self._log_box.insert("end", msg + "\n")
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        self.after(0, _write)

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    # ------------------------------------------------------------------
    # Progress callback (called from worker thread)
    # ------------------------------------------------------------------

    def _on_progress(self, current: int, total: int):
        """Update progress bar from worker thread via after()."""
        def _update():
            value = current / total if total > 0 else 0
            self._progress.set(value)
        self.after(0, _update)

    # ------------------------------------------------------------------
    # Backup execution
    # ------------------------------------------------------------------

    def _start(self):
        """Validate inputs, reset UI, then launch backup in background thread."""
        data_dir      = self._data_row.path
        plurks_dir    = data_dir / "data" / "plurks"
        responses_dir = data_dir / "data" / "responses"
        # Output is always created inside the selected backup folder
        output_root   = data_dir / "plurk_images_by_date"
        do_exif       = self._exif_var.get()

        # Reset UI
        self._clear_log()
        self._progress.set(0)
        self._card_dl.set(0)
        self._card_skip.set(0)
        self._card_exif.set(0)
        self._card_fail.set(0)

        plurks_ok    = plurks_dir.exists()
        responses_ok = responses_dir.exists()

        self._append_log("🔍 檢查資料夾結構...")
        self._append_log(f"   {'✅' if plurks_ok    else '❌'} {plurks_dir}")
        self._append_log(f"   {'✅' if responses_ok else '❌'} {responses_dir}")
        self._append_log("")

        if not plurks_ok and not responses_ok:
            self._append_log("⚠️ 找不到 plurks/ 與 responses/ 子資料夾，請確認所選的備份資料夾是否正確。")
            return

        if not plurks_ok:
            self._append_log("💡 找不到 plurks/ 子資料夾，將只處理 responses/。")
        if not responses_ok:
            self._append_log("💡 找不到 responses/ 子資料夾，將只處理 plurks/。")
        self._append_log("")

        self._start_btn.configure(state="disabled", text="執行中...")

        self._append_log("🚀 開始執行備份...")
        self._append_log(f"   備份資料夾：{data_dir}")
        self._append_log(f"   輸出資料夾：{output_root}")
        self._append_log(f"   EXIF 補寫：{'是' if do_exif else '否'}")
        self._append_log("")

        # Run backup in background thread to keep UI responsive
        def worker():
            stats: ProcessStats = run_full_backup(
                plurks_dir=plurks_dir,
                responses_dir=responses_dir,
                output_root=output_root,
                do_exif=do_exif,
                on_log=self._append_log,
                on_progress=self._on_progress,
            )
            self.after(0, lambda: self._on_done(stats))

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, stats: ProcessStats):
        """Called on main thread when backup completes."""
        self._progress.set(1)
        self._card_dl.set(stats.downloaded)
        self._card_skip.set(stats.skipped)
        self._card_exif.set(stats.exif_updated)
        self._card_fail.set(stats.failed)

        self._append_log("")
        self._append_log("=" * 36)
        self._append_log("✨ 備份完成！")
        self._append_log(f"   📥 新下載：{stats.downloaded} 張")
        self._append_log(f"   ⏭️  略過：{stats.skipped} 張")
        self._append_log(f"   ❌ 失敗：{stats.failed} 張")
        if stats.exif_updated:
            self._append_log(f"   🕒 EXIF 更新：{stats.exif_updated} 張")
        self._append_log("=" * 36)

        self._start_btn.configure(state="normal", text="▶  開始備份")


# ==========================================
# Entry point for UI mode
# ==========================================
def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()