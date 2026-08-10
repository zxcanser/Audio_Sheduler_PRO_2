import tkinter as tk
from tkinter import ttk


def build_main_window(window) -> None:
    frame = tk.Frame(window.root, padx=10, pady=6)
    frame.pack(fill="both", expand=True)

    scheduler_frame = tk.LabelFrame(frame, text="Планировщик оповещений", padx=10, pady=10)
    scheduler_frame.grid(row=0, column=0, sticky="nsew")

    tk.Label(scheduler_frame, text="Аудиофайл:").grid(row=0, column=0, sticky="w")
    tk.Entry(scheduler_frame, textvariable=window.selected_file_display, width=32, state="readonly").grid(row=0, column=1, sticky="we", padx=5)
    tk.Button(scheduler_frame, text="Выбрать", width=12, command=window._browse_clicked).grid(row=0, column=2, padx=5)

    tk.Label(scheduler_frame, text="Время:").grid(row=1, column=0, sticky="w", pady=(3, 0))

    time_frame = tk.Frame(scheduler_frame)
    time_frame.grid(row=1, column=1, sticky="w", padx=5, pady=(3, 0))
    window._time_entry = tk.Entry(time_frame, textvariable=window.time_var, width=5, justify="center")
    window._time_entry.pack(side="left")
    window._time_entry.bind("<FocusIn>", window._time_entry_focused)
    window._time_entry.bind("<Button-1>", window._time_entry_clicked)
    window._time_entry.bind("<Left>", window._time_entry_move_left)
    window._time_entry.bind("<Right>", window._time_entry_move_right)
    window._time_entry.bind("<Home>", window._time_entry_home)
    window._time_entry.bind("<End>", window._time_entry_end)
    window._time_entry.bind("<BackSpace>", window._time_entry_backspace)
    window._time_entry.bind("<Delete>", window._time_entry_delete)
    window._time_entry.bind("<KeyPress>", window._time_entry_keypress, add="+")

    window._schedule_add_button = tk.Button(scheduler_frame, text="Добавить", width=12, command=window._add_clicked)
    window._schedule_add_button.grid(row=1, column=2, padx=5, pady=(3, 0))

    schedule_header = tk.Frame(scheduler_frame)
    schedule_header.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(10, 4))
    schedule_header.columnconfigure(0, weight=1)
    tk.Label(schedule_header, text="Расписание:").grid(row=0, column=0, sticky="w")

    workday_indicator = tk.Frame(schedule_header, cursor="hand2")
    workday_indicator.grid(row=0, column=1, sticky="e")
    workday_indicator.bind("<Button-1>", window._workday_indicator_clicked)
    window._workday_lamp_canvas = tk.Canvas(
        workday_indicator,
        width=10,
        height=10,
        highlightthickness=0,
        bd=0,
    )
    window._workday_lamp_canvas.pack(side="left", padx=(0, 4))
    window._workday_lamp_id = window._workday_lamp_canvas.create_oval(2, 2, 8, 8, fill="#8a8a8a", outline="")
    window._workday_lamp_canvas.bind("<Button-1>", window._workday_indicator_clicked)
    workday_label = tk.Label(workday_indicator, textvariable=window.workday_status_var, cursor="hand2")
    workday_label.pack(side="left")
    workday_label.bind("<Button-1>", window._workday_indicator_clicked)

    window.listbox = tk.Listbox(scheduler_frame, width=52, height=10)
    window.listbox.grid(row=3, column=0, columnspan=3, sticky="nsew")
    window.listbox.bind("<<ListboxSelect>>", lambda event: window._select_entry())
    window.listbox.bind("<Double-Button-1>", window._schedule_listbox_double_clicked)

    actions = tk.Frame(scheduler_frame)
    actions.grid(row=4, column=0, columnspan=3, sticky="ew", pady=6)

    actions_left = tk.Frame(actions)
    actions_left.pack(side="left")
    actions_center = tk.Frame(actions)
    actions_center.pack(side="left", fill="x", expand=True, padx=(10, 10))
    actions_right = tk.Frame(actions)
    actions_right.pack(side="right")

    window._play_button = tk.Button(actions_left, text="▶", width=6, command=window._play_clicked)
    window._play_button.pack(side="left")
    window.last_error_status_label = tk.Label(
        actions_center,
        textvariable=window.last_error_status_var,
        fg="#2f855a",
        anchor="w",
        cursor="hand2",
    )
    window.last_error_status_label.pack(fill="x")
    window.last_error_status_label.bind("<Button-1>", window._last_error_status_clicked)
    tk.Button(actions_right, text="Удалить", width=9, command=window._delete_clicked).pack(side="right")

    calls_frame = tk.LabelFrame(frame, text="Очередь вызовов", padx=10, pady=10)
    calls_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
    calls_frame.columnconfigure(0, weight=1)

    window.client_calls_rows_frame = tk.Frame(calls_frame, bd=1, relief="sunken", bg="#ffffff")
    window.client_calls_rows_frame.grid(row=0, column=0, sticky="ew")
    window.client_call_row_canvases = []
    window.client_call_row_fill_ids = []
    window.client_call_row_text_ids = []
    window.client_call_row_remove_ids = []

    for _ in range(window.VISIBLE_QUEUE_ROWS):
        row_canvas = tk.Canvas(
            window.client_calls_rows_frame,
            height=24,
            highlightthickness=0,
            bd=0,
            bg="#ffffff",
        )
        row_canvas.pack(fill="x")
        fill_id = row_canvas.create_rectangle(0, 0, 0, 24, fill="#63c174", width=0, state="hidden")
        text_id = row_canvas.create_text(6, 12, anchor="w", text="", fill="#1f2933", font=("TkDefaultFont", 10))
        remove_id = row_canvas.create_text(0, 12, anchor="e", text="", fill="#8a8a8a", font=("TkDefaultFont", 10, "bold"))
        row_canvas.bind("<Button-1>", window._queue_row_clicked)
        window.client_call_row_canvases.append(row_canvas)
        window.client_call_row_fill_ids.append(fill_id)
        window.client_call_row_text_ids.append(text_id)
        window.client_call_row_remove_ids.append(remove_id)

    for canvas in window.client_call_row_canvases[1:]:
        canvas.pack_forget()

    window.client_calls_rows_frame.bind("<Configure>", lambda event: window._resize_client_call_rows())

    stamp_label = tk.Label(
        frame,
        text="ASP v2.3.3 builded by sega",
        font=("TkDefaultFont", 8, "italic"),
        fg="#555555",
    )
    stamp_label.grid(row=2, column=0, pady=(4, 0))

    window.device_var.trace_add("write", window._device_changed)
    window.client_calls_device_var.trace_add("write", window._client_calls_device_changed)
    window.client_calls_voice_message_device_var.trace_add("write", window._client_calls_voice_message_device_changed)
    window.generator_device_var.trace_add("write", window._generator_device_changed)

    window.root.bind("<Return>", lambda event: window._add_clicked())
    window.root.bind_all("<Delete>", window._delete_key_pressed)
    window.root.bind_all("<KP_Delete>", window._delete_key_pressed)
    window.root.bind_all("<Command-BackSpace>", window._delete_shortcut_pressed)
    window.root.bind_all("<Command-Delete>", window._delete_shortcut_pressed)
    window.root.bind_all("<space>", window._space_pressed)
    window.root.bind_all("<Button-1>", window._global_left_click, add="+")
    window.root.bind("<Configure>", window._window_configured)
    window.root.bind("<Unmap>", window._window_unmapped)
    window.root.protocol("WM_DELETE_WINDOW", window._close_requested)

    frame.columnconfigure(0, weight=1)
    scheduler_frame.columnconfigure(1, weight=1)
    window._build_menu()
    window._build_client_calls_settings_window()
    window._build_generator_window()
    window._build_employees_window()
    window._bind_edit_shortcuts_recursively(window.root)
    window._bind_button_hover_recursively(window.root)
    if window._client_calls_settings_window is not None:
        window._bind_button_hover_recursively(window._client_calls_settings_window)
    if window._generator_window is not None:
        window._bind_button_hover_recursively(window._generator_window)
    if window._employees_window is not None:
        window._bind_button_hover_recursively(window._employees_window)


def build_menu(window) -> None:
    menubar = tk.Menu(window.root)

    program_menu = tk.Menu(menubar, tearoff=0)
    program_menu.add_command(label="Убрать в трей", command=window._hide_to_tray_clicked)
    program_menu.add_command(label="Сохранить и закрыть", command=window._quit_application_clicked)
    menubar.add_cascade(label="Программа", menu=program_menu)

    settings_menu = tk.Menu(menubar, tearoff=0)
    hotkeys_menu = tk.Menu(settings_menu, tearoff=0)
    hotkeys_menu.add_command(label="Enter - добавить запись", state="disabled")
    hotkeys_menu.add_command(label="Delete - удалить запись", state="disabled")
    hotkeys_menu.add_command(label="Пробел - Play/Stop", state="disabled")

    settings_menu.add_command(label="Настройки", command=window.show_client_calls_settings_window)
    settings_menu.add_command(label="Генератор", command=window._show_generator_clicked)
    settings_menu.add_command(label="Сотрудники", command=window._show_employees_clicked)
    settings_menu.add_cascade(label="Горячие клавиши", menu=hotkeys_menu)
    menubar.add_cascade(label="Опции", menu=settings_menu)

    window.root.config(menu=menubar)


def build_client_calls_settings_window(window) -> None:
    build_fn = _build_client_calls_settings_window
    build_fn(window)


def _build_client_calls_settings_window(window) -> None:
    window_instance = tk.Toplevel(window.root)
    window_instance.title("Настройки")
    window_instance.resizable(False, False)
    window_instance.withdraw()
    window._apply_window_icon(window_instance)
    window_instance.protocol("WM_DELETE_WINDOW", window._hide_client_calls_settings_window)

    content = tk.Frame(window_instance, padx=10, pady=10)
    content.pack(fill="both", expand=True)
    content.columnconfigure(0, weight=1)
    notebook = ttk.Notebook(content)
    notebook.grid(row=0, column=0, sticky="nsew")

    audio_tab = tk.Frame(notebook, padx=6, pady=6)
    planner_tab = tk.Frame(notebook, padx=6, pady=6)
    notification_tab = tk.Frame(notebook, padx=6, pady=6)
    queue_tab = tk.Frame(notebook, padx=6, pady=6)
    generator_tab = tk.Frame(notebook, padx=6, pady=6)

    notebook.add(audio_tab, text="Аудио")
    notebook.add(planner_tab, text="Планировщик")
    notebook.add(notification_tab, text="Очередь")
    notebook.add(queue_tab, text="Вызовы")
    notebook.add(generator_tab, text="Генератор")

    audio_tab.columnconfigure(0, weight=1)
    planner_tab.columnconfigure(0, weight=1)
    notification_tab.columnconfigure(0, weight=1)
    queue_tab.columnconfigure(0, weight=1)
    generator_tab.columnconfigure(0, weight=1)

    devices_frame = tk.LabelFrame(audio_tab, text="Выбор аудио устройства", padx=10, pady=10)
    devices_frame.grid(row=0, column=0, sticky="ew")
    devices_frame.columnconfigure(1, weight=1)

    tk.Label(devices_frame, text="Планировщик:").grid(row=0, column=0, sticky="w")
    window.device_menu = tk.OptionMenu(devices_frame, window.device_var, "")
    window.device_menu.grid(row=0, column=1, sticky="ew", padx=5)

    tk.Label(devices_frame, text="Очередь вызовов:").grid(row=1, column=0, sticky="w", pady=(10, 0))
    window.client_calls_device_menu = tk.OptionMenu(devices_frame, window.client_calls_device_var, "")
    window.client_calls_device_menu.grid(row=1, column=1, sticky="ew", padx=5, pady=(10, 0))

    tk.Label(devices_frame, text="Голосовое сообщение:").grid(row=2, column=0, sticky="w", pady=(10, 0))
    window.client_calls_voice_message_device_menu = tk.OptionMenu(devices_frame, window.client_calls_voice_message_device_var, "")
    window.client_calls_voice_message_device_menu.grid(row=2, column=1, sticky="ew", padx=5, pady=(10, 0))

    tk.Label(devices_frame, text="Генератор:").grid(row=3, column=0, sticky="w", pady=(10, 0))
    window.generator_device_menu = tk.OptionMenu(devices_frame, window.generator_device_var, "")
    window.generator_device_menu.grid(row=3, column=1, sticky="ew", padx=5, pady=(10, 0))

    tk.Button(devices_frame, text="Обновить устройства", width=18, command=window._refresh_devices_clicked).grid(
        row=4,
        column=1,
        sticky="e",
        padx=5,
        pady=(12, 0),
    )

    volumes_frame = tk.LabelFrame(audio_tab, text="Настройка громкости", padx=10, pady=10)
    volumes_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
    volumes_frame.columnconfigure(1, weight=1)

    tk.Label(volumes_frame, text="Планировщик:").grid(row=0, column=0, sticky="w")
    scheduler_volume_frame = tk.Frame(volumes_frame)
    scheduler_volume_frame.grid(row=0, column=1, sticky="w", padx=5)
    window._create_settings_scale(
        scheduler_volume_frame,
        variable=window.volume_var,
        command=window._volume_changed,
        from_=0.0,
        to=1.0,
        resolution=0.1,
    ).pack(side="left")
    tk.Label(scheduler_volume_frame, textvariable=window.volume_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

    tk.Label(volumes_frame, text="Очередь вызовов:").grid(row=1, column=0, sticky="w", pady=(10, 0))
    calls_volume_frame = tk.Frame(volumes_frame)
    calls_volume_frame.grid(row=1, column=1, sticky="w", padx=5, pady=(10, 0))
    window._create_settings_scale(
        calls_volume_frame,
        variable=window.client_calls_volume_var,
        command=window._client_calls_volume_changed,
        from_=0.0,
        to=1.0,
        resolution=0.1,
    ).pack(side="left")
    tk.Label(calls_volume_frame, textvariable=window.client_calls_volume_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

    tk.Label(volumes_frame, text="Звук уведомления:").grid(row=2, column=0, sticky="w", pady=(10, 0))
    notification_volume_frame = tk.Frame(volumes_frame)
    notification_volume_frame.grid(row=2, column=1, sticky="w", padx=5, pady=(10, 0))
    window._create_settings_scale(
        notification_volume_frame,
        variable=window.notification_volume_var,
        command=window._notification_volume_changed,
        from_=0.0,
        to=1.0,
        resolution=0.1,
    ).pack(side="left")
    tk.Label(notification_volume_frame, textvariable=window.notification_volume_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

    tk.Label(volumes_frame, text="Генератор:").grid(row=3, column=0, sticky="w", pady=(10, 0))
    generator_volume_frame = tk.Frame(volumes_frame)
    generator_volume_frame.grid(row=3, column=1, sticky="w", padx=5, pady=(10, 0))
    window._create_settings_scale(
        generator_volume_frame,
        variable=window.generator_volume_var,
        command=window._generator_volume_changed,
        from_=0.0,
        to=1.0,
        resolution=0.1,
    ).pack(side="left")
    tk.Label(generator_volume_frame, textvariable=window.generator_volume_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

    notification_frame = tk.LabelFrame(audio_tab, text="Звук уведомления", padx=10, pady=10)
    notification_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
    notification_frame.columnconfigure(1, weight=1)

    tk.Label(notification_frame, text="Файл:").grid(row=0, column=0, sticky="w")
    tk.Entry(notification_frame, textvariable=window.notification_sound_display, width=30, state="readonly").grid(row=0, column=1, sticky="we", padx=5)
    tk.Button(notification_frame, text="Выбрать", width=12, command=window._browse_notification_sound_file_clicked).grid(row=0, column=2, padx=5)
    tk.Button(
        notification_frame,
        textvariable=window.notification_sound_preview_button_var,
        width=12,
        command=window._play_notification_sound_clicked,
    ).grid(row=1, column=2, padx=5, pady=(8, 0), sticky="n")

    tk.Checkbutton(
        notification_frame,
        text="Перед планировщиком",
        variable=window.scheduler_notification_var,
        command=window._scheduler_notification_toggled,
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
    tk.Checkbutton(
        notification_frame,
        text="Перед очередью вызовов",
        variable=window.client_calls_notification_var,
        command=window._client_calls_notification_toggled,
    ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
    tk.Checkbutton(
        notification_frame,
        text="Звук перед повтором",
        variable=window.client_calls_repeat_notification_var,
        command=window._client_calls_repeat_notification_toggled,
    ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

    startup_frame = tk.LabelFrame(planner_tab, text="Запуск программы", padx=10, pady=10)
    startup_frame.grid(row=0, column=0, sticky="ew")
    tk.Checkbutton(
        startup_frame,
        text="Запускать вместе с системой",
        variable=window.autostart_var,
        command=window._autostart_toggled,
    ).grid(row=0, column=0, sticky="w")

    updates_frame = tk.LabelFrame(planner_tab, text="Обновления", padx=10, pady=10)
    updates_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
    window.update_check_button = tk.Button(
        updates_frame,
        textvariable=window.update_check_button_var,
        width=22,
        command=window._check_updates_clicked,
    )
    window.update_check_button.grid(row=0, column=0, sticky="w")

    schedule_transfer_frame = tk.LabelFrame(planner_tab, text="Перенос расписания", padx=10, pady=10)
    schedule_transfer_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
    tk.Button(
        schedule_transfer_frame,
        text="Экспорт расписания",
        width=18,
        command=window._export_schedule_clicked,
    ).grid(row=0, column=0, sticky="w")
    tk.Button(
        schedule_transfer_frame,
        text="Импорт расписания",
        width=18,
        command=window._import_schedule_clicked,
    ).grid(row=0, column=1, sticky="w", padx=(8, 0))

    queue_frame = tk.LabelFrame(queue_tab, text="Настройки вызовов", padx=10, pady=10)
    queue_frame.grid(row=0, column=0, sticky="nsew")
    queue_frame.columnconfigure(1, weight=1)

    tk.Label(queue_frame, text="Файл данных:").grid(row=0, column=0, sticky="w")
    tk.Entry(queue_frame, textvariable=window.client_calls_file_display, width=30, state="readonly").grid(row=0, column=1, sticky="we", padx=5)
    tk.Button(queue_frame, text="Выбрать", width=12, command=window._browse_client_calls_file_clicked).grid(row=0, column=2, padx=5)

    tk.Label(queue_frame, text="Список сотрудников:").grid(row=1, column=0, sticky="w", pady=(12, 0))
    window.employees_file_path = tk.StringVar()
    window.employees_file_display = tk.StringVar()
    tk.Entry(queue_frame, textvariable=window.employees_file_display, width=30, state="readonly").grid(row=1, column=1, sticky="we", padx=5, pady=(12, 0))
    tk.Button(queue_frame, text="Выбрать", width=12, command=window._browse_employees_file_clicked).grid(row=1, column=2, padx=5, pady=(12, 0))

    tk.Label(queue_frame, text="Скорость воспроизведения:").grid(row=2, column=0, sticky="w", pady=(12, 0))
    speech_rate_frame = tk.Frame(queue_frame)
    speech_rate_frame.grid(row=2, column=1, columnspan=2, sticky="w", padx=5, pady=(12, 0))
    window._create_settings_scale(
        speech_rate_frame,
        variable=window.client_calls_speech_rate_var,
        command=window._client_calls_speech_rate_changed,
        from_=0.5,
        to=2.0,
        resolution=0.1,
    ).pack(side="left")
    tk.Label(speech_rate_frame, textvariable=window.client_calls_speech_rate_display_var, width=4, anchor="w").pack(side="left", padx=(8, 0))

    number_assembly_frame = tk.LabelFrame(queue_frame, text="Склейка номера", padx=10, pady=8)
    number_assembly_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(12, 0))
    number_assembly_frame.columnconfigure(1, weight=1)
    tk.Checkbutton(
        number_assembly_frame,
        text="Автообрезка тишины у цифр и букв",
        variable=window.number_trim_silence_var,
        command=window._number_trim_silence_toggled,
    ).grid(row=0, column=0, columnspan=3, sticky="w")

    tk.Label(number_assembly_frame, text="Порог тишины (дБ):").grid(row=1, column=0, sticky="w", pady=(8, 0))
    threshold_frame = tk.Frame(number_assembly_frame)
    threshold_frame.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=(8, 0))
    window._create_settings_scale(
        threshold_frame,
        variable=window.number_silence_threshold_var,
        command=window._number_silence_threshold_changed,
        from_=-70,
        to=-20,
        resolution=1,
    ).pack(side="left")
    tk.Label(threshold_frame, textvariable=window.number_silence_threshold_display_var, width=5, anchor="w").pack(side="left", padx=(8, 0))

    tk.Label(number_assembly_frame, text="Запас начала (мс):").grid(row=2, column=0, sticky="w", pady=(8, 0))
    leading_frame = tk.Frame(number_assembly_frame)
    leading_frame.grid(row=2, column=1, columnspan=2, sticky="w", padx=5, pady=(8, 0))
    window._create_settings_scale(
        leading_frame,
        variable=window.number_trim_leading_padding_var,
        command=window._number_trim_leading_padding_changed,
        from_=0,
        to=200,
        resolution=5,
    ).pack(side="left")
    tk.Label(leading_frame, textvariable=window.number_trim_leading_padding_display_var, width=5, anchor="w").pack(side="left", padx=(8, 0))

    tk.Label(number_assembly_frame, text="Запас хвоста (мс):").grid(row=3, column=0, sticky="w", pady=(8, 0))
    trailing_frame = tk.Frame(number_assembly_frame)
    trailing_frame.grid(row=3, column=1, columnspan=2, sticky="w", padx=5, pady=(8, 0))
    window._create_settings_scale(
        trailing_frame,
        variable=window.number_trim_trailing_padding_var,
        command=window._number_trim_trailing_padding_changed,
        from_=0,
        to=300,
        resolution=5,
    ).pack(side="left")
    tk.Label(trailing_frame, textvariable=window.number_trim_trailing_padding_display_var, width=5, anchor="w").pack(side="left", padx=(8, 0))

    tk.Label(number_assembly_frame, text="Пауза между символами (мс):").grid(row=4, column=0, sticky="w", pady=(8, 0))
    pause_frame = tk.Frame(number_assembly_frame)
    pause_frame.grid(row=4, column=1, columnspan=2, sticky="w", padx=5, pady=(8, 0))
    window._create_settings_scale(
        pause_frame,
        variable=window.number_symbol_pause_var,
        command=window._number_symbol_pause_changed,
        from_=0,
        to=300,
        resolution=5,
    ).pack(side="left")
    tk.Label(pause_frame, textvariable=window.number_symbol_pause_display_var, width=5, anchor="w").pack(side="left", padx=(8, 0))

    tk.Label(number_assembly_frame, text="Тест номера:").grid(row=5, column=0, sticky="w", pady=(8, 0))
    preview_frame = tk.Frame(number_assembly_frame)
    preview_frame.grid(row=5, column=1, columnspan=2, sticky="w", padx=5, pady=(8, 0))
    tk.Entry(preview_frame, textvariable=window.number_preview_var, width=12).pack(side="left")
    tk.Button(
        preview_frame,
        text="Прослушать",
        width=12,
        command=window._preview_number_assembly_clicked,
    ).pack(side="left", padx=(8, 0))

    tk.Label(queue_frame, text="Интервал (сек):").grid(row=4, column=0, sticky="w", pady=(12, 0))
    interval_entry = tk.Entry(queue_frame, textvariable=window.client_calls_interval_var, width=2)
    interval_entry.grid(row=4, column=1, sticky="w", padx=5, pady=(12, 0))
    interval_entry.bind("<FocusOut>", lambda event: window._client_calls_interval_changed())
    interval_entry.bind("<Return>", window._client_calls_interval_submitted)

    tk.Checkbutton(
        queue_frame,
        text="Повторный вызов клиента",
        variable=window.client_calls_repeat_var,
        command=window._client_calls_repeat_toggled,
    ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(10, 0))

    tk.Label(queue_frame, text="Интервал повтора (сек):").grid(row=6, column=0, sticky="w", pady=(12, 0))
    repeat_interval_entry = tk.Entry(queue_frame, textvariable=window.client_calls_repeat_interval_var, width=2)
    repeat_interval_entry.grid(row=6, column=1, sticky="w", padx=5, pady=(12, 0))
    repeat_interval_entry.bind("<FocusOut>", lambda event: window._client_calls_repeat_interval_changed())
    repeat_interval_entry.bind("<Return>", window._client_calls_repeat_interval_submitted)

    api_frame = tk.LabelFrame(notification_tab, text="API прием вызовов", padx=10, pady=10)
    api_frame.grid(row=0, column=0, sticky="ew")
    api_frame.columnconfigure(1, weight=1)
    api_frame.columnconfigure(2, weight=0)

    tk.Checkbutton(
        api_frame,
        text="Включить внутренний API сервер",
        variable=window.client_calls_api_enabled_var,
        command=window._client_calls_api_enabled_toggled,
    ).grid(row=0, column=0, columnspan=2, sticky="w")
    tk.Button(
        api_frame,
        textvariable=window.client_calls_api_edit_button_var,
        width=10,
        command=window._toggle_client_calls_api_edit_mode,
    ).grid(row=0, column=2, sticky="e")

    tk.Label(api_frame, text="Адрес:").grid(row=1, column=0, sticky="w", pady=(12, 0))
    window._client_calls_api_host_entry = tk.Entry(api_frame, textvariable=window.client_calls_api_host_var, width=18)
    window._client_calls_api_host_entry.grid(row=1, column=1, sticky="w", padx=5, pady=(12, 0))
    window._bind_standard_edit_shortcuts(window._client_calls_api_host_entry)
    window._client_calls_api_host_entry.bind("<FocusOut>", lambda event: window._client_calls_api_host_changed())
    window._client_calls_api_host_entry.bind("<Return>", window._client_calls_api_host_submitted)

    tk.Label(api_frame, text="Порт:").grid(row=2, column=0, sticky="w", pady=(10, 0))
    window._client_calls_api_port_entry = tk.Entry(api_frame, textvariable=window.client_calls_api_port_var, width=8)
    window._client_calls_api_port_entry.grid(row=2, column=1, sticky="w", padx=5, pady=(10, 0))
    window._bind_standard_edit_shortcuts(window._client_calls_api_port_entry)
    window._client_calls_api_port_entry.bind("<FocusOut>", lambda event: window._client_calls_api_port_changed())
    window._client_calls_api_port_entry.bind("<Return>", window._client_calls_api_port_submitted)

    tk.Label(api_frame, text="Токен:").grid(row=3, column=0, sticky="w", pady=(10, 0))
    token_row = tk.Frame(api_frame)
    token_row.grid(row=3, column=1, sticky="w", padx=5, pady=(10, 0))
    window._client_calls_api_token_entry = tk.Entry(
        token_row,
        textvariable=window.client_calls_api_token_button_var,
        width=15,
        state="disabled",
        disabledbackground="#e6e6e6",
        disabledforeground="#333333",
        relief="sunken",
        bd=1,
    )
    window._client_calls_api_token_entry.pack(side="left")
    window._client_calls_api_copy_button = tk.Button(
        token_row,
        text="⧉",
        width=2,
        command=window._copy_client_calls_api_token_clicked,
    )
    window._client_calls_api_copy_button.pack(side="left", padx=(3, 0))
    actions_row = tk.Frame(api_frame)
    actions_row.grid(row=3, column=2, sticky="e", padx=5, pady=(10, 0))
    window._client_calls_api_generate_button = tk.Button(
        actions_row,
        text="Новый токен",
        width=12,
        command=window._generate_client_calls_api_token_clicked,
    )
    window._client_calls_api_generate_button.pack(side="left")
    window._set_client_calls_api_editable(False)

    voice_message_frame = tk.LabelFrame(notification_tab, text="Голосовое сообщение", padx=10, pady=10)
    voice_message_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
    voice_message_frame.columnconfigure(1, weight=1)

    tk.Label(voice_message_frame, text="Файл:").grid(row=0, column=0, sticky="w")
    tk.Entry(voice_message_frame, textvariable=window.client_calls_voice_message_file_display, width=30, state="readonly").grid(row=0, column=1, sticky="we", padx=5)
    tk.Button(voice_message_frame, text="Выбрать", width=12, command=window._browse_client_calls_voice_message_file_clicked).grid(row=0, column=2, padx=5)

    tk.Label(voice_message_frame, text="Громкость голосового сообщения:").grid(row=1, column=0, sticky="w", pady=(12, 0))
    voice_message_volume_frame = tk.Frame(voice_message_frame)
    voice_message_volume_frame.grid(row=1, column=1, sticky="w", padx=5, pady=(12, 0))
    window._create_settings_scale(
        voice_message_volume_frame,
        variable=window.client_calls_voice_message_volume_var,
        command=window._client_calls_voice_message_volume_changed,
        from_=0.0,
        to=2.0,
        resolution=0.1,
    ).pack(side="left")
    tk.Label(
        voice_message_frame,
        textvariable=window.client_calls_voice_message_volume_display_var,
        width=5,
        anchor="w",
    ).grid(row=1, column=2, sticky="w", padx=(2, 0), pady=(12, 0))

    generator_frame = tk.LabelFrame(generator_tab, text="AI Генератор", padx=10, pady=10)
    generator_frame.grid(row=0, column=0, sticky="ew")
    generator_frame.columnconfigure(1, weight=1)
    generator_frame.columnconfigure(2, weight=0)

    tk.Label(generator_frame, text="API ключ:").grid(row=0, column=0, sticky="w")
    generator_api_row = tk.Frame(generator_frame)
    generator_api_row.grid(row=0, column=1, columnspan=2, sticky="w", padx=5)
    window._generator_api_key_entry = tk.Entry(
        generator_api_row,
        textvariable=window.generator_api_key_button_var,
        width=12,
        state="disabled",
        disabledbackground="#e6e6e6",
        disabledforeground="#333333",
        relief="sunken",
        bd=1,
    )
    window._generator_api_key_entry.pack(side="left")
    window._generator_api_key_entry.bind("<FocusOut>", window._generator_api_key_unfocused)
    window._generator_api_key_entry.bind("<KeyRelease>", window._generator_api_key_changed)
    tk.Button(
        generator_api_row,
        textvariable=window.generator_api_edit_button_var,
        width=6,
        command=window._toggle_generator_api_key_edit_mode,
    ).pack(side="left", padx=(6, 0))
    window._set_generator_api_key_editable(False)

    tk.Label(generator_frame, text="Скорость голоса:").grid(row=1, column=0, sticky="w", pady=(12, 0))
    generator_speed_frame = tk.Frame(generator_frame)
    generator_speed_frame.grid(row=1, column=1, sticky="w", padx=5, pady=(12, 0))
    window._create_settings_scale(
        generator_speed_frame,
        variable=window.generator_speed_var,
        command=window._generator_speed_changed,
        from_=-100,
        to=100,
        resolution=1,
    ).pack(side="left")
    tk.Label(generator_frame, textvariable=window.generator_speed_display_var, width=5, anchor="w").grid(
        row=1,
        column=2,
        sticky="w",
        padx=(2, 0),
        pady=(12, 0),
    )

    tk.Label(generator_frame, text="Громкость генерации:").grid(row=2, column=0, sticky="w", pady=(12, 0))
    generator_master_volume_frame = tk.Frame(generator_frame)
    generator_master_volume_frame.grid(row=2, column=1, sticky="w", padx=5, pady=(12, 0))
    window._create_settings_scale(
        generator_master_volume_frame,
        variable=window.generator_master_volume_var,
        command=window._generator_master_volume_changed,
        from_=50,
        to=150,
        resolution=1,
    ).pack(side="left")
    tk.Label(generator_frame, textvariable=window.generator_master_volume_display_var, width=5, anchor="w").grid(
        row=2,
        column=2,
        sticky="w",
        padx=(2, 0),
        pady=(12, 0),
    )

    tk.Label(generator_frame, text="Язык произвольного текста:").grid(row=3, column=0, sticky="w", pady=(12, 0))
    window.client_calls_text_language_combobox = ttk.Combobox(
        generator_frame,
        textvariable=window.client_calls_text_language_var,
        state="normal",
        width=27,
    )
    window.client_calls_text_language_combobox.grid(row=3, column=1, columnspan=2, sticky="ew", padx=5, pady=(12, 0))
    window.client_calls_text_language_combobox.bind("<<ComboboxSelected>>", window._client_calls_text_language_selected)
    window.client_calls_text_language_combobox.bind("<KeyRelease>", window._client_calls_text_language_typed)

    tk.Label(generator_frame, text="Акцент:").grid(row=4, column=0, sticky="w", pady=(12, 0))
    window.generator_accent_combobox = ttk.Combobox(
        generator_frame,
        textvariable=window.generator_accent_var,
        state="normal",
        width=27,
    )
    window.generator_accent_combobox.grid(row=4, column=1, columnspan=2, sticky="ew", padx=5, pady=(12, 0))
    window.generator_accent_combobox.bind("<<ComboboxSelected>>", window._generator_accent_selected)
    window.generator_accent_combobox.bind("<KeyRelease>", window._generator_accent_typed)
    window.generator_accent_hint_label = tk.Label(generator_frame, text="", fg="#666666")
    window.generator_accent_hint_label.grid(row=5, column=1, columnspan=2, sticky="w", padx=5, pady=(4, 0))
    window.generator_accent_hint_label.grid_remove()

    tk.Label(generator_frame, text="Голос для произвольного текста:").grid(row=6, column=0, sticky="w", pady=(12, 0))
    window.client_calls_text_voice_combobox = ttk.Combobox(
        generator_frame,
        textvariable=window.client_calls_text_voice_var,
        state="normal",
        width=27,
    )
    window.client_calls_text_voice_combobox.grid(row=6, column=1, columnspan=2, sticky="ew", padx=5, pady=(12, 0))
    window.client_calls_text_voice_combobox.bind("<<ComboboxSelected>>", window._client_calls_text_voice_selected)
    window.client_calls_text_voice_combobox.bind("<KeyRelease>", window._client_calls_text_voice_typed)
    window.client_calls_text_voice_combobox.bind("<Button-1>", window._client_calls_text_voice_dropdown_clicked)
    window.client_calls_text_voice_combobox.bind("<FocusIn>", window._client_calls_text_voice_dropdown_clicked)
    tk.Button(
        generator_frame,
        textvariable=window.client_calls_text_voice_preview_button_var,
        width=12,
        command=window._preview_client_calls_text_voice_clicked,
    ).grid(row=7, column=1, columnspan=2, sticky="e", padx=5, pady=(8, 0))

    tk.Button(content, text="Закрыть", width=12, command=window._hide_client_calls_settings_window).grid(row=1, column=0, sticky="e", pady=(18, 0))
    window._client_calls_settings_window = window_instance
    window._fit_window_to_content(window_instance)


def build_generator_window(window) -> None:
    window_instance = tk.Toplevel(window.root)
    window_instance.title("Генератор")
    window_instance.resizable(False, False)
    window_instance.withdraw()
    window._apply_window_icon(window_instance)
    window_instance.protocol("WM_DELETE_WINDOW", window._hide_generator_window)

    content = tk.Frame(window_instance, padx=10, pady=10)
    content.pack(fill="both", expand=True)
    content.columnconfigure(0, weight=1)

    generator_frame = tk.LabelFrame(content, text="AI Генератор речи", padx=10, pady=10)
    generator_frame.grid(row=0, column=0, sticky="ew")
    generator_frame.columnconfigure(1, weight=1)
    generator_frame.columnconfigure(2, weight=0)

    tk.Label(generator_frame, text="Язык:", anchor="w", width=12).grid(row=0, column=0, sticky="w", pady=(0, 10))
    window.generator_language_combobox = ttk.Combobox(
        generator_frame,
        textvariable=window.generator_language_var,
        state="normal",
        width=32,
    )
    window.generator_language_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=(0, 10))
    window.generator_language_combobox.bind("<<ComboboxSelected>>", window._generator_language_selected)
    window.generator_language_combobox.bind("<KeyRelease>", window._generator_language_typed)

    tk.Label(generator_frame, text="Акцент:", anchor="w", width=12).grid(row=1, column=0, sticky="w", pady=(0, 10))
    window.generator_accent_window_combobox = ttk.Combobox(
        generator_frame,
        textvariable=window.generator_accent_var,
        state="normal",
        width=32,
    )
    window.generator_accent_window_combobox.grid(row=1, column=1, sticky="ew", padx=5, pady=(0, 10))
    window.generator_accent_window_combobox.bind("<<ComboboxSelected>>", window._generator_accent_selected)
    window.generator_accent_window_combobox.bind("<KeyRelease>", window._generator_accent_typed)
    window.generator_accent_window_hint_label = tk.Label(generator_frame, text="", fg="#666666")
    window.generator_accent_window_hint_label.grid(row=2, column=1, sticky="w", padx=5, pady=(0, 10))
    window.generator_accent_window_hint_label.grid_remove()

    tk.Label(generator_frame, text="Голос:", anchor="w", width=12).grid(row=3, column=0, sticky="w", pady=(0, 10))
    window.generator_voice_combobox = ttk.Combobox(
        generator_frame,
        textvariable=window.generator_voice_var,
        state="normal",
        width=32,
    )
    window.generator_voice_combobox.grid(row=3, column=1, columnspan=2, sticky="ew", padx=5, pady=(0, 10))
    window.generator_voice_combobox.bind("<<ComboboxSelected>>", window._generator_voice_selected)
    window.generator_voice_combobox.bind("<KeyRelease>", window._generator_voice_typed)
    window.generator_voice_combobox.bind("<Button-1>", window._generator_voice_dropdown_clicked)
    window.generator_voice_combobox.bind("<FocusIn>", window._generator_voice_dropdown_clicked)
    tk.Button(
        generator_frame,
        textvariable=window.client_calls_text_voice_preview_button_var,
        width=12,
        command=window._preview_client_calls_text_voice_clicked,
    ).grid(row=4, column=1, sticky="w", padx=5, pady=(0, 10))

    tk.Label(generator_frame, text="Скорость:", anchor="w", width=12).grid(row=5, column=0, sticky="w", pady=(0, 10))
    generator_window_speed_frame = tk.Frame(generator_frame)
    generator_window_speed_frame.grid(row=5, column=1, sticky="w", padx=5, pady=(0, 10))
    window._create_settings_scale(
        generator_window_speed_frame,
        variable=window.generator_speed_var,
        command=window._generator_speed_changed,
        from_=-100,
        to=100,
        resolution=1,
    ).pack(side="left")
    tk.Label(generator_frame, textvariable=window.generator_speed_display_var, width=5, anchor="w").grid(
        row=5,
        column=2,
        sticky="w",
        padx=(2, 0),
        pady=(0, 10),
    )

    tk.Label(generator_frame, text="Текст:").grid(row=6, column=0, sticky="nw")
    window._generator_text_widget = tk.Text(generator_frame, width=34, height=8, wrap="word")
    window._generator_text_widget.grid(row=6, column=1, columnspan=2, sticky="ew", padx=5)
    window._bind_standard_edit_shortcuts(window._generator_text_widget)

    tk.Label(generator_frame, text="Название файла:").grid(row=7, column=0, sticky="w", pady=(12, 0))
    file_name_frame = tk.Frame(generator_frame)
    file_name_frame.grid(row=7, column=1, columnspan=2, sticky="w", padx=5, pady=(12, 0))
    generator_file_name_entry = tk.Entry(file_name_frame, textvariable=window.generator_file_name_var, width=32)
    generator_file_name_entry.pack(side="left")
    window._bind_standard_edit_shortcuts(generator_file_name_entry)
    tk.Label(file_name_frame, text=".mp3").pack(side="left", padx=(6, 0))

    buttons_frame = tk.Frame(content)
    buttons_frame.grid(row=1, column=0, sticky="e", pady=(14, 0))
    tk.Button(buttons_frame, text="Сгенерировать", width=14, command=window._generate_ai_speech_clicked).pack(side="left")
    tk.Button(buttons_frame, text="Сохранить в...", width=14, command=window._save_generated_ai_speech_clicked).pack(side="left", padx=(8, 0))
    tk.Button(buttons_frame, text="Закрыть", width=12, command=window._hide_generator_window).pack(side="left", padx=(8, 0))

    window_instance.bind("<Return>", window._generator_enter_pressed)
    window._generator_text_widget.bind("<Return>", window._generator_enter_pressed)

    window._generator_window = window_instance
    window._fit_window_to_content(window_instance)


def build_employees_window(window) -> None:
    window_instance = tk.Toplevel(window.root)
    window_instance.title("Сотрудники")
    window_instance.resizable(False, False)
    window_instance.withdraw()
    window._apply_window_icon(window_instance)
    window_instance.protocol("WM_DELETE_WINDOW", window._hide_employees_window)

    content = tk.Frame(window_instance, padx=10, pady=10)
    content.pack(fill="both", expand=True)
    content.columnconfigure(0, weight=1)

    employees_frame = tk.LabelFrame(content, text="Список сотрудников", padx=10, pady=10)
    employees_frame.grid(row=0, column=0, sticky="ew")
    employees_frame.columnconfigure(0, weight=1)

    list_frame = tk.Frame(employees_frame)
    list_frame.grid(row=0, column=0, sticky="w")
    window.employees_listbox = tk.Listbox(list_frame, width=26, height=20)
    window.employees_listbox.pack(side="left", fill="y")
    window.employees_listbox.bind("<Double-Button-1>", window._employee_listbox_double_clicked)
    window.employees_listbox.bind("<space>", window._employee_listbox_space_pressed)
    employees_scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=window.employees_listbox.yview)
    employees_scrollbar.pack(side="left", fill="y")
    window.employees_listbox.config(yscrollcommand=employees_scrollbar.set)

    add_frame = tk.Frame(employees_frame)
    add_frame.grid(row=1, column=0, sticky="w", pady=(10, 0))
    window.employee_input_var = tk.StringVar()
    employee_entry = tk.Entry(
        add_frame,
        textvariable=window.employee_input_var,
        width=26,
        font=window._employee_entry_font,
    )
    employee_entry.pack(anchor="w")
    employee_entry.bind("<Return>", window._employee_enter_pressed)
    employee_entry.bind("<FocusIn>", window._employee_entry_focused)
    employee_entry.bind("<FocusOut>", window._employee_entry_unfocused)
    add_actions_frame = tk.Frame(add_frame)
    add_actions_frame.pack(anchor="w", pady=(8, 0))
    tk.Button(add_actions_frame, text="Добавить сотрудника", width=18, command=window._add_employee_clicked).pack(side="left")
    help_button = tk.Label(
        add_actions_frame,
        text="?",
        width=2,
        relief="ridge",
        cursor="question_arrow",
    )
    help_button.pack(side="left", padx=(8, 0))
    help_button.bind("<Enter>", window._show_employees_help_tooltip)
    help_button.bind("<Leave>", window._hide_employees_help_tooltip)
    window._employee_entry = employee_entry
    window._show_employee_placeholder()

    buttons_frame = tk.Frame(employees_frame)
    buttons_frame.grid(row=2, column=0, sticky="w", pady=(10, 0))
    tk.Button(buttons_frame, text="Удалить", width=9, command=window._delete_employee_clicked).pack(side="left")
    tk.Button(buttons_frame, text="Закрыть", width=12, command=window._hide_employees_window).pack(side="left", padx=(8, 0))

    window_instance.bind("<Return>", window._employee_enter_pressed)
    window._employees_window = window_instance
    window._fit_window_to_content(window_instance)
