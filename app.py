import threading
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk

from utils import sha256
from preview import load_image
from deduplicate import find_and_copy_uniques


class DeduplicatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pixel Art Deduplicator")
        self.geometry("1150x700")
        self.configure(bg="#0f172a")

        self.dir_a = tk.StringVar()
        self.dir_b = tk.StringVar()
        self.dir_out = tk.StringVar()

        self.duplicate_pairs = []

        self._setup_style()
        self._build_ui()

    # ---------- STYLE ----------
    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("default")

        style.configure(
            "TFrame",
            background="#0f172a"
        )

        style.configure(
            "Card.TFrame",
            background="#111827",
            relief="flat"
        )

        style.configure(
            "TLabel",
            background="#0f172a",
            foreground="#e5e7eb"
        )

        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 14, "bold"),
            foreground="#38bdf8"
        )

        style.configure(
            "Muted.TLabel",
            foreground="#94a3b8",
            font=("Segoe UI", 9)
        )

        style.configure(
            "TEntry",
            fieldbackground="#020617",
            foreground="#e5e7eb",
            insertcolor="#38bdf8"
        )

        style.configure(
            "Accent.TButton",
            background="#0ea5e9",
            foreground="#020617",
            font=("Segoe UI", 10, "bold"),
            padding=8
        )

        style.map(
            "Accent.TButton",
            background=[("active", "#38bdf8")]
        )

        style.configure(
            "TProgressbar",
            troughcolor="#020617",
            background="#38bdf8",
            thickness=8
        )

        style.configure(
            "TListbox",
            background="#020617",
            foreground="#e5e7eb"
        )

    # ---------- UI ----------
    def _build_ui(self):
        self._build_header()
        self._build_config()
        self._build_progress()
        self._build_main()

    def _build_header(self):
        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ttk.Label(
            header,
            text="Pixel Art Deduplicator",
            style="Title.TLabel"
        ).pack(anchor="w", padx=16, pady=(12, 2))

        ttk.Label(
            header,
            text="Find exact duplicates and clean datasets for ML pipelines",
            style="Muted.TLabel"
        ).pack(anchor="w", padx=16, pady=(0, 12))

    def _build_config(self):
        card = ttk.Frame(self, style="Card.TFrame")
        card.pack(fill="x", padx=20, pady=10)

        self._folder_row(card, "Existing dataset", self.dir_a)
        self._folder_row(card, "New files", self.dir_b)
        self._folder_row(card, "Output folder", self.dir_out)

        ttk.Button(
            card,
            text="Start Deduplication",
            style="Accent.TButton",
            command=self.start
        ).pack(anchor="e", padx=16, pady=12)

    def _folder_row(self, parent, label, var):
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", padx=16, pady=6)

        ttk.Label(row, text=label, width=18).pack(side="left")
        ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row, text="Browse", command=lambda: self.browse(var)).pack(side="left")

    def _build_progress(self):
        frame = ttk.Frame(self)
        frame.pack(fill="x", padx=20, pady=10)

        self.progress = ttk.Progressbar(frame)
        self.progress.pack(fill="x")

        self.status = ttk.Label(frame, text="Idle", style="Muted.TLabel")
        self.status.pack(anchor="w", pady=4)

    def _build_main(self):
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=20, pady=10)

        # left panel
        left = ttk.Frame(main, style="Card.TFrame", width=300)
        left.pack(side="left", fill="y")

        ttk.Label(left, text="Detected duplicates", style="Title.TLabel") \
            .pack(anchor="w", padx=12, pady=8)

        self.listbox = tk.Listbox(
            left,
            bg="#020617",
            fg="#e5e7eb",
            selectbackground="#38bdf8",
            relief="flat"
        )
        self.listbox.pack(fill="both", expand=True, padx=12, pady=8)
        self.listbox.bind("<<ListboxSelect>>", self.show_preview)

        # right panel
        right = ttk.Frame(main, style="Card.TFrame")
        right.pack(side="right", fill="both", expand=True, padx=(10, 0))

        ttk.Label(right, text="Visual comparison", style="Title.TLabel") \
            .pack(anchor="w", padx=12, pady=8)

        preview = ttk.Frame(right, style="Card.TFrame")
        preview.pack(fill="both", expand=True, padx=12, pady=12)

        self.img_a = ttk.Label(preview)
        self.img_a.pack(side="left", expand=True)

        self.img_b = ttk.Label(preview)
        self.img_b.pack(side="right", expand=True)

    # ---------- LOGIC ----------
    def browse(self, var):
        path = filedialog.askdirectory()
        if path:
            var.set(path)

    def start(self):
        self.listbox.delete(0, tk.END)
        self.duplicate_pairs.clear()
        self.progress["value"] = 0
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        def progress(i, total):
            self._progress(i, total)

        copied, self.duplicate_pairs = find_and_copy_uniques(
            self.dir_b.get(),
            self.dir_a.get(),
            self.dir_out.get(),
            progress_callback=progress
        )

        self.listbox.delete(0, tk.END)
        for dup, _ in self.duplicate_pairs:
            self.listbox.insert(tk.END, dup.name)

        self.status.config(
            text=f"Done • Copied: {copied} • Duplicates: {len(self.duplicate_pairs)}"
        )

    def _progress(self, i, total):
        percent = int((i + 1) / total * 100)
        self.progress["value"] = percent
        self.status.config(text=f"Processing: {i + 1} / {total} ({percent}%)")
        self.update_idletasks()

    # ---------- PREVIEW ----------
    def show_preview(self, event):
        if not self.listbox.curselection():
            return

        idx = self.listbox.curselection()[0]
        b, a = self.duplicate_pairs[idx]

        load_image(a, self.img_a, size=(256, 256))
        load_image(b, self.img_b, size=(256, 256))