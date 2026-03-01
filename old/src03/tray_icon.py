import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk


class TrayIcon:
    def __init__(self, on_settings=None, on_quit=None):
        self.on_settings = on_settings
        self.on_quit = on_quit

        self.menu = Gtk.Menu()

        settings_item = Gtk.MenuItem(label="Impostazioni")
        settings_item.connect("activate", self._on_settings)
        self.menu.append(settings_item)

        quit_item = Gtk.MenuItem(label="Esci")
        quit_item.connect("activate", self._on_quit)
        self.menu.append(quit_item)

        self.menu.show_all()

    def get_menu(self):
        return self.menu

    def _on_settings(self, item):
        if self.on_settings:
            self.on_settings()

    def _on_quit(self, item):
        if self.on_quit:
            self.on_quit()
