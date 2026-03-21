import os
import tkinter as tk
from tkinter import messagebox
from typing import Callable, List, Optional

from models import ClientCall, ScheduleEntry
from config import WINDOW_TITLE, WINDOW_SIZE


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.resizable(False, False)

        self.selected_file_path = tk.StringVar()
        self.selected_file_display = tk.StringVar()
        self.hours_var = tk.StringVar()
        self.minutes_var = tk.StringVar()
        self.volume_var = tk.DoubleVar(value=0.8)
        self.volume_display_var = tk.StringVar(value="0.8")
        self.device_var = tk.StringVar()
        self.client_calls_file_path = tk.StringVar()
        self.client_calls_file_display = tk.StringVar()
        self.client_calls_volume_var = tk.DoubleVar(value=0.8)
        self.client_calls_volume_display_var = tk.StringVar(value="0.8")
        self.client_calls_device_var = tk.StringVar()
        self.client_calls_interval_var = tk.StringVar(value="5")
        self._current_client_call: Optional[ClientCall] = None
        self._queued_client_calls: list[ClientCall] = []
        self._current_client_call_progress = 0.0
        self._client_calls_settings_window: Optional[tk.Toplevel] = None

        self._entry_ids_by_index: list[str] = []

        self.on_add: Optional[Callable[[], None]] = None
        self.on_delete: Optional[Callable[[], None]] = None
        self.on_browse: Optional[Callable[[], None]] = None
        self.on_play: Optional[Callable[[], None]] = None
        self.on_stop: Optional[Callable[[], None]] = None
        self.on_device_change: Optional[Callable[[str], None]] = None
        self.on_volume_change: Optional[Callable[[float], None]] = None
        self.on_select_entry: Optional[Callable[[], None]] = None
        self.on_browse_client_calls_file: Optional[Callable[[], None]] = None
        self.on_client_calls_volume_change: Optional[Callable[[float], None]] = None
        self.on_client_calls_device_change: Optional[Callable[[str], None]] = None
        self.on_client_calls_interval_change: Optional[Callable[[], None]] = None
        self.on_close: Optional[Callable[[], None]] = None
        self.on_window_unmap: Optional[Callable[[], None]] = None

        self._build()

    def _build(self) -> None:
        frame = tk.Frame(self.root, padx=10, pady=10)
        frame.pack(fill="both", expand=True)

        scheduler_frame = tk.LabelFrame(frame, text="Планировщик оповещений", padx=10, pady=10)
        scheduler_frame.grid(row=0, column=0, sticky="nsew")

        tk.Label(scheduler_frame, text="Аудиофайл:").grid(row=0, column=0, sticky="w")
        tk.Entry(scheduler_frame, textvariable=self.selected_file_display, width=50, state="readonly").grid(row=0, column=1, sticky="we", padx=5)
        tk.Button(scheduler_frame, text="Выбрать", width=12, command=self._browse_clicked).grid(row=0, column=2, padx=5)

        tk.Label(scheduler_frame, text="Время (HH:MM):").grid(row=1, column=0, sticky="w", pady=(10, 0))

        time_frame = tk.Frame(scheduler_frame)
        time_frame.grid(row=1, column=1, sticky="w", padx=5, pady=(10, 0))
        tk.Entry(time_frame, textvariable=self.hours_var, width=2).pack(side="left")
        tk.Label(time_frame, text=":").pack(side="left", padx=1)
        tk.Entry(time_frame, textvariable=self.minutes_var, width=2).pack(side="left")

        tk.Button(scheduler_frame, text="Добавить", width=12, command=self._add_clicked).grid(row=1, column=2, padx=5, pady=(10, 0))

        tk.Label(scheduler_frame, text="Расписание:").grid(row=2, column=0, sticky="w", pady=(15, 5))
        self.listbox = tk.Listbox(scheduler_frame, width=80, height=10)
        self.listbox.grid(row=3, column=0, columnspan=3, sticky="nsew")
        self.listbox.bind("<<ListboxSelect>>", lambda event: self._select_entry())

        actions = tk.Frame(scheduler_frame)
        actions.grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)

        actions_left = tk.Frame(actions)
        actions_left.pack(side="left")
        actions_right = tk.Frame(actions)
        actions_right.pack(side="right")

        tk.Button(actions_left, text="▶/⏸ Плей/Пауза", width=14, command=self._play_clicked).pack(side="left")
        tk.Button(actions_right, text="Удалить", width=12, command=self._delete_clicked).pack(side="right")

        tk.Label(scheduler_frame, text="Громкость:").grid(row=5, column=0, sticky="w")
        volume_frame = tk.Frame(scheduler_frame)
        volume_frame.grid(row=5, column=1, sticky="w")
        tk.Scale(
            volume_frame,
            from_=0.0,
            to=1.0,
            resolution=0.1,
            orient="horizontal",
            variable=self.volume_var,
            command=self._volume_changed,
            showvalue=False
        ).pack(side="left")
        tk.Label(volume_frame, textvariable=self.volume_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

        tk.Label(scheduler_frame, text="Аудиоустройство:").grid(row=6, column=0, sticky="w", pady=(10, 0))
        self.device_menu = tk.OptionMenu(scheduler_frame, self.device_var, "")
        self.device_menu.grid(row=6, column=1, sticky="w", pady=(10, 0))

        calls_frame = tk.LabelFrame(frame, text="Очередь вызова клиентов", padx=10, pady=10)
        calls_frame.grid(row=1, column=0, sticky="nsew", pady=(18, 0))

        self.client_calls_rows_frame = tk.Frame(calls_frame)
        self.client_calls_rows_frame.grid(row=0, column=0, sticky="we")
        self.client_call_row_canvases: list[tk.Canvas] = []
        self.client_call_row_fill_ids: list[int] = []
        self.client_call_row_text_ids: list[int] = []

        for _ in range(3):
            row_canvas = tk.Canvas(
                self.client_calls_rows_frame,
                height=24,
                highlightthickness=0,
                bd=0,
                bg="#ffffff",
            )
            row_canvas.pack(fill="x")
            fill_id = row_canvas.create_rectangle(0, 0, 0, 24, fill="#63c174", width=0, state="hidden")
            text_id = row_canvas.create_text(6, 12, anchor="w", text="", fill="#1f2933", font=("TkDefaultFont", 10))
            self.client_call_row_canvases.append(row_canvas)
            self.client_call_row_fill_ids.append(fill_id)
            self.client_call_row_text_ids.append(text_id)

        self.client_calls_rows_frame.bind("<Configure>", lambda event: self._resize_client_call_rows())

        self.device_var.trace_add("write", self._device_changed)
        self.client_calls_device_var.trace_add("write", self._client_calls_device_changed)

        self.root.bind("<Return>", lambda event: self._add_clicked())
        self.root.bind_all("<Delete>", self._delete_key_pressed)
        self.root.bind_all("<KP_Delete>", self._delete_key_pressed)
        self.root.bind_all("<Command-BackSpace>", self._delete_shortcut_pressed)
        self.root.bind_all("<Command-Delete>", self._delete_shortcut_pressed)
        self.root.bind_all("<space>", self._space_pressed)
        self.root.bind("<Unmap>", self._window_unmapped)
        self.root.protocol("WM_DELETE_WINDOW", self._close_requested)

        frame.columnconfigure(0, weight=1)
        scheduler_frame.columnconfigure(1, weight=1)
        calls_frame.columnconfigure(0, weight=1)
        self._build_menu()
        self._build_client_calls_settings_window()

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)

        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Настройки вызовов", command=self.show_client_calls_settings_window)
        menubar.add_cascade(label="Настройки", menu=settings_menu)

        self.root.config(menu=menubar)

    def _build_client_calls_settings_window(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("Настройки вызовов")
        window.geometry("560x230")
        window.resizable(False, False)
        window.withdraw()
        window.transient(self.root)
        window.protocol("WM_DELETE_WINDOW", self._hide_client_calls_settings_window)

        content = tk.Frame(window, padx=12, pady=12)
        content.pack(fill="both", expand=True)

        tk.Label(content, text="Файл данных:").grid(row=0, column=0, sticky="w")
        tk.Entry(content, textvariable=self.client_calls_file_display, width=38, state="readonly").grid(row=0, column=1, sticky="we", padx=5)
        tk.Button(content, text="Выбрать", width=12, command=self._browse_client_calls_file_clicked).grid(row=0, column=2, padx=5)

        tk.Label(content, text="Интервал (сек):").grid(row=1, column=0, sticky="w", pady=(12, 0))
        interval_entry = tk.Entry(content, textvariable=self.client_calls_interval_var, width=3)
        interval_entry.grid(row=1, column=1, sticky="w", padx=5, pady=(12, 0))
        interval_entry.bind("<FocusOut>", lambda event: self._client_calls_interval_changed())
        interval_entry.bind("<Return>", self._client_calls_interval_submitted)

        tk.Label(content, text="Громкость Бота:").grid(row=2, column=0, sticky="w", pady=(12, 0))
        calls_volume_frame = tk.Frame(content)
        calls_volume_frame.grid(row=2, column=1, sticky="w", pady=(12, 0))
        tk.Scale(
            calls_volume_frame,
            from_=0.0,
            to=1.0,
            resolution=0.1,
            orient="horizontal",
            variable=self.client_calls_volume_var,
            command=self._client_calls_volume_changed,
            showvalue=False
        ).pack(side="left")
        tk.Label(calls_volume_frame, textvariable=self.client_calls_volume_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

        tk.Label(content, text="Аудиоустройство:").grid(row=3, column=0, sticky="w", pady=(12, 0))
        self.client_calls_device_menu = tk.OptionMenu(content, self.client_calls_device_var, "")
        self.client_calls_device_menu.grid(row=3, column=1, sticky="w", pady=(12, 0))

        tk.Button(content, text="Закрыть", width=12, command=self._hide_client_calls_settings_window).grid(row=4, column=2, sticky="e", pady=(18, 0))
        content.columnconfigure(1, weight=1)
        self._client_calls_settings_window = window

    def _browse_clicked(self) -> None:
        if self.on_browse:
            self.on_browse()

    def _add_clicked(self) -> None:
        if self.on_add:
            self.on_add()


    def _delete_clicked(self) -> None:
        if self.on_delete:
            self.on_delete()


    def _play_clicked(self) -> None:
        if self.on_play:
            self.on_play()

    def _stop_clicked(self) -> None:
        if self.on_stop:
            self.on_stop()

    def _browse_client_calls_file_clicked(self) -> None:
        if self.on_browse_client_calls_file:
            self.on_browse_client_calls_file()

    def _client_calls_volume_changed(self, value: str) -> None:
        self.client_calls_volume_display_var.set(f"{float(value):.1f}")
        if self.on_client_calls_volume_change:
            self.on_client_calls_volume_change(float(value))

    def _client_calls_device_changed(self, *args) -> None:
        if self.on_client_calls_device_change:
            self.on_client_calls_device_change(self.client_calls_device_var.get())

    def _client_calls_interval_changed(self) -> None:
        if self.on_client_calls_interval_change:
            self.on_client_calls_interval_change()

    def _client_calls_interval_submitted(self, event: tk.Event) -> str:
        self._client_calls_interval_changed()
        return "break"


    def _hide_client_calls_settings_window(self) -> None:
        if self._client_calls_settings_window is not None:
            self._client_calls_settings_window.withdraw()

    def _close_requested(self) -> None:
        if self.on_close:
            self.on_close()

    def _window_unmapped(self, event: tk.Event) -> None:
        if event.widget is self.root and self.on_window_unmap:
            self.on_window_unmap()

    def _space_pressed(self, event: tk.Event) -> str:
        if self.on_play:
            self.on_play()
        return "break"

    def _delete_key_pressed(self, event: tk.Event) -> str:
        self._delete_clicked()
        return "break"

    def _delete_shortcut_pressed(self, event: tk.Event) -> str:
        self._delete_clicked()
        return "break"

    def _device_changed(self, *args) -> None:
        if self.on_device_change:
            self.on_device_change(self.device_var.get())

    def _volume_changed(self, value: str) -> None:
        self.volume_display_var.set(f"{float(value):.1f}")
        if self.on_volume_change:
            self.on_volume_change(float(value))

    def _select_entry(self) -> None:
        if self.on_select_entry:
            self.on_select_entry()

    def _resize_client_call_rows(self) -> None:
        self.render_client_calls(
            self._current_client_call,
            self._queued_client_calls,
            self._current_client_call_progress,
        )

    def show_client_calls_settings_window(self) -> None:
        if self._client_calls_settings_window is None:
            return

        self._client_calls_settings_window.deiconify()
        self._client_calls_settings_window.lift()
        self._client_calls_settings_window.focus_force()

    def set_selected_file(self, file_path: str) -> None:
        self.selected_file_path.set(file_path)
        self.selected_file_display.set(os.path.basename(file_path) if file_path else "")

    def set_client_calls_file(self, file_path: str) -> None:
        self.client_calls_file_path.set(file_path)
        self.client_calls_file_display.set(os.path.basename(file_path) if file_path else "")

    def get_selected_file(self) -> str:
        return self.selected_file_path.get()

    def get_client_calls_file(self) -> str:
        return self.client_calls_file_path.get()

    def get_time_input(self) -> tuple[str, str]:
        return self.hours_var.get().strip(), self.minutes_var.get().strip()

    def set_time_input(self, time_str: str) -> None:
        hours, minutes = time_str.split(":")
        self.hours_var.set(hours)
        self.minutes_var.set(minutes)

    def clear_time_input(self) -> None:
        self.hours_var.set("")
        self.minutes_var.set("")

    def get_selected_index(self) -> Optional[int]:
        selected = self.listbox.curselection()
        return selected[0] if selected else None

    def get_selected_entry_id(self) -> Optional[str]:
        index = self.get_selected_index()
        if index is None:
            return None
        if 0 <= index < len(self._entry_ids_by_index):
            return self._entry_ids_by_index[index]
        return None

    def fill_schedule_list(self, entries: List[ScheduleEntry]) -> None:
        self.listbox.delete(0, tk.END)
        self._entry_ids_by_index.clear()

        for entry in entries:
            status = "ON" if entry.enabled else "OFF"
            self.listbox.insert(tk.END, f"{entry.time_str} | {entry.file_name} | {status}")
            self._entry_ids_by_index.append(entry.entry_id)

    def render_client_calls(self, current_call: Optional[ClientCall], queued_calls: List[ClientCall], progress: float) -> None:
        self._current_client_call = current_call
        self._queued_client_calls = queued_calls[:]
        self._current_client_call_progress = progress
        rows: list[tuple[str, float]] = []
        if current_call is not None:
            rows.append((current_call.display_text, max(0.0, min(progress, 1.0))))

        for call in queued_calls[: max(0, 3 - len(rows))]:
            rows.append((call.display_text, 0.0))

        while len(rows) < 3:
            rows.append(("", 0.0))

        for index, (text, fill_ratio) in enumerate(rows):
            canvas = self.client_call_row_canvases[index]
            fill_id = self.client_call_row_fill_ids[index]
            text_id = self.client_call_row_text_ids[index]
            width = max(canvas.winfo_width(), 1)
            height = max(canvas.winfo_height(), 24)

            canvas.config(bg="#ffffff")
            canvas.coords(fill_id, 0, 0, width * fill_ratio, height)
            canvas.itemconfigure(fill_id, state="normal" if text and fill_ratio > 0 else "hidden")
            canvas.coords(text_id, 6, height / 2)
            canvas.itemconfigure(text_id, text=text, fill="#ffffff" if fill_ratio > 0.6 else "#1f2933")

            if not text:
                canvas.itemconfigure(fill_id, state="hidden")

    def set_device_options(self, device_names: List[str], selected: str = "") -> None:
        menu = self.device_menu["menu"]
        menu.delete(0, "end")

        for name in device_names:
            menu.add_command(
                label=name,
                command=lambda value=name: self.device_var.set(value)
            )

        if device_names:
            self.device_var.set(selected if selected in device_names else device_names[0])
        else:
            self.device_var.set("")

    def set_client_calls_device_options(self, device_names: List[str], selected: str = "") -> None:
        menu = self.client_calls_device_menu["menu"]
        menu.delete(0, "end")

        for name in device_names:
            menu.add_command(
                label=name,
                command=lambda value=name: self.client_calls_device_var.set(value)
            )

        if device_names:
            self.client_calls_device_var.set(selected if selected in device_names else device_names[0])
        else:
            self.client_calls_device_var.set("")

    def set_volume(self, value: float) -> None:
        self.volume_var.set(value)
        self.volume_display_var.set(f"{value:.1f}")

    def set_client_calls_volume(self, value: float) -> None:
        self.client_calls_volume_var.set(value)
        self.client_calls_volume_display_var.set(f"{value:.1f}")

    def get_client_calls_interval(self) -> str:
        return self.client_calls_interval_var.get().strip()

    def set_client_calls_interval(self, value: float) -> None:
        if float(value).is_integer():
            self.client_calls_interval_var.set(str(int(value)))
        else:
            self.client_calls_interval_var.set(str(value).replace(".", ","))

    def show_error(self, text: str) -> None:
        messagebox.showerror("Ошибка", text)

    def show_info(self, text: str) -> None:
        messagebox.showinfo("Информация", text)
