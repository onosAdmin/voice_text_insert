import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk


class SettingsWindow(Gtk.Window):
    def __init__(self, devices: list, current_device: str = "default", on_select=None):
        super().__init__(title="Impostazioni Microfono")
        self.set_default_size(400, 300)

        self.devices = devices
        self.current_device = current_device
        self.on_select = on_select

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(self.box)

        label = Gtk.Label(label="Seleziona microfono:")
        label.set_alignment(0, 0)
        self.box.pack_start(label, False, False, 10)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.box.pack_start(scrolled, True, True, 0)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scrolled.add(self.listbox)

        for device in devices:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

            radio = Gtk.RadioButton(group=None)
            radio.set_label(device.get("description", device.get("name")))
            hbox.pack_start(radio, False, False, 0)

            row.add(hbox)
            self.listbox.add(row)

            if device.get("name") == current_device:
                self.listbox.select_row(row)

        self.listbox.connect("row-selected", self._on_row_selected)

        button_box = Gtk.ButtonBox()
        button_box.set_layout(Gtk.ButtonBoxStyle.END)
        self.box.pack_start(button_box, False, False, 10)

        ok_button = Gtk.Button(label="Conferma")
        ok_button.connect("clicked", self._on_confirm)
        button_box.add(ok_button)

        cancel_button = Gtk.Button(label="Annulla")
        cancel_button.connect("clicked", lambda x: self.close())
        button_box.add(cancel_button)

    def _on_row_selected(self, listbox, row):
        if row:
            index = row.get_index()
            self.selected_device = self.devices[index]

    def _on_confirm(self, button):
        if hasattr(self, "selected_device") and self.on_select:
            self.on_select(self.selected_device["name"])
        self.close()
