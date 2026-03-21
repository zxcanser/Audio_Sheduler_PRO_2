from tkinter import filedialog
import tkinter as tk

from config import CONFIG_FILE, SCHEDULE_FILE, WINDOW_TITLE
from models import ClientCall
from repository import JsonRepository
from services.audio_device_service import AudioDeviceService
from services.audio_player import AudioPlayer
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

        self.repository = JsonRepository(CONFIG_FILE, SCHEDULE_FILE)
        self.device_service = AudioDeviceService()
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
            on_trigger=self._run_scheduled_entry
        )
        self.client_call_service = ClientCallService(
            tk_root=root,
            playback_coordinator=self.playback_coordinator,
            synthesizer=self.speech_synthesizer,
            get_source_path=self.window.get_client_calls_file,
            get_device_name=lambda: self.settings.client_calls_selected_device,
            get_volume=lambda: self.settings.client_calls_volume,
            on_state_change=self._refresh_client_calls_queue,
            on_error=lambda message: self.window.show_error(message),
        )

        self._connect_events()
        self._load_initial_state()

    def _connect_events(self) -> None:
        self.window.on_browse = self.browse_file
        self.window.on_add = self.add_schedule
        self.window.on_edit = self.edit_schedule
        self.window.on_delete = self.delete_schedule
        self.window.on_toggle = self.toggle_schedule
        self.window.on_play = self.play_selected_or_current
        self.window.on_stop = self.stop_audio
        self.window.on_device_change = self.change_device
        self.window.on_volume_change = self.change_volume
        self.window.on_select_entry = self.load_selected_entry_into_form
        self.window.on_browse_client_calls_file = self.browse_client_calls_file
        self.window.on_client_calls_volume_change = self.change_client_calls_volume
        self.window.on_client_calls_device_change = self.change_client_calls_device
        self.window.on_client_calls_interval_change = self.change_client_calls_interval
        self.window.on_clear_client_calls_queue = self.clear_client_calls_queue
        self.window.on_close = self.handle_close_request
        self.window.on_window_unmap = self.handle_window_unmap

    def _load_initial_state(self) -> None:
        self.window.set_volume(self.settings.volume)
        self.window.set_client_calls_volume(self.settings.client_calls_volume)
        self.window.set_client_calls_file(self.settings.client_calls_file_path)
        self.window.set_client_calls_interval(self.settings.client_calls_interval_seconds)
        self._refresh_devices()
        self._refresh_schedule_list()
        self._refresh_client_calls_queue(None, [], 0.0)
        self.platform_integration.start()
        self.scheduler.start()
        self.client_call_service.start()

    def _refresh_devices(self) -> None:
        device_names = self.device_service.get_output_device_names()
        self.window.set_device_options(device_names, self.settings.selected_device)
        self.window.set_client_calls_device_options(device_names, self.settings.client_calls_selected_device)

        if self.window.device_var.get():
            self.settings.selected_device = self.window.device_var.get()
        if self.window.client_calls_device_var.get():
            self.settings.client_calls_selected_device = self.window.client_calls_device_var.get()
        self.repository.save_settings(self.settings)

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

    def add_schedule(self) -> None:
        try:
            file_path = self.window.get_selected_file()
            ValidationService.validate_file(file_path)

            hours, minutes = self.window.get_time_input()
            time_str = ValidationService.validate_time(hours, minutes)

            self.schedule_manager.add_entry(time_str, file_path)
            self._refresh_schedule_list()
            self.window.clear_time_input()

        except ValidationError as e:
            self.window.show_error(str(e))

    def edit_schedule(self) -> None:
        try:
            entry_id = self.window.get_selected_entry_id()
            if not entry_id:
                raise ValidationError("Выберите запись для редактирования")

            file_path = self.window.get_selected_file()
            ValidationService.validate_file(file_path)

            hours, minutes = self.window.get_time_input()
            time_str = ValidationService.validate_time(hours, minutes)

            self.schedule_manager.update_entry(entry_id, time_str, file_path)
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

    def toggle_schedule(self) -> None:
        try:
            entry_id = self.window.get_selected_entry_id()
            if not entry_id:
                raise ValidationError("Выберите запись")

            self.schedule_manager.toggle_entry(entry_id)
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
        if self.playback_coordinator.is_busy:
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

        self.playback_coordinator.enqueue(
            PlaybackTask(
                file_path=file_path,
                volume=self.settings.volume,
                device_name=self.settings.selected_device,
                on_error=lambda msg: self.window.show_error(msg),
            )
        )

    def stop_audio(self) -> None:
        self.playback_coordinator.stop()

    def change_device(self, device_name: str) -> None:
        self.settings.selected_device = device_name
        self.repository.save_settings(self.settings)

    def change_volume(self, volume: float) -> None:
        self.settings.volume = volume
        self.repository.save_settings(self.settings)

    def _run_scheduled_entry(self, entry) -> None:
        self._play_file(entry.file_path)

    def change_client_calls_device(self, device_name: str) -> None:
        self.settings.client_calls_selected_device = device_name
        self.repository.save_settings(self.settings)

    def change_client_calls_volume(self, volume: float) -> None:
        self.settings.client_calls_volume = volume
        self.repository.save_settings(self.settings)

    def change_client_calls_interval(self) -> None:
        if not self._sync_client_calls_interval(show_errors=True):
            return

    def clear_client_calls_queue(self) -> None:
        self.client_call_service.clear_queue()

    def _refresh_client_calls_queue(self, current_call: ClientCall | None, calls: list[ClientCall], progress: float) -> None:
        self.window.render_client_calls(current_call, calls, progress)

    def handle_close_request(self) -> None:
        self.platform_integration.request_close()

    def handle_window_unmap(self) -> None:
        self.platform_integration.handle_window_unmap()

    def shutdown(self) -> None:
        self._sync_client_calls_interval(show_errors=False)
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
