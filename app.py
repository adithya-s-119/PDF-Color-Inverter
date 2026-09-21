
import io
import os
import sys
import threading
import subprocess
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import fitz
from PIL import Image, ImageOps, ImageTk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    DND_FILES = None
    TkinterDnD = None


APP_NAME = "PDF Color Inverter"
VERSION = "1.0"


def resource_path(*parts):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


class AppBase:
    pass


class PDFColorInverter(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME}  •  {VERSION}")
        self.geometry("1220x790")
        self.minsize(1000, 680)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.files = []
        self.queue = {}
        self.output_dir = tk.StringVar()
        self.dpi = tk.IntVar(value=200)
        self.ocr_enabled = tk.BooleanVar(value=False)
        self.theme = tk.StringVar(value="System")
        self.suffix = tk.StringVar(value="_inverted")

        self.preview_doc = None
        self.preview_index = 0
        self.preview_image = None
        self.running = False

        self._build_ui()
        self._enable_native_windows_drop()

        self._refresh_queue()
        self._update_preview()


    def _enable_native_windows_drop(self):
        """Accept files dropped from Windows Explorer using WM_DROPFILES."""
        if sys.platform != "win32":
            return

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32

            WM_DROPFILES = 0x0233
            GWLP_WNDPROC = -4

            WNDPROC = ctypes.WINFUNCTYPE(
                ctypes.c_longlong,
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            )

            hwnd = wintypes.HWND(self.winfo_id())

            def wndproc(h, msg, wparam, lparam):
                if msg == WM_DROPFILES:
                    try:
                        hdrop = wparam
                        count = shell32.DragQueryFileW(
                            hdrop, 0xFFFFFFFF, None, 0
                        )
                        paths = []

                        for i in range(count):
                            length = shell32.DragQueryFileW(
                                hdrop, i, None, 0
                            )
                            buf = ctypes.create_unicode_buffer(length + 1)
                            shell32.DragQueryFileW(
                                hdrop, i, buf, length + 1
                            )
                            paths.append(buf.value)

                        shell32.DragFinish(hdrop)

                        self.after(0, lambda p=paths: self._add_paths(p))
                    except Exception as exc:
                        self.after(
                            0,
                            lambda e=exc: self._show_error(
                                "Drag-and-drop error", e
                            )
                        )
                    return 0

                return user32.CallWindowProcW(
                    self._native_old_wndproc,
                    h, msg, wparam, lparam
                )

            # Keep both the callback and original procedure alive.
            self._native_drop_proc = WNDPROC(wndproc)
            shell32.DragAcceptFiles(hwnd, True)

            self._native_old_wndproc = user32.SetWindowLongPtrW(
                hwnd,
                GWLP_WNDPROC,
                ctypes.cast(
                    self._native_drop_proc,
                    ctypes.c_void_p
                ).value
            )

            self._native_drop_user32 = user32
            self._native_drop_shell32 = shell32
            self._native_drop_hwnd = hwnd

            if hasattr(self, "drop_hint"):
                self.drop_hint.configure(
                    text="Drag & drop PDF files anywhere into this window"
                )

        except Exception:
            # Normal Add PDF button remains available.
            if hasattr(self, "drop_hint"):
                self.drop_hint.configure(
                    text="Drag & drop unavailable — use Add PDF files"
                )

    # ---------- UI ----------
    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._sidebar()
        self._main()

    def _sidebar(self):
        side = ctk.CTkFrame(
            self, width=230, corner_radius=0,
            fg_color=("gray94", "gray12")
        )
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)

        ctk.CTkLabel(
            side, text="PDF\nColor Inverter",
            font=ctk.CTkFont("Segoe UI", 27, "bold"),
            justify="left"
        ).pack(anchor="w", padx=28, pady=(34, 8))

        ctk.CTkLabel(
            side, text="Document utility",
            font=ctk.CTkFont(size=12),
            text_color=("gray45", "gray60")
        ).pack(anchor="w", padx=30, pady=(0, 30))

        self._nav(side, "▣  Invert PDF", True)
        self._nav(side, "▤  Conversion queue", False)
        self._nav(side, "⌕  English + Malayalam OCR", False)

        ctk.CTkFrame(side, fg_color="transparent").pack(fill="both", expand=True)

        ctk.CTkLabel(
            side, text="Appearance",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray40", "gray65")
        ).pack(anchor="w", padx=30, pady=(0, 8))

        ctk.CTkOptionMenu(
            side, values=["System", "Light", "Dark"],
            variable=self.theme, command=lambda v: ctk.set_appearance_mode(v),
            width=170, height=36, corner_radius=9
        ).pack(anchor="w", padx=28, pady=(0, 26))

        ctk.CTkLabel(
            side, text=f"Version {VERSION}",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray55")
        ).pack(anchor="w", padx=30, pady=(0, 24))

    def _nav(self, parent, text, active):
        ctk.CTkLabel(
            parent, text=text, height=42, corner_radius=8,
            anchor="w", padx=14,
            fg_color=("gray86", "gray20") if active else "transparent",
            text_color=("gray15", "gray92") if active else ("gray35", "gray68"),
            font=ctk.CTkFont(size=13, weight="bold" if active else "normal")
        ).pack(fill="x", padx=18, pady=3)

    def _main(self):
        main = ctk.CTkFrame(self, fg_color=("gray97", "gray10"), corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        head = ctk.CTkFrame(main, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=38, pady=(28, 8))
        head.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            head, text="Invert your PDFs",
            font=ctk.CTkFont("Segoe UI", 29, "bold"),
            anchor="w"
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            head,
            text="Preview the result, drag files into the queue, and convert them in batch.",
            font=ctk.CTkFont(size=13),
            text_color=("gray42", "gray62"),
            anchor="w"
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        toolbar = ctk.CTkFrame(main, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", padx=38, pady=(12, 12))

        self.add_btn = ctk.CTkButton(
            toolbar, text="+  Add PDF files", width=150, height=40,
            command=self._add_files
        )
        self.add_btn.pack(side="left")

        self.folder_btn = ctk.CTkButton(
            toolbar, text="Add folder", width=115, height=40,
            fg_color=("gray88", "gray22"),
            text_color=("gray12", "gray90"),
            hover_color=("gray80", "gray28"),
            command=self._add_folder
        )
        self.folder_btn.pack(side="left", padx=9)

        self.clear_btn = ctk.CTkButton(
            toolbar, text="Clear", width=80, height=40,
            fg_color="transparent",
            border_width=1, border_color=("gray78", "gray30"),
            text_color=("gray25", "gray82"),
            command=self._clear
        )
        self.clear_btn.pack(side="left")

        self.drop_hint = ctk.CTkLabel(
            toolbar,
            text="Drag & drop PDF files anywhere into this window",
            font=ctk.CTkFont(size=11),
            text_color=("gray48", "gray60")
        )
        self.drop_hint.pack(side="left", padx=18)

        self.count = ctk.CTkLabel(
            toolbar, text="0 files",
            font=ctk.CTkFont(size=12),
            text_color=("gray45", "gray60")
        )
        self.count.pack(side="right")

        content = ctk.CTkFrame(main, fg_color="transparent")
        content.grid(row=2, column=0, sticky="nsew", padx=38, pady=(0, 25))
        content.grid_columnconfigure(0, weight=5)
        content.grid_columnconfigure(1, weight=3)
        content.grid_rowconfigure(0, weight=1)

        self._queue_panel(content)
        self._right_panel(content)

    def _queue_panel(self, parent):
        panel = ctk.CTkFrame(
            parent, corner_radius=14,
            fg_color=("white", "gray14"),
            border_width=1, border_color=("gray88", "gray25")
        )
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(panel, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 5))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top, text="Conversion queue",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            top, text="Each file reports its own progress and status.",
            font=ctk.CTkFont(size=11),
            text_color=("gray48", "gray58")
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        self.queue_scroll = ctk.CTkScrollableFrame(
            panel, fg_color=("gray97", "gray11"), corner_radius=10
        )
        self.queue_scroll.grid(
            row=2, column=0, sticky="nsew",
            padx=16, pady=(8, 16)
        )

    def _right_panel(self, parent):
        right = ctk.CTkFrame(parent, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        preview = ctk.CTkFrame(
            right, corner_radius=14,
            fg_color=("white", "gray14"),
            border_width=1, border_color=("gray88", "gray25")
        )
        preview.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        preview.grid_columnconfigure(0, weight=1)
        preview.grid_rowconfigure(1, weight=1)

        ph = ctk.CTkFrame(preview, fg_color="transparent")
        ph.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 7))
        ph.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            ph, text="Live preview",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        self.page_label = ctk.CTkLabel(
            ph, text="No PDF selected",
            font=ctk.CTkFont(size=10),
            text_color=("gray48", "gray60")
        )
        self.page_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        nav = ctk.CTkFrame(ph, fg_color="transparent")
        nav.grid(row=0, column=1, rowspan=2, sticky="e")

        self.prev_btn = ctk.CTkButton(
            nav, text="‹", width=34, height=30,
            command=lambda: self._preview_page(-1)
        )
        self.prev_btn.pack(side="left", padx=2)

        self.next_btn = ctk.CTkButton(
            nav, text="›", width=34, height=30,
            command=lambda: self._preview_page(1)
        )
        self.next_btn.pack(side="left", padx=2)

        self.preview_area = ctk.CTkLabel(
            preview,
            text="Add a PDF to see a live inverted preview.",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60"),
            fg_color=("gray96", "gray11"),
            corner_radius=10
        )
        self.preview_area.grid(
            row=1, column=0, sticky="nsew",
            padx=16, pady=(0, 16)
        )

        settings = ctk.CTkFrame(
            right, corner_radius=14,
            fg_color=("white", "gray14"),
            border_width=1, border_color=("gray88", "gray25")
        )
        settings.grid(row=1, column=0, sticky="ew")
        settings.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            settings, text="Settings",
            font=ctk.CTkFont(size=15, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(13, 10))

        # DPI
        dpirow = ctk.CTkFrame(settings, fg_color="transparent")
        dpirow.grid(row=1, column=0, sticky="ew", padx=18)
        dpirow.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            dpirow, text="Quality", font=ctk.CTkFont(size=10, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        self.dpi_slider = ctk.CTkSlider(
            dpirow, from_=100, to=300, number_of_steps=8,
            command=self._dpi
        )
        self.dpi_slider.set(200)
        self.dpi_slider.grid(row=0, column=1, sticky="ew", padx=12)

        self.dpi_text = ctk.CTkLabel(
            dpirow, text="200 DPI", width=60,
            font=ctk.CTkFont(size=10, weight="bold")
        )
        self.dpi_text.grid(row=0, column=2)

        # OCR
        ocrrow = ctk.CTkFrame(settings, fg_color="transparent")
        ocrrow.grid(row=2, column=0, sticky="ew", padx=18, pady=(12, 0))
        ocrrow.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            ocrrow, text="English + Malayalam OCR",
            font=ctk.CTkFont(size=11, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        self.ocr_switch = ctk.CTkSwitch(
            ocrrow, text="", variable=self.ocr_enabled,
            width=42, command=self._ocr_changed
        )
        self.ocr_switch.grid(row=0, column=1, sticky="e")

        self.ocr_status = ctk.CTkLabel(
            settings,
            text="OCR is optional • Tesseract runtime is bundled during build",
            font=ctk.CTkFont(size=9),
            text_color=("gray48", "gray60"),
            anchor="w"
        )
        self.ocr_status.grid(row=3, column=0, sticky="ew", padx=18, pady=(3, 10))

        # Output
        outrow = ctk.CTkFrame(settings, fg_color="transparent")
        outrow.grid(row=4, column=0, sticky="ew", padx=18)
        outrow.grid_columnconfigure(0, weight=1)

        self.output_entry = ctk.CTkEntry(
            outrow, textvariable=self.output_dir,
            height=34, corner_radius=8,
            placeholder_text="Output folder (defaults to Inverted beside source)"
        )
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 7))

        ctk.CTkButton(
            outrow, text="…", width=40, height=34,
            command=self._choose_output
        ).grid(row=0, column=1)

        ctk.CTkEntry(
            settings, textvariable=self.suffix,
            height=34, corner_radius=8,
            placeholder_text="Filename suffix"
        ).grid(row=5, column=0, sticky="ew", padx=18, pady=(8, 12))

        self.start_btn = ctk.CTkButton(
            settings, text="Invert queued PDFs",
            height=42, corner_radius=9,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._start
        )
        self.start_btn.grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 16))

    # ---------- DnD ----------

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            parent=self, title="Select PDF files",
            filetypes=[("PDF files", "*.pdf")]
        )
        if paths:
            self._add_paths(paths)

    def _add_folder(self):
        folder = filedialog.askdirectory(
            parent=self, title="Select folder containing PDFs"
        )
        if not folder:
            return
        self._add_paths(
            sorted(str(p) for p in Path(folder).glob("*.pdf"))
        )

    def _add_paths(self, paths):
        for p in paths:
            p = os.path.abspath(str(p))
            if p.lower().endswith(".pdf") and p not in self.files:
                self.files.append(p)
                self.queue[p] = {"status": "Queued", "progress": 0}
        self._refresh_queue()
        self._select_preview(0)

    def _clear(self):
        if self.running:
            return
        self.files.clear()
        self.queue.clear()
        self._refresh_queue()
        self._close_preview()

    def _remove(self, path):
        if self.running:
            return
        if path in self.files:
            self.files.remove(path)
        self.queue.pop(path, None)
        self._refresh_queue()
        self._select_preview(0)

    def _refresh_queue(self):
        for w in self.queue_scroll.winfo_children():
            w.destroy()

        n = len(self.files)
        self.count.configure(text=f"{n} file" + ("" if n == 1 else "s"))

        if not self.files:
            ctk.CTkLabel(
                self.queue_scroll,
                text="No files in the queue.\n\n"
                     "Add PDFs above or drag them into the window.",
                font=ctk.CTkFont(size=13),
                text_color=("gray50", "gray60"),
                justify="center"
            ).pack(expand=True, pady=150)
            return

        for i, path in enumerate(self.files):
            state = self.queue.get(path, {"status": "Queued", "progress": 0})

            row = ctk.CTkFrame(
                self.queue_scroll, corner_radius=10,
                fg_color=("white", "gray16"),
                border_width=1, border_color=("gray88", "gray27")
            )
            row.pack(fill="x", padx=3, pady=4)
            row.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                row, text=f"{i+1:02d}", width=34, height=30,
                corner_radius=7, fg_color=("gray90", "gray25"),
                text_color=("gray35", "gray75"),
                font=ctk.CTkFont(size=9, weight="bold")
            ).grid(row=0, column=0, rowspan=3, padx=(8, 9), pady=9)

            ctk.CTkLabel(
                row, text=os.path.basename(path),
                font=ctk.CTkFont(size=11, weight="bold"),
                anchor="w"
            ).grid(row=0, column=1, sticky="ew", pady=(8, 0))

            status_color = ("gray48", "gray60")
            if state["status"] == "Done":
                status_color = "#16A34A"
            elif state["status"] == "Error":
                status_color = "#DC2626"
            elif state["status"] == "Converting":
                status_color = "#2563EB"

            ctk.CTkLabel(
                row, text=state["status"],
                font=ctk.CTkFont(size=9),
                text_color=status_color, anchor="w"
            ).grid(row=1, column=1, sticky="ew")

            bar = ctk.CTkProgressBar(row, height=6, corner_radius=4)
            bar.set(float(state["progress"]))
            bar.grid(row=2, column=1, sticky="ew", pady=(4, 9))

            ctk.CTkButton(
                row, text="×", width=28, height=28,
                corner_radius=7, fg_color="transparent",
                hover_color=("gray88", "gray28"),
                text_color=("gray45", "gray70"),
                command=lambda p=path: self._remove(p)
            ).grid(row=0, column=2, rowspan=3, padx=8)

            row.bind("<Button-1>", lambda e, p=path: self._preview_path(p))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, p=path: self._preview_path(p))

    # ---------- Preview ----------
    def _select_preview(self, index):
        if not self.files:
            self._close_preview()
            return
        index = max(0, min(index, len(self.files) - 1))
        self._preview_path(self.files[index])

    def _preview_path(self, path):
        try:
            if self.preview_doc:
                self.preview_doc.close()
            self.preview_doc = fitz.open(path)
            self.preview_index = 0
            self._update_preview()
        except Exception as exc:
            self._show_error("Preview error", exc)

    def _close_preview(self):
        if self.preview_doc:
            self.preview_doc.close()
        self.preview_doc = None
        self.preview_area.configure(image=None, text="Add a PDF to see a live inverted preview.")
        self.page_label.configure(text="No PDF selected")

    def _preview_page(self, delta):
        if not self.preview_doc:
            return
        self.preview_index = max(
            0, min(self.preview_index + delta, len(self.preview_doc) - 1)
        )
        self._update_preview()

    def _update_preview(self):
        if not self.preview_doc:
            return

        page = self.preview_doc[self.preview_index]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.4, 1.4), colorspace=fitz.csRGB, alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        image = ImageOps.invert(image)

        area_w = max(self.preview_area.winfo_width() - 20, 280)
        area_h = max(self.preview_area.winfo_height() - 20, 300)

        image.thumbnail((area_w, area_h), Image.Resampling.LANCZOS)
        self.preview_image = ctk.CTkImage(
            light_image=image, dark_image=image,
            size=image.size
        )
        self.preview_area.configure(image=self.preview_image, text="")
        self.page_label.configure(
            text=f"Page {self.preview_index + 1} of {len(self.preview_doc)}"
        )

    # ---------- Settings ----------
    def _dpi(self, value):
        dpi = int(round(float(value) / 25) * 25)
        self.dpi.set(dpi)
        self.dpi_text.configure(text=f"{dpi} DPI")
        if self.preview_doc:
            self._update_preview()

    def _choose_output(self):
        folder = filedialog.askdirectory(
            parent=self, title="Choose output folder"
        )
        if folder:
            self.output_dir.set(folder)

    def _ocr_changed(self):
        if self.ocr_enabled.get():
            self.ocr_status.configure(
                text="OCR: English + Malayalam • bundled Tesseract runtime",
                text_color="#2563EB"
            )
        else:
            self.ocr_status.configure(
                text="OCR disabled • no OCR processing will be performed",
                text_color=("gray48", "gray60")
            )

    # ---------- Conversion ----------
    def _start(self):
        if self.running:
            return

        if not self.files:
            messagebox.showwarning(
                "Queue is empty",
                "Add at least one PDF first.",
                parent=self
            )
            return

        output = self.output_dir.get().strip()
        if not output:
            output = os.path.join(os.path.dirname(self.files[0]), "Inverted")
            self.output_dir.set(output)
        os.makedirs(output, exist_ok=True)

        self.running = True
        self.start_btn.configure(state="disabled", text="Converting…")
        self.add_btn.configure(state="disabled")
        self.folder_btn.configure(state="disabled")
        self.clear_btn.configure(state="disabled")

        for p in self.files:
            self.queue[p] = {"status": "Queued", "progress": 0}
        self._refresh_queue()

        threading.Thread(
            target=self._worker,
            args=(list(self.files), output, int(self.dpi.get()), self.ocr_enabled.get()),
            daemon=True
        ).start()

    def _worker(self, files, output, dpi, ocr):
        completed = 0
        errors = []

        for path in files:
            self._queue_update(path, "Converting", 0)
            try:
                self._convert_one(path, output, dpi, ocr)
                self._queue_update(path, "Done", 1)
                completed += 1
            except Exception as exc:
                self._queue_update(path, "Error", 0)
                errors.append(f"{os.path.basename(path)}: {exc}")

        self.after(0, lambda: self._finished(completed, errors))

    def _queue_update(self, path, status, progress):
        def update():
            if path in self.queue:
                self.queue[path] = {
                    "status": status, "progress": progress
                }
                self._refresh_queue()
        self.after(0, update)

    def _convert_one(self, source, output, dpi, ocr):
        src = fitz.open(source)
        dst = fitz.open()

        try:
            matrix = fitz.Matrix(dpi / 72, dpi / 72)
            total = max(len(src), 1)
            stem = Path(source).stem
            suffix = self.suffix.get().strip() or "_inverted"
            dest = os.path.join(output, f"{stem}{suffix}.pdf")

            if os.path.abspath(dest) == os.path.abspath(source):
                dest = os.path.join(output, f"{stem}_inverted.pdf")

            for page_no, page in enumerate(src, 1):
                pix = page.get_pixmap(
                    matrix=matrix, colorspace=fitz.csRGB, alpha=False
                )
                image = Image.frombytes(
                    "RGB", (pix.width, pix.height), pix.samples
                )
                inverted = ImageOps.invert(image)

                buf = io.BytesIO()
                inverted.save(buf, "PNG", optimize=True)

                new_page = dst.new_page(
                    width=page.rect.width, height=page.rect.height
                )
                new_page.insert_image(
                    new_page.rect, stream=buf.getvalue()
                )

                if ocr:
                    self._add_ocr(new_page, inverted, page.rect)

                self._queue_update(
                    source, "Converting", page_no / total
                )

            try:
                dst.set_metadata(src.metadata)
            except Exception:
                pass

            dst.save(dest, deflate=True, garbage=4)

        finally:
            dst.close()
            src.close()

    def _tesseract_path(self):
        """Find the bundled Tesseract executable first, then a system install."""
        bundled = resource_path("tesseract", "tesseract.exe")
        if bundled.exists():
            return str(bundled)

        candidates = [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        found = shutil.which("tesseract")
        if found:
            return found

        raise RuntimeError(
            "Tesseract OCR could not be found. "
            "Please rebuild the application with build_windows.bat."
        )

    def _tessdata_path(self, tess):
        """Return a valid tessdata directory next to the selected executable."""
        bundled = resource_path("tesseract", "tessdata")
        if (bundled / "eng.traineddata").is_file() and (bundled / "mal.traineddata").is_file():
            return bundled

        system = Path(tess).resolve().parent / "tessdata"
        if (system / "eng.traineddata").is_file() and (system / "mal.traineddata").is_file():
            return system

        raise RuntimeError(
            "English/Malayalam OCR models are missing.\n\n"
            f"Expected:\n{bundled}\\eng.traineddata\n"
            f"{bundled}\\mal.traineddata\n\n"
            "Please rebuild the application with build_windows.bat."
        )

    def _add_ocr(self, page, image, page_rect):
        import pytesseract

        tess = self._tesseract_path()
        tessdata = self._tessdata_path(tess)
        font_path = resource_path("fonts", "NotoSansMalayalam-Regular.ttf")

        if not font_path.is_file():
            raise RuntimeError("The bundled Malayalam Unicode font is missing.")

        # Explicitly tell Tesseract where its language data is located.
        # This is important for PyInstaller one-file builds, where resources
        # are extracted into a temporary _MEIPASS directory.
        os.environ["TESSDATA_PREFIX"] = str(tessdata)
        pytesseract.pytesseract.tesseract_cmd = tess

        config = f'--tessdata-dir "{tessdata}" --oem 1 --psm 3'

        data = pytesseract.image_to_data(
            image,
            lang="eng+mal",
            config=config,
            output_type=pytesseract.Output.DICT
        )

        sx = page_rect.width / image.width
        sy = page_rect.height / image.height

        # Register the Unicode font once for the page.
        page.insert_font(
            fontname="NotoMalayalam",
            fontfile=str(font_path)
        )

        for i, text_value in enumerate(data["text"]):
            text_value = (text_value or "").strip()
            if not text_value:
                continue

            try:
                confidence = float(data["conf"][i])
            except Exception:
                confidence = -1

            if confidence < 20:
                continue

            x = float(data["left"][i]) * sx
            y = float(data["top"][i]) * sy
            w = max(1.0, float(data["width"][i]) * sx)
            h = max(1.0, float(data["height"][i]) * sy)

            fontsize = max(4.0, min(24.0, h * 0.78))
            rect = fitz.Rect(x, y, x + w, y + h * 1.25)

            # render_mode=3 = invisible text. The OCR remains searchable/selectable.
            page.insert_textbox(
                rect,
                text_value,
                fontsize=fontsize,
                fontname="NotoMalayalam",
                color=(0, 0, 0),
                render_mode=3,
                overlay=True
            )

    def _finished(self, completed, errors):
        self.running = False
        self.start_btn.configure(state="normal", text="Invert queued PDFs")
        self.add_btn.configure(state="normal")
        self.folder_btn.configure(state="normal")
        self.clear_btn.configure(state="normal")

        if errors:
            messagebox.showwarning(
                "Conversion finished",
                f"{completed} PDF(s) converted.\n\n"
                f"{len(errors)} failed:\n\n" +
                "\n".join(errors[:10]),
                parent=self
            )
        else:
            messagebox.showinfo(
                "Conversion complete",
                f"{completed} PDF(s) converted successfully.",
                parent=self
            )


if __name__ == "__main__":
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

    app = PDFColorInverter()
    app.mainloop()