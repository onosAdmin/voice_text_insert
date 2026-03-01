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
        self.set_accept_focus(True)

        screen = Gdk.Screen.get_default()
        monitor = screen.get_primary_monitor()
        geometry = screen.get_monitor_geometry(monitor)

        x = geometry.width - width - 20
        y = 20
        self.move(x, y)

        self.set_default_size(width, height)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(self.box)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        self.box.pack_start(scrolled, True, True, 0)

        self.textview = Gtk.TextView()
        self.textview.set_editable(True)
        self.textview.set_cursor_visible(True)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textview.modify_font(Pango.FontDescription("Sans 14"))
        scrolled.add(self.textview)

        self.status_label = Gtk.Label()
        self.status_label.set_alignment(0.5, 0.5)
        self.status_label.modify_font(Pango.FontDescription("Sans 10"))
        self.status_label.set_opacity(0.7)
        self.box.pack_start(self.status_label, False, False, 5)

        button_box = Gtk.Box(spacing=10)
        self.box.pack_start(button_box, False, False, 5)

        self.copy_button = Gtk.Button(label="Copia in clipboard")
        self.copy_button.connect("clicked", self._on_copy_clicked)
        button_box.pack_end(self.copy_button, False, False, 0)

        self.connect("key-press-event", self._on_key_press)

        self._callback = None
        self._closed = False

    def get_text(self):
        if self._closed:
            return ""
        buffer = self.textview.get_buffer()
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)

    def set_text(self, text: str):
        if self._closed:
            return
        buffer = self.textview.get_buffer()
        buffer.set_text(text)

    def append_text(self, text: str):
        if self._closed:
            return
        buffer = self.textview.get_buffer()
        end_iter = buffer.get_end_iter()
        buffer.insert(end_iter, " " + text)

    def set_status(self, status: str):
        if self._closed:
            return
        self.status_label.set_text(status)

    def clear(self):
        if self._closed:
            return
        buffer = self.textview.get_buffer()
        buffer.set_text("")
        self.status_label.set_text("")

    def show_recording(self):
        self.set_status("Registrazione in corso... (Esc per annullare)")

    def show_processing(self):
        self.set_status("Elaborazione in corso...")

    def show_error(self, message: str):
        self.set_status(f"Errore: {message}")

    def close(self):
        self._closed = True
        super().close()

    def is_closed(self):
        return self._closed

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self._callback:
                self._callback("cancel")
            return True
        return False

    def _on_copy_clicked(self, widget):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        text = self.get_text()
        clipboard.set_text(text, -1)
        if self._callback:
            self._callback("copy")

    def set_cancel_callback(self, callback):
        self._callback = callback
