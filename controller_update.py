from services.update_service import UpdateInfo


def check_for_updates(controller) -> None:
    if controller._update_check_busy:
        return

    controller._update_check_busy = True
    controller.window.set_update_checking(True)
    controller._start_worker(controller._check_for_updates_worker)


def _check_for_updates_worker(controller) -> None:
    try:
        update_info = controller.update_service.get_available_update()
    except Exception as error:
        controller._post_to_ui(controller._finish_update_check_error, str(error))
        return

    controller._post_to_ui(controller._finish_update_check_success, update_info)


def _finish_update_check_success(controller, update_info: UpdateInfo | None) -> None:
    controller._update_check_busy = False
    controller.window.set_update_checking(False)

    if update_info is None:
        controller.window.show_info("Обновления", "Установлена последняя версия")
        return

    confirmed = controller.window.ask_yes_no(
        "Доступно обновление",
        f"Доступна версия {update_info.version}.\nСкачать и запустить установщик?",
    )
    if not confirmed:
        return

    controller._update_check_busy = True
    controller.window.set_update_checking(True, text="Скачиваю...")
    controller._start_worker(controller._download_update_worker, update_info)


def _finish_update_check_error(controller, error_message: str) -> None:
    controller._update_check_busy = False
    controller.window.set_update_checking(False)
    controller.window.show_error(f"Не удалось проверить обновления: {error_message}")


def _download_update_worker(controller, update_info: UpdateInfo) -> None:
    try:
        installer_path = controller.update_service.download_installer(update_info)
    except Exception as error:
        controller._post_to_ui(controller._finish_update_download_error, str(error))
        return

    controller._post_to_ui(controller._finish_update_download_success, installer_path)


def _finish_update_download_success(controller, installer_path: str) -> None:
    controller._update_check_busy = False
    controller.window.set_update_checking(False)

    try:
        controller.update_service.launch_installer(installer_path)
    except Exception as error:
        controller.window.show_error(f"Не удалось запустить установщик: {error}")
        return

    controller.save_and_close()


def _finish_update_download_error(controller, error_message: str) -> None:
    controller._update_check_busy = False
    controller.window.set_update_checking(False)
    controller.window.show_error(f"Не удалось скачать обновление: {error_message}")
