import os
import platform
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from typing import Callable, List, Optional

from config import WINDOW_TITLE
from ui.main_window_builders import (
    build_client_calls_settings_window,
    build_employees_window,
    build_generator_window,
    build_main_window,
    build_menu,
)
from ui.main_window_behaviors import (
    _app_window_activated as _behavior_app_window_activated,
    _apply_window_icon as _behavior_apply_window_icon,
    _clear_text_selection as _behavior_clear_text_selection,
    _delete_key_pressed as _behavior_delete_key_pressed,
    _delete_shortcut_pressed as _behavior_delete_shortcut_pressed,
    _employee_listbox_double_clicked as _behavior_employee_listbox_double_clicked,
    _employee_listbox_space_pressed as _behavior_employee_listbox_space_pressed,
    _extract_window_position as _behavior_extract_window_position,
    _fit_main_window_to_content as _behavior_fit_main_window_to_content,
    _fit_window_to_content as _behavior_fit_window_to_content,
    _get_app_windows as _behavior_get_app_windows,
    _global_left_click as _behavior_global_left_click,
    _hide_employees_help_tooltip as _behavior_hide_employees_help_tooltip,
    _is_editable_text_widget as _behavior_is_editable_text_widget,
    _is_interactive_widget as _behavior_is_interactive_widget,
    _is_widget_inside_listbox as _behavior_is_widget_inside_listbox,
    _mask_api_token as _behavior_mask_api_token,
    _next_time_digit_index as _behavior_next_time_digit_index,
    _previous_time_digit_index as _behavior_previous_time_digit_index,
    _queue_row_clicked as _behavior_queue_row_clicked,
    _register_window_group_behavior as _behavior_register_window_group_behavior,
    _replace_time_digit as _behavior_replace_time_digit,
    _resize_client_call_rows as _behavior_resize_client_call_rows,
    _resolve_widget as _behavior_resolve_widget,
    _safe_clear_selection as _behavior_safe_clear_selection,
    _safe_destroy_widget as _behavior_safe_destroy_widget,
    _schedule_listbox_double_clicked as _behavior_schedule_listbox_double_clicked,
    _set_time_cursor as _behavior_set_time_cursor,
    _set_visible_queue_row_count as _behavior_set_visible_queue_row_count,
    _should_handle_employee_shortcut as _behavior_should_handle_employee_shortcut,
    _show_employees_help_tooltip as _behavior_show_employees_help_tooltip,
    _show_side_window as _behavior_show_side_window,
    _space_pressed as _behavior_space_pressed,
    _time_entry_backspace as _behavior_time_entry_backspace,
    _time_entry_clicked as _behavior_time_entry_clicked,
    _time_entry_delete as _behavior_time_entry_delete,
    _time_entry_end as _behavior_time_entry_end,
    _time_entry_focused as _behavior_time_entry_focused,
    _time_entry_home as _behavior_time_entry_home,
    _time_entry_keypress as _behavior_time_entry_keypress,
    _time_entry_move_left as _behavior_time_entry_move_left,
    _time_entry_move_right as _behavior_time_entry_move_right,
    _normalize_time_value as _behavior_normalize_time_value,
    render_client_calls as _behavior_render_client_calls_public,
    show_client_calls_settings_window as _behavior_show_client_calls_settings_window,
    show_employees_window as _behavior_show_employees_window,
    show_generator_window as _behavior_show_generator_window,
)
from ui.main_window_bindings import (
    _add_clicked as _bindings_add_clicked,
    _add_employee_clicked as _bindings_add_employee_clicked,
    _autostart_toggled as _bindings_autostart_toggled,
    _browse_clicked as _bindings_browse_clicked,
    _browse_client_calls_file_clicked as _bindings_browse_client_calls_file_clicked,
    _browse_client_calls_voice_message_file_clicked as _bindings_browse_client_calls_voice_message_file_clicked,
    _browse_employees_file_clicked as _bindings_browse_employees_file_clicked,
    _browse_notification_sound_file_clicked as _bindings_browse_notification_sound_file_clicked,
    _client_calls_api_enabled_toggled as _bindings_client_calls_api_enabled_toggled,
    _client_calls_api_host_changed as _bindings_client_calls_api_host_changed,
    _client_calls_api_host_submitted as _bindings_client_calls_api_host_submitted,
    _client_calls_api_port_changed as _bindings_client_calls_api_port_changed,
    _client_calls_api_port_submitted as _bindings_client_calls_api_port_submitted,
    _client_calls_device_changed as _bindings_client_calls_device_changed,
    _client_calls_interval_changed as _bindings_client_calls_interval_changed,
    _client_calls_interval_submitted as _bindings_client_calls_interval_submitted,
    _client_calls_notification_toggled as _bindings_client_calls_notification_toggled,
    _client_calls_repeat_notification_toggled as _bindings_client_calls_repeat_notification_toggled,
    _client_calls_repeat_toggled as _bindings_client_calls_repeat_toggled,
    _client_calls_text_language_selected as _bindings_client_calls_text_language_selected,
    _client_calls_text_voice_dropdown_clicked as _bindings_client_calls_text_voice_dropdown_clicked,
    _client_calls_text_voice_selected as _bindings_client_calls_text_voice_selected,
    _client_calls_voice_message_device_changed as _bindings_client_calls_voice_message_device_changed,
    _close_requested as _bindings_close_requested,
    _delete_clicked as _bindings_delete_clicked,
    _delete_employee_clicked as _bindings_delete_employee_clicked,
    _device_changed as _bindings_device_changed,
    _employee_enter_pressed as _bindings_employee_enter_pressed,
    _export_schedule_clicked as _bindings_export_schedule_clicked,
    _generate_ai_speech_clicked as _bindings_generate_ai_speech_clicked,
    _generator_accent_selected as _bindings_generator_accent_selected,
    _generator_api_key_changed as _bindings_generator_api_key_changed,
    _generator_api_key_focused as _bindings_generator_api_key_focused,
    _generator_api_key_unfocused as _bindings_generator_api_key_unfocused,
    _generator_device_changed as _bindings_generator_device_changed,
    _generator_enter_pressed as _bindings_generator_enter_pressed,
    _generator_language_selected as _bindings_generator_language_selected,
    _generator_voice_changed as _bindings_generator_voice_changed,
    _generator_voice_dropdown_clicked as _bindings_generator_voice_dropdown_clicked,
    _generator_voice_selected as _bindings_generator_voice_selected,
    _hide_to_tray_clicked as _bindings_hide_to_tray_clicked,
    _import_schedule_clicked as _bindings_import_schedule_clicked,
    _last_error_status_clicked as _bindings_last_error_status_clicked,
    _play_clicked as _bindings_play_clicked,
    _play_notification_sound_clicked as _bindings_play_notification_sound_clicked,
    _preview_client_calls_text_voice_clicked as _bindings_preview_client_calls_text_voice_clicked,
    _quit_application_clicked as _bindings_quit_application_clicked,
    _refresh_devices_clicked as _bindings_refresh_devices_clicked,
    _save_generated_ai_speech_clicked as _bindings_save_generated_ai_speech_clicked,
    _scheduler_notification_toggled as _bindings_scheduler_notification_toggled,
    _select_entry as _bindings_select_entry,
    _show_employees_clicked as _bindings_show_employees_clicked,
    _show_generator_clicked as _bindings_show_generator_clicked,
    _window_configured as _bindings_window_configured,
    _window_unmapped as _bindings_window_unmapped,
    _workday_indicator_clicked as _bindings_workday_indicator_clicked,
)
from ui.main_window_state import (
    _create_settings_scale as _state_create_settings_scale,
    _employee_entry_focused as _state_employee_entry_focused,
    _employee_entry_unfocused as _state_employee_entry_unfocused,
    _filter_combobox_values as _state_filter_combobox_values,
    _handle_speed_change as _state_handle_speed_change,
    _handle_volume_change as _state_handle_volume_change,
    _set_file_value as _state_set_file_value,
    _set_option_menu_values as _state_set_option_menu_values,
    _show_employee_placeholder as _state_show_employee_placeholder,
    clear_employee_input as _state_clear_employee_input,
    close_workday_calendar as _state_close_workday_calendar,
    clear_schedule_selection as _state_clear_schedule_selection,
    fill_employees_list as _state_fill_employees_list,
    fill_schedule_list as _state_fill_schedule_list,
    focus_employees_list as _state_focus_employees_list,
    get_client_calls_api_host as _state_get_client_calls_api_host,
    get_client_calls_api_port as _state_get_client_calls_api_port,
    get_client_calls_file as _state_get_client_calls_file,
    get_client_calls_interval as _state_get_client_calls_interval,
    get_client_calls_repeat_interval as _state_get_client_calls_repeat_interval,
    get_employee_input as _state_get_employee_input,
    get_entry_id_by_index as _state_get_entry_id_by_index,
    get_generator_api_key as _state_get_generator_api_key,
    get_generator_file_name as _state_get_generator_file_name,
    get_generator_text as _state_get_generator_text,
    get_main_window_geometry as _state_get_main_window_geometry,
    get_number_preview_text as _state_get_number_preview_text,
    get_notification_sound_file as _state_get_notification_sound_file,
    get_selected_employee as _state_get_selected_employee,
    get_selected_entry_id as _state_get_selected_entry_id,
    get_selected_file as _state_get_selected_file,
    get_selected_index as _state_get_selected_index,
    get_time_input as _state_get_time_input,
    is_autostart_enabled as _state_is_autostart_enabled,
    is_client_calls_api_enabled as _state_is_client_calls_api_enabled,
    is_client_calls_notification_enabled as _state_is_client_calls_notification_enabled,
    is_client_calls_repeat_enabled as _state_is_client_calls_repeat_enabled,
    is_client_calls_repeat_notification_enabled as _state_is_client_calls_repeat_notification_enabled,
    is_number_trim_silence_enabled as _state_is_number_trim_silence_enabled,
    is_scheduler_notification_enabled as _state_is_scheduler_notification_enabled,
    ask_yes_no as _state_ask_yes_no,
    set_autostart_enabled as _state_set_autostart_enabled,
    set_client_calls_api_enabled as _state_set_client_calls_api_enabled,
    set_client_calls_api_host as _state_set_client_calls_api_host,
    set_client_calls_api_port as _state_set_client_calls_api_port,
    set_client_calls_api_token as _state_set_client_calls_api_token,
    set_client_calls_device_options as _state_set_client_calls_device_options,
    set_client_calls_file as _state_set_client_calls_file,
    set_client_calls_interval as _state_set_client_calls_interval,
    set_client_calls_notification_enabled as _state_set_client_calls_notification_enabled,
    set_client_calls_repeat_enabled as _state_set_client_calls_repeat_enabled,
    set_client_calls_repeat_interval as _state_set_client_calls_repeat_interval,
    set_client_calls_repeat_notification_enabled as _state_set_client_calls_repeat_notification_enabled,
    set_client_calls_speech_rate as _state_set_client_calls_speech_rate,
    set_client_calls_text_language_options as _state_set_client_calls_text_language_options,
    set_client_calls_text_voice_options as _state_set_client_calls_text_voice_options,
    set_client_calls_text_voice_preview_playing as _state_set_client_calls_text_voice_preview_playing,
    set_client_calls_voice_message_device_options as _state_set_client_calls_voice_message_device_options,
    set_client_calls_voice_message_file as _state_set_client_calls_voice_message_file,
    set_client_calls_voice_message_volume as _state_set_client_calls_voice_message_volume,
    set_client_calls_volume as _state_set_client_calls_volume,
    set_device_options as _state_set_device_options,
    set_employees_file as _state_set_employees_file,
    set_generator_accent_enabled as _state_set_generator_accent_enabled,
    set_generator_accent_options as _state_set_generator_accent_options,
    set_generator_api_key as _state_set_generator_api_key,
    set_generator_device_options as _state_set_generator_device_options,
    set_generator_language as _state_set_generator_language,
    set_generator_language_options as _state_set_generator_language_options,
    set_generator_master_volume as _state_set_generator_master_volume,
    set_generator_speed as _state_set_generator_speed,
    set_generator_voice as _state_set_generator_voice,
    set_generator_voice_options as _state_set_generator_voice_options,
    set_generator_volume as _state_set_generator_volume,
    set_last_error_status as _state_set_last_error_status,
    set_main_playback_active as _state_set_main_playback_active,
    set_main_window_geometry as _state_set_main_window_geometry,
    set_notification_sound_file as _state_set_notification_sound_file,
    set_notification_sound_preview_playing as _state_set_notification_sound_preview_playing,
    set_notification_volume as _state_set_notification_volume,
    set_number_silence_threshold as _state_set_number_silence_threshold,
    set_number_symbol_pause as _state_set_number_symbol_pause,
    set_number_trim_leading_padding as _state_set_number_trim_leading_padding,
    set_number_trim_silence_enabled as _state_set_number_trim_silence_enabled,
    set_number_trim_trailing_padding as _state_set_number_trim_trailing_padding,
    set_schedule_action_button_label as _state_set_schedule_action_button_label,
    set_scheduler_notification_enabled as _state_set_scheduler_notification_enabled,
    set_selected_file as _state_set_selected_file,
    set_time_input as _state_set_time_input,
    set_update_checking as _state_set_update_checking,
    set_volume as _state_set_volume,
    set_workday_status as _state_set_workday_status,
    show_error as _state_show_error,
    show_info as _state_show_info,
    show_workday_calendar as _state_show_workday_calendar,
    show_workday_calendar_loading as _state_show_workday_calendar_loading,
    _mask_secret as _state_mask_secret,
)
from ui.main_window_init import initialize_callbacks, initialize_state


class MainWindow:
    VISIBLE_QUEUE_ROWS = 5
    WEEKDAY_LABELS: list[tuple[int, str]] = [
        (0, "Пн"),
        (1, "Вт"),
        (2, "Ср"),
        (3, "Чт"),
        (4, "Пт"),
        (5, "Сб"),
        (6, "Вс"),
    ]
    EDIT_SHORTCUT_KEYS = {
        "select_all": {"a", "A", "ф", "Ф"},
        "copy": {"c", "C", "с", "С"},
        "paste": {"v", "V", "м", "М"},
        "cut": {"x", "X", "ч", "Ч"},
    }
    _time_entry_focused = _behavior_time_entry_focused
    _time_entry_clicked = _behavior_time_entry_clicked
    _time_entry_move_left = _behavior_time_entry_move_left
    _time_entry_move_right = _behavior_time_entry_move_right
    _time_entry_home = _behavior_time_entry_home
    _time_entry_end = _behavior_time_entry_end
    _time_entry_backspace = _behavior_time_entry_backspace
    _time_entry_delete = _behavior_time_entry_delete
    _time_entry_keypress = _behavior_time_entry_keypress
    _normalize_time_value = _behavior_normalize_time_value
    _set_time_cursor = _behavior_set_time_cursor
    _replace_time_digit = _behavior_replace_time_digit
    _next_time_digit_index = _behavior_next_time_digit_index
    _previous_time_digit_index = _behavior_previous_time_digit_index
    _global_left_click = _behavior_global_left_click
    _space_pressed = _behavior_space_pressed
    _schedule_listbox_double_clicked = _behavior_schedule_listbox_double_clicked
    _delete_key_pressed = _behavior_delete_key_pressed
    _delete_shortcut_pressed = _behavior_delete_shortcut_pressed
    _employee_listbox_double_clicked = _behavior_employee_listbox_double_clicked
    _employee_listbox_space_pressed = _behavior_employee_listbox_space_pressed
    _show_employees_help_tooltip = _behavior_show_employees_help_tooltip
    _hide_employees_help_tooltip = _behavior_hide_employees_help_tooltip
    _resize_client_call_rows = _behavior_resize_client_call_rows
    show_client_calls_settings_window = _behavior_show_client_calls_settings_window
    show_generator_window = _behavior_show_generator_window
    show_employees_window = _behavior_show_employees_window
    render_client_calls = _behavior_render_client_calls_public
    _queue_row_clicked = _behavior_queue_row_clicked
    _set_visible_queue_row_count = _behavior_set_visible_queue_row_count
    _mask_api_token = _behavior_mask_api_token
    _fit_window_to_content = _behavior_fit_window_to_content
    _show_side_window = _behavior_show_side_window
    _register_window_group_behavior = _behavior_register_window_group_behavior
    _get_app_windows = _behavior_get_app_windows
    _app_window_activated = _behavior_app_window_activated
    _extract_window_position = _behavior_extract_window_position
    _apply_window_icon = _behavior_apply_window_icon
    _fit_main_window_to_content = _behavior_fit_main_window_to_content
    _resolve_widget = _behavior_resolve_widget
    _is_editable_text_widget = _behavior_is_editable_text_widget
    _should_handle_employee_shortcut = _behavior_should_handle_employee_shortcut
    _is_widget_inside_listbox = _behavior_is_widget_inside_listbox
    _clear_text_selection = _behavior_clear_text_selection
    _safe_clear_selection = _behavior_safe_clear_selection
    _safe_destroy_widget = _behavior_safe_destroy_widget
    _is_interactive_widget = _behavior_is_interactive_widget
    _browse_clicked = _bindings_browse_clicked
    _add_clicked = _bindings_add_clicked
    _delete_clicked = _bindings_delete_clicked
    _play_clicked = _bindings_play_clicked
    _browse_client_calls_file_clicked = _bindings_browse_client_calls_file_clicked
    _browse_client_calls_voice_message_file_clicked = _bindings_browse_client_calls_voice_message_file_clicked
    _browse_employees_file_clicked = _bindings_browse_employees_file_clicked
    _refresh_devices_clicked = _bindings_refresh_devices_clicked
    _browse_notification_sound_file_clicked = _bindings_browse_notification_sound_file_clicked
    _play_notification_sound_clicked = _bindings_play_notification_sound_clicked
    _export_schedule_clicked = _bindings_export_schedule_clicked
    _import_schedule_clicked = _bindings_import_schedule_clicked
    _generator_api_key_focused = _bindings_generator_api_key_focused
    _generator_api_key_changed = _bindings_generator_api_key_changed
    _generator_api_key_unfocused = _bindings_generator_api_key_unfocused
    _show_generator_clicked = _bindings_show_generator_clicked
    _show_employees_clicked = _bindings_show_employees_clicked
    _hide_to_tray_clicked = _bindings_hide_to_tray_clicked
    _quit_application_clicked = _bindings_quit_application_clicked
    _client_calls_device_changed = _bindings_client_calls_device_changed
    _client_calls_voice_message_device_changed = _bindings_client_calls_voice_message_device_changed
    _generator_device_changed = _bindings_generator_device_changed
    _generator_voice_changed = _bindings_generator_voice_changed
    _generator_language_selected = _bindings_generator_language_selected
    _generator_accent_selected = _bindings_generator_accent_selected
    _generator_voice_selected = _bindings_generator_voice_selected
    _client_calls_text_voice_selected = _bindings_client_calls_text_voice_selected
    _client_calls_text_language_selected = _bindings_client_calls_text_language_selected
    _preview_client_calls_text_voice_clicked = _bindings_preview_client_calls_text_voice_clicked
    _generator_voice_dropdown_clicked = _bindings_generator_voice_dropdown_clicked
    _client_calls_text_voice_dropdown_clicked = _bindings_client_calls_text_voice_dropdown_clicked
    _client_calls_interval_changed = _bindings_client_calls_interval_changed
    _client_calls_interval_submitted = _bindings_client_calls_interval_submitted
    _client_calls_api_enabled_toggled = _bindings_client_calls_api_enabled_toggled
    _client_calls_api_host_changed = _bindings_client_calls_api_host_changed
    _client_calls_api_host_submitted = _bindings_client_calls_api_host_submitted
    _client_calls_api_port_changed = _bindings_client_calls_api_port_changed
    _client_calls_api_port_submitted = _bindings_client_calls_api_port_submitted
    _workday_indicator_clicked = _bindings_workday_indicator_clicked
    _scheduler_notification_toggled = _bindings_scheduler_notification_toggled
    _client_calls_notification_toggled = _bindings_client_calls_notification_toggled
    _client_calls_repeat_toggled = _bindings_client_calls_repeat_toggled
    _client_calls_repeat_notification_toggled = _bindings_client_calls_repeat_notification_toggled
    _autostart_toggled = _bindings_autostart_toggled
    _close_requested = _bindings_close_requested
    _window_unmapped = _bindings_window_unmapped
    _window_configured = _bindings_window_configured
    _last_error_status_clicked = _bindings_last_error_status_clicked
    _device_changed = _bindings_device_changed
    _select_entry = _bindings_select_entry
    _generate_ai_speech_clicked = _bindings_generate_ai_speech_clicked
    _save_generated_ai_speech_clicked = _bindings_save_generated_ai_speech_clicked
    _add_employee_clicked = _bindings_add_employee_clicked
    _delete_employee_clicked = _bindings_delete_employee_clicked
    _employee_enter_pressed = _bindings_employee_enter_pressed
    _generator_enter_pressed = _bindings_generator_enter_pressed
    set_selected_file = _state_set_selected_file
    clear_schedule_selection = _state_clear_schedule_selection
    set_main_playback_active = _state_set_main_playback_active
    set_schedule_action_button_label = _state_set_schedule_action_button_label
    set_client_calls_file = _state_set_client_calls_file
    set_client_calls_api_enabled = _state_set_client_calls_api_enabled
    set_client_calls_api_host = _state_set_client_calls_api_host
    set_client_calls_api_port = _state_set_client_calls_api_port
    set_client_calls_api_token = _state_set_client_calls_api_token
    set_client_calls_voice_message_file = _state_set_client_calls_voice_message_file
    set_notification_sound_file = _state_set_notification_sound_file
    set_notification_sound_preview_playing = _state_set_notification_sound_preview_playing
    set_generator_api_key = _state_set_generator_api_key
    get_generator_api_key = _state_get_generator_api_key
    _mask_secret = _state_mask_secret
    set_employees_file = _state_set_employees_file
    get_selected_file = _state_get_selected_file
    get_client_calls_file = _state_get_client_calls_file
    is_client_calls_api_enabled = _state_is_client_calls_api_enabled
    get_client_calls_api_host = _state_get_client_calls_api_host
    get_client_calls_api_port = _state_get_client_calls_api_port
    get_notification_sound_file = _state_get_notification_sound_file
    get_number_preview_text = _state_get_number_preview_text
    get_generator_text = _state_get_generator_text
    get_generator_file_name = _state_get_generator_file_name
    get_employee_input = _state_get_employee_input
    clear_employee_input = _state_clear_employee_input
    close_workday_calendar = _state_close_workday_calendar
    focus_employees_list = _state_focus_employees_list
    get_selected_employee = _state_get_selected_employee
    get_time_input = _state_get_time_input
    set_time_input = _state_set_time_input
    get_selected_index = _state_get_selected_index
    get_selected_entry_id = _state_get_selected_entry_id
    get_entry_id_by_index = _state_get_entry_id_by_index
    fill_schedule_list = _state_fill_schedule_list
    fill_employees_list = _state_fill_employees_list
    set_device_options = _state_set_device_options
    set_client_calls_device_options = _state_set_client_calls_device_options
    set_client_calls_voice_message_device_options = _state_set_client_calls_voice_message_device_options
    set_generator_device_options = _state_set_generator_device_options
    set_generator_voice_options = _state_set_generator_voice_options
    set_client_calls_text_voice_options = _state_set_client_calls_text_voice_options
    set_client_calls_text_language_options = _state_set_client_calls_text_language_options
    set_client_calls_text_voice_preview_playing = _state_set_client_calls_text_voice_preview_playing
    set_generator_language_options = _state_set_generator_language_options
    set_generator_accent_options = _state_set_generator_accent_options
    set_generator_accent_enabled = _state_set_generator_accent_enabled
    set_volume = _state_set_volume
    set_client_calls_volume = _state_set_client_calls_volume
    set_client_calls_voice_message_volume = _state_set_client_calls_voice_message_volume
    set_client_calls_speech_rate = _state_set_client_calls_speech_rate
    set_number_trim_silence_enabled = _state_set_number_trim_silence_enabled
    set_number_silence_threshold = _state_set_number_silence_threshold
    set_number_trim_leading_padding = _state_set_number_trim_leading_padding
    set_number_trim_trailing_padding = _state_set_number_trim_trailing_padding
    set_number_symbol_pause = _state_set_number_symbol_pause
    set_notification_volume = _state_set_notification_volume
    set_generator_volume = _state_set_generator_volume
    set_generator_master_volume = _state_set_generator_master_volume
    set_generator_speed = _state_set_generator_speed
    set_generator_voice = _state_set_generator_voice
    set_generator_language = _state_set_generator_language
    get_client_calls_interval = _state_get_client_calls_interval
    set_client_calls_interval = _state_set_client_calls_interval
    set_client_calls_repeat_enabled = _state_set_client_calls_repeat_enabled
    get_client_calls_repeat_interval = _state_get_client_calls_repeat_interval
    set_client_calls_repeat_interval = _state_set_client_calls_repeat_interval
    set_workday_status = _state_set_workday_status
    show_workday_calendar_loading = _state_show_workday_calendar_loading
    show_workday_calendar = _state_show_workday_calendar
    set_scheduler_notification_enabled = _state_set_scheduler_notification_enabled
    set_autostart_enabled = _state_set_autostart_enabled
    set_update_checking = _state_set_update_checking
    set_client_calls_notification_enabled = _state_set_client_calls_notification_enabled
    set_client_calls_repeat_notification_enabled = _state_set_client_calls_repeat_notification_enabled
    is_scheduler_notification_enabled = _state_is_scheduler_notification_enabled
    is_client_calls_notification_enabled = _state_is_client_calls_notification_enabled
    is_client_calls_repeat_enabled = _state_is_client_calls_repeat_enabled
    is_client_calls_repeat_notification_enabled = _state_is_client_calls_repeat_notification_enabled
    is_number_trim_silence_enabled = _state_is_number_trim_silence_enabled
    is_autostart_enabled = _state_is_autostart_enabled
    ask_yes_no = _state_ask_yes_no
    show_error = _state_show_error
    show_info = _state_show_info
    set_last_error_status = _state_set_last_error_status
    set_main_window_geometry = _state_set_main_window_geometry
    get_main_window_geometry = _state_get_main_window_geometry
    _set_option_menu_values = _state_set_option_menu_values
    _handle_volume_change = _state_handle_volume_change
    _handle_speed_change = _state_handle_speed_change
    _create_settings_scale = _state_create_settings_scale
    _set_file_value = _state_set_file_value
    _filter_combobox_values = _state_filter_combobox_values
    _employee_entry_focused = _state_employee_entry_focused
    _employee_entry_unfocused = _state_employee_entry_unfocused
    _show_employee_placeholder = _state_show_employee_placeholder

    def __init__(self, root: tk.Tk):
        self.root = root
        self._is_windows = platform.system() == "Windows"
        self._window_icon_image = None
        self.root.title(WINDOW_TITLE)
        self.root.resizable(False, False)
        self._apply_window_icon(self.root)
        initialize_state(self)
        initialize_callbacks(self)

        self._build()
        self._fit_window_to_content(self.root)
        self._register_window_group_behavior()

    def _build(self) -> None:
        build_main_window(self)

    def _build_menu(self) -> None:
        build_menu(self)

    def _build_client_calls_settings_window(self) -> None:
        build_client_calls_settings_window(self)

    def _build_generator_window(self) -> None:
        build_generator_window(self)

    def _build_employees_window(self) -> None:
        build_employees_window(self)

    def _volume_changed(self, value: str) -> None:
        self._handle_volume_change(value, self.volume_display_var, self.on_volume_change)

    def _client_calls_volume_changed(self, value: str) -> None:
        self._handle_volume_change(value, self.client_calls_volume_display_var, self.on_client_calls_volume_change)

    def _client_calls_voice_message_volume_changed(self, value: str) -> None:
        self._handle_volume_change(
            value,
            self.client_calls_voice_message_volume_display_var,
            self.on_client_calls_voice_message_volume_change,
        )

    def _client_calls_speech_rate_changed(self, value: str) -> None:
        self._handle_volume_change(value, self.client_calls_speech_rate_display_var, self.on_client_calls_speech_rate_change)

    def _number_trim_silence_toggled(self) -> None:
        if self.on_number_trim_silence_toggle:
            self.on_number_trim_silence_toggle()

    def _number_silence_threshold_changed(self, value: str) -> None:
        self._handle_speed_change(
            value,
            self.number_silence_threshold_display_var,
            self.on_number_silence_threshold_change,
        )

    def _number_trim_leading_padding_changed(self, value: str) -> None:
        self._handle_speed_change(
            value,
            self.number_trim_leading_padding_display_var,
            self.on_number_trim_leading_padding_change,
        )

    def _number_trim_trailing_padding_changed(self, value: str) -> None:
        self._handle_speed_change(
            value,
            self.number_trim_trailing_padding_display_var,
            self.on_number_trim_trailing_padding_change,
        )

    def _number_symbol_pause_changed(self, value: str) -> None:
        self._handle_speed_change(value, self.number_symbol_pause_display_var, self.on_number_symbol_pause_change)

    def _preview_number_assembly_clicked(self) -> None:
        if self.on_preview_number_assembly:
            self.on_preview_number_assembly()

    def _check_updates_clicked(self) -> None:
        if self.on_check_updates:
            self.on_check_updates()

    def _notification_volume_changed(self, value: str) -> None:
        self._handle_volume_change(value, self.notification_volume_display_var, self.on_notification_volume_change)

    def _generator_volume_changed(self, value: str) -> None:
        self._handle_volume_change(value, self.generator_volume_display_var, self.on_generator_volume_change)

    def _generator_master_volume_changed(self, value: str) -> None:
        self._handle_speed_change(value, self.generator_master_volume_display_var, self.on_generator_master_volume_change)

    def _generator_language_typed(self, event: tk.Event) -> None:
        self._filter_combobox_values(
            self.generator_language_combobox,
            getattr(self, "_generator_language_options", []),
            self.generator_language_var.get(),
        )

    def _generator_accent_typed(self, event: tk.Event) -> None:
        self._filter_combobox_values(
            event.widget,
            getattr(self, "_generator_accent_options", []),
            self.generator_accent_var.get(),
        )

    def _client_calls_text_language_typed(self, event: tk.Event) -> None:
        self._filter_combobox_values(
            self.client_calls_text_language_combobox,
            getattr(self, "_client_calls_text_language_options", []),
            self.client_calls_text_language_var.get(),
        )

    def _generator_voice_typed(self, event: tk.Event) -> None:
        self._filter_combobox_values(
            self.generator_voice_combobox,
            getattr(self, "_generator_voice_options", []),
            self.generator_voice_var.get(),
        )

    def _generator_speed_changed(self, value: str) -> None:
        self._handle_speed_change(value, self.generator_speed_display_var, self.on_generator_speed_change)

    def _client_calls_text_voice_typed(self, event: tk.Event) -> None:
        self._filter_combobox_values(
            self.client_calls_text_voice_combobox,
            getattr(self, "_client_calls_text_voice_options", []),
            self.client_calls_text_voice_var.get(),
        )

    def _toggle_client_calls_api_edit_mode(self) -> None:
        editable = not self._client_calls_api_settings_editable
        if self._client_calls_api_settings_editable and not editable:
            self._client_calls_api_host_changed()
            self._client_calls_api_port_changed()
        self._set_client_calls_api_editable(editable)

    def _toggle_generator_api_key_edit_mode(self) -> None:
        editable = not self._generator_api_key_editable
        if self._generator_api_key_editable and not editable:
            self._generator_api_key_changed()
        self._set_generator_api_key_editable(editable)

    def _copy_client_calls_api_token_clicked(self) -> None:
        token = self.client_calls_api_token_var.get().strip()
        if not token:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(token)
        self.root.update_idletasks()

    def _generate_client_calls_api_token_clicked(self) -> None:
        has_existing_token = bool(self.client_calls_api_token_var.get().strip())
        if has_existing_token:
            confirmed = messagebox.askyesno(
                "Подтверждение",
                "Перегенерировать API токен?\nСтарый токен перестанет работать.",
            )
            if not confirmed:
                return

        if self.on_generate_client_calls_api_token:
            self.on_generate_client_calls_api_token()

    def _set_client_calls_api_editable(self, editable: bool) -> None:
        self._client_calls_api_settings_editable = editable
        self.client_calls_api_edit_button_var.set("Готово" if editable else "Изменить")

        host_state = "normal" if editable else "disabled"
        token_action_state = "normal" if editable else "disabled"
        if self._client_calls_api_host_entry is not None:
            self._client_calls_api_host_entry.configure(state=host_state)
        if self._client_calls_api_port_entry is not None:
            self._client_calls_api_port_entry.configure(state=host_state)
        if self._client_calls_api_generate_button is not None:
            self._client_calls_api_generate_button.configure(state=token_action_state)
        if self._client_calls_api_copy_button is not None:
            self._client_calls_api_copy_button.configure(state="normal")

    def _set_generator_api_key_editable(self, editable: bool) -> None:
        self._generator_api_key_editable = editable
        self.generator_api_edit_button_var.set("Готово" if editable else "Изм.")
        if self._generator_api_key_entry is None:
            return

        if editable:
            self.generator_api_key_button_var.set(self._generator_api_key_value)
            self._generator_api_key_entry.configure(state="normal")
            self._generator_api_key_entry.focus_set()
            self._generator_api_key_entry.icursor(tk.END)
            return

        self._generator_api_key_entry.configure(state="disabled")
        masked = self._mask_secret(self._generator_api_key_value, visible_suffix=5)
        self.generator_api_key_button_var.set(masked)
        self._generator_api_key_entry.configure(width=max(len(masked), 10))

    def _bind_button_hover_recursively(self, widget: tk.Widget) -> None:
        if isinstance(widget, tk.Button):
            self._bind_button_hover(widget)

        for child in widget.winfo_children():
            self._bind_button_hover_recursively(child)

    def _bind_button_hover(self, button: tk.Button) -> None:
        try:
            button.configure(overrelief="groove", cursor="pointinghand")
        except tk.TclError:
            try:
                button.configure(overrelief="groove", cursor="hand2")
            except tk.TclError:
                return

    def _client_calls_repeat_interval_changed(self) -> None:
        if self.on_client_calls_repeat_interval_change:
            self.on_client_calls_repeat_interval_change()

    def _client_calls_repeat_interval_submitted(self, event: tk.Event) -> str:
        self._client_calls_repeat_interval_changed()
        return "break"

    def _hide_client_calls_settings_window(self) -> None:
        self._settings_window_requested_visible = False
        if self._client_calls_settings_window is not None:
            self._client_calls_settings_window.withdraw()

    def _hide_generator_window(self) -> None:
        self._generator_window_requested_visible = False
        if self._generator_window is not None:
            self._generator_window.withdraw()

    def _hide_employees_window(self) -> None:
        self._employees_window_requested_visible = False
        if self._employees_window is not None:
            self._employees_window.withdraw()

    def set_device_options(self, device_names: List[str], selected: str = "") -> None:
        self._set_option_menu_values(self.device_menu, self.device_var, device_names, selected)

    def set_client_calls_device_options(self, device_names: List[str], selected: str = "") -> None:
        self._set_option_menu_values(self.client_calls_device_menu, self.client_calls_device_var, device_names, selected)

    def set_client_calls_voice_message_device_options(self, device_names: List[str], selected: str = "") -> None:
        self._set_option_menu_values(
            self.client_calls_voice_message_device_menu,
            self.client_calls_voice_message_device_var,
            device_names,
            selected,
        )

    def set_generator_device_options(self, device_names: List[str], selected: str = "") -> None:
        self._set_option_menu_values(self.generator_device_menu, self.generator_device_var, device_names, selected)

    def set_generator_voice_options(self, voice_names: List[str], selected: str = "") -> None:
        self._generator_voice_options = voice_names[:]
        self.generator_voice_combobox["values"] = tuple(voice_names)
        if selected:
            self.generator_voice_var.set(selected)
        elif voice_names:
            self.generator_voice_var.set(voice_names[0])
        else:
            self.generator_voice_var.set("")

    def set_client_calls_text_voice_options(self, voice_names: List[str], selected: str = "") -> None:
        self._client_calls_text_voice_options = voice_names[:]
        self.client_calls_text_voice_combobox["values"] = tuple(voice_names)
        if selected:
            self.client_calls_text_voice_var.set(selected)
        elif voice_names:
            self.client_calls_text_voice_var.set(voice_names[0])
        else:
            self.client_calls_text_voice_var.set("")

    def set_client_calls_text_language_options(self, language_names: List[str], selected: str = "") -> None:
        self._client_calls_text_language_options = language_names[:]
        self.client_calls_text_language_combobox["values"] = tuple(language_names)
        if selected:
            self.client_calls_text_language_var.set(selected)
        elif language_names:
            self.client_calls_text_language_var.set(language_names[0])
        else:
            self.client_calls_text_language_var.set("")

    def set_client_calls_text_voice_preview_playing(self, is_playing: bool) -> None:
        self.client_calls_text_voice_preview_button_var.set("Стоп" if is_playing else "Прослушать")

    def set_generator_language_options(self, language_names: List[str], selected: str = "") -> None:
        self._generator_language_options = language_names[:]
        self.generator_language_combobox["values"] = tuple(language_names)
        if selected:
            self.generator_language_var.set(selected)
        elif language_names:
            self.generator_language_var.set(language_names[0])
        else:
            self.generator_language_var.set("")

    def set_generator_accent_options(self, accent_names: List[str], selected: str = "") -> None:
        self._generator_accent_options = accent_names[:]
        if hasattr(self, "generator_accent_combobox"):
            self.generator_accent_combobox["values"] = tuple(accent_names)
        if hasattr(self, "generator_accent_window_combobox"):
            self.generator_accent_window_combobox["values"] = tuple(accent_names)
        if selected:
            self.generator_accent_var.set(selected)
        else:
            self.generator_accent_var.set(accent_names[0] if accent_names else "")

    def set_generator_accent_enabled(self, enabled: bool, message: str = "") -> None:
        state = "normal" if enabled else "disabled"
        if hasattr(self, "generator_accent_combobox"):
            self.generator_accent_combobox.configure(state=state)
        if hasattr(self, "generator_accent_window_combobox"):
            self.generator_accent_window_combobox.configure(state=state)
        if hasattr(self, "generator_accent_hint_label"):
            self.generator_accent_hint_label.config(text=message)
            if message:
                self.generator_accent_hint_label.grid()
            else:
                self.generator_accent_hint_label.grid_remove()
        if hasattr(self, "generator_accent_window_hint_label"):
            self.generator_accent_window_hint_label.config(text=message)
            if message:
                self.generator_accent_window_hint_label.grid()
            else:
                self.generator_accent_window_hint_label.grid_remove()

    def set_volume(self, value: float) -> None:
        self.volume_var.set(value)
        self.volume_display_var.set(f"{value:.1f}")

    def set_client_calls_volume(self, value: float) -> None:
        self.client_calls_volume_var.set(value)
        self.client_calls_volume_display_var.set(f"{value:.1f}")

    def set_client_calls_voice_message_volume(self, value: float) -> None:
        self.client_calls_voice_message_volume_var.set(value)
        self.client_calls_voice_message_volume_display_var.set(f"{value:.1f}")

    def set_client_calls_speech_rate(self, value: float) -> None:
        self.client_calls_speech_rate_var.set(value)
        self.client_calls_speech_rate_display_var.set(f"{value:.1f}")

    def set_number_trim_silence_enabled(self, enabled: bool) -> None:
        self.number_trim_silence_var.set(enabled)

    def set_number_silence_threshold(self, value: int) -> None:
        self.number_silence_threshold_var.set(value)
        self.number_silence_threshold_display_var.set(str(int(value)))

    def set_number_trim_leading_padding(self, value: int) -> None:
        self.number_trim_leading_padding_var.set(value)
        self.number_trim_leading_padding_display_var.set(str(int(value)))

    def set_number_trim_trailing_padding(self, value: int) -> None:
        self.number_trim_trailing_padding_var.set(value)
        self.number_trim_trailing_padding_display_var.set(str(int(value)))

    def set_number_symbol_pause(self, value: int) -> None:
        self.number_symbol_pause_var.set(value)
        self.number_symbol_pause_display_var.set(str(int(value)))

    def set_notification_volume(self, value: float) -> None:
        self.notification_volume_var.set(value)
        self.notification_volume_display_var.set(f"{value:.1f}")

    def set_generator_volume(self, value: float) -> None:
        self.generator_volume_var.set(value)
        self.generator_volume_display_var.set(f"{value:.1f}")

    def set_generator_master_volume(self, value: int) -> None:
        self.generator_master_volume_var.set(value)
        self.generator_master_volume_display_var.set(str(int(value)))

    def set_generator_speed(self, value: int) -> None:
        self.generator_speed_var.set(value)
        self.generator_speed_display_var.set(str(int(value)))

    def set_generator_voice(self, voice_name: str) -> None:
        self.generator_voice_var.set(voice_name)

    def set_generator_language(self, language_name: str) -> None:
        self.generator_language_var.set(language_name)

    def _bind_standard_edit_shortcuts(self, widget: tk.Widget) -> None:
        for sequence in ("<Command-a>", "<Control-a>"):
            widget.bind(sequence, self._select_all_shortcut)
        for sequence in ("<Command-c>", "<Control-c>"):
            widget.bind(sequence, self._copy_shortcut)
        for sequence in ("<Command-v>", "<Control-v>"):
            widget.bind(sequence, self._paste_shortcut)
        for sequence in ("<Command-x>", "<Control-x>"):
            widget.bind(sequence, self._cut_shortcut)
        widget.bind("<KeyPress>", self._handle_edit_shortcuts_on_any_layout, add="+")

    def _bind_edit_shortcuts_recursively(self, widget: tk.Widget) -> None:
        if isinstance(widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox)):
            self._bind_standard_edit_shortcuts(widget)

        for child in widget.winfo_children():
            self._bind_edit_shortcuts_recursively(child)

    def _handle_edit_shortcuts_on_any_layout(self, event: tk.Event) -> str | None:
        if not self._has_edit_shortcut_modifier(event):
            return None

        key = getattr(event, "keysym", "")
        if key in self.EDIT_SHORTCUT_KEYS["select_all"]:
            return self._select_all_shortcut(event)
        if key in self.EDIT_SHORTCUT_KEYS["copy"]:
            return self._copy_shortcut(event)
        if key in self.EDIT_SHORTCUT_KEYS["paste"]:
            return self._paste_shortcut(event)
        if key in self.EDIT_SHORTCUT_KEYS["cut"]:
            return self._cut_shortcut(event)
        return None

    def _has_edit_shortcut_modifier(self, event: tk.Event) -> bool:
        state = getattr(event, "state", 0)
        if self._is_windows:
            return bool(state & 0x4)
        return bool(state & 0x4 or state & 0x8)

    def _select_all_shortcut(self, event: tk.Event) -> str:
        widget = event.widget
        if isinstance(widget, tk.Text):
            widget.tag_add("sel", "1.0", "end-1c")
            widget.mark_set("insert", "1.0")
            widget.see("insert")
        elif isinstance(widget, (tk.Entry, ttk.Entry)):
            widget.selection_range(0, tk.END)
            widget.icursor(tk.END)
        return "break"

    def _copy_shortcut(self, event: tk.Event) -> str:
        event.widget.event_generate("<<Copy>>")
        return "break"

    def _paste_shortcut(self, event: tk.Event) -> str:
        event.widget.event_generate("<<Paste>>")
        return "break"

    def _cut_shortcut(self, event: tk.Event) -> str:
        event.widget.event_generate("<<Cut>>")
        return "break"

    def get_client_calls_interval(self) -> str:
        return self.client_calls_interval_var.get().strip()

    def set_client_calls_interval(self, value: float) -> None:
        if float(value).is_integer():
            self.client_calls_interval_var.set(str(int(value)))
        else:
            self.client_calls_interval_var.set(str(value).replace(".", ","))

    def set_client_calls_repeat_enabled(self, enabled: bool) -> None:
        self.client_calls_repeat_var.set(enabled)

    def get_client_calls_repeat_interval(self) -> str:
        return self.client_calls_repeat_interval_var.get().strip()

    def set_client_calls_repeat_interval(self, value: float) -> None:
        if float(value).is_integer():
            self.client_calls_repeat_interval_var.set(str(int(value)))
        else:
            self.client_calls_repeat_interval_var.set(str(value).replace(".", ","))

    def set_scheduler_notification_enabled(self, enabled: bool) -> None:
        self.scheduler_notification_var.set(enabled)

    def set_autostart_enabled(self, enabled: bool) -> None:
        self.autostart_var.set(enabled)

    def set_update_checking(self, checking: bool, text: str = "Проверяю...") -> None:
        self.update_check_button_var.set(text if checking else "Проверить обновления")
        if hasattr(self, "update_check_button"):
            self.update_check_button.configure(state="disabled" if checking else "normal")

    def set_client_calls_notification_enabled(self, enabled: bool) -> None:
        self.client_calls_notification_var.set(enabled)

    def set_client_calls_repeat_notification_enabled(self, enabled: bool) -> None:
        self.client_calls_repeat_notification_var.set(enabled)

    def is_scheduler_notification_enabled(self) -> bool:
        return self.scheduler_notification_var.get()

    def is_client_calls_notification_enabled(self) -> bool:
        return self.client_calls_notification_var.get()

    def is_client_calls_repeat_enabled(self) -> bool:
        return self.client_calls_repeat_var.get()

    def is_client_calls_repeat_notification_enabled(self) -> bool:
        return self.client_calls_repeat_notification_var.get()

    def is_number_trim_silence_enabled(self) -> bool:
        return self.number_trim_silence_var.get()

    def is_autostart_enabled(self) -> bool:
        return self.autostart_var.get()

    def ask_yes_no(self, title: str, text: str) -> bool:
        return bool(messagebox.askyesno(title, text))

    def show_error(self, text: str) -> None:
        messagebox.showerror("Ошибка", text)

    def show_info(self, title: str, text: str) -> None:
        messagebox.showinfo(title, text)

    def set_last_error_status(self, text: str) -> None:
        message = text.strip() or "Готово"
        self.last_error_status_var.set(message)
        is_error = message != "Готово"
        self.last_error_status_label.configure(fg="#b42318" if is_error else "#2f855a")

    def set_main_window_geometry(self, geometry: str) -> None:
        self._fit_window_to_content(self.root)
        position = self._extract_window_position(geometry)
        if position:
            self.root.geometry(position)

    def get_main_window_geometry(self) -> str:
        return self._extract_window_position(self.root.geometry())

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

        if self._is_windows:
            longest_option = max((len(name) for name in options), default=24)
            option_menu.config(width=min(max(longest_option, 24), 48))

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

    def _handle_speed_change(
        self,
        value: str,
        display_var: tk.StringVar,
        callback: Optional[Callable[[float], None]],
    ) -> None:
        speed = float(value)
        display_var.set(str(int(round(speed))))
        if callback:
            callback(speed)

    def _create_settings_scale(
        self,
        parent: tk.Misc,
        variable: tk.Variable,
        command,
        from_: float,
        to: float,
        resolution: float,
    ) -> tk.Scale:
        return tk.Scale(
            parent,
            from_=from_,
            to=to,
            resolution=resolution,
            orient="horizontal",
            variable=variable,
            command=command,
            showvalue=False,
            length=180 if self._is_windows else 210,
            width=10,
            sliderlength=16,
            highlightthickness=0,
            bd=0,
        )

    def _set_file_value(self, path_var: tk.StringVar, display_var: tk.StringVar, file_path: str) -> None:
        path_var.set(file_path)
        display_var.set(os.path.basename(file_path) if file_path else "")

    def _filter_combobox_values(self, combobox: ttk.Combobox, all_values: List[str], query: str) -> None:
        normalized_query = query.strip().lower()
        if not normalized_query:
            combobox["values"] = tuple(all_values)
            return

        filtered = [value for value in all_values if normalized_query in value.lower()]
        combobox["values"] = tuple(filtered if filtered else all_values)

    def _generate_ai_speech_clicked(self) -> None:
        if self.on_generate_ai_speech:
            self.on_generate_ai_speech()

    def _save_generated_ai_speech_clicked(self) -> None:
        if self.on_save_generated_ai_speech:
            self.on_save_generated_ai_speech()

    def _add_employee_clicked(self) -> None:
        if self.on_add_employee:
            self.on_add_employee()

    def _delete_employee_clicked(self) -> None:
        if self.on_delete_employee:
            self.on_delete_employee()

    def _employee_enter_pressed(self, event: tk.Event) -> str:
        self._add_employee_clicked()
        return "break"

    def _employee_entry_focused(self, event: tk.Event) -> None:
        if not self._employee_placeholder_visible or self._employee_entry is None:
            return
        self.employee_input_var.set("")
        self._employee_entry.config(fg="#111111", font=self._employee_entry_font)
        self._employee_placeholder_visible = False

    def _employee_entry_unfocused(self, event: tk.Event) -> None:
        if self.employee_input_var.get().strip():
            return
        self._show_employee_placeholder()

    def _show_employee_placeholder(self) -> None:
        if self._employee_entry is None:
            return
        self.employee_input_var.set(self._employee_placeholder_text)
        self._employee_entry.config(fg="#8a8a8a", font=self._employee_entry_placeholder_font)
        self._employee_entry.icursor(0)
        self._employee_placeholder_visible = True

    def _generator_enter_pressed(self, event: tk.Event) -> str:
        self._generate_ai_speech_clicked()
        return "break"
