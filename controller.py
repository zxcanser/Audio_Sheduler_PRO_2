from functools import partial
import threading
import tkinter as tk

from config import CONFIG_FILE, GITHUB_RELEASES_API_URL, SCHEDULE_FILE, WINDOW_TITLE, APP_VERSION
from models import ClientCall
from repository import JsonRepository
from services.audio_device_service import AudioDeviceService
from services.audio_player import AudioPlayer
from services.autostart_service import AutostartService
from services.call_api_server import CallApiServerService
from services.client_call_service import ClientCallService
from services.platform_integration import PlatformIntegration
from services.playback_coordinator import PlaybackCoordinator, PlaybackTask
from services.recorded_call_builder import RecordedCallBuilderService
from services.scheduler_service import SchedulerService
from services.schedule_manager import ScheduleManager
from services.update_service import UpdateService
from services.voicemaker_service import VoiceMakerService, VoiceMakerVoice
from services.validation_service import ValidationError, ValidationService
from services.workday_calendar_service import WorkdayCalendarService
from controller_update import (
    _check_for_updates_worker as _update_check_for_updates_worker,
    _download_update_worker as _update_download_update_worker,
    _finish_update_check_error as _update_finish_update_check_error,
    _finish_update_check_success as _update_finish_update_check_success,
    _finish_update_download_error as _update_finish_update_download_error,
    _finish_update_download_success as _update_finish_update_download_success,
    check_for_updates as _update_check_for_updates,
)
from controller_workday import (
    _finish_workday_calendar as _workday_finish_workday_calendar,
    _finish_workday_status as _workday_finish_workday_status,
    _is_today_workday as _workday_is_today_workday,
    _load_workday_calendar_worker as _workday_load_workday_calendar_worker,
    _refresh_workday_status_loop as _workday_refresh_workday_status_loop,
    _refresh_workday_status_worker as _workday_refresh_workday_status_worker,
    show_workday_calendar as _workday_show_workday_calendar,
)
from controller_voice import (
    _accent_code_by_label as _voice_accent_code_by_label,
    _accent_label_by_code as _voice_accent_label_by_code,
    _add_employee_worker as _voice_add_employee_worker,
    _append_employee_to_file as _voice_append_employee_to_file,
    _apply_default_client_calls_text_voice as _voice_apply_default_client_calls_text_voice,
    _apply_default_generator_voice as _voice_apply_default_generator_voice,
    _build_client_call_text_audio_file as _voice_build_client_call_text_audio_file,
    _build_client_call_text_request_signature as _voice_build_client_call_text_request_signature,
    _build_client_calls_text_voice_preview_signature as _voice_build_client_calls_text_voice_preview_signature,
    _build_generator_request_signature as _voice_build_generator_request_signature,
    _build_voice_request_signature as _voice_build_voice_request_signature,
    _cleanup_client_calls_text_voice_preview_file as _voice_cleanup_client_calls_text_voice_preview_file,
    _clear_client_calls_text_voice_options as _voice_clear_client_calls_text_voice_options,
    _clear_generator_voice_options as _voice_clear_generator_voice_options,
    _delete_worker_audio as _voice_delete_worker_audio,
    _employee_audio_stem as _voice_employee_audio_stem,
    _finish_add_employee_error as _voice_finish_add_employee_error,
    _finish_add_employee_success as _voice_finish_add_employee_success,
    _finish_client_calls_text_voice_preview_error as _voice_finish_client_calls_text_voice_preview_error,
    _finish_client_calls_text_voice_preview_success as _voice_finish_client_calls_text_voice_preview_success,
    _finish_generator_error as _voice_finish_generator_error,
    _finish_generator_success as _voice_finish_generator_success,
    _finish_refresh_client_calls_text_voices as _voice_finish_refresh_client_calls_text_voices,
    _finish_refresh_generator_voices as _voice_finish_refresh_generator_voices,
    _generate_ai_speech_worker as _voice_generate_ai_speech_worker,
    _generate_voice_maker_audio as _voice_generate_voice_maker_audio,
    _handle_client_calls_text_voice_preview_finished as _voice_handle_client_calls_text_voice_preview_finished,
    _handle_voice_refresh_failure as _voice_handle_voice_refresh_failure,
    _language_code_by_label as _voice_language_code_by_label,
    _language_label_by_code as _voice_language_label_by_code,
    _list_voice_maker_voices as _voice_list_voice_maker_voices,
    _normalize_employee_name as _voice_normalize_employee_name,
    _normalized_employee_audio_stem as _voice_normalized_employee_audio_stem,
    _play_client_calls_text_voice_preview as _voice_play_client_calls_text_voice_preview,
    _play_generated_audio as _voice_play_generated_audio,
    _preview_client_calls_text_voice_worker as _voice_preview_client_calls_text_voice_worker,
    _read_employees_file as _voice_read_employees_file,
    _read_generator_api_key as _voice_read_generator_api_key,
    _refresh_client_calls_text_voices as _voice_refresh_client_calls_text_voices,
    _refresh_client_calls_text_voices_worker as _voice_refresh_client_calls_text_voices_worker,
    _refresh_employees_list as _voice_refresh_employees_list,
    _refresh_generator_voices as _voice_refresh_generator_voices,
    _refresh_generator_voices_worker as _voice_refresh_generator_voices_worker,
    _resolve_selected_voice_label as _voice_resolve_selected_voice_label,
    _set_generator_voice_options as _voice_set_generator_voice_options,
    _stop_client_calls_text_voice_preview as _voice_stop_client_calls_text_voice_preview,
    _sync_generator_accent_availability as _voice_sync_generator_accent_availability,
    _write_employees_file as _voice_write_employees_file,
    _write_worker_audio as _voice_write_worker_audio,
    add_employee as _voice_add_employee,
    delete_employee as _voice_delete_employee,
    generate_ai_speech as _voice_generate_ai_speech,
    preview_client_calls_text_voice as _voice_preview_client_calls_text_voice,
    preview_employee as _voice_preview_employee,
    request_generator_voices as _voice_request_generator_voices,
    save_generated_ai_speech as _voice_save_generated_ai_speech,
    show_employees_window as _voice_show_employees_window,
    show_generator_window as _voice_show_generator_window,
)
from controller_runtime import (
    _append_event_log as _runtime_append_event_log,
    _append_planner_queue_call as _runtime_append_planner_queue_call,
    _build_planner_playback_task as _runtime_build_planner_playback_task,
    _clear_current_planner_playback as _runtime_clear_current_planner_playback,
    _dispatch_deferred_planner_if_possible as _runtime_dispatch_deferred_planner_if_possible,
    _enqueue_with_optional_notification as _runtime_enqueue_with_optional_notification,
    _get_audio_duration as _runtime_get_audio_duration,
    _get_combined_queued_calls as _runtime_get_combined_queued_calls,
    _get_missing_schedule_entry_ids as _runtime_get_missing_schedule_entry_ids,
    _get_next_deferred_planner_group_index as _runtime_get_next_deferred_planner_group_index,
    _get_persistent_status_error as _runtime_get_persistent_status_error,
    _get_waiting_client_calls as _runtime_get_waiting_client_calls,
    _handle_client_call_playback_finished as _runtime_handle_client_call_playback_finished,
    _handle_planner_playback_error as _runtime_handle_planner_playback_error,
    _handle_planner_playback_finished as _runtime_handle_planner_playback_finished,
    _handle_planner_playback_started as _runtime_handle_planner_playback_started,
    _handle_runtime_event as _runtime_handle_runtime_event,
    _has_pending_client_calls as _runtime_has_pending_client_calls,
    _has_pending_playback as _runtime_has_pending_playback,
    _has_priority_deferred_planner as _runtime_has_priority_deferred_planner,
    _has_valid_notification_sound as _runtime_has_valid_notification_sound,
    _play_file as _runtime_play_file,
    _refresh_client_calls_queue as _runtime_refresh_client_calls_queue,
    _refresh_runtime_status_loop as _runtime_refresh_runtime_status_loop,
    _remove_planner_queue_call as _runtime_remove_planner_queue_call,
    _render_combined_call_queue as _runtime_render_combined_call_queue,
    _report_runtime_error as _runtime_report_runtime_error,
    _run_scheduled_entry as _runtime_run_scheduled_entry,
    _schedule_planner_progress_update as _runtime_schedule_planner_progress_update,
    _set_ready_status as _runtime_set_ready_status,
    open_error_log as _runtime_open_error_log,
    remove_queued_call as _runtime_remove_queued_call,
    stop_audio as _runtime_stop_audio,
)
from controller_api import (
    _apply_client_calls_api_settings_to_window as _api_apply_client_calls_api_settings_to_window,
    _build_client_call_from_api_payload as _api_build_client_call_from_api_payload,
    _handle_api_call_request as _api_handle_api_call_request,
    _restore_client_calls_api_settings as _api_restore_client_calls_api_settings,
    _sync_client_calls_api_server as _api_sync_client_calls_api_server,
    change_client_calls_api_enabled as _api_change_client_calls_api_enabled,
    change_client_calls_api_host as _api_change_client_calls_api_host,
    change_client_calls_api_port as _api_change_client_calls_api_port,
    generate_client_calls_api_token as _api_generate_client_calls_api_token,
)
from controller_settings import (
    _generator_master_volume_for_request as _settings_generator_master_volume_for_request,
    _cleanup_number_assembly_preview_file as _settings_cleanup_number_assembly_preview_file,
    _finish_number_assembly_preview_error as _settings_finish_number_assembly_preview_error,
    _finish_number_assembly_preview_success as _settings_finish_number_assembly_preview_success,
    _handle_number_assembly_preview_finished as _settings_handle_number_assembly_preview_finished,
    _preview_number_assembly_worker as _settings_preview_number_assembly_worker,
    _sync_autostart_state as _settings_sync_autostart_state,
    _sync_client_calls_interval as _settings_sync_client_calls_interval,
    _sync_client_calls_repeat_interval as _settings_sync_client_calls_repeat_interval,
    _sync_interval_setting as _settings_sync_interval_setting,
    _sync_notification_settings as _settings_sync_notification_settings,
    _update_setting as _settings_update_setting,
    change_autostart_enabled as _settings_change_autostart_enabled,
    change_client_calls_device as _settings_change_client_calls_device,
    change_client_calls_interval as _settings_change_client_calls_interval,
    change_client_calls_notification_enabled as _settings_change_client_calls_notification_enabled,
    change_client_calls_repeat_enabled as _settings_change_client_calls_repeat_enabled,
    change_client_calls_repeat_interval as _settings_change_client_calls_repeat_interval,
    change_client_calls_repeat_notification_enabled as _settings_change_client_calls_repeat_notification_enabled,
    change_client_calls_speech_rate as _settings_change_client_calls_speech_rate,
    change_client_calls_text_language as _settings_change_client_calls_text_language,
    change_client_calls_text_voice as _settings_change_client_calls_text_voice,
    change_client_calls_voice_message_device as _settings_change_client_calls_voice_message_device,
    change_client_calls_voice_message_volume as _settings_change_client_calls_voice_message_volume,
    change_client_calls_volume as _settings_change_client_calls_volume,
    change_device as _settings_change_device,
    change_generator_accent as _settings_change_generator_accent,
    change_generator_api_key as _settings_change_generator_api_key,
    change_generator_device as _settings_change_generator_device,
    change_generator_language as _settings_change_generator_language,
    change_generator_master_volume as _settings_change_generator_master_volume,
    change_generator_speed as _settings_change_generator_speed,
    change_generator_voice as _settings_change_generator_voice,
    change_generator_volume as _settings_change_generator_volume,
    change_notification_volume as _settings_change_notification_volume,
    change_number_silence_threshold as _settings_change_number_silence_threshold,
    change_number_symbol_pause as _settings_change_number_symbol_pause,
    change_number_trim_leading_padding as _settings_change_number_trim_leading_padding,
    change_number_trim_silence_enabled as _settings_change_number_trim_silence_enabled,
    change_number_trim_trailing_padding as _settings_change_number_trim_trailing_padding,
    change_scheduler_notification_enabled as _settings_change_scheduler_notification_enabled,
    change_volume as _settings_change_volume,
    preview_number_assembly as _settings_preview_number_assembly,
    request_client_calls_text_voices as _settings_request_client_calls_text_voices,
)
from controller_schedule import (
    _parse_imported_schedule_entries as _schedule_parse_imported_schedule_entries,
    _refresh_schedule_list as _schedule_refresh_schedule_list,
    add_schedule as _schedule_add_schedule,
    browse_client_calls_file as _schedule_browse_client_calls_file,
    browse_client_calls_voice_message_file as _schedule_browse_client_calls_voice_message_file,
    browse_employees_file as _schedule_browse_employees_file,
    browse_file as _schedule_browse_file,
    browse_notification_sound_file as _schedule_browse_notification_sound_file,
    delete_schedule as _schedule_delete_schedule,
    export_schedule as _schedule_export_schedule,
    import_schedule as _schedule_import_schedule,
    load_selected_entry_into_form as _schedule_load_selected_entry_into_form,
    play_selected_or_current as _schedule_play_selected_or_current,
    queue_selected_schedule_entry as _schedule_queue_selected_schedule_entry,
)
from controller_wiring import connect_window_events, load_initial_window_state
from ui.main_window import MainWindow


class AudioSchedulerController:
    CLIENT_CALLS_TEXT_VOICE_PREVIEW_TEXT = "Это проверка голоса. Уважаемые клиенты. Дорогие гости. Я люблю орешки"
    _refresh_schedule_list = _schedule_refresh_schedule_list
    browse_file = _schedule_browse_file
    browse_client_calls_file = _schedule_browse_client_calls_file
    browse_client_calls_voice_message_file = _schedule_browse_client_calls_voice_message_file
    browse_employees_file = _schedule_browse_employees_file
    browse_notification_sound_file = _schedule_browse_notification_sound_file
    add_schedule = _schedule_add_schedule
    delete_schedule = _schedule_delete_schedule
    load_selected_entry_into_form = _schedule_load_selected_entry_into_form
    play_selected_or_current = _schedule_play_selected_or_current
    queue_selected_schedule_entry = _schedule_queue_selected_schedule_entry
    export_schedule = _schedule_export_schedule
    import_schedule = _schedule_import_schedule
    _parse_imported_schedule_entries = _schedule_parse_imported_schedule_entries
    change_device = _settings_change_device
    change_volume = _settings_change_volume
    change_notification_volume = _settings_change_notification_volume
    change_client_calls_device = _settings_change_client_calls_device
    change_client_calls_voice_message_device = _settings_change_client_calls_voice_message_device
    change_client_calls_volume = _settings_change_client_calls_volume
    change_client_calls_voice_message_volume = _settings_change_client_calls_voice_message_volume
    change_client_calls_speech_rate = _settings_change_client_calls_speech_rate
    change_number_trim_silence_enabled = _settings_change_number_trim_silence_enabled
    change_number_silence_threshold = _settings_change_number_silence_threshold
    change_number_trim_leading_padding = _settings_change_number_trim_leading_padding
    change_number_trim_trailing_padding = _settings_change_number_trim_trailing_padding
    change_number_symbol_pause = _settings_change_number_symbol_pause
    preview_number_assembly = _settings_preview_number_assembly
    _preview_number_assembly_worker = _settings_preview_number_assembly_worker
    _finish_number_assembly_preview_success = _settings_finish_number_assembly_preview_success
    _finish_number_assembly_preview_error = _settings_finish_number_assembly_preview_error
    _handle_number_assembly_preview_finished = _settings_handle_number_assembly_preview_finished
    _cleanup_number_assembly_preview_file = _settings_cleanup_number_assembly_preview_file
    change_client_calls_interval = _settings_change_client_calls_interval
    change_client_calls_repeat_enabled = _settings_change_client_calls_repeat_enabled
    change_client_calls_repeat_interval = _settings_change_client_calls_repeat_interval
    change_client_calls_text_language = _settings_change_client_calls_text_language
    change_client_calls_text_voice = _settings_change_client_calls_text_voice
    change_generator_device = _settings_change_generator_device
    change_generator_api_key = _settings_change_generator_api_key
    change_generator_volume = _settings_change_generator_volume
    change_generator_master_volume = _settings_change_generator_master_volume
    change_generator_language = _settings_change_generator_language
    change_generator_accent = _settings_change_generator_accent
    change_generator_speed = _settings_change_generator_speed
    _generator_master_volume_for_request = _settings_generator_master_volume_for_request
    change_generator_voice = _settings_change_generator_voice
    request_client_calls_text_voices = _settings_request_client_calls_text_voices
    change_autostart_enabled = _settings_change_autostart_enabled
    _sync_autostart_state = _settings_sync_autostart_state
    change_scheduler_notification_enabled = _settings_change_scheduler_notification_enabled
    change_client_calls_notification_enabled = _settings_change_client_calls_notification_enabled
    change_client_calls_repeat_notification_enabled = _settings_change_client_calls_repeat_notification_enabled
    _sync_client_calls_interval = _settings_sync_client_calls_interval
    _sync_client_calls_repeat_interval = _settings_sync_client_calls_repeat_interval
    _sync_interval_setting = _settings_sync_interval_setting
    _sync_notification_settings = _settings_sync_notification_settings
    _update_setting = _settings_update_setting
    change_client_calls_api_enabled = _api_change_client_calls_api_enabled
    change_client_calls_api_host = _api_change_client_calls_api_host
    change_client_calls_api_port = _api_change_client_calls_api_port
    generate_client_calls_api_token = _api_generate_client_calls_api_token
    _handle_api_call_request = _api_handle_api_call_request
    _build_client_call_from_api_payload = _api_build_client_call_from_api_payload
    _sync_client_calls_api_server = _api_sync_client_calls_api_server
    _restore_client_calls_api_settings = _api_restore_client_calls_api_settings
    _apply_client_calls_api_settings_to_window = _api_apply_client_calls_api_settings_to_window
    _play_file = _runtime_play_file
    stop_audio = _runtime_stop_audio
    _run_scheduled_entry = _runtime_run_scheduled_entry
    _refresh_client_calls_queue = _runtime_refresh_client_calls_queue
    _report_runtime_error = _runtime_report_runtime_error
    _handle_runtime_event = _runtime_handle_runtime_event
    _handle_client_call_playback_finished = _runtime_handle_client_call_playback_finished
    _set_ready_status = _runtime_set_ready_status
    _get_persistent_status_error = _runtime_get_persistent_status_error
    _get_missing_schedule_entry_ids = _runtime_get_missing_schedule_entry_ids
    _refresh_runtime_status_loop = _runtime_refresh_runtime_status_loop
    _append_event_log = _runtime_append_event_log
    open_error_log = _runtime_open_error_log
    _render_combined_call_queue = _runtime_render_combined_call_queue
    _handle_planner_playback_started = _runtime_handle_planner_playback_started
    _handle_planner_playback_finished = _runtime_handle_planner_playback_finished
    _handle_planner_playback_error = _runtime_handle_planner_playback_error
    _schedule_planner_progress_update = _runtime_schedule_planner_progress_update
    _has_valid_notification_sound = _runtime_has_valid_notification_sound
    _get_audio_duration = _runtime_get_audio_duration
    _enqueue_with_optional_notification = _runtime_enqueue_with_optional_notification
    _append_planner_queue_call = _runtime_append_planner_queue_call
    _build_planner_playback_task = _runtime_build_planner_playback_task
    _clear_current_planner_playback = _runtime_clear_current_planner_playback
    _remove_planner_queue_call = _runtime_remove_planner_queue_call
    _get_combined_queued_calls = _runtime_get_combined_queued_calls
    _get_waiting_client_calls = _runtime_get_waiting_client_calls
    _get_next_deferred_planner_group_index = _runtime_get_next_deferred_planner_group_index
    _has_pending_playback = _runtime_has_pending_playback
    _has_pending_client_calls = _runtime_has_pending_client_calls
    _has_priority_deferred_planner = _runtime_has_priority_deferred_planner
    _dispatch_deferred_planner_if_possible = _runtime_dispatch_deferred_planner_if_possible
    remove_queued_call = _runtime_remove_queued_call
    show_generator_window = _voice_show_generator_window
    show_employees_window = _voice_show_employees_window
    request_generator_voices = _voice_request_generator_voices
    preview_client_calls_text_voice = _voice_preview_client_calls_text_voice
    _preview_client_calls_text_voice_worker = _voice_preview_client_calls_text_voice_worker
    _finish_client_calls_text_voice_preview_success = _voice_finish_client_calls_text_voice_preview_success
    _finish_client_calls_text_voice_preview_error = _voice_finish_client_calls_text_voice_preview_error
    _play_client_calls_text_voice_preview = _voice_play_client_calls_text_voice_preview
    _stop_client_calls_text_voice_preview = _voice_stop_client_calls_text_voice_preview
    _handle_client_calls_text_voice_preview_finished = _voice_handle_client_calls_text_voice_preview_finished
    generate_ai_speech = _voice_generate_ai_speech
    _generate_ai_speech_worker = _voice_generate_ai_speech_worker
    _finish_generator_success = _voice_finish_generator_success
    _finish_generator_error = _voice_finish_generator_error
    _play_generated_audio = _voice_play_generated_audio
    save_generated_ai_speech = _voice_save_generated_ai_speech
    add_employee = _voice_add_employee
    _add_employee_worker = _voice_add_employee_worker
    _finish_add_employee_success = _voice_finish_add_employee_success
    _finish_add_employee_error = _voice_finish_add_employee_error
    delete_employee = _voice_delete_employee
    preview_employee = _voice_preview_employee
    _refresh_employees_list = _voice_refresh_employees_list
    _read_generator_api_key = _voice_read_generator_api_key
    _build_generator_request_signature = _voice_build_generator_request_signature
    _build_client_calls_text_voice_preview_signature = _voice_build_client_calls_text_voice_preview_signature
    _build_client_call_text_request_signature = _voice_build_client_call_text_request_signature
    _build_voice_request_signature = _voice_build_voice_request_signature
    _cleanup_client_calls_text_voice_preview_file = _voice_cleanup_client_calls_text_voice_preview_file
    _refresh_generator_voices = _voice_refresh_generator_voices
    _refresh_generator_voices_worker = _voice_refresh_generator_voices_worker
    _refresh_client_calls_text_voices = _voice_refresh_client_calls_text_voices
    _refresh_client_calls_text_voices_worker = _voice_refresh_client_calls_text_voices_worker
    _finish_refresh_client_calls_text_voices = _voice_finish_refresh_client_calls_text_voices
    _finish_refresh_generator_voices = _voice_finish_refresh_generator_voices
    _set_generator_voice_options = _voice_set_generator_voice_options
    _clear_generator_voice_options = _voice_clear_generator_voice_options
    _clear_client_calls_text_voice_options = _voice_clear_client_calls_text_voice_options
    _handle_voice_refresh_failure = _voice_handle_voice_refresh_failure
    _resolve_selected_voice_label = _voice_resolve_selected_voice_label
    _apply_default_client_calls_text_voice = _voice_apply_default_client_calls_text_voice
    _apply_default_generator_voice = _voice_apply_default_generator_voice
    _sync_generator_accent_availability = _voice_sync_generator_accent_availability
    _language_code_by_label = _voice_language_code_by_label
    _language_label_by_code = _voice_language_label_by_code
    _accent_code_by_label = _voice_accent_code_by_label
    _accent_label_by_code = _voice_accent_label_by_code
    _read_employees_file = _voice_read_employees_file
    _append_employee_to_file = _voice_append_employee_to_file
    _write_employees_file = _voice_write_employees_file
    _write_worker_audio = _voice_write_worker_audio
    _delete_worker_audio = _voice_delete_worker_audio
    _employee_audio_stem = _voice_employee_audio_stem
    _normalized_employee_audio_stem = _voice_normalized_employee_audio_stem
    _normalize_employee_name = _voice_normalize_employee_name
    _build_client_call_text_audio_file = _voice_build_client_call_text_audio_file
    _generate_voice_maker_audio = _voice_generate_voice_maker_audio
    _list_voice_maker_voices = _voice_list_voice_maker_voices
    check_for_updates = _update_check_for_updates
    _check_for_updates_worker = _update_check_for_updates_worker
    _finish_update_check_success = _update_finish_update_check_success
    _finish_update_check_error = _update_finish_update_check_error
    _download_update_worker = _update_download_update_worker
    _finish_update_download_success = _update_finish_update_download_success
    _finish_update_download_error = _update_finish_update_download_error
    _is_today_workday = _workday_is_today_workday
    _refresh_workday_status_loop = _workday_refresh_workday_status_loop
    _refresh_workday_status_worker = _workday_refresh_workday_status_worker
    _finish_workday_status = _workday_finish_workday_status
    show_workday_calendar = _workday_show_workday_calendar
    _load_workday_calendar_worker = _workday_load_workday_calendar_worker
    _finish_workday_calendar = _workday_finish_workday_calendar

    def __init__(self, root: tk.Tk):
        self.root = root
        self._save_geometry_after_id: str | None = None

        self.repository = JsonRepository(CONFIG_FILE, SCHEDULE_FILE)
        self.device_service = AudioDeviceService()
        self.autostart_service = AutostartService()
        self.player = AudioPlayer(self.device_service)
        self.generator_preview_player = AudioPlayer(self.device_service)
        self.notification_preview_player = AudioPlayer(self.device_service)
        self.playback_coordinator = PlaybackCoordinator(
            tk_root=root,
            player=self.player,
            get_interval_seconds=lambda: self.settings.client_calls_interval_seconds,
        )
        self.recorded_call_builder = RecordedCallBuilderService()
        self.voice_maker_service = VoiceMakerService()
        self.workday_calendar_service = WorkdayCalendarService()
        self.update_service = UpdateService(GITHUB_RELEASES_API_URL, APP_VERSION)
        self.platform_integration = PlatformIntegration(root, WINDOW_TITLE, self.shutdown)
        self._generated_voice_bytes: bytes | None = None
        self._generated_voice_signature: str = ""
        self._client_calls_text_audio_bytes: bytes | None = None
        self._client_calls_text_audio_signature: str = ""
        self._notification_sound_preview_playing = False
        self._generator_busy = False
        self._generator_voices_by_label: dict[str, VoiceMakerVoice] = {}
        self._generator_voices_loading = False
        self._client_calls_text_voices_by_label: dict[str, VoiceMakerVoice] = {}
        self._client_calls_text_voices_loading = False
        self._devices_loading = False
        self._employee_generation_in_progress: set[str] = set()
        self._client_calls_text_voice_preview_busy = False
        self._client_calls_text_voice_preview_playing = False
        self._client_calls_text_voice_preview_bytes: bytes | None = None
        self._client_calls_text_voice_preview_signature = ""
        self._client_calls_text_voice_preview_temp_path: str | None = None
        self._number_assembly_preview_busy = False
        self._number_assembly_preview_temp_path: str | None = None
        self._client_call_queue_current: ClientCall | None = None
        self._client_call_queue_items: list[ClientCall] = []
        self._client_call_queue_progress = 0.0
        self._planner_queue_current: ClientCall | None = None
        self._planner_queue_items: list[ClientCall] = []
        self._planner_queue_progress = 0.0
        self._planner_queue_started_at: float | None = None
        self._planner_queue_duration = 0.0
        self._priority_planner_queue_ids: set[str] = set()
        self._deferred_planner_queue_ids: set[str] = set()
        self._deferred_planner_task_groups: list[tuple[str, list[PlaybackTask]]] = []
        self._last_manual_queue_signature = ""
        self._last_manual_queue_at = 0.0
        self._last_runtime_error = ""
        self._missing_schedule_entry_ids: set[str] = set()
        self._today_workday_date = None
        self._today_workday_status: int | None = None
        self._today_workday_error = ""
        self._workday_status_loading = False
        self._update_check_busy = False

        self.settings = self.repository.load_settings()
        loaded_entries = self.repository.load_schedule()
        self.schedule_manager = ScheduleManager(loaded_entries)

        self.window = MainWindow(root)
        self.scheduler = SchedulerService(
            tk_root=root,
            get_entries=self.schedule_manager.get_all,
            is_workday=self._is_today_workday,
            on_trigger=self._run_scheduled_entry,
            on_error=lambda message: self._post_to_ui(self._report_runtime_error, message),
        )
        self.client_call_service = ClientCallService(
            tk_root=root,
            playback_coordinator=self.playback_coordinator,
            call_builder=self.recorded_call_builder,
            build_text_audio_file=self._build_client_call_text_audio_file,
            get_source_path=self.window.get_client_calls_file,
            get_voice_message_path=lambda: self.settings.client_calls_voice_message_file_path,
            get_device_name=lambda: self.settings.client_calls_selected_device,
            get_voice_message_device_name=lambda: (
                self.settings.client_calls_voice_message_selected_device
                or self.settings.client_calls_selected_device
            ),
            get_volume=lambda: self.settings.client_calls_volume,
            get_voice_message_volume=lambda: self.settings.client_calls_voice_message_volume,
            get_speech_rate=lambda: self.settings.client_calls_speech_rate,
            is_number_trim_silence_enabled=lambda: self.settings.number_trim_silence_enabled,
            get_number_silence_threshold_db=lambda: self.settings.number_silence_threshold_db,
            get_number_trim_leading_padding_ms=lambda: self.settings.number_trim_leading_padding_ms,
            get_number_trim_trailing_padding_ms=lambda: self.settings.number_trim_trailing_padding_ms,
            get_number_symbol_pause_ms=lambda: self.settings.number_symbol_pause_ms,
            is_repeat_enabled=lambda: self.settings.client_calls_repeat_enabled,
            get_repeat_interval_seconds=lambda: self.settings.client_calls_repeat_interval_seconds,
            is_repeat_notification_enabled=lambda: self.settings.client_calls_repeat_notification_enabled,
            get_notification_volume=lambda: self.settings.notification_volume,
            get_notification_sound_path=lambda: self.settings.notification_sound_file_path,
            is_notification_enabled=lambda: self.settings.client_calls_notification_enabled,
            should_wait_for_priority=self._has_priority_deferred_planner,
            on_state_change=self._refresh_client_calls_queue,
            on_error=lambda message: self._post_to_ui(self._report_runtime_error, message),
            on_log=lambda message: self._post_to_ui(self._handle_runtime_event, message),
            on_finished=lambda: self._post_to_ui(self._handle_client_call_playback_finished),
        )
        self.call_api_server = CallApiServerService(
            on_call_request=self._handle_api_call_request,
            on_error=lambda message: self._post_to_ui(self._report_runtime_error, message),
        )

        self._connect_events()
        self._load_initial_state()

    def _connect_events(self) -> None:
        connect_window_events(self)

    def _load_initial_state(self) -> None:
        load_initial_window_state(self)

    def _refresh_devices(self, force_refresh: bool = False) -> None:
        if self._devices_loading:
            return

        self._devices_loading = True
        self._start_worker(self._refresh_devices_worker, force_refresh)

    def _refresh_devices_worker(self, force_refresh: bool) -> None:
        try:
            if force_refresh:
                device_names = self.device_service.refresh_output_device_names()
            else:
                device_names = self.device_service.get_output_device_names()
        except Exception as error:
            self._post_to_ui(self._finish_refresh_devices, [], str(error))
            return

        self._post_to_ui(self._finish_refresh_devices, device_names, "")

    def _finish_refresh_devices(self, device_names: list[str], error_message: str) -> None:
        self._devices_loading = False
        if error_message:
            self._report_runtime_error(f"Не удалось обновить аудиоустройства: {error_message}")
            return

        self.window.set_device_options(device_names, self.settings.selected_device)
        self.window.set_client_calls_device_options(device_names, self.settings.client_calls_selected_device)
        self.window.set_client_calls_voice_message_device_options(
            device_names,
            self.settings.client_calls_voice_message_selected_device or self.settings.client_calls_selected_device,
        )
        self.window.set_generator_device_options(device_names, self.settings.generator_selected_device)

        if self.window.device_var.get():
            self.settings.selected_device = self.window.device_var.get()
        if self.window.client_calls_device_var.get():
            self.settings.client_calls_selected_device = self.window.client_calls_device_var.get()
        if self.window.client_calls_voice_message_device_var.get():
            self.settings.client_calls_voice_message_selected_device = self.window.client_calls_voice_message_device_var.get()
        if self.window.generator_device_var.get():
            self.settings.generator_selected_device = self.window.generator_device_var.get()
        self.repository.save_settings(self.settings)

    def refresh_devices(self) -> None:
        self._refresh_devices(force_refresh=True)
        self.root.update_idletasks()

    def play_notification_sound(self) -> None:
        if self._notification_sound_preview_playing:
            self.notification_preview_player.stop()
            self._handle_notification_sound_preview_finished()
            return

        try:
            ValidationService.validate_optional_file(
                self.window.get_notification_sound_file(),
                "Сначала выберите файл звука уведомления",
            )
        except ValidationError as error:
            self.window.show_error(str(error))
            return

        device_name = self.settings.selected_device or self.settings.client_calls_selected_device
        self._notification_sound_preview_playing = True
        self.window.set_notification_sound_preview_playing(True)
        self.notification_preview_player.play_async(
            file_path=self.window.get_notification_sound_file(),
            volume=self.settings.notification_volume,
            device_name=device_name,
            on_error=lambda message: self.root.after(
                0, lambda msg=message: self._handle_notification_sound_preview_finished(error_message=msg)
            ),
            on_finished=lambda: self.root.after(0, self._handle_notification_sound_preview_finished),
        )

    def _handle_notification_sound_preview_finished(self, error_message: str = "") -> None:
        self._notification_sound_preview_playing = False
        self.window.set_notification_sound_preview_playing(False)
        if error_message:
            self.window.show_error(f"Не удалось воспроизвести звук уведомления: {error_message}")

    def _post_to_ui(self, callback, *args) -> None:
        self.root.after(0, partial(callback, *args))

    def _start_worker(self, target, *args) -> None:
        threading.Thread(target=target, args=args, daemon=True).start()

    def _schedule_root_after(self, delay_ms: int, callback) -> None:
        try:
            self.root.after(delay_ms, callback)
        except tk.TclError:
            pass

    def handle_close_request(self) -> None:
        self.platform_integration.request_close()

    def hide_to_tray(self) -> None:
        self.platform_integration.hide_window()

    def save_and_close(self) -> None:
        self.platform_integration.quit_application()

    def handle_window_unmap(self) -> None:
        self.platform_integration.handle_window_unmap()

    def shutdown(self) -> None:
        self.generator_preview_player.stop()
        self.notification_preview_player.stop()
        self._cleanup_client_calls_text_voice_preview_file()
        self._cleanup_number_assembly_preview_file()
        self._sync_client_calls_interval(show_errors=False)
        self._save_main_window_geometry()
        self.scheduler.stop()
        self.playback_coordinator.reset()
        self.client_call_service.stop()
        self.call_api_server.stop()
        self.platform_integration.cleanup()
        self.root.destroy()

    def handle_window_configure(self) -> None:
        try:
            if self.root.state() != "normal":
                return
        except tk.TclError:
            return

        if self._save_geometry_after_id is not None:
            self.root.after_cancel(self._save_geometry_after_id)
        self._save_geometry_after_id = self.root.after(250, self._save_main_window_geometry)

    def _save_main_window_geometry(self) -> None:
        self._save_geometry_after_id = None
        geometry = self.window.get_main_window_geometry()
        if geometry and geometry != self.settings.main_window_geometry:
            self._update_setting("main_window_geometry", geometry)
