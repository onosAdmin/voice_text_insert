#!/usr/bin/env python3
import sys
import os
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import VoiceTextInsertApp

if __name__ == "__main__":
    app = VoiceTextInsertApp()
    Gtk.main()
