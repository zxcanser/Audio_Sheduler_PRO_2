import os
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from typing import Callable, List, Optional

from models import ClientCall, ScheduleEntry
from config import WINDOW_TITLE


class MainWindow:
    WEEKDAY_LABELS: list[tuple[int, str]] = [
        (0, "Пн"),
        (1, "Вт"),
        (2, "Ср"),
        (3, "Чт"),
        (4, "Пт"),
        (5, "Сб"),
        (6, "Вс"),
    ]

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.resizable(False, False)

        self.selected_file_path = tk.StringVar()
        self.selected_file_display = tk.StringVar()
        self.hours_var = tk.StringVar()
        self.minutes_var = tk.StringVar()
        self.volume_var = tk.DoubleVar(value=0.8)
        self.volume_display_var = tk.StringVar(value="0.8")
        self.notification_volume_var = tk.DoubleVar(value=0.8)
        self.notification_volume_display_var = tk.StringVar(value="0.8")
        self.device_var = tk.StringVar()
        self.notification_sound_file_path = tk.StringVar()
        self.notification_sound_display = tk.StringVar()
        self.autostart_var = tk.BooleanVar(value=False)
        self.scheduler_notification_var = tk.BooleanVar(value=False)
        self.client_calls_notification_var = tk.BooleanVar(value=False)
        self.client_calls_file_path = tk.StringVar()
        self.client_calls_file_display = tk.StringVar()
        self.client_calls_volume_var = tk.DoubleVar(value=0.8)
        self.client_calls_volume_display_var = tk.StringVar(value="0.8")
        self.client_calls_speech_rate_var = tk.DoubleVar(value=1.0)
        self.client_calls_speech_rate_display_var = tk.StringVar(value="1.0")
        self.client_calls_device_var = tk.StringVar()
        self.client_calls_interval_var = tk.StringVar(value="5")
        self.scheduler_weekday_vars: dict[int, tk.BooleanVar] = {
            day: tk.BooleanVar(value=True) for day, _ in self.WEEKDAY_LABELS
        }
        self._current_client_call: Optional[ClientCall] = None
        self._queued_client_calls: list[ClientCall] = []
        self._current_client_call_progress = 0.0
        self._client_calls_settings_window: Optional[tk.Toplevel] = None

        self._entry_ids_by_index: list[str] = []

        self.on_add: Optional[Callable[[], None]] = None
        self.on_delete: Optional[Callable[[], None]] = None
        self.on_browse: Optional[Callable[[], None]] = None
        self.on_play: Optional[Callable[[], None]] = None
        self.on_refresh_devices: Optional[Callable[[], None]] = None
        self.on_device_change: Optional[Callable[[str], None]] = None
        self.on_volume_change: Optional[Callable[[float], None]] = None
        self.on_notification_volume_change: Optional[Callable[[float], None]] = None
        self.on_select_entry: Optional[Callable[[], None]] = None
        self.on_browse_client_calls_file: Optional[Callable[[], None]] = None
        self.on_client_calls_volume_change: Optional[Callable[[float], None]] = None
        self.on_client_calls_speech_rate_change: Optional[Callable[[float], None]] = None
        self.on_client_calls_device_change: Optional[Callable[[str], None]] = None
        self.on_client_calls_interval_change: Optional[Callable[[], None]] = None
        self.on_scheduler_weekdays_change: Optional[Callable[[], None]] = None
        self.on_browse_notification_sound_file: Optional[Callable[[], None]] = None
        self.on_play_notification_sound: Optional[Callable[[], None]] = None
        self.on_autostart_toggle: Optional[Callable[[], None]] = None
        self.on_scheduler_notification_toggle: Optional[Callable[[], None]] = None
        self.on_client_calls_notification_toggle: Optional[Callable[[], None]] = None
        self.on_close: Optional[Callable[[], None]] = None
        self.on_window_unmap: Optional[Callable[[], None]] = None
        self.on_window_configure: Optional[Callable[[], None]] = None

        self._build()
        self._fit_window_to_content(self.root)

    def _build(self) -> None:
        frame = tk.Frame(self.root, padx=10, pady=10)
        frame.pack(fill="both", expand=True)

        scheduler_frame = tk.LabelFrame(frame, text="Планировщик оповещений", padx=10, pady=10)
        scheduler_frame.grid(row=0, column=0, sticky="nsew")

        tk.Label(scheduler_frame, text="Аудиофайл:").grid(row=0, column=0, sticky="w")
        tk.Entry(scheduler_frame, textvariable=self.selected_file_display, width=32, state="readonly").grid(row=0, column=1, sticky="we", padx=5)
        tk.Button(scheduler_frame, text="Выбрать", width=12, command=self._browse_clicked).grid(row=0, column=2, padx=5)

        tk.Label(scheduler_frame, text="Время (ЧЧ:ММ):").grid(row=1, column=0, sticky="w", pady=(10, 0))

        time_frame = tk.Frame(scheduler_frame)
        time_frame.grid(row=1, column=1, sticky="w", padx=5, pady=(10, 0))
        tk.Entry(time_frame, textvariable=self.hours_var, width=2).pack(side="left")
        tk.Label(time_frame, text=":").pack(side="left")
        tk.Entry(time_frame, textvariable=self.minutes_var, width=2).pack(side="left")

        tk.Button(scheduler_frame, text="Добавить", width=12, command=self._add_clicked).grid(row=1, column=2, padx=5, pady=(10, 0))

        tk.Label(scheduler_frame, text="Расписание:").grid(row=2, column=0, sticky="w", pady=(15, 5))
        self.listbox = tk.Listbox(scheduler_frame, width=52, height=10)
        self.listbox.grid(row=3, column=0, columnspan=3, sticky="nsew")
        self.listbox.bind("<<ListboxSelect>>", lambda event: self._select_entry())

        actions = tk.Frame(scheduler_frame)
        actions.grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)

        actions_left = tk.Frame(actions)
        actions_left.pack(side="left")
        actions_right = tk.Frame(actions)
        actions_right.pack(side="right")

        tk.Button(actions_left, text="▶/⏹ Play/Stop", width=14, command=self._play_clicked).pack(side="left")
        tk.Button(actions_right, text="Удалить", width=12, command=self._delete_clicked).pack(side="right")

        calls_frame = tk.LabelFrame(frame, text="Очередь вызова клиентов", padx=10, pady=10)
        calls_frame.grid(row=1, column=0, sticky="nsew", pady=(18, 0))
        calls_frame.columnconfigure(0, weight=1)

        self.client_calls_rows_frame = tk.Frame(calls_frame, bd=1, relief="sunken", bg="#ffffff")
        self.client_calls_rows_frame.grid(row=0, column=0, sticky="ew")
        self.client_call_row_canvases = []
        self.client_call_row_fill_ids = []
        self.client_call_row_text_ids = []

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

        stamp_label = tk.Label(
            frame,
            text="Builded by sega",
            font=("TkDefaultFont", 8, "italic"),
            fg="#555555",
        )
        stamp_label.grid(row=2, column=0, pady=(10, 0))

        self.device_var.trace_add("write", self._device_changed)
        self.client_calls_device_var.trace_add("write", self._client_calls_device_changed)

        self.root.bind("<Return>", lambda event: self._add_clicked())
        self.root.bind_all("<Delete>", self._delete_key_pressed)
        self.root.bind_all("<KP_Delete>", self._delete_key_pressed)
        self.root.bind_all("<Command-BackSpace>", self._delete_shortcut_pressed)
        self.root.bind_all("<Command-Delete>", self._delete_shortcut_pressed)
        self.root.bind_all("<space>", self._space_pressed)
        self.root.bind("<Configure>", self._window_configured)
        self.root.bind("<Unmap>", self._window_unmapped)
        self.root.protocol("WM_DELETE_WINDOW", self._close_requested)

        frame.columnconfigure(0, weight=1)
        scheduler_frame.columnconfigure(1, weight=1)
        self._build_menu()
        self._build_client_calls_settings_window()

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)

        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Настройки", command=self.show_client_calls_settings_window)
        menubar.add_cascade(label="Опции", menu=settings_menu)

        self.root.config(menu=menubar)

    def _build_client_calls_settings_window(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("Настройки")
        window.resizable(False, False)
        window.withdraw()
        window.transient(self.root)
        window.protocol("WM_DELETE_WINDOW", self._hide_client_calls_settings_window)

        content = tk.Frame(window, padx=10, pady=10)
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        notebook = ttk.Notebook(content)
        notebook.grid(row=0, column=0, sticky="nsew")

        audio_tab = tk.Frame(notebook, padx=6, pady=6)
        notifications_tab = tk.Frame(notebook, padx=6, pady=6)
        queue_tab = tk.Frame(notebook, padx=6, pady=6)

        notebook.add(audio_tab, text="Аудио")
        notebook.add(notifications_tab, text="Планировщик")
        notebook.add(queue_tab, text="Очередь")

        audio_tab.columnconfigure(0, weight=1)
        notifications_tab.columnconfigure(0, weight=1)
        queue_tab.columnconfigure(0, weight=1)

        devices_frame = tk.LabelFrame(audio_tab, text="Выбор аудио устройства", padx=10, pady=10)
        devices_frame.grid(row=0, column=0, sticky="ew")
        devices_frame.columnconfigure(1, weight=1)
        devices_frame.columnconfigure(2, weight=0)

        tk.Button(devices_frame, text="Обновить устройства", width=18, command=self._refresh_devices_clicked).grid(row=0, column=2, sticky="ne", padx=(10, 0))

        tk.Label(devices_frame, text="Планировщик:").grid(row=0, column=0, sticky="w")
        self.device_menu = tk.OptionMenu(devices_frame, self.device_var, "")
        self.device_menu.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(devices_frame, text="Очередь вызовов:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.client_calls_device_menu = tk.OptionMenu(devices_frame, self.client_calls_device_var, "")
        self.client_calls_device_menu.grid(row=1, column=1, sticky="w", padx=5, pady=(10, 0))

        volumes_frame = tk.LabelFrame(audio_tab, text="Настройка громкости", padx=10, pady=10)
        volumes_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        volumes_frame.columnconfigure(1, weight=1)

        tk.Label(volumes_frame, text="Планировщик:").grid(row=0, column=0, sticky="w")
        scheduler_volume_frame = tk.Frame(volumes_frame)
        scheduler_volume_frame.grid(row=0, column=1, sticky="w", padx=5)
        tk.Scale(
            scheduler_volume_frame,
            from_=0.0,
            to=1.0,
            resolution=0.1,
            orient="horizontal",
            variable=self.volume_var,
            command=self._volume_changed,
            showvalue=False
        ).pack(side="left")
        tk.Label(scheduler_volume_frame, textvariable=self.volume_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

        tk.Label(volumes_frame, text="Очередь вызовов:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        calls_volume_frame = tk.Frame(volumes_frame)
        calls_volume_frame.grid(row=1, column=1, sticky="w", padx=5, pady=(10, 0))
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

        tk.Label(volumes_frame, text="Уведомление:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        notification_volume_frame = tk.Frame(volumes_frame)
        notification_volume_frame.grid(row=2, column=1, sticky="w", padx=5, pady=(10, 0))
        tk.Scale(
            notification_volume_frame,
            from_=0.0,
            to=1.0,
            resolution=0.1,
            orient="horizontal",
            variable=self.notification_volume_var,
            command=self._notification_volume_changed,
            showvalue=False
        ).pack(side="left")
        tk.Label(notification_volume_frame, textvariable=self.notification_volume_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

        notification_frame = tk.LabelFrame(audio_tab, text="Звук уведомления", padx=10, pady=10)
        notification_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        notification_frame.columnconfigure(1, weight=1)

        tk.Label(notification_frame, text="Файл:").grid(row=0, column=0, sticky="w")
        tk.Entry(notification_frame, textvariable=self.notification_sound_display, width=38, state="readonly").grid(row=0, column=1, sticky="we", padx=5)
        tk.Button(notification_frame, text="Выбрать", width=12, command=self._browse_notification_sound_file_clicked).grid(row=0, column=2, padx=5)
        tk.Button(notification_frame, text="Прослушать", width=12, command=self._play_notification_sound_clicked).grid(row=1, column=2, padx=5, pady=(8, 0), sticky="n")

        tk.Checkbutton(
            notification_frame,
            text="Перед планировщиком",
            variable=self.scheduler_notification_var,
            command=self._scheduler_notification_toggled,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        tk.Checkbutton(
            notification_frame,
            text="Перед очередью вызовов",
            variable=self.client_calls_notification_var,
            command=self._client_calls_notification_toggled,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        weekdays_frame = tk.LabelFrame(notifications_tab, text="Дни работы планировщика", padx=10, pady=10)
        weekdays_frame.grid(row=0, column=0, sticky="ew")

        for column, (day, label) in enumerate(self.WEEKDAY_LABELS):
            tk.Checkbutton(
                weekdays_frame,
                text=label,
                variable=self.scheduler_weekday_vars[day],
                command=self._scheduler_weekdays_changed,
            ).grid(row=0, column=column, padx=4, sticky="w")

        startup_frame = tk.LabelFrame(notifications_tab, text="Запуск программы", padx=10, pady=10)
        startup_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        tk.Checkbutton(
            startup_frame,
            text="Запускать вместе с системой",
            variable=self.autostart_var,
            command=self._autostart_toggled,
        ).grid(row=0, column=0, sticky="w")

        queue_frame = tk.LabelFrame(queue_tab, text="Настройки очереди", padx=10, pady=10)
        queue_frame.grid(row=0, column=0, sticky="nsew")
        queue_frame.columnconfigure(1, weight=1)

        tk.Label(queue_frame, text="Файл данных:").grid(row=0, column=0, sticky="w")
        tk.Entry(queue_frame, textvariable=self.client_calls_file_display, width=38, state="readonly").grid(row=0, column=1, sticky="we", padx=5)
        tk.Button(queue_frame, text="Выбрать", width=12, command=self._browse_client_calls_file_clicked).grid(row=0, column=2, padx=5)

        tk.Label(queue_frame, text="Интервал (сек):").grid(row=1, column=0, sticky="w", pady=(12, 0))
        interval_entry = tk.Entry(queue_frame, textvariable=self.client_calls_interval_var, width=3)
        interval_entry.grid(row=1, column=1, sticky="w", padx=5, pady=(12, 0))
        interval_entry.bind("<FocusOut>", lambda event: self._client_calls_interval_changed())
        interval_entry.bind("<Return>", self._client_calls_interval_submitted)

        tk.Label(queue_frame, text="Скорость речи:").grid(row=2, column=0, sticky="w", pady=(12, 0))
        speech_rate_frame = tk.Frame(queue_frame)
        speech_rate_frame.grid(row=2, column=1, columnspan=2, sticky="w", padx=5, pady=(12, 0))
        tk.Scale(
            speech_rate_frame,
            from_=0.5,
            to=1.5,
            resolution=0.1,
            orient="horizontal",
            variable=self.client_calls_speech_rate_var,
            command=self._client_calls_speech_rate_changed,
            showvalue=False
        ).pack(side="left")
        tk.Label(speech_rate_frame, textvariable=self.client_calls_speech_rate_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

        tk.Button(content, text="Закрыть", width=12, command=self._hide_client_calls_settings_window).grid(row=1, column=0, sticky="e", pady=(18, 0))
        self._client_calls_settings_window = window
        self._fit_window_to_content(window)

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

    def _browse_client_calls_file_clicked(self) -> None:
        if self.on_browse_client_calls_file:
            self.on_browse_client_calls_file()

    def _refresh_devices_clicked(self) -> None:
        if self.on_refresh_devices:
            self.on_refresh_devices()

    def _browse_notification_sound_file_clicked(self) -> None:
        if self.on_browse_notification_sound_file:
            self.on_browse_notification_sound_file()

    def _play_notification_sound_clicked(self) -> None:
        if self.on_play_notification_sound:
            self.on_play_notification_sound()

    def _client_calls_volume_changed(self, value: str) -> None:
        self._handle_volume_change(value, self.client_calls_volume_display_var, self.on_client_calls_volume_change)

    def _client_calls_speech_rate_changed(self, value: str) -> None:
        self._handle_volume_change(value, self.client_calls_speech_rate_display_var, self.on_client_calls_speech_rate_change)

    def _notification_volume_changed(self, value: str) -> None:
        self._handle_volume_change(value, self.notification_volume_display_var, self.on_notification_volume_change)

    def _client_calls_device_changed(self, *args) -> None:
        if self.on_client_calls_device_change:
            self.on_client_calls_device_change(self.client_calls_device_var.get())

    def _client_calls_interval_changed(self) -> None:
        if self.on_client_calls_interval_change:
            self.on_client_calls_interval_change()

    def _client_calls_interval_submitted(self, event: tk.Event) -> str:
        self._client_calls_interval_changed()
        return "break"

    def _scheduler_weekdays_changed(self) -> None:
        if self.on_scheduler_weekdays_change:
            self.on_scheduler_weekdays_change()

    def _scheduler_notification_toggled(self) -> None:
        if self.on_scheduler_notification_toggle:
            self.on_scheduler_notification_toggle()

    def _client_calls_notification_toggled(self) -> None:
        if self.on_client_calls_notification_toggle:
            self.on_client_calls_notification_toggle()

    def _autostart_toggled(self) -> None:
        if self.on_autostart_toggle:
            self.on_autostart_toggle()

    def _hide_client_calls_settings_window(self) -> None:
        if self._client_calls_settings_window is not None:
            self._client_calls_settings_window.withdraw()

    def _close_requested(self) -> None:
        if self.on_close:
            self.on_close()

    def _window_unmapped(self, event: tk.Event) -> None:
        if event.widget is self.root and self.on_window_unmap:
            self.on_window_unmap()

    def _window_configured(self, event: tk.Event) -> None:
        if event.widget is self.root and self.on_window_configure:
            self.on_window_configure()

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
        self._handle_volume_change(value, self.volume_display_var, self.on_volume_change)

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

        self._fit_window_to_content(self._client_calls_settings_window)
        self._client_calls_settings_window.deiconify()
        self._client_calls_settings_window.lift()
        self._client_calls_settings_window.focus_force()

    def set_selected_file(self, file_path: str) -> None:
        self._set_file_value(self.selected_file_path, self.selected_file_display, file_path)

    def set_client_calls_file(self, file_path: str) -> None:
        self._set_file_value(self.client_calls_file_path, self.client_calls_file_display, file_path)

    def set_notification_sound_file(self, file_path: str) -> None:
        self._set_file_value(self.notification_sound_file_path, self.notification_sound_display, file_path)

    def get_selected_file(self) -> str:
        return self.selected_file_path.get()

    def get_client_calls_file(self) -> str:
        return self.client_calls_file_path.get()

    def get_notification_sound_file(self) -> str:
        return self.notification_sound_file_path.get()

    def get_time_input(self) -> tuple[str, str]:
        return self.hours_var.get().strip(), self.minutes_var.get().strip()

    def set_time_input(self, time_str: str) -> None:
        hours, minutes = time_str.split(":")
        self.hours_var.set(hours)
        self.minutes_var.set(minutes)

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
            self.listbox.insert(tk.END, f"{entry.time_str} | {entry.file_name}")
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
        self._set_option_menu_values(self.device_menu, self.device_var, device_names, selected)

    def set_client_calls_device_options(self, device_names: List[str], selected: str = "") -> None:
        self._set_option_menu_values(self.client_calls_device_menu, self.client_calls_device_var, device_names, selected)

    def set_volume(self, value: float) -> None:
        self.volume_var.set(value)
        self.volume_display_var.set(f"{value:.1f}")

    def set_client_calls_volume(self, value: float) -> None:
        self.client_calls_volume_var.set(value)
        self.client_calls_volume_display_var.set(f"{value:.1f}")

    def set_client_calls_speech_rate(self, value: float) -> None:
        self.client_calls_speech_rate_var.set(value)
        self.client_calls_speech_rate_display_var.set(f"{value:.1f}")

    def set_notification_volume(self, value: float) -> None:
        self.notification_volume_var.set(value)
        self.notification_volume_display_var.set(f"{value:.1f}")

    def get_client_calls_interval(self) -> str:
        return self.client_calls_interval_var.get().strip()

    def set_client_calls_interval(self, value: float) -> None:
        if float(value).is_integer():
            self.client_calls_interval_var.set(str(int(value)))
        else:
            self.client_calls_interval_var.set(str(value).replace(".", ","))

    def get_scheduler_weekdays(self) -> list[int]:
        return [day for day, _ in self.WEEKDAY_LABELS if self.scheduler_weekday_vars[day].get()]

    def set_scheduler_weekdays(self, weekdays: list[int]) -> None:
        selected = set(weekdays)
        for day, _ in self.WEEKDAY_LABELS:
            self.scheduler_weekday_vars[day].set(day in selected)

    def set_scheduler_notification_enabled(self, enabled: bool) -> None:
        self.scheduler_notification_var.set(enabled)

    def set_autostart_enabled(self, enabled: bool) -> None:
        self.autostart_var.set(enabled)

    def set_client_calls_notification_enabled(self, enabled: bool) -> None:
        self.client_calls_notification_var.set(enabled)

    def is_scheduler_notification_enabled(self) -> bool:
        return self.scheduler_notification_var.get()

    def is_client_calls_notification_enabled(self) -> bool:
        return self.client_calls_notification_var.get()

    def is_autostart_enabled(self) -> bool:
        return self.autostart_var.get()

    def show_error(self, text: str) -> None:
        messagebox.showerror("Ошибка", text)

    def set_main_window_geometry(self, geometry: str) -> None:
        self._fit_window_to_content(self.root)
        position = self._extract_window_position(geometry)
        if position:
            self.root.geometry(position)

    def get_main_window_geometry(self) -> str:
        return self._extract_window_position(self.root.geometry())

    def _fit_window_to_content(self, window: tk.Misc) -> None:
        window.update_idletasks()
        width = window.winfo_reqwidth()
        height = window.winfo_reqheight()
        window.geometry(f"{width}x{height}")

    def _extract_window_position(self, geometry: str) -> str:
        if not geometry:
            return ""

        parts = geometry.split("+")
        if len(parts) < 3:
            return ""

        x_pos = parts[-2].strip()
        y_pos = parts[-1].strip()
        if not x_pos or not y_pos:
            return ""

        return f"+{x_pos}+{y_pos}"

    def _set_option_menu_values(
        self,
        option_menu: tk.OptionMenu,
        variable: tk.StringVar,
        options: List[str],
        selected: str = "",
    ) -> None:
        menu = option_menu["menu"]
        menu.delete(0, "end")

        for name in options:
            menu.add_command(label=name, command=lambda value=name: variable.set(value))

        if options:
            variable.set(selected if selected in options else options[0])
        else:
            variable.set("")

    def _handle_volume_change(
        self,
        value: str,
        display_var: tk.StringVar,
        callback: Optional[Callable[[float], None]],
    ) -> None:
        volume = float(value)
        display_var.set(f"{volume:.1f}")
        if callback:
            callback(volume)

    def _set_file_value(self, path_var: tk.StringVar, display_var: tk.StringVar, file_path: str) -> None:
        path_var.set(file_path)
        display_var.set(os.path.basename(file_path) if file_path else "")
