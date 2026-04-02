from tkinter import filedialog
import os
import tempfile
import threading
import tkinter as tk
import unicodedata

from config import CONFIG_FILE, SCHEDULE_FILE, WINDOW_TITLE
from models import ClientCall
from repository import JsonRepository
from services.audio_device_service import AudioDeviceService
from services.audio_player import AudioPlayer
from services.autostart_service import AutostartService
from services.client_call_service import ClientCallService
from services.platform_integration import PlatformIntegration
from services.playback_coordinator import PlaybackCoordinator, PlaybackTask
from services.recorded_call_builder import RecordedCallBuilderService
from services.scheduler_service import SchedulerService
from services.schedule_manager import ScheduleManager
from services.voicemaker_service import VoiceMakerService, VoiceMakerVoice
from services.validation_service import ValidationError, ValidationService
from ui.main_window import MainWindow


class AudioSchedulerController:
    CLIENT_CALLS_TEXT_VOICE_PREVIEW_TEXT = "Это проверка голоса. Уважаемые клиенты. Дорогие гости. Я люблю орешки"

    def __init__(self, root: tk.Tk):
        self.root = root
        self._save_geometry_after_id: str | None = None

        self.repository = JsonRepository(CONFIG_FILE, SCHEDULE_FILE)
        self.device_service = AudioDeviceService()
        self.autostart_service = AutostartService()
        self.player = AudioPlayer(self.device_service)
        self.generator_preview_player = AudioPlayer(self.device_service)
        self.playback_coordinator = PlaybackCoordinator(
            tk_root=root,
            player=self.player,
            get_interval_seconds=lambda: self.settings.client_calls_interval_seconds,
        )
        self.recorded_call_builder = RecordedCallBuilderService()
        self.voice_maker_service = VoiceMakerService()
        self.platform_integration = PlatformIntegration(root, WINDOW_TITLE, self.shutdown)
        self._generated_voice_bytes: bytes | None = None
        self._generated_voice_signature: str = ""
        self._generator_busy = False
        self._generator_voices_by_label: dict[str, VoiceMakerVoice] = {}
        self._generator_voices_loading = False
        self._client_calls_text_voices_by_label: dict[str, VoiceMakerVoice] = {}
        self._client_calls_text_voices_loading = False
        self._employee_generation_in_progress: set[str] = set()
        self._client_calls_text_voice_preview_busy = False
        self._client_calls_text_voice_preview_playing = False
        self._client_calls_text_voice_preview_bytes: bytes | None = None
        self._client_calls_text_voice_preview_signature = ""
        self._client_calls_text_voice_preview_temp_path: str | None = None

        self.settings = self.repository.load_settings()
        loaded_entries = self.repository.load_schedule()
        self.schedule_manager = ScheduleManager(loaded_entries)

        self.window = MainWindow(root)
        self.scheduler = SchedulerService(
            tk_root=root,
            get_entries=self.schedule_manager.get_all,
            get_active_weekdays=lambda: self.settings.scheduler_weekdays,
            on_trigger=self._run_scheduled_entry
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
            is_repeat_enabled=lambda: self.settings.client_calls_repeat_enabled,
            get_repeat_interval_seconds=lambda: self.settings.client_calls_repeat_interval_seconds,
            is_repeat_notification_enabled=lambda: self.settings.client_calls_repeat_notification_enabled,
            get_notification_volume=lambda: self.settings.notification_volume,
            get_notification_sound_path=lambda: self.settings.notification_sound_file_path,
            is_notification_enabled=lambda: self.settings.client_calls_notification_enabled,
            on_state_change=self._refresh_client_calls_queue,
            on_error=lambda message: self.window.show_error(message),
        )

        self._connect_events()
        self._load_initial_state()

    def _connect_events(self) -> None:
        self.window.on_browse = self.browse_file
        self.window.on_add = self.add_schedule
        self.window.on_delete = self.delete_schedule
        self.window.on_play = self.play_selected_or_current
        self.window.on_refresh_devices = self.refresh_devices
        self.window.on_device_change = self.change_device
        self.window.on_volume_change = self.change_volume
        self.window.on_notification_volume_change = self.change_notification_volume
        self.window.on_select_entry = self.load_selected_entry_into_form
        self.window.on_browse_client_calls_file = self.browse_client_calls_file
        self.window.on_browse_client_calls_voice_message_file = self.browse_client_calls_voice_message_file
        self.window.on_browse_employees_file = self.browse_employees_file
        self.window.on_client_calls_volume_change = self.change_client_calls_volume
        self.window.on_client_calls_voice_message_volume_change = self.change_client_calls_voice_message_volume
        self.window.on_client_calls_speech_rate_change = self.change_client_calls_speech_rate
        self.window.on_client_calls_device_change = self.change_client_calls_device
        self.window.on_client_calls_voice_message_device_change = self.change_client_calls_voice_message_device
        self.window.on_client_calls_interval_change = self.change_client_calls_interval
        self.window.on_client_calls_repeat_toggle = self.change_client_calls_repeat_enabled
        self.window.on_client_calls_repeat_interval_change = self.change_client_calls_repeat_interval
        self.window.on_client_calls_repeat_notification_toggle = self.change_client_calls_repeat_notification_enabled
        self.window.on_client_calls_text_language_change = self.change_client_calls_text_language
        self.window.on_client_calls_text_voice_change = self.change_client_calls_text_voice
        self.window.on_preview_client_calls_text_voice = self.preview_client_calls_text_voice
        self.window.on_request_client_calls_text_voices = self.request_client_calls_text_voices
        self.window.on_scheduler_weekdays_change = self.change_scheduler_weekdays
        self.window.on_browse_notification_sound_file = self.browse_notification_sound_file
        self.window.on_play_notification_sound = self.play_notification_sound
        self.window.on_show_generator = self.show_generator_window
        self.window.on_show_employees = self.show_employees_window
        self.window.on_browse_generator_api_file = self.browse_generator_api_file
        self.window.on_generator_device_change = self.change_generator_device
        self.window.on_generator_volume_change = self.change_generator_volume
        self.window.on_generator_language_change = self.change_generator_language
        self.window.on_generator_voice_change = self.change_generator_voice
        self.window.on_request_generator_voices = self.request_generator_voices
        self.window.on_generate_ai_speech = self.generate_ai_speech
        self.window.on_save_generated_ai_speech = self.save_generated_ai_speech
        self.window.on_add_employee = self.add_employee
        self.window.on_delete_employee = self.delete_employee
        self.window.on_preview_employee = self.preview_employee
        self.window.on_autostart_toggle = self.change_autostart_enabled
        self.window.on_scheduler_notification_toggle = self.change_scheduler_notification_enabled
        self.window.on_client_calls_notification_toggle = self.change_client_calls_notification_enabled
        self.window.on_hide_to_tray = self.hide_to_tray
        self.window.on_quit_application = self.save_and_close
        self.window.on_close = self.handle_close_request
        self.window.on_window_unmap = self.handle_window_unmap
        self.window.on_window_configure = self.handle_window_configure

    def _load_initial_state(self) -> None:
        self.window.set_main_window_geometry(self.settings.main_window_geometry)
        self.window.set_volume(self.settings.volume)
        self.window.set_notification_volume(self.settings.notification_volume)
        self.window.set_notification_sound_file(self.settings.notification_sound_file_path)
        self.window.set_autostart_enabled(self.settings.autostart_enabled)
        self.window.set_scheduler_notification_enabled(self.settings.scheduler_notification_enabled)
        self.window.set_client_calls_notification_enabled(self.settings.client_calls_notification_enabled)
        self.window.set_client_calls_volume(self.settings.client_calls_volume)
        self.window.set_client_calls_voice_message_volume(self.settings.client_calls_voice_message_volume)
        self.window.set_client_calls_speech_rate(self.settings.client_calls_speech_rate)
        self.window.set_client_calls_file(self.settings.client_calls_file_path)
        self.window.set_client_calls_voice_message_file(self.settings.client_calls_voice_message_file_path)
        self.window.set_client_calls_interval(self.settings.client_calls_interval_seconds)
        self.window.set_client_calls_repeat_enabled(self.settings.client_calls_repeat_enabled)
        self.window.set_client_calls_repeat_interval(self.settings.client_calls_repeat_interval_seconds)
        self.window.set_client_calls_repeat_notification_enabled(self.settings.client_calls_repeat_notification_enabled)
        self.window.set_employees_file(self.settings.employees_file_path)
        self.window.set_generator_api_file(self.settings.generator_api_file_path)
        self.window.set_generator_volume(self.settings.generator_volume)
        self.window.set_client_calls_text_voice_preview_playing(False)
        self.window.set_scheduler_weekdays(self.settings.scheduler_weekdays)
        language_labels = [language.label for language in self.voice_maker_service.get_languages()]
        self.window.set_client_calls_text_language_options(
            language_labels,
            self._language_label_by_code(self.settings.client_calls_text_language_code or "ru-RU"),
        )
        self.window.set_generator_language_options(
            language_labels,
            self._language_label_by_code(self.settings.generator_language_code),
        )
        self._refresh_devices()
        self._refresh_generator_voices(show_errors=False)
        self._refresh_client_calls_text_voices(show_errors=False)
        self._refresh_schedule_list()
        self._refresh_employees_list()
        self._refresh_client_calls_queue(None, [], 0.0)
        self.platform_integration.start()
        self.scheduler.start()
        self.client_call_service.start()

    def _refresh_devices(self) -> None:
        device_names = self.device_service.refresh_output_device_names()
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
        self._refresh_devices()
        self.root.update_idletasks()

    def _refresh_schedule_list(self) -> None:
        entries = self.schedule_manager.get_all()
        self.window.fill_schedule_list(entries)
        self.repository.save_schedule(entries)

    def browse_file(self) -> None:
        file_path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.wav;*.mp3;*.flac;*.ogg")]
        )
        if file_path:
            self.window.set_selected_file(file_path)

    def browse_client_calls_file(self) -> None:
        file_path = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            self.window.set_client_calls_file(file_path)
            self.settings.client_calls_file_path = file_path
            self.repository.save_settings(self.settings)

    def browse_client_calls_voice_message_file(self) -> None:
        file_path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.wav;*.mp3;*.flac;*.ogg"), ("All Files", "*.*")]
        )
        if file_path:
            self.window.set_client_calls_voice_message_file(file_path)
            self._update_setting("client_calls_voice_message_file_path", file_path)

    def browse_employees_file(self) -> None:
        file_path = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            self.window.set_employees_file(file_path)
            self._update_setting("employees_file_path", file_path)
            self._refresh_employees_list()

    def browse_notification_sound_file(self) -> None:
        file_path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.wav;*.mp3;*.flac;*.ogg"), ("All Files", "*.*")]
        )
        if file_path:
            self.window.set_notification_sound_file(file_path)
            self._update_setting("notification_sound_file_path", file_path)

    def browse_generator_api_file(self) -> None:
        file_path = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file_path:
            self.window.set_generator_api_file(file_path)
            self._update_setting("generator_api_file_path", file_path)
            self._refresh_generator_voices(show_errors=False)
            self._refresh_client_calls_text_voices(show_errors=False)

    def play_notification_sound(self) -> None:
        try:
            ValidationService.validate_optional_file(
                self.window.get_notification_sound_file(),
                "Сначала выберите файл звука уведомления",
            )
        except ValidationError as error:
            self.window.show_error(str(error))
            return

        device_name = self.settings.selected_device or self.settings.client_calls_selected_device
        self.playback_coordinator.enqueue(
            PlaybackTask(
                file_path=self.window.get_notification_sound_file(),
                volume=self.settings.notification_volume,
                device_name=device_name,
                on_error=lambda msg: self.window.show_error(msg),
            )
        )

    def add_schedule(self) -> None:
        try:
            file_path = self.window.get_selected_file()
            ValidationService.validate_file(file_path)

            hours, minutes = self.window.get_time_input()
            time_str = ValidationService.validate_time(hours, minutes)

            self.schedule_manager.add_entry(time_str, file_path)
            self._refresh_schedule_list()

        except ValidationError as e:
            self.window.show_error(str(e))


    def delete_schedule(self) -> None:
        try:
            entry_id = self.window.get_selected_entry_id()
            if not entry_id:
                raise ValidationError("Выберите запись для удаления")

            self.schedule_manager.delete_entry(entry_id)
            self._refresh_schedule_list()

        except ValidationError as e:
            self.window.show_error(str(e))


    def load_selected_entry_into_form(self) -> None:
        entry_id = self.window.get_selected_entry_id()
        if not entry_id:
            return

        entry = self.schedule_manager.get_by_id(entry_id)
        if not entry:
            return

        self.window.set_time_input(entry.time_str)
        self.window.set_selected_file(entry.file_path)

    def play_selected_or_current(self) -> None:
        if self.playback_coordinator.is_actively_playing:
            self.stop_audio()
            return

        file_path = self.window.get_selected_file()
        if not file_path:
            entry_id = self.window.get_selected_entry_id()
            if not entry_id:
                self.window.show_error("Выберите файл или запись из расписания")
                return

            entry = self.schedule_manager.get_by_id(entry_id)
            if not entry:
                self.window.show_error("Запись не найдена")
                return

            file_path = entry.file_path

        self._play_file(file_path)

    def _play_file(self, file_path: str) -> None:
        if not self.settings.selected_device:
            self.window.show_error("Не выбрано аудиоустройство")
            return

        self._enqueue_with_optional_notification(
            main_task=PlaybackTask(
                file_path=file_path,
                volume=self.settings.volume,
                device_name=self.settings.selected_device,
                on_error=lambda msg: self.window.show_error(msg),
            ),
            notification_enabled=self.settings.scheduler_notification_enabled,
            notification_device_name=self.settings.selected_device,
            notification_volume=self.settings.notification_volume,
        )

    def stop_audio(self) -> None:
        self.playback_coordinator.stop()

    def change_device(self, device_name: str) -> None:
        self._update_setting("selected_device", device_name)

    def change_volume(self, volume: float) -> None:
        self._update_setting("volume", volume)

    def change_notification_volume(self, volume: float) -> None:
        self._update_setting("notification_volume", volume)

    def _run_scheduled_entry(self, entry) -> None:
        self._play_file(entry.file_path)

    def change_client_calls_device(self, device_name: str) -> None:
        self._update_setting("client_calls_selected_device", device_name)

    def change_client_calls_voice_message_device(self, device_name: str) -> None:
        self._update_setting("client_calls_voice_message_selected_device", device_name)

    def change_client_calls_volume(self, volume: float) -> None:
        self._update_setting("client_calls_volume", volume)

    def change_client_calls_voice_message_volume(self, volume: float) -> None:
        self._update_setting("client_calls_voice_message_volume", volume)

    def change_client_calls_speech_rate(self, speech_rate: float) -> None:
        self._update_setting("client_calls_speech_rate", speech_rate)

    def change_client_calls_interval(self) -> None:
        if not self._sync_client_calls_interval(show_errors=True):
            return

    def change_client_calls_repeat_enabled(self) -> None:
        self._update_setting("client_calls_repeat_enabled", self.window.is_client_calls_repeat_enabled())

    def change_client_calls_repeat_interval(self) -> None:
        if not self._sync_client_calls_repeat_interval(show_errors=True):
            return

    def change_client_calls_text_language(self, language_label: str) -> None:
        language_code = self._language_code_by_label(language_label)
        self._update_setting("client_calls_text_language_code", language_code)
        self._update_setting("client_calls_text_voice", "")
        self.settings.client_calls_text_voice_id = ""
        self.repository.save_settings(self.settings)
        self._client_calls_text_voice_preview_signature = ""
        self._client_calls_text_voice_preview_bytes = None
        self._refresh_client_calls_text_voices(show_errors=True)

    def change_client_calls_text_voice(self, voice_label: str) -> None:
        voice = self._client_calls_text_voices_by_label.get(voice_label)
        self._update_setting("client_calls_text_voice", voice_label)
        self._client_calls_text_voice_preview_signature = ""
        self._client_calls_text_voice_preview_bytes = None
        if voice is not None:
            self.settings.client_calls_text_voice_id = voice.voice_id
            self.settings.client_calls_text_language_code = voice.language_code or self.settings.client_calls_text_language_code
            self.repository.save_settings(self.settings)

    def change_generator_device(self, device_name: str) -> None:
        self._update_setting("generator_selected_device", device_name)

    def change_generator_volume(self, volume: float) -> None:
        self._update_setting("generator_volume", volume)

    def change_generator_language(self, language_label: str) -> None:
        language_code = self._language_code_by_label(language_label)
        self._update_setting("generator_language_code", language_code)
        self._refresh_generator_voices(show_errors=True)

    def change_generator_voice(self, voice_label: str) -> None:
        voice = self._generator_voices_by_label.get(voice_label)
        if voice is not None:
            self.settings.generator_voice_id = voice.voice_id
        self._update_setting("generator_voice", voice_label)
        if voice is not None:
            self.repository.save_settings(self.settings)

    def request_client_calls_text_voices(self) -> None:
        self._refresh_client_calls_text_voices(show_errors=True)

    def change_autostart_enabled(self) -> None:
        enabled = self.window.is_autostart_enabled()
        try:
            self.autostart_service.set_enabled(enabled)
        except Exception as error:
            self.window.show_error(f"Не удалось изменить автозапуск: {error}")
            self.window.set_autostart_enabled(self.settings.autostart_enabled)
            return

        self._update_setting("autostart_enabled", enabled)

    def change_scheduler_notification_enabled(self) -> None:
        if not self._sync_notification_settings(
            enabled=self.window.is_scheduler_notification_enabled(),
            field_name="scheduler_notification_enabled",
            reset=lambda: self.window.set_scheduler_notification_enabled(self.settings.scheduler_notification_enabled),
        ):
            return

    def change_client_calls_notification_enabled(self) -> None:
        if not self._sync_notification_settings(
            enabled=self.window.is_client_calls_notification_enabled(),
            field_name="client_calls_notification_enabled",
            reset=lambda: self.window.set_client_calls_notification_enabled(self.settings.client_calls_notification_enabled),
        ):
            return

    def change_client_calls_repeat_notification_enabled(self) -> None:
        if not self._sync_notification_settings(
            enabled=self.window.is_client_calls_repeat_notification_enabled(),
            field_name="client_calls_repeat_notification_enabled",
            reset=lambda: self.window.set_client_calls_repeat_notification_enabled(
                self.settings.client_calls_repeat_notification_enabled
            ),
        ):
            return

    def change_scheduler_weekdays(self) -> None:
        weekdays = self.window.get_scheduler_weekdays()
        if not weekdays:
            self.window.show_error("Выберите хотя бы один день недели для планировщика")
            self.window.set_scheduler_weekdays(self.settings.scheduler_weekdays)
            return

        self._update_setting("scheduler_weekdays", weekdays)


    def _refresh_client_calls_queue(self, current_call: ClientCall | None, calls: list[ClientCall], progress: float) -> None:
        self.window.render_client_calls(current_call, calls, progress)

    def show_generator_window(self) -> None:
        self.window.show_generator_window()
        self._refresh_generator_voices(show_errors=True)

    def show_employees_window(self) -> None:
        self._refresh_employees_list()
        self.window.show_employees_window()

    def request_generator_voices(self) -> None:
        self._refresh_generator_voices(show_errors=True)

    def preview_client_calls_text_voice(self) -> None:
        if self._client_calls_text_voice_preview_playing:
            self._stop_client_calls_text_voice_preview()
            return

        if self._client_calls_text_voice_preview_busy:
            return

        try:
            ValidationService.validate_optional_file(
                self.settings.generator_api_file_path,
                "Сначала выберите .txt файл с API ключом генератора",
            )
        except ValidationError as error:
            self.window.show_error(str(error))
            return

        if not self.settings.generator_selected_device:
            self.window.show_error("Выберите аудиоустройство для генератора")
            return

        voice_id = self.settings.client_calls_text_voice_id or self.settings.generator_voice_id
        if not voice_id:
            self.window.show_error("Сначала выберите голос для произвольного текста")
            return

        signature = self._build_client_calls_text_voice_preview_signature()
        if self._client_calls_text_voice_preview_bytes and signature == self._client_calls_text_voice_preview_signature:
            self._play_client_calls_text_voice_preview(self._client_calls_text_voice_preview_bytes)
            return

        self._client_calls_text_voice_preview_busy = True
        self.window.set_client_calls_text_voice_preview_playing(True)
        thread = threading.Thread(target=self._preview_client_calls_text_voice_worker, daemon=True)
        thread.start()

    def _preview_client_calls_text_voice_worker(self) -> None:
        try:
            generated_audio = self.voice_maker_service.generate_mp3(
                api_key=self._read_generator_api_key(),
                text=self.CLIENT_CALLS_TEXT_VOICE_PREVIEW_TEXT,
                voice_id=self.settings.client_calls_text_voice_id or self.settings.generator_voice_id,
                language_code=(
                    self.settings.client_calls_text_language_code
                    or "ru-RU"
                ),
            )
        except Exception as error:
            error_message = str(error)
            self.root.after(0, lambda message=error_message: self._finish_client_calls_text_voice_preview_error(message))
            return

        self.root.after(0, lambda: self._finish_client_calls_text_voice_preview_success(generated_audio))

    def _finish_client_calls_text_voice_preview_success(self, generated_audio: bytes) -> None:
        self._client_calls_text_voice_preview_busy = False
        self._client_calls_text_voice_preview_bytes = generated_audio
        self._client_calls_text_voice_preview_signature = self._build_client_calls_text_voice_preview_signature()
        self._play_client_calls_text_voice_preview(generated_audio)

    def _finish_client_calls_text_voice_preview_error(self, message: str) -> None:
        self._client_calls_text_voice_preview_busy = False
        self._client_calls_text_voice_preview_playing = False
        self.window.set_client_calls_text_voice_preview_playing(False)
        self.window.show_error(f"Не удалось воспроизвести тест голоса: {message}")

    def _play_client_calls_text_voice_preview(self, audio_bytes: bytes) -> None:
        self._cleanup_client_calls_text_voice_preview_file()
        temp_fd, temp_path = tempfile.mkstemp(suffix=".mp3")
        with os.fdopen(temp_fd, "wb") as temp_file:
            temp_file.write(audio_bytes)

        self._client_calls_text_voice_preview_temp_path = temp_path
        self._client_calls_text_voice_preview_playing = True
        self.window.set_client_calls_text_voice_preview_playing(True)
        self.generator_preview_player.play_async(
            file_path=temp_path,
            volume=min(self.settings.generator_volume * 2.0, 1.0),
            device_name=self.settings.generator_selected_device,
            on_error=lambda message: self.root.after(
                0, lambda msg=message: self._handle_client_calls_text_voice_preview_finished(error_message=msg)
            ),
            on_finished=lambda: self.root.after(0, self._handle_client_calls_text_voice_preview_finished),
        )

    def _stop_client_calls_text_voice_preview(self) -> None:
        self.generator_preview_player.stop()
        self._handle_client_calls_text_voice_preview_finished()

    def _handle_client_calls_text_voice_preview_finished(self, error_message: str = "") -> None:
        self._client_calls_text_voice_preview_playing = False
        self.window.set_client_calls_text_voice_preview_playing(False)
        self._cleanup_client_calls_text_voice_preview_file()
        if error_message:
            self.window.show_error(f"Не удалось воспроизвести тест голоса: {error_message}")

    def generate_ai_speech(self) -> None:
        if self._generator_busy:
            return

        try:
            ValidationService.validate_optional_file(
                self.settings.generator_api_file_path,
                "Сначала выберите .txt файл с API ключом генератора",
            )
        except ValidationError as error:
            self.window.show_error(str(error))
            return

        text = self.window.get_generator_text()
        if not text.strip():
            self.window.show_error("Введите текст для генерации")
            return
        if not self.settings.generator_selected_device:
            self.window.show_error("Выберите аудиоустройство для генератора")
            return

        request_signature = self._build_generator_request_signature(text)
        if self._generated_voice_bytes and request_signature == self._generated_voice_signature:
            self._play_generated_audio(self._generated_voice_bytes)
            return

        self._generator_busy = True
        thread = threading.Thread(target=self._generate_ai_speech_worker, args=(text,), daemon=True)
        thread.start()

    def _generate_ai_speech_worker(self, text: str) -> None:
        try:
            api_key = self._read_generator_api_key()
            generated_audio = self.voice_maker_service.generate_mp3(
                api_key=api_key,
                text=text,
                voice_id=self.settings.generator_voice_id,
                language_code=self.settings.generator_language_code,
            )
        except Exception as error:
            error_message = str(error)
            self.root.after(0, lambda message=error_message: self._finish_generator_error(message))
            return

        self.root.after(0, lambda: self._finish_generator_success(generated_audio))

    def _finish_generator_success(self, generated_audio: bytes) -> None:
        self._generator_busy = False
        self._generated_voice_bytes = generated_audio
        self._generated_voice_signature = self._build_generator_request_signature(self.window.get_generator_text())
        self._play_generated_audio(generated_audio)

    def _finish_generator_error(self, message: str) -> None:
        self._generator_busy = False
        self.window.show_error(f"Не удалось сгенерировать речь: {message}")

    def _play_generated_audio(self, audio_bytes: bytes) -> None:
        device_name = self.settings.generator_selected_device
        if not device_name:
            self.window.show_error("Не выбрано аудиоустройство для генератора")
            return

        temp_fd, temp_path = tempfile.mkstemp(suffix=".mp3")
        with os.fdopen(temp_fd, "wb") as temp_file:
            temp_file.write(audio_bytes)

        self.playback_coordinator.enqueue(
            PlaybackTask(
                file_path=temp_path,
                volume=min(self.settings.generator_volume * 2.0, 1.0),
                device_name=device_name,
                cleanup_file=True,
                on_error=lambda msg: self.window.show_error(msg),
            )
        )

    def save_generated_ai_speech(self) -> None:
        if not self._generated_voice_bytes:
            self.window.show_error("Сначала сгенерируйте речь")
            return

        suggested_name = self.window.get_generator_file_name().strip().replace(" ", "_") or "generated_voice"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            initialfile=f"{suggested_name}.mp3",
            filetypes=[("MP3 Files", "*.mp3")],
        )
        if not file_path:
            return

        try:
            with open(file_path, "wb") as output_file:
                output_file.write(self._generated_voice_bytes)
        except OSError as error:
            self.window.show_error(f"Не удалось сохранить файл: {error}")

    def add_employee(self) -> None:
        try:
            ValidationService.validate_optional_file(
                self.settings.employees_file_path,
                "Сначала выберите файл списка сотрудников",
            )
            ValidationService.validate_optional_file(
                self.settings.generator_api_file_path,
                "Сначала выберите .txt файл с API ключом генератора",
            )
        except ValidationError as error:
            self.window.show_error(str(error))
            return

        employee_name = self._normalize_employee_name(self.window.get_employee_input())
        if not employee_name:
            self.window.show_error("Введите Имя Фамилию сотрудника")
            return
        if not self.settings.generator_voice_id:
            self.window.show_error("Сначала выберите голос генератора")
            return

        existing_employees = self._read_employees_file()
        if employee_name in existing_employees:
            self.window.show_error("Такой сотрудник уже есть в списке")
            return

        self._append_employee_to_file(employee_name)
        self.window.clear_employee_input()
        self._refresh_employees_list()
        self.window.focus_employees_list()
        self._employee_generation_in_progress.add(employee_name)
        thread = threading.Thread(target=self._add_employee_worker, args=(employee_name,), daemon=True)
        thread.start()

    def _add_employee_worker(self, employee_name: str) -> None:
        try:
            api_key = self._read_generator_api_key()
            generated_audio = self.voice_maker_service.generate_mp3(
                api_key=api_key,
                text=employee_name,
                voice_id=self.settings.generator_voice_id,
                language_code=self.settings.generator_language_code,
            )
            self._write_worker_audio(employee_name, generated_audio)
        except Exception as error:
            error_message = str(error)
            self.root.after(0, lambda message=error_message, name=employee_name: self._finish_add_employee_error(name, message))
            return

        self.root.after(0, lambda name=employee_name: self._finish_add_employee_success(name))

    def _finish_add_employee_success(self, employee_name: str) -> None:
        self._employee_generation_in_progress.discard(employee_name)

    def _finish_add_employee_error(self, employee_name: str, message: str) -> None:
        self._employee_generation_in_progress.discard(employee_name)
        self.window.show_error(
            f"Сотрудник добавлен в список, но не удалось создать его аудио: {message}"
        )

    def delete_employee(self) -> None:
        try:
            ValidationService.validate_optional_file(
                self.settings.employees_file_path,
                "Сначала выберите файл списка сотрудников",
            )
        except ValidationError as error:
            self.window.show_error(str(error))
            return

        employee_name = self._normalize_employee_name(self.window.get_selected_employee())
        if not employee_name:
            self.window.show_error("Выберите сотрудника для удаления")
            return

        employees = self._read_employees_file()
        filtered = [item for item in employees if item != employee_name]
        self._write_employees_file(filtered)
        self._delete_worker_audio(employee_name)
        self._refresh_employees_list()

    def preview_employee(self) -> None:
        employee_name = self._normalize_employee_name(self.window.get_selected_employee())
        if not employee_name:
            self.window.show_error("Выберите сотрудника для воспроизведения")
            return

        worker_audio_path = self.recorded_call_builder.get_worker_audio_path(employee_name)
        if not worker_audio_path or not os.path.exists(worker_audio_path):
            self.window.show_error("Для этого сотрудника не найден аудиофайл")
            return

        if not self.settings.generator_selected_device:
            self.window.show_error("Выберите аудиоустройство для генератора")
            return

        self.generator_preview_player.play_async(
            file_path=worker_audio_path,
            volume=min(self.settings.generator_volume * 2.0, 1.0),
            device_name=self.settings.generator_selected_device,
            on_error=lambda message: self.root.after(
                0, lambda msg=message: self.window.show_error(f"Не удалось воспроизвести сотрудника: {msg}")
            ),
        )

    def _refresh_employees_list(self) -> None:
        employees = self._read_employees_file() if self.settings.employees_file_path else []
        self.window.fill_employees_list(employees)

    def _read_generator_api_key(self) -> str:
        with open(self.settings.generator_api_file_path, "r", encoding="utf-8") as file:
            for line in file:
                key = line.strip()
                if key:
                    if key.lower().startswith("bearer "):
                        return key[7:].strip()
                    return key
        raise RuntimeError("В файле API генератора не найден ключ")

    def _build_generator_request_signature(self, text: str) -> str:
        return "|".join(
            [
                self.settings.generator_language_code.strip(),
                self.settings.generator_voice_id.strip(),
                text.strip(),
            ]
        )

    def _build_client_calls_text_voice_preview_signature(self) -> str:
        return "|".join(
            [
                (self.settings.client_calls_text_language_code or "ru-RU").strip(),
                (self.settings.client_calls_text_voice_id or self.settings.generator_voice_id).strip(),
                self.CLIENT_CALLS_TEXT_VOICE_PREVIEW_TEXT,
            ]
        )

    def _cleanup_client_calls_text_voice_preview_file(self) -> None:
        if not self._client_calls_text_voice_preview_temp_path:
            return
        if os.path.exists(self._client_calls_text_voice_preview_temp_path):
            try:
                os.remove(self._client_calls_text_voice_preview_temp_path)
            except OSError:
                pass
        self._client_calls_text_voice_preview_temp_path = None

    def _refresh_generator_voices(self, show_errors: bool) -> None:
        if self._generator_voices_loading:
            return
        if not self.settings.generator_api_file_path:
            self._set_generator_voice_options([], "")
            return

        self._generator_voices_loading = True
        thread = threading.Thread(
            target=self._refresh_generator_voices_worker,
            args=(show_errors,),
            daemon=True,
        )
        thread.start()

    def _refresh_generator_voices_worker(self, show_errors: bool) -> None:
        try:
            api_key = self._read_generator_api_key()
            voices = self.voice_maker_service.list_voices(api_key, self.settings.generator_language_code)
        except Exception as error:
            error_message = str(error)
            self.root.after(
                0,
                lambda message=error_message: self._finish_refresh_generator_voices([], show_errors, message),
            )
            return

        self.root.after(0, lambda: self._finish_refresh_generator_voices(voices, show_errors, ""))

    def _refresh_client_calls_text_voices(self, show_errors: bool) -> None:
        if self._client_calls_text_voices_loading:
            return
        if not self.settings.generator_api_file_path:
            self.window.set_client_calls_text_voice_options([], "")
            return

        self._client_calls_text_voices_loading = True
        thread = threading.Thread(
            target=self._refresh_client_calls_text_voices_worker,
            args=(show_errors,),
            daemon=True,
        )
        thread.start()

    def _refresh_client_calls_text_voices_worker(self, show_errors: bool) -> None:
        try:
            api_key = self._read_generator_api_key()
            voices = self.voice_maker_service.list_voices(
                api_key,
                self.settings.client_calls_text_language_code or "ru-RU",
            )
        except Exception as error:
            error_message = str(error)
            self.root.after(
                0,
                lambda message=error_message: self._finish_refresh_client_calls_text_voices([], show_errors, message),
            )
            return

        self.root.after(0, lambda: self._finish_refresh_client_calls_text_voices(voices, show_errors, ""))

    def _finish_refresh_client_calls_text_voices(
        self,
        voices: list[VoiceMakerVoice],
        show_errors: bool,
        error_message: str,
    ) -> None:
        self._client_calls_text_voices_loading = False
        if error_message:
            if show_errors:
                self.window.show_error(f"Не удалось загрузить голоса VoiceMaker: {error_message}")
            self._client_calls_text_voices_by_label = {}
            self.window.set_client_calls_text_voice_options([], "")
            return

        if not voices:
            if show_errors:
                self.window.show_error("VoiceMaker не вернул ни одного голоса для выбранного языка")
            self._client_calls_text_voices_by_label = {}
            self.window.set_client_calls_text_voice_options([], "")
            return

        self._client_calls_text_voices_by_label = {voice.label: voice for voice in voices}
        labels = [voice.label for voice in voices]
        selected_label = (
            self.settings.client_calls_text_voice
            if self.settings.client_calls_text_voice in self._client_calls_text_voices_by_label
            else ""
        )
        if not selected_label and labels:
            selected_label = labels[0]
            selected_voice = self._client_calls_text_voices_by_label[selected_label]
            self.settings.client_calls_text_voice = selected_label
            self.settings.client_calls_text_voice_id = selected_voice.voice_id
            self.settings.client_calls_text_language_code = selected_voice.language_code or "ru-RU"
            self.repository.save_settings(self.settings)

        self.window.set_client_calls_text_voice_options(labels, selected_label)

    def _finish_refresh_generator_voices(
        self,
        voices: list[VoiceMakerVoice],
        show_errors: bool,
        error_message: str,
    ) -> None:
        self._generator_voices_loading = False
        if error_message:
            if show_errors:
                self.window.show_error(f"Не удалось загрузить голоса VoiceMaker: {error_message}")
            self._generator_voices_by_label = {}
            self._set_generator_voice_options([], "")
            return

        if not voices:
            if show_errors:
                self.window.show_error("VoiceMaker не вернул ни одного голоса для выбранного языка")
            self._generator_voices_by_label = {}
            self._set_generator_voice_options([], "")
            return

        self._generator_voices_by_label = {voice.label: voice for voice in voices}
        labels = [voice.label for voice in voices]
        selected_label = self.settings.generator_voice if self.settings.generator_voice in self._generator_voices_by_label else ""
        if not selected_label and labels:
            selected_label = labels[0]
            selected_voice = self._generator_voices_by_label[selected_label]
            self.settings.generator_voice = selected_label
            self.settings.generator_voice_id = selected_voice.voice_id
            self.repository.save_settings(self.settings)

        self._set_generator_voice_options(labels, selected_label)

    def _set_generator_voice_options(self, labels: list[str], selected_label: str) -> None:
        self.window.set_generator_voice_options(labels, selected_label)

    def _language_code_by_label(self, label: str) -> str:
        for language in self.voice_maker_service.get_languages():
            if language.label == label:
                return language.code
        return "ru-RU"

    def _language_label_by_code(self, code: str) -> str:
        for language in self.voice_maker_service.get_languages():
            if language.code == code:
                return language.label
        return "Русский"

    def _read_employees_file(self) -> list[str]:
        if not self.settings.employees_file_path or not os.path.exists(self.settings.employees_file_path):
            return []
        with open(self.settings.employees_file_path, "r", encoding="utf-8") as file:
            employees: list[str] = []
            for line in file:
                employee_name = self._normalize_employee_name(line)
                if employee_name:
                    employees.append(employee_name)
            return employees

    def _append_employee_to_file(self, employee_name: str) -> None:
        with open(self.settings.employees_file_path, "a", encoding="utf-8") as file:
            file.write(f"{employee_name}\n")

    def _write_employees_file(self, employees: list[str]) -> None:
        with open(self.settings.employees_file_path, "w", encoding="utf-8") as file:
            for employee_name in employees:
                file.write(f"{employee_name}\n")

    def _write_worker_audio(self, employee_name: str, audio_bytes: bytes) -> None:
        workers_dir = os.path.join(self.recorded_call_builder.audio_root, "workers")
        os.makedirs(workers_dir, exist_ok=True)
        worker_path = os.path.join(workers_dir, f"{self._employee_audio_stem(employee_name)}.mp3")
        with open(worker_path, "wb") as audio_file:
            audio_file.write(audio_bytes)

    def _delete_worker_audio(self, employee_name: str) -> None:
        workers_dir = os.path.join(self.recorded_call_builder.audio_root, "workers")
        if not os.path.isdir(workers_dir):
            return

        normalized_stem = self._normalized_employee_audio_stem(employee_name)
        for extension in (".mp3", ".wav"):
            worker_path = os.path.join(workers_dir, f"{self._employee_audio_stem(employee_name)}{extension}")
            if os.path.exists(worker_path):
                os.remove(worker_path)
                return

        for file_name in os.listdir(workers_dir):
            file_path = os.path.join(workers_dir, file_name)
            if not os.path.isfile(file_path):
                continue
            stem, extension = os.path.splitext(file_name)
            if extension.lower() not in {".mp3", ".wav"}:
                continue
            if self._normalized_employee_audio_stem(stem) == normalized_stem:
                os.remove(file_path)
                return

    def _employee_audio_stem(self, employee_name: str) -> str:
        normalized = self._normalize_employee_name(employee_name)
        parts = normalized.split()
        if len(parts) >= 2:
            normalized = f"{parts[0]}_{parts[1]}"
        else:
            normalized = normalized.replace(" ", "_")
        return normalized.replace(" ", "_")

    def _normalized_employee_audio_stem(self, employee_name: str) -> str:
        return unicodedata.normalize("NFKC", self._employee_audio_stem(employee_name)).casefold()

    def _normalize_employee_name(self, employee_name: str) -> str:
        normalized = unicodedata.normalize("NFKC", employee_name or "")
        return " ".join(normalized.split())

    def _build_client_call_text_audio_file(self, text: str) -> str:
        if not self.settings.generator_api_file_path:
            raise RuntimeError("Сначала выберите .txt файл с API ключом генератора")

        voice_id = self.settings.client_calls_text_voice_id or self.settings.generator_voice_id
        if not voice_id:
            raise RuntimeError("Сначала выберите голос для текстовых сообщений")

        language_code = (
            self.settings.client_calls_text_language_code
            or "ru-RU"
        )
        generated_audio = self.voice_maker_service.generate_mp3(
            api_key=self._read_generator_api_key(),
            text=text,
            voice_id=voice_id,
            language_code=language_code,
        )
        temp_fd, temp_path = tempfile.mkstemp(suffix=".mp3")
        with os.fdopen(temp_fd, "wb") as temp_file:
            temp_file.write(generated_audio)
        return temp_path

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
        self._cleanup_client_calls_text_voice_preview_file()
        self._sync_client_calls_interval(show_errors=False)
        self._save_main_window_geometry()
        self.scheduler.stop()
        self.playback_coordinator.reset()
        self.client_call_service.stop()
        self.platform_integration.cleanup()
        self.root.destroy()

    def _sync_client_calls_interval(self, show_errors: bool) -> bool:
        try:
            interval = ValidationService.validate_interval(self.window.get_client_calls_interval())
        except ValidationError as error:
            if show_errors:
                self.window.show_error(str(error))
                self.window.set_client_calls_interval(self.settings.client_calls_interval_seconds)
            return False

        self.settings.client_calls_interval_seconds = interval
        self.window.set_client_calls_interval(interval)
        self.repository.save_settings(self.settings)
        return True

    def _sync_client_calls_repeat_interval(self, show_errors: bool) -> bool:
        try:
            interval = ValidationService.validate_interval(self.window.get_client_calls_repeat_interval())
        except ValidationError as error:
            if show_errors:
                self.window.show_error(str(error))
                self.window.set_client_calls_repeat_interval(self.settings.client_calls_repeat_interval_seconds)
            return False

        self.settings.client_calls_repeat_interval_seconds = interval
        self.window.set_client_calls_repeat_interval(interval)
        self.repository.save_settings(self.settings)
        return True

    def _sync_notification_settings(self, enabled: bool, field_name: str, reset) -> bool:
        if enabled:
            try:
                ValidationService.validate_optional_file(
                    self.window.get_notification_sound_file(),
                    "Сначала выберите файл звука уведомления",
                )
            except ValidationError as error:
                self.window.show_error(str(error))
                reset()
                return False

        self._update_setting(field_name, enabled)
        return True

    def _enqueue_with_optional_notification(
        self,
        main_task: PlaybackTask,
        notification_enabled: bool,
        notification_device_name: str,
        notification_volume: float,
    ) -> None:
        if notification_enabled:
            try:
                ValidationService.validate_optional_file(
                    self.settings.notification_sound_file_path,
                    "Сначала выберите файл звука уведомления",
                )
            except ValidationError as error:
                if main_task.on_error:
                    main_task.on_error(str(error))
                return

            self.playback_coordinator.enqueue(
                PlaybackTask(
                    file_path=self.settings.notification_sound_file_path,
                    volume=notification_volume,
                    device_name=notification_device_name,
                    on_error=main_task.on_error,
                )
            )

        self.playback_coordinator.enqueue(main_task)

    def _update_setting(self, field_name: str, value) -> None:
        setattr(self.settings, field_name, value)
        self.repository.save_settings(self.settings)

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
