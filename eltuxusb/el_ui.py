# -*- coding: utf-8 -*-
# GTK4 + libadwaita user interface

import time

import usb.core
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from .el_device import el1_device, el1_math
from .el_input import el1_input
from .el_parse import el1_parse
from .el_plot import plot

SAMPLE_RATES = [
    ("every 10 seconds", 10),
    ("every 1 minute", 60),
    ("every 5 minutes", 300),
    ("every 10 minutes", 600),
    ("every 30 minutes", 1800),
    ("every 1 hour", 3600),
    ("every 2 hours", 7200),
    ("every 6 hours", 21600),
    ("every 12 hours", 43200),
    ("every 24 hours", 86400),
]

SUPPORTED_MODELS = ("elusb1_17", "elusb2", "elusb2lcd")


class EltuxusbWindow(Gtk.ApplicationWindow):
    def __init__(self, app, debug, recover_mode):
        super().__init__(application=app, title="ELTuxUSB")
        self.set_default_size(650, 550)

        self.debug = debug
        self.recover_mode = recover_mode
        self.dev1 = el1_device(self.debug, self.recover_mode)
        self.parse = el1_parse()
        self.math = el1_math()
        self.model = ""
        self.file = ""
        self.name_recording = ""

        self.build_ui()
        self.refresh()

    # ------------------------------------------------------------------ UI

    def build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header = Adw.HeaderBar()
        self.set_titlebar(header)

        about_button = Gtk.Button(icon_name="help-about-symbolic")
        about_button.connect("clicked", self.about_window)
        header.pack_start(about_button)

        refresh_button = Gtk.Button(label="Refresh")
        refresh_button.connect("clicked", self.refresh)
        header.pack_end(refresh_button)

        # --- Device status page (shown when no device is found)
        self.not_found = Adw.StatusPage(icon_name="dialog-error-symbolic",
                                        title="Device not found",
                                        description="Plug the data logger in, then press Refresh.")
        self.not_found.set_vexpand(True)

        # --- Main page
        self.found = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                             margin_top=12, margin_bottom=12,
                             margin_start=12, margin_end=12)

        self.device_label = Gtk.Label(halign=Gtk.Align.START)
        self.device_label.add_css_class("title-3")
        self.found.append(self.device_label)

        self.status_label = Gtk.Label(halign=Gtk.Align.START, wrap=True)
        self.found.append(self.status_label)

        self.recordings_label = Gtk.Label(halign=Gtk.Align.START)
        self.found.append(self.recordings_label)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.download_button = Gtk.Button(label="Download")
        self.download_button.connect("clicked", self.download)
        self.stop_button = Gtk.Button(label="Stop recording")
        self.stop_button.connect("clicked", self.stop_recording)
        self.new_button = Gtk.Button(label="New recording")
        self.new_button.connect("clicked", self.new_recording)
        self.graph_button = Gtk.Button(label="Graph")
        self.graph_button.connect("clicked", self.generate_graph)
        for b in (self.download_button, self.stop_button,
                  self.new_button, self.graph_button):
            button_box.append(b)
        self.found.append(button_box)

        # --- New recording form (revealed by the "New recording" button)
        self.form_revealer = Gtk.Revealer()
        self.found.append(self.form_revealer)

        form = Adw.PreferencesGroup(title="New recording")

        name_row = Adw.EntryRow(title="Recording name")
        self.name_entry = name_row
        form.add(name_row)

        rate_strings = [s for s, _ in SAMPLE_RATES]
        rate_drop = Gtk.DropDown.new_from_strings(rate_strings)
        rate_drop.set_selected(1)
        rate_row = Adw.ActionRow(title="Sample rate")
        rate_row.add_suffix(rate_drop)
        rate_row.set_activatable_widget(rate_drop)
        self.rate_drop = rate_drop
        form.add(rate_row)

        unit_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6,
                           halign=Gtk.Align.END)
        self.unit_c = Gtk.CheckButton(label="Celsius (°C)", active=True)
        self.unit_f = Gtk.CheckButton(label="Fahrenheit (°F)")
        self.unit_f.set_group(self.unit_c)
        unit_row = Adw.ActionRow(title="Unit")
        unit_box.append(self.unit_c)
        unit_box.append(self.unit_f)
        unit_row.add_suffix(unit_box)
        form.add(unit_row)

        self.delay_check = Gtk.CheckButton(label="Delayed start")
        self.delay_check.connect("toggled", self.delay_recording)
        delay_row = Adw.ActionRow(title="Delayed start")
        delay_row.add_suffix(self.delay_check)
        delay_row.set_activatable_widget(self.delay_check)
        form.add(delay_row)

        self.calendar = Gtk.Calendar(margin_top=6, margin_bottom=6,
                                     halign=Gtk.Align.CENTER, sensitive=False)
        form.add(self.calendar)

        time_row = Adw.ActionRow(title="Start time")
        self.hour_spin = Gtk.SpinButton.new_with_range(0, 23, 1)
        self.min_spin = Gtk.SpinButton.new_with_range(0, 59, 1)
        self.hour_spin.set_sensitive(False)
        self.min_spin.set_sensitive(False)
        time_row.add_suffix(self.hour_spin)
        time_row.add_suffix(Gtk.Label(label=" : "))
        time_row.add_suffix(self.min_spin)
        form.add(time_row)

        self.high_alarm_check = Gtk.CheckButton(label="Enabled")
        self.high_alarm_check.connect("toggled", self.high_temp_alarm)
        self.high_alarm_spin = Gtk.SpinButton.new_with_range(-39.5, 87.5, 0.5)
        self.high_alarm_spin.set_sensitive(False)
        self.high_alarm_latch = Gtk.CheckButton(label="Latch")
        self.high_alarm_latch.set_sensitive(False)
        high_row = Adw.ActionRow(title="High temp. alarm (°C)")
        high_row.add_suffix(self.high_alarm_spin)
        high_row.add_suffix(self.high_alarm_check)
        high_row.add_suffix(self.high_alarm_latch)
        high_row.set_activatable_widget(self.high_alarm_check)
        form.add(high_row)

        self.low_alarm_check = Gtk.CheckButton(label="Enabled")
        self.low_alarm_check.connect("toggled", self.low_temp_alarm)
        self.low_alarm_spin = Gtk.SpinButton.new_with_range(-39.5, 87.5, 0.5)
        self.low_alarm_spin.set_sensitive(False)
        self.low_alarm_latch = Gtk.CheckButton(label="Latch")
        self.low_alarm_latch.set_sensitive(False)
        low_row = Adw.ActionRow(title="Low temp. alarm (°C)")
        low_row.add_suffix(self.low_alarm_spin)
        low_row.add_suffix(self.low_alarm_check)
        low_row.add_suffix(self.low_alarm_latch)
        low_row.set_activatable_widget(self.low_alarm_check)
        form.add(low_row)

        self.humidity_group = Adw.PreferencesGroup(title="Humidity alarms")
        self.high_hum_check = Gtk.CheckButton(label="Enabled")
        self.high_hum_check.connect("toggled", self.high_hum_alarm)
        self.high_hum_spin = Gtk.SpinButton.new_with_range(0, 100, 1)
        self.high_hum_spin.set_sensitive(False)
        self.high_hum_latch = Gtk.CheckButton(label="Latch")
        self.high_hum_latch.set_sensitive(False)
        high_hum_row = Adw.ActionRow(title="High humidity alarm (%rh)")
        high_hum_row.add_suffix(self.high_hum_spin)
        high_hum_row.add_suffix(self.high_hum_check)
        high_hum_row.add_suffix(self.high_hum_latch)
        high_hum_row.set_activatable_widget(self.high_hum_check)
        self.humidity_group.add(high_hum_row)

        self.low_hum_check = Gtk.CheckButton(label="Enabled")
        self.low_hum_check.connect("toggled", self.low_hum_alarm)
        self.low_hum_spin = Gtk.SpinButton.new_with_range(0, 100, 1)
        self.low_hum_spin.set_sensitive(False)
        self.low_hum_latch = Gtk.CheckButton(label="Latch")
        self.low_hum_latch.set_sensitive(False)
        low_hum_row = Adw.ActionRow(title="Low humidity alarm (%rh)")
        low_hum_row.add_suffix(self.low_hum_spin)
        low_hum_row.add_suffix(self.low_hum_check)
        low_hum_row.add_suffix(self.low_hum_latch)
        low_hum_row.set_activatable_widget(self.low_hum_check)
        self.humidity_group.add(low_hum_row)

        self.apply_button = Gtk.Button(label="Apply")
        self.apply_button.add_css_class("suggested-action")
        self.apply_button.connect("clicked", self.start_recording)
        self.apply_button.set_halign(Gtk.Align.END)
        self.apply_button.set_margin_top(6)

        form_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        form_box.append(form)
        form_box.append(self.humidity_group)
        form_box.append(self.apply_button)
        self.form_label = Gtk.Label(halign=Gtk.Align.START)
        form_box.append(self.form_label)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(form_box)
        scrolled.set_vexpand(True)
        self.form_revealer.set_child(scrolled)

        self.stack = Gtk.Stack()
        self.stack.add_named(self.not_found, "not_found")
        self.stack.add_named(self.found, "found")
        self.stack.set_visible_child(self.not_found)
        main_box.append(self.stack)
        self.set_child(main_box)

    # ------------------------------------------------------------- callbacks

    def about_window(self, source=None):
        about = Adw.AboutWindow()
        about.set_application_name("ELTuxUSB")
        about.set_website("https://github.com/eltuxusb")
        about.set_copyright("Copyright © 2009-2013 Romain Aviolat")
        about.set_version("0.6")
        about.set_developers(["Romain Aviolat", "David Strauss"])
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_transient_for(self)
        about.present()

    def delay_recording(self, source=None):
        active = self.delay_check.get_active()
        self.calendar.set_sensitive(active)
        self.hour_spin.set_sensitive(active)
        self.min_spin.set_sensitive(active)

    def high_temp_alarm(self, source=None):
        active = self.high_alarm_check.get_active()
        self.high_alarm_spin.set_sensitive(active)
        self.high_alarm_latch.set_sensitive(active)

    def low_temp_alarm(self, source=None):
        active = self.low_alarm_check.get_active()
        self.low_alarm_spin.set_sensitive(active)
        self.low_alarm_latch.set_sensitive(active)

    def high_hum_alarm(self, source=None):
        active = self.high_hum_check.get_active()
        self.high_hum_spin.set_sensitive(active)
        self.high_hum_latch.set_sensitive(active)

    def low_hum_alarm(self, source=None):
        active = self.low_hum_check.get_active()
        self.low_hum_spin.set_sensitive(active)
        self.low_hum_latch.set_sensitive(active)

    # ------------------------------------------------------------ device ops

    def refresh(self, source=None):
        try:
            init_ok = self.dev1.init() is not False
        except usb.core.USBError as e:
            self.dev1.last_error = str(e)
            init_ok = False
        if not init_ok:
            self.status_label.set_text(self.dev1.get_last_err())
            self.device_label.set_text("")
            self.recordings_label.set_text("")
            self.stack.set_visible_child(self.not_found)
            err = self.dev1.get_last_err()
            if err:
                self.not_found.set_description(err)
            self.stop_button.set_sensitive(False)
            self.download_button.set_sensitive(False)
            self.new_button.set_sensitive(False)
            self.form_revealer.set_reveal_child(False)
            if self.debug:
                print("#DEBUG# DEVICE NOT FOUND")
            return

        status_msg = "state: "
        self.model = self.dev1.device_model
        flag_bits = self.dev1.get_status()
        config = self.dev1.get_config()
        full_name = self.dev1.device_full_name

        self.sample_count = self.math.base256to10(config[30:32])

        if self.model not in SUPPORTED_MODELS:
            self.download_button.set_sensitive(False)
            self.stop_button.set_sensitive(False)
            self.new_button.set_sensitive(False)
            self.device_label.set_text(full_name)
            self.status_label.set_text("DEVICE NOT SUPPORTED YET")
            self.stack.set_visible_child(self.found)
            return

        if self.sample_count == 0:
            self.download_button.set_sensitive(False)
            status_msg += "zero records, "
        else:
            self.download_button.set_sensitive(True)

        self.recordings_label.set_text(str(self.sample_count) + " recordings")

        if flag_bits[8] == "1":
            status_msg += "delayed start or logging, "
            self.stop_button.set_sensitive(True)
        else:
            status_msg += "stopped, "
            self.stop_button.set_sensitive(False)

        if flag_bits[9] == "1":
            status_msg += "data NOT downloaded"
        else:
            status_msg += "data ALREADY downloaded"

        if flag_bits[10] == "1":
            status_msg += ", during the last acquisition battery level dropped to a low level but logging continued"

        if flag_bits[11] == "1":
            status_msg += ", during the last acquisition battery level dropped to a critical level and logging stopped"

        self.status_label.set_text(status_msg)
        self.device_label.set_text(full_name)
        self.stack.set_visible_child(self.found)
        self.new_button.set_sensitive(True)

        self.name_recording = self.math.name_translate(self.dev1.get_config()[2:18])
        self.name_entry.set_text(self.name_recording)

        is_hum = self.model in ("elusb2", "elusb2lcd")
        self.humidity_group.set_visible(is_hum)

        if self.debug:
            print("#DEBUG# DEVICE STATE: %s" % status_msg)
            print("#DEBUG# RECORDING COUNT: %d" % self.sample_count)

    def new_recording(self, source=None):
        self.form_revealer.set_reveal_child(True)
        self.delay_check.set_active(False)
        self.calendar.set_sensitive(False)

    def stop_recording(self, source=None):
        self.status_label.set_text(self.dev1.stop_recording())

    def download(self, source=None):
        dialog = Gtk.FileDialog()
        dialog.set_title("Please, choose an output file")

        def on_response(dialog, result):
            try:
                file = dialog.save_finish(result)
            except GLib.Error:
                return
            path = file.get_path()

            def worker():
                ok = self.dev1.init() and self.dev1.download() and self.dev1.clear_flag_bits()
                GLib.idle_add(self._download_done, ok, path)

            import threading
            threading.Thread(target=worker, daemon=True).start()

        dialog.save(self, None, on_response)

    def _download_done(self, ok, path):
        if not ok:
            self.status_label.set_text(self.dev1.get_last_err())
            return False
        self.parse.data_translate(self.dev1.get_data(), self.dev1.get_config(),
                                  self.dev1.get_status(), path, self.model)
        if self.debug:
            self.status_label.set_text("Downloaded but not stopped")
        else:
            self.status_label.set_text("Downloaded and stopped")
            self.stop_button.set_sensitive(False)
        return False

    def generate_graph(self, source=None):
        dialog = Gtk.FileDialog()
        dialog.set_title("Select a previously saved recording")

        def on_response(dialog, result):
            try:
                file = dialog.open_finish(result)
            except GLib.Error:
                return
            path = file.get_path()
            graph = plot()
            try:
                graph.parse_file(path)
            except Exception as e:
                self.status_label.set_text("Cannot parse file: %s" % e)
                return
            fig = graph.render_plot()
            self.show_graph_window(fig, graph.recName)

        dialog.open(self, None, on_response)

    def show_graph_window(self, fig, title):
        from matplotlib.backends.backend_gtk4agg import FigureCanvas
        win = Adw.Window(title=title)
        win.set_default_size(900, 600)
        win.set_transient_for(self)
        canvas = FigureCanvas(fig)
        canvas.set_size_request(800, 500)
        canvas.set_hexpand(True)
        canvas.set_vexpand(True)
        win.set_content(canvas)
        win.present()

    def start_recording(self, source=None):
        status = 0
        self.form_label.set_text("")

        recording_name = self.name_entry.get_text()
        illegal = self.math.illegal_char(recording_name)
        if illegal:
            status = 1
            self.form_label.set_text(illegal)

        converted_name = el1_input().convert_name(recording_name)

        sample_rate = SAMPLE_RATES[self.rate_drop.get_selected()][1]
        converted_sample_rate = self.math.base10to256(sample_rate, 2)

        start_sec = 0
        if self.delay_check.get_active():
            y, m, d = self.calendar.get_date().get_ymd()
            start_year = int(str(y)[2:4])
            start_month = m
            start_day = d
            start_hour = int(self.hour_spin.get_value())
            start_min = int(self.min_spin.get_value())
            time_start = int(time.mktime((y, m, d, start_hour, start_min, start_sec,
                                          0, 0, -1)))
            offset_seconds = time_start - int(time.time())
        else:
            now = time.localtime()
            start_day = now.tm_mday
            start_month = now.tm_mon
            start_year = int(str(now.tm_year)[2:4])
            start_hour = now.tm_hour
            start_min = now.tm_min
            offset_seconds = 0

        if offset_seconds < 0:
            self.form_label.set_text("Start date is in the past")
            status = 1

        offset_seconds_converted = self.math.base10to256(offset_seconds, 4)

        unit = 0 if self.unit_c.get_active() else 1

        high_alarm = "0"
        high_alarm_latch = "0"
        high_alarm_value_converted = 0
        if self.high_alarm_check.get_active():
            high_alarm = "1"
            high_alarm_value_converted = self.math.alarm_convert(
                int(self.high_alarm_spin.get_value()), unit)
            if self.high_alarm_latch.get_active():
                high_alarm_latch = "1"

        low_alarm = "0"
        low_alarm_latch = "0"
        low_alarm_value_converted = 0
        if self.low_alarm_check.get_active():
            low_alarm = "1"
            low_alarm_value_converted = self.math.alarm_convert(
                int(self.low_alarm_spin.get_value()), unit)
            if self.low_alarm_latch.get_active():
                low_alarm_latch = "1"

        high_humidity_alarm = "0"
        high_humidity_alarm_latch = "0"
        high_humidity_alarm_value_converted = 0
        low_humidity_alarm = "0"
        low_humidity_alarm_latch = "0"
        low_humidity_alarm_value_converted = 0

        if self.model in ("elusb2", "elusb2lcd"):
            if self.high_hum_check.get_active():
                high_humidity_alarm = "1"
                high_humidity_alarm_value_converted = self.math.humidity_alarm_convert(
                    int(self.high_hum_spin.get_value()))
                if self.high_hum_latch.get_active():
                    high_humidity_alarm_latch = "1"

            if self.low_hum_check.get_active():
                low_humidity_alarm = "1"
                low_humidity_alarm_value_converted = self.math.humidity_alarm_convert(
                    int(self.low_hum_spin.get_value()))
                if self.low_hum_latch.get_active():
                    low_humidity_alarm_latch = "1"

            flag_bit_32 = (low_humidity_alarm_latch + high_humidity_alarm_latch +
                           low_humidity_alarm + high_humidity_alarm +
                           low_alarm_latch + high_alarm_latch +
                           low_alarm + high_alarm)
        else:
            flag_bit_32 = "0000" + low_alarm_latch + high_alarm_latch + low_alarm + high_alarm

        flag_bit_33 = "00000011"

        if status == 0:
            self.dev1.new_buffer.set_cmd_type(0)
            self.dev1.new_buffer.set_flag_bits([int(flag_bit_32, 2), int(flag_bit_33, 2)])
            self.dev1.new_buffer.set_name(converted_name)
            self.dev1.new_buffer.set_sample_rate(converted_sample_rate)
            self.dev1.new_buffer.set_start_offset(offset_seconds_converted)
            self.dev1.new_buffer.set_unit(unit)
            self.dev1.new_buffer.set_hour(start_hour)
            self.dev1.new_buffer.set_minutes(start_min)
            self.dev1.new_buffer.set_seconds(0)
            self.dev1.new_buffer.set_day(start_day)
            self.dev1.new_buffer.set_month(start_month)
            self.dev1.new_buffer.set_year(start_year)

            if self.model != "elusb3_2":
                self.dev1.new_buffer.set_hal(high_alarm_value_converted)
                self.dev1.new_buffer.set_lal(low_alarm_value_converted)

            self.dev1.new_buffer.set_sample_count([0, 0])

            if self.model in ("elusb2", "elusb2lcd"):
                self.dev1.new_buffer.set_hal_ch2(high_humidity_alarm_value_converted)
                self.dev1.new_buffer.set_lal_ch2(low_humidity_alarm_value_converted)

            new_buffer = self.dev1.new_buffer.get_modified_buffer()

            if self.debug:
                self.form_label.set_text("Debug mode, nothing sent to the device, see console")
                print("#DEBUG# NEW CONFIG  : %s" % new_buffer)
            else:
                if self.dev1.config_write(new_buffer) is True:
                    self.form_label.set_text("Ready, please remove device")
                else:
                    self.form_label.set_text("Something bad happened")


class EltuxusbApp(Adw.Application):
    def __init__(self, debug, recover_mode):
        super().__init__(application_id="com.github.eltuxusb.eltuxusb")
        self.debug = debug
        self.recover_mode = recover_mode

    def do_activate(self):
        win = EltuxusbWindow(self, self.debug, self.recover_mode)
        win.present()
