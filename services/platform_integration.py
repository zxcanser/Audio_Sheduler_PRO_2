import os
import platform
import queue
import tempfile
import tkinter as tk
from typing import Callable, Optional

from PIL import Image, ImageFilter


class PlatformIntegration:
    def __init__(self, root: tk.Tk, app_name: str, on_quit: Callable[[], None]):
        self.root = root
        self.app_name = app_name
        self.on_quit = on_quit
        self.platform = platform.system()
        self.icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ASP_icon.ico")
        self._is_quitting = False
        self._tray_icon = None
        self._status_item = None
        self._status_delegate = None
        self._pending_actions: queue.SimpleQueue[str] = queue.SimpleQueue()
        self._macos_icon_temp_path: Optional[str] = None

    def start(self) -> None:
        self._schedule_pending_action_poll()
        if self.platform == "Darwin":
            self._setup_macos_menu_bar()

    def request_close(self) -> None:
        self.hide_window()

    def handle_window_unmap(self) -> None:
        if self.platform != "Windows" or self._is_quitting:
            return

        try:
            if self.root.state() == "iconic":
                self._safe_after(0, self.hide_window)
        except tk.TclError:
            pass

    def hide_window(self) -> None:
        if self._is_quitting:
            return

        if self.platform == "Windows":
            self._show_windows_tray_icon()
        elif self.platform == "Darwin":
            self._set_macos_activation_policy(show_in_dock=False)

        self.root.withdraw()

    def show_window(self) -> None:
        if self._is_quitting:
            return

        if self.platform == "Windows" and self._tray_icon is not None:
            self._tray_icon.visible = False
        elif self.platform == "Darwin":
            self._set_macos_activation_policy(show_in_dock=True)

        self.root.deiconify()
        self.root.update_idletasks()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()

        if self.platform == "Darwin":
            self._activate_macos_app()

    def quit_application(self) -> None:
        if self._is_quitting:
            return

        self._is_quitting = True
        self._cleanup_ui_integrations()
        self.on_quit()

    def cleanup(self) -> None:
        self._is_quitting = True
        self._cleanup_ui_integrations()

    def enqueue_show_window(self) -> None:
        self._pending_actions.put("show")

    def enqueue_quit(self) -> None:
        self._pending_actions.put("quit")

    def _cleanup_ui_integrations(self) -> None:
        self._stop_tray_icon()
        self._remove_macos_temp_icon()
        self._remove_macos_status_item()

    def _process_pending_actions(self) -> None:
        if self._is_quitting:
            return

        while True:
            try:
                action = self._pending_actions.get_nowait()
            except queue.Empty:
                break

            if action == "show":
                self.show_window()
            elif action == "quit":
                self.quit_application()

        self._schedule_pending_action_poll()

    def _show_windows_tray_icon(self) -> None:
        if self._tray_icon is None:
            self._create_windows_tray_icon()

        self._tray_icon.visible = True

    def _create_windows_tray_icon(self) -> None:
        import pystray

        menu = pystray.Menu(
            pystray.MenuItem("Открыть окно планировщика", lambda icon, item: self.enqueue_show_window()),
            pystray.MenuItem("Сохранить и закрыть", lambda icon, item: self.enqueue_quit()),
        )
        self._tray_icon = pystray.Icon(
            "audio_scheduler",
            self._load_tray_image(),
            self.app_name,
            menu,
        )
        self._tray_icon.run_detached()
        self._tray_icon.visible = False

    def _setup_macos_menu_bar(self) -> None:
        if self._status_item is not None:
            return

        from AppKit import NSApplication, NSMenu, NSMenuItem, NSStatusBar, NSVariableStatusItemLength
        from Foundation import NSObject

        outer = self

        class StatusDelegate(NSObject):
            def showWindow_(self, sender) -> None:
                outer.enqueue_show_window()

            def quitApp_(self, sender) -> None:
                outer.enqueue_quit()

        self._status_delegate = StatusDelegate.alloc().init()
        self._status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        button = self._status_item.button()
        if button is not None:
            icon_image = self._load_macos_status_image()
            if icon_image is not None:
                button.setImage_(icon_image)
                button.setTitle_("")
            else:
                button.setTitle_("♪")
            button.setToolTip_(self.app_name)

        menu = NSMenu.alloc().init()

        show_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Открыть окно планировщика", "showWindow:", "")
        show_item.setTarget_(self._status_delegate)
        menu.addItem_(show_item)

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Сохранить и закрыть", "quitApp:", "q")
        quit_item.setTarget_(self._status_delegate)
        menu.addItem_(quit_item)

        self._status_item.setMenu_(menu)
        NSApplication.sharedApplication()

    def _set_macos_activation_policy(self, show_in_dock: bool) -> None:
        from AppKit import NSApp, NSApplication, NSApplicationActivationPolicyAccessory, NSApplicationActivationPolicyRegular

        app = NSApp() or NSApplication.sharedApplication()
        policy = NSApplicationActivationPolicyRegular if show_in_dock else NSApplicationActivationPolicyAccessory
        app.setActivationPolicy_(policy)

    def _activate_macos_app(self) -> None:
        from AppKit import NSApp, NSApplication

        app = NSApp() or NSApplication.sharedApplication()
        app.activateIgnoringOtherApps_(True)

    def _load_tray_image(self) -> Image.Image:
        with Image.open(self.icon_path) as image:
            return image.copy()

    def _load_macos_status_image(self):
        if not os.path.exists(self.icon_path):
            return None

        try:
            from AppKit import NSImage

            with Image.open(self.icon_path) as image:
                template_image = self._build_macos_template_icon(image)
            temp_fd, temp_path = tempfile.mkstemp(suffix=".png")
            os.close(temp_fd)
            template_image.save(temp_path, format="PNG")
            self._macos_icon_temp_path = temp_path

            ns_image = NSImage.alloc().initByReferencingFile_(temp_path)
            if ns_image is not None:
                ns_image.setSize_((18, 18))
                ns_image.setTemplate_(True)
            return ns_image
        except (ImportError, OSError, RuntimeError, ValueError):
            return None

    def _build_macos_template_icon(self, image: Image.Image) -> Image.Image:
        rgba = image.convert("RGBA")
        grayscale = rgba.convert("L")
        width, height = rgba.size
        template = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        for x in range(width):
            for y in range(height):
                r, g, b, a = rgba.getpixel((x, y))
                luminance = grayscale.getpixel((x, y))

                if a == 0 or luminance > 245:
                    continue

                alpha = max(0, 255 - luminance)
                template.putpixel((x, y), (0, 0, 0, alpha))

        alpha_channel = template.getchannel("A")
        alpha_channel = alpha_channel.filter(ImageFilter.MaxFilter(5))
        alpha_channel = alpha_channel.point(lambda value: min(255, int(value * 1.35)))
        template.putalpha(alpha_channel)
        return template

    def _schedule_pending_action_poll(self) -> None:
        self._safe_after(100, self._process_pending_actions)

    def _safe_after(self, delay_ms: int, callback: Callable[[], None]) -> None:
        try:
            self.root.after(delay_ms, callback)
        except tk.TclError:
            pass

    def _stop_tray_icon(self) -> None:
        if self._tray_icon is None:
            return

        try:
            self._tray_icon.visible = False
            self._tray_icon.stop()
        except (AttributeError, OSError, RuntimeError):
            pass
        self._tray_icon = None

    def _remove_macos_temp_icon(self) -> None:
        if not self._macos_icon_temp_path or not os.path.exists(self._macos_icon_temp_path):
            self._macos_icon_temp_path = None
            return

        try:
            os.remove(self._macos_icon_temp_path)
        except OSError:
            pass
        self._macos_icon_temp_path = None

    def _remove_macos_status_item(self) -> None:
        if self._status_item is None:
            return

        try:
            from AppKit import NSStatusBar

            NSStatusBar.systemStatusBar().removeStatusItem_(self._status_item)
        except ImportError:
            pass
        self._status_item = None
        self._status_delegate = None
