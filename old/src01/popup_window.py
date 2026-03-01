import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango
import threading


class PopupWindow(Gtk.Window):
    def __init__(self, width: int = 400, height: int = 200):
        super().__init__(Gtk.WindowType.TOPLEVEL)

        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_accept_focus(False)

        screen = Gdk.Screen.get_default()
        monitor = screen.get_primary_monitor()
        geometry = screen.get_monitor_geometry(monitor)

        x = geometry.width - width - 20
        y = 20
        self.move(x, y)

        self.set_default_size(width, height)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(self.box)

        self.label = Gtk.Label()
        self.label.set_alignment(0, 0)
        self.label.set_line_wrap(True)
        self.label.set_selectable(True)
        self.label.modify_font(Pango.FontDescription("Sans 14"))
        self.box.pack_start(self.label, True, True, 10)

        self.status_label = Gtk.Label()
        self.status_label.set_alignment(0.5, 0.5)
        self.status_label.modify_font(Pango.FontDescription("Sans 10"))
        self.status_label.set_opacity(0.7)
        self.box.pack_start(self.status_label, False, False, 5)

        self.connect("key-press-event", self._on_key_press)

        self._callback = None

    def set_text(self, text: str):
        self.label.set_text(text)

    def append_text(self, text: str):
        current = self.label.get_text()
        self.label.set_text(current + " " + text)

    def set_status(self, status: str):
        self.status_label.set_text(status)

    def clear(self):
        self.label.set_text("")
        self.status_label.set_text("")

    def show_recording(self):
        self.set_status("🎤 Registrazione in corso... (Esc per annullare)")

    def show_processing(self):
        self.set_status("⏳ Elaborazione in corso...")

    def show_error(self, message: str):
        self.set_status(f"❌ {message}")

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self._callback:
                self._callback("cancel")
            return True
        return False

    def set_cancel_callback(self, callback):
        self._callback = callback
