import signal
import sys
import tkinter as tk

from controller import AudioSchedulerController
from config import INSTANCE_LOCK_FILE
from services.single_instance import SingleInstanceGuard


def main() -> None:
    instance_guard = SingleInstanceGuard(INSTANCE_LOCK_FILE)
    if not instance_guard.acquire():
        sys.stderr.write(
            "Audio Scheduler PRO уже запущен. "
            "Закройте предыдущий экземпляр перед повторным запуском.\n"
        )
        return

    root = tk.Tk()
    controller = AudioSchedulerController(root)
    shutdown_requested = False

    def request_shutdown(*_args) -> None:
        nonlocal shutdown_requested
        if shutdown_requested:
            return

        shutdown_requested = True
        try:
            root.after(0, controller.shutdown)
        except Exception:
            instance_guard.release()
            raise SystemExit(0)

    signal.signal(signal.SIGINT, request_shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_shutdown)
    if hasattr(signal, "SIGTSTP"):
        signal.signal(signal.SIGTSTP, request_shutdown)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        request_shutdown()
    finally:
        instance_guard.release()


if __name__ == "__main__":
    main()
