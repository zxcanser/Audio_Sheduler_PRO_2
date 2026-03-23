from tkinter import filedialog
import tkinter as tk

from config import CONFIG_FILE, SCHEDULE_FILE, WINDOW_TITLE
from models import ClientCall
from repository import JsonRepository
from services.audio_device_service import AudioDeviceService
from services.audio_player import AudioPlayer
from services.autostart_service import AutostartService
from services.client_call_service import ClientCallService
from services.platform_integration import PlatformIntegration
from services.playback_coordinator import PlaybackCoordinator, PlaybackTask
from services.scheduler_service import SchedulerService
from services.schedule_manager import ScheduleManager
from services.speech_synthesizer import SpeechSynthesizerService
from services.validation_service import ValidationError, ValidationService
from ui.main_window import MainWindow


class AudioSchedulerController:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._save_geometry_after_id: str | None = None

        self.repository = JsonRepository(CONFIG_FILE, SCHEDULE_FILE)
        self.device_service = AudioDeviceService()
        self.autostart_service = AutostartService()
        self.player = AudioPlayer(self.device_service)
        self.playback_coordinator = PlaybackCoordinator(
            tk_root=root,
            player=self.player,
            get_interval_seconds=lambda: self.settings.client_calls_interval_seconds,
        )
        self.speech_synthesizer = SpeechSynthesizerService()
        self.platform_integration = PlatformIntegration(root, WINDOW_TITLE, self.shutdown)

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
            synthesizer=self.speech_synthesizer,
            get_source_path=self.window.get_client_calls_file,
            get_device_name=lambda: self.settings.client_calls_selected_device,
            get_volume=lambda: self.settings.client_calls_volume,
            get_speech_rate=lambda: self.settings.client_calls_speech_rate,
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
        self.window.on_client_calls_volume_change = self.change_client_calls_volume
        self.window.on_client_calls_speech_rate_change = self.change_client_calls_speech_rate
        self.window.on_client_calls_device_change = self.change_client_calls_device
        self.window.on_client_calls_interval_change = self.change_client_calls_interval
        self.window.on_scheduler_weekdays_change = self.change_scheduler_weekdays
        self.window.on_browse_notification_sound_file = self.browse_notification_sound_file
        self.window.on_play_notification_sound = self.play_notification_sound
        self.window.on_autostart_toggle = self.change_autostart_enabled
        self.window.on_scheduler_notification_toggle = self.change_scheduler_notification_enabled
        self.window.on_client_calls_notification_toggle = self.change_client_calls_notification_enabled
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
        self.window.set_client_calls_speech_rate(self.settings.client_calls_speech_rate)
        self.window.set_client_calls_file(self.settings.client_calls_file_path)
        self.window.set_client_calls_interval(self.settings.client_calls_interval_seconds)
        self.window.set_scheduler_weekdays(self.settings.scheduler_weekdays)
        self._refresh_devices()
        self._refresh_schedule_list()
        self._refresh_client_calls_queue(None, [], 0.0)
        self.platform_integration.start()
        self.scheduler.start()
        self.client_call_service.start()

    def _refresh_devices(self) -> None:
        device_names = self.device_service.refresh_output_device_names()
        self.window.set_device_options(device_names, self.settings.selected_device)
        self.window.set_client_calls_device_options(device_names, self.settings.client_calls_selected_device)

        if self.window.device_var.get():
            self.settings.selected_device = self.window.device_var.get()
        if self.window.client_calls_device_var.get():
            self.settings.client_calls_selected_device = self.window.client_calls_device_var.get()
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

    def browse_notification_sound_file(self) -> None:
        file_path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.wav;*.mp3;*.flac;*.ogg"), ("All Files", "*.*")]
        )
        if file_path:
            self.window.set_notification_sound_file(file_path)
            self._update_setting("notification_sound_file_path", file_path)

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

    def change_client_calls_volume(self, volume: float) -> None:
        self._update_setting("client_calls_volume", volume)

    def change_client_calls_speech_rate(self, speech_rate: float) -> None:
        self._update_setting("client_calls_speech_rate", speech_rate)

    def change_client_calls_interval(self) -> None:
        if not self._sync_client_calls_interval(show_errors=True):
            return

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

    def change_scheduler_weekdays(self) -> None:
        weekdays = self.window.get_scheduler_weekdays()
        if not weekdays:
            self.window.show_error("Выберите хотя бы один день недели для планировщика")
            self.window.set_scheduler_weekdays(self.settings.scheduler_weekdays)
            return

        self._update_setting("scheduler_weekdays", weekdays)


    def _refresh_client_calls_queue(self, current_call: ClientCall | None, calls: list[ClientCall], progress: float) -> None:
        self.window.render_client_calls(current_call, calls, progress)

    def handle_close_request(self) -> None:
        self.platform_integration.request_close()

    def handle_window_unmap(self) -> None:
        self.platform_integration.handle_window_unmap()

    def shutdown(self) -> None:
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
