import copy
import os
import secrets
import threading

from models import ClientCall
from services.validation_service import ValidationError, ValidationService


def change_client_calls_api_enabled(controller) -> None:
    if controller.window.is_client_calls_api_enabled() and not controller.settings.client_calls_api_token.strip():
        controller.settings.client_calls_api_token = secrets.token_hex(16)
        controller.repository.save_settings(controller.settings)
        controller.window.set_client_calls_api_token(controller.settings.client_calls_api_token)
    controller._sync_client_calls_api_server(show_errors=True)


def change_client_calls_api_host(controller) -> None:
    controller._sync_client_calls_api_server(show_errors=True)


def change_client_calls_api_port(controller) -> None:
    controller._sync_client_calls_api_server(show_errors=True)


def generate_client_calls_api_token(controller) -> None:
    controller.settings.client_calls_api_token = secrets.token_hex(16)
    controller.repository.save_settings(controller.settings)
    controller.window.set_client_calls_api_token(controller.settings.client_calls_api_token)
    controller._sync_client_calls_api_server(show_errors=True)


def _handle_api_call_request(controller, payload: dict) -> dict:
    completion_event = threading.Event()
    result: dict = {}

    def enqueue_on_ui_thread() -> None:
        try:
            call = controller._build_client_call_from_api_payload(payload)
            controller.client_call_service.enqueue_external_call(call)
            result.update(
                {
                    "message": "Вызов добавлен в очередь",
                    "call_id": call.call_id,
                    "display_text": call.display_text,
                }
            )
        except Exception as error:
            result["error"] = str(error)
        finally:
            completion_event.set()

    controller.root.after(0, enqueue_on_ui_thread)
    if not completion_event.wait(timeout=10.0):
        raise RuntimeError("Программа не ответила на API запрос вовремя")

    error_message = result.get("error")
    if error_message:
        raise RuntimeError(error_message)
    return result


def _build_client_call_from_api_payload(controller, payload: dict) -> ClientCall:
    payload_type = str(payload.get("type") or "").strip().lower()
    text_message = str(
        payload.get("text")
        or payload.get("message")
        or payload.get("speech_text")
        or ""
    ).strip()
    audio_file_path = str(
        payload.get("audio_file")
        or payload.get("audio_path")
        or payload.get("file_path")
        or ""
    ).strip()

    if payload_type == "text" or text_message:
        if not text_message:
            raise RuntimeError("Для текстового вызова нужно поле text")
        return ClientCall(
            start_choice="",
            car_number="",
            end_choice="",
            display_message=text_message,
            is_text_message=True,
            speech_text_override=text_message,
        )

    if payload_type == "audio" or audio_file_path:
        ValidationService.validate_optional_file(audio_file_path, "Для голосового сообщения нужно поле audio_file")
        display_message = str(payload.get("display_message") or "").strip() or os.path.basename(audio_file_path)
        return ClientCall(
            start_choice="",
            car_number="",
            end_choice="",
            display_message=display_message,
            audio_file_path=audio_file_path,
        )

    start_choice = str(payload.get("start_choice") or "").strip()
    car_number = str(payload.get("car_number") or "").strip()
    end_choice = str(payload.get("end_choice") or "").strip()
    if not (start_choice and car_number and end_choice):
        raise RuntimeError(
            "Для вызова по номеру нужны поля start_choice, car_number и end_choice"
        )

    display_message = str(payload.get("display_message") or "").strip() or controller.recorded_call_builder.build_display_text(
        start_choice,
        car_number,
        end_choice,
    )
    return ClientCall(
        start_choice=start_choice,
        car_number=car_number,
        end_choice=end_choice,
        display_message=display_message,
    )


def _sync_client_calls_api_server(controller, show_errors: bool) -> bool:
    previous_settings = copy.deepcopy(controller.settings)

    try:
        enabled = controller.window.is_client_calls_api_enabled()
        host = ValidationService.validate_host(controller.window.get_client_calls_api_host())
        port = ValidationService.validate_port(controller.window.get_client_calls_api_port())
    except ValidationError as error:
        if show_errors:
            controller.window.show_error(str(error))
        controller._restore_client_calls_api_settings(previous_settings)
        return False

    controller.settings.client_calls_api_enabled = enabled
    controller.settings.client_calls_api_host = host
    controller.settings.client_calls_api_port = port
    controller.repository.save_settings(controller.settings)
    controller._apply_client_calls_api_settings_to_window()

    try:
        if enabled:
            controller.call_api_server.start(
                host=host,
                port=port,
                token=controller.settings.client_calls_api_token,
            )
        else:
            controller.call_api_server.stop()
    except RuntimeError as error:
        controller._restore_client_calls_api_settings(previous_settings)
        if show_errors:
            controller.window.show_error(str(error))
        return False

    return True


def _restore_client_calls_api_settings(controller, settings_snapshot) -> None:
    controller.settings = settings_snapshot
    controller.repository.save_settings(controller.settings)
    controller._apply_client_calls_api_settings_to_window()
    try:
        if controller.settings.client_calls_api_enabled:
            controller.call_api_server.start(
                host=controller.settings.client_calls_api_host,
                port=controller.settings.client_calls_api_port,
                token=controller.settings.client_calls_api_token,
            )
        else:
            controller.call_api_server.stop()
    except RuntimeError:
        controller.call_api_server.stop()


def _apply_client_calls_api_settings_to_window(controller) -> None:
    controller.window.set_client_calls_api_enabled(controller.settings.client_calls_api_enabled)
    controller.window.set_client_calls_api_host(controller.settings.client_calls_api_host)
    controller.window.set_client_calls_api_port(controller.settings.client_calls_api_port)
    controller.window.set_client_calls_api_token(controller.settings.client_calls_api_token)
