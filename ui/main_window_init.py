import tkinter as tk
import tkinter.font as tkfont
from typing import Callable, Optional

from models import ClientCall


def initialize_state(window) -> None:
    window.selected_file_path = tk.StringVar()
    window.selected_file_display = tk.StringVar()
    window.time_var = tk.StringVar(value="00:00")
    window.volume_var = tk.DoubleVar(value=0.8)
    window.volume_display_var = tk.StringVar(value="0.8")
    window.notification_volume_var = tk.DoubleVar(value=0.8)
    window.notification_volume_display_var = tk.StringVar(value="0.8")
    window.device_var = tk.StringVar()
    window.notification_sound_file_path = tk.StringVar()
    window.notification_sound_display = tk.StringVar()
    window.notification_sound_preview_button_var = tk.StringVar(value="Прослушать")
    window.autostart_var = tk.BooleanVar(value=False)
    window.update_check_button_var = tk.StringVar(value="Проверить обновления")
    window.scheduler_notification_var = tk.BooleanVar(value=False)
    window.client_calls_notification_var = tk.BooleanVar(value=False)
    window.client_calls_file_path = tk.StringVar()
    window.client_calls_file_display = tk.StringVar()
    window.client_calls_api_enabled_var = tk.BooleanVar(value=False)
    window.client_calls_api_host_var = tk.StringVar(value="127.0.0.1")
    window.client_calls_api_port_var = tk.StringVar(value="8765")
    window.client_calls_api_token_var = tk.StringVar()
    window.client_calls_api_token_button_var = tk.StringVar(value="Не сгенерирован")
    window.client_calls_api_edit_button_var = tk.StringVar(value="Изменить")
    window._client_calls_api_settings_editable = False
    window.client_calls_voice_message_file_path = tk.StringVar()
    window.client_calls_voice_message_file_display = tk.StringVar()
    window.client_calls_volume_var = tk.DoubleVar(value=0.8)
    window.client_calls_volume_display_var = tk.StringVar(value="0.8")
    window.client_calls_voice_message_volume_var = tk.DoubleVar(value=1.0)
    window.client_calls_voice_message_volume_display_var = tk.StringVar(value="1.0")
    window.client_calls_speech_rate_var = tk.DoubleVar(value=1.0)
    window.client_calls_speech_rate_display_var = tk.StringVar(value="1.0")
    window.number_trim_silence_var = tk.BooleanVar(value=True)
    window.number_silence_threshold_var = tk.DoubleVar(value=-42)
    window.number_silence_threshold_display_var = tk.StringVar(value="-42")
    window.number_trim_leading_padding_var = tk.DoubleVar(value=20)
    window.number_trim_leading_padding_display_var = tk.StringVar(value="20")
    window.number_trim_trailing_padding_var = tk.DoubleVar(value=55)
    window.number_trim_trailing_padding_display_var = tk.StringVar(value="55")
    window.number_symbol_pause_var = tk.DoubleVar(value=120)
    window.number_symbol_pause_display_var = tk.StringVar(value="120")
    window.number_preview_var = tk.StringVar(value="а123вс")
    window.client_calls_device_var = tk.StringVar()
    window.client_calls_voice_message_device_var = tk.StringVar()
    window.client_calls_interval_var = tk.StringVar(value="5")
    window.client_calls_repeat_var = tk.BooleanVar(value=False)
    window.client_calls_repeat_interval_var = tk.StringVar(value="3")
    window.client_calls_repeat_notification_var = tk.BooleanVar(value=False)
    window.client_calls_text_voice_var = tk.StringVar()
    window.client_calls_text_language_var = tk.StringVar(value="Русский")
    window.client_calls_text_voice_preview_button_var = tk.StringVar(value="Прослушать")
    window.generator_api_key_var = tk.StringVar()
    window.generator_api_key_button_var = tk.StringVar(value="Не указан")
    window.generator_api_edit_button_var = tk.StringVar(value="Изм.")
    window._generator_api_key_value = ""
    window._generator_api_key_masked = True
    window._generator_api_key_editable = False
    window.generator_volume_var = tk.DoubleVar(value=0.8)
    window.generator_volume_display_var = tk.StringVar(value="0.8")
    window.generator_master_volume_var = tk.DoubleVar(value=14.0)
    window.generator_master_volume_display_var = tk.StringVar(value="14")
    window.generator_device_var = tk.StringVar()
    window.generator_language_var = tk.StringVar(value="Русский")
    window.generator_accent_var = tk.StringVar(value="")
    window.generator_speed_var = tk.DoubleVar(value=0.0)
    window.generator_speed_display_var = tk.StringVar(value="0")
    window.generator_voice_var = tk.StringVar(value="")
    window.generator_file_name_var = tk.StringVar()
    window.workday_status_var = tk.StringVar(value="Проверка дня")
    window._current_client_call: Optional[ClientCall] = None
    window._queued_client_calls: list[ClientCall] = []
    window._current_client_call_progress = 0.0
    window._visible_queue_rows: list[tuple[Optional[str], bool]] = []
    window._visible_queue_row_count = 1
    window.last_error_status_var = tk.StringVar(value="Готово")
    window._client_calls_settings_window: Optional[tk.Toplevel] = None
    window._generator_window: Optional[tk.Toplevel] = None
    window._employees_window: Optional[tk.Toplevel] = None
    window._generator_text_widget: Optional[tk.Text] = None
    window._client_calls_api_host_entry: Optional[tk.Entry] = None
    window._client_calls_api_port_entry: Optional[tk.Entry] = None
    window._client_calls_api_token_entry: Optional[tk.Entry] = None
    window._generator_api_key_entry: Optional[tk.Entry] = None
    window._time_entry: Optional[tk.Entry] = None
    window._schedule_add_button: Optional[tk.Button] = None
    window._play_button: Optional[tk.Button] = None
    window.update_check_button: Optional[tk.Button] = None
    window._workday_lamp_canvas: Optional[tk.Canvas] = None
    window._workday_lamp_id: Optional[int] = None
    window._workday_calendar_window: Optional[tk.Toplevel] = None
    window._client_calls_api_copy_button: Optional[tk.Button] = None
    window._client_calls_api_generate_button: Optional[tk.Button] = None
    window._employee_entry: Optional[tk.Entry] = None
    window._employee_entry_font = tkfont.nametofont("TkDefaultFont").copy()
    window._employee_entry_placeholder_font = window._employee_entry_font.copy()
    window._employee_entry_placeholder_font.configure(slant="italic")
    window._employees_help_tooltip: Optional[tk.Toplevel] = None
    window._settings_window_requested_visible = False
    window._generator_window_requested_visible = False
    window._employees_window_requested_visible = False
    window._employee_placeholder_text = "Фамилия Имя"
    window._employee_placeholder_visible = False
    window._main_playback_active = False
    window._last_schedule_double_click_at = 0.0
    window._last_schedule_double_click_index = None
    window._entry_ids_by_index: list[str] = []


def initialize_callbacks(window) -> None:
    window.on_add: Optional[Callable[[], None]] = None
    window.on_delete: Optional[Callable[[], None]] = None
    window.on_browse: Optional[Callable[[], None]] = None
    window.on_play: Optional[Callable[[], None]] = None
    window.on_stop: Optional[Callable[[], None]] = None
    window.on_queue_selected_schedule: Optional[Callable[[str], None]] = None
    window.on_remove_queued_call: Optional[Callable[[str], None]] = None
    window.on_refresh_devices: Optional[Callable[[], None]] = None
    window.on_device_change: Optional[Callable[[str], None]] = None
    window.on_volume_change: Optional[Callable[[float], None]] = None
    window.on_notification_volume_change: Optional[Callable[[float], None]] = None
    window.on_select_entry: Optional[Callable[[], None]] = None
    window.on_browse_client_calls_file: Optional[Callable[[], None]] = None
    window.on_browse_client_calls_voice_message_file: Optional[Callable[[], None]] = None
    window.on_browse_employees_file: Optional[Callable[[], None]] = None
    window.on_client_calls_api_enabled_toggle: Optional[Callable[[], None]] = None
    window.on_client_calls_api_host_change: Optional[Callable[[], None]] = None
    window.on_client_calls_api_port_change: Optional[Callable[[], None]] = None
    window.on_generate_client_calls_api_token: Optional[Callable[[], None]] = None
    window.on_client_calls_volume_change: Optional[Callable[[float], None]] = None
    window.on_client_calls_voice_message_volume_change: Optional[Callable[[float], None]] = None
    window.on_client_calls_speech_rate_change: Optional[Callable[[float], None]] = None
    window.on_number_trim_silence_toggle: Optional[Callable[[], None]] = None
    window.on_number_silence_threshold_change: Optional[Callable[[float], None]] = None
    window.on_number_trim_leading_padding_change: Optional[Callable[[float], None]] = None
    window.on_number_trim_trailing_padding_change: Optional[Callable[[float], None]] = None
    window.on_number_symbol_pause_change: Optional[Callable[[float], None]] = None
    window.on_preview_number_assembly: Optional[Callable[[], None]] = None
    window.on_client_calls_device_change: Optional[Callable[[str], None]] = None
    window.on_client_calls_voice_message_device_change: Optional[Callable[[str], None]] = None
    window.on_client_calls_interval_change: Optional[Callable[[], None]] = None
    window.on_client_calls_repeat_toggle: Optional[Callable[[], None]] = None
    window.on_client_calls_repeat_interval_change: Optional[Callable[[], None]] = None
    window.on_client_calls_repeat_notification_toggle: Optional[Callable[[], None]] = None
    window.on_client_calls_text_language_change: Optional[Callable[[str], None]] = None
    window.on_client_calls_text_voice_change: Optional[Callable[[str], None]] = None
    window.on_preview_client_calls_text_voice: Optional[Callable[[], None]] = None
    window.on_request_client_calls_text_voices: Optional[Callable[[], None]] = None
    window.on_workday_indicator_click: Optional[Callable[[], None]] = None
    window.on_browse_notification_sound_file: Optional[Callable[[], None]] = None
    window.on_play_notification_sound: Optional[Callable[[], None]] = None
    window.on_export_schedule: Optional[Callable[[], None]] = None
    window.on_import_schedule: Optional[Callable[[], None]] = None
    window.on_show_generator: Optional[Callable[[], None]] = None
    window.on_show_employees: Optional[Callable[[], None]] = None
    window.on_generator_api_key_change: Optional[Callable[[str], None]] = None
    window.on_generator_device_change: Optional[Callable[[str], None]] = None
    window.on_generator_volume_change: Optional[Callable[[float], None]] = None
    window.on_generator_master_volume_change: Optional[Callable[[float], None]] = None
    window.on_generator_language_change: Optional[Callable[[str], None]] = None
    window.on_generator_accent_change: Optional[Callable[[str], None]] = None
    window.on_generator_speed_change: Optional[Callable[[float], None]] = None
    window.on_generator_voice_change: Optional[Callable[[str], None]] = None
    window.on_request_generator_voices: Optional[Callable[[], None]] = None
    window.on_generate_ai_speech: Optional[Callable[[], None]] = None
    window.on_save_generated_ai_speech: Optional[Callable[[], None]] = None
    window.on_add_employee: Optional[Callable[[], None]] = None
    window.on_delete_employee: Optional[Callable[[], None]] = None
    window.on_preview_employee: Optional[Callable[[], None]] = None
    window.on_autostart_toggle: Optional[Callable[[], None]] = None
    window.on_check_updates: Optional[Callable[[], None]] = None
    window.on_scheduler_notification_toggle: Optional[Callable[[], None]] = None
    window.on_client_calls_notification_toggle: Optional[Callable[[], None]] = None
    window.on_hide_to_tray: Optional[Callable[[], None]] = None
    window.on_quit_application: Optional[Callable[[], None]] = None
    window.on_close: Optional[Callable[[], None]] = None
    window.on_window_unmap: Optional[Callable[[], None]] = None
    window.on_window_configure: Optional[Callable[[], None]] = None
    window.on_open_error_log: Optional[Callable[[], None]] = None
