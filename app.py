import threading
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk

from utils import sha256
from preview import load_image
from deduplicate import find_duplicates_within_folder, find_duplicates_across_folders


class DeduplicatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Deduplicator")
        self.geometry("1150x700")
        self.configure(bg="#0f172a")

        self.dir_a = tk.StringVar()
        self.dir_b = tk.StringVar()
        self.dir_c = tk.StringVar()

        # Добавляем проверку на изменение пути
        self.dir_a.trace_add("write", lambda *args: self._validate_folder(self.dir_a))
        self.dir_b.trace_add("write", lambda *args: self._validate_folder(self.dir_b))
        self.dir_c.trace_add("write", lambda *args: self._validate_folder(self.dir_c))

        self.duplicate_pairs = []

        self._setup_style()
        self._build_ui()

    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("default")

        style.configure("TFrame", background="#0f172a")
        style.configure("Card.TFrame", background="#111827", relief="flat")
        style.configure("TLabel", background="#0f172a", foreground="#e5e7eb")
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"), foreground="#38bdf8")
        style.configure("Muted.TLabel", foreground="#94a3b8", font=("Segoe UI", 9))
        style.configure("TEntry", fieldbackground="#020617", foreground="#e5e7eb", insertcolor="#38bdf8")
        style.configure("Accent.TButton", background="#0ea5e9", foreground="#020617", font=("Segoe UI", 10, "bold"), padding=8)
        style.map("Accent.TButton", background=[("active", "#38bdf8")])
        style.configure("TProgressbar", troughcolor="#020617", background="#38bdf8", thickness=8)
        style.configure("TListbox", background="#020617", foreground="#e5e7eb")


    def _build_ui(self):
        self._build_header()
        self._build_config()
        self._build_progress()
        self._build_main()

    def _build_header(self):
        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill="x", padx=20, pady=(20, 10))

        ttk.Label(header,text="SHA256 Deduplicator", style="Title.TLabel").pack(anchor="w", padx=16, pady=(12, 2))
        ttk.Label(header, text="Find exact duplicates and clean datasets for ML pipelines", style="Muted.TLabel").pack(anchor="w", padx=16, pady=(0, 12))

    def _build_config(self):
        card = ttk.Frame(self, style="Card.TFrame")
        card.pack(fill="x", padx=20, pady=10)

        self._folder_row(card, "Folder A", self.dir_a)
        self._folder_row(card, "Folder B", self.dir_b)
        self._folder_row(card, "Folder C", self.dir_c)

        ttk.Button(card, text="Start Deduplication", style="Accent.TButton", command=self.start).pack(anchor="e", padx=16, pady=12)
        ttk.Button(card, text="Delete Duplicates from Selected Folder", style="Accent.TButton", command=self.delete_duplicates).pack(anchor="e", padx=16, pady=12)

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

    def _prepare_folders(self):
        folders = []
        if self.dir_a.get():
            folders.append(Path(self.dir_a.get()))
        if self.dir_b.get():
            folders.append(Path(self.dir_b.get()))
        if self.dir_c.get():
            folders.append(Path(self.dir_c.get()))
        return folders

    def browse(self, var):
        path = filedialog.askdirectory()
        if path:
            # Проверяем, не совпадает ли выбранная папка с уже заполненными полями
            if var == self.dir_a:
                if path == self.dir_b.get() or path == self.dir_c.get():
                    tk.messagebox.showerror("Error", "This folder is already selected!")
                    return
            elif var == self.dir_b:
                if path == self.dir_a.get() or path == self.dir_c.get():
                    tk.messagebox.showerror("Error", "This folder is already selected!")
                    return
            elif var == self.dir_c:
                if path == self.dir_a.get() or path == self.dir_b.get():
                    tk.messagebox.showerror("Error", "This folder is already selected!")
                    return

            var.set(path)

    def start(self):
        folders = self._prepare_folders()
        if not folders:
            self.status.config(text="Error: At least one folder must be specified!")
            return

        # Проверяем, что все папки уникальны
        if len(folders) != len(set(str(folder) for folder in folders)):
            self.status.config(text="Error: All folders must be unique!")
            return

        # Проверяем, что все папки существуют
        for folder in folders:
            if not folder.exists():
                self.status.config(text=f"Error: Folder '{folder}' does not exist!")
                return

        self.listbox.delete(0, tk.END)
        self.duplicate_pairs.clear()
        self.progress["value"] = 0
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        def progress(i, total):
            self._progress(i, total)

        folders = self._prepare_folders()
        if not folders:
            self.status.config(text="Error: At least one folder must be specified!")
            return

        if len(folders) == 1:
            self.duplicate_pairs = find_duplicates_within_folder(folders[0], progress_callback=progress)
        else:
            self.duplicate_pairs = find_duplicates_across_folders(*folders, progress_callback=progress)

        self.listbox.delete(0, tk.END)
        for dup, original in self.duplicate_pairs:
            # Добавляем оба имени файлов в список
            self.listbox.insert(tk.END, f"{dup.name} <-> {original.name}")

        self.status.config(text=f"Done • Duplicates: {len(self.duplicate_pairs)}")

    def _progress(self, i, total):
        percent = int((i + 1) / total * 100)
        self.progress["value"] = percent
        self.status.config(text=f"Processing: {i + 1} / {total} ({percent}%)")
        self.update_idletasks()


    def show_preview(self, event):
        if not self.listbox.curselection():
            return

        idx = self.listbox.curselection()[0]
        b, a = self.duplicate_pairs[idx]

        load_image(a, self.img_a, size=(256, 256))
        load_image(b, self.img_b, size=(256, 256))

    def delete_duplicates(self):
        if not self.duplicate_pairs:
            self.status.config(text="No duplicates found!")
            return

        # Запрашиваем подтверждение удаления
        confirm = tk.messagebox.askyesno(
            "Confirm Deletion",
            "Are you sure you want to delete all duplicates?\nThis action cannot be undone!",
            icon="warning"
        )

        if not confirm:
            self.status.config(text="Deletion cancelled.")
            return

        deleted_count = 0
        for dup, _ in self.duplicate_pairs:
            try:
                dup.unlink()  # Удаляем дубликат
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {dup}: {e}")

        self.status.config(text=f"Deleted {deleted_count} duplicates.")
        self.listbox.delete(0, tk.END)
        self.duplicate_pairs.clear()

    def _validate_folder(self, var):
        path = var.get()
        if path and not Path(path).exists():
            # Если папка не существует, показываем предупреждение
            var_entry = self.nametowidget(self.focus_get())
            var_entry.configure(foreground="red")
        else:
            # Возвращаем стандартный цвет текста
            var_entry = self.nametowidget(self.focus_get())
            var_entry.configure(foreground="#e5e7eb")

