# -*- coding: utf-8 -*-
"""
ANOMALY SCANNER V2.4 ANDROID
Un solo archivo Python. Sin Termux:API ni servicios web.
Usa Kivy + Plyer para acceder a sensores/capacidades Android.

Instalación/compilación Android: Kivy + Plyer + python-for-android.
Los sensores no disponibles se muestran como N/D; no se simulan.
El índice es instrumental y NO demuestra fantasmas, entidades o ángeles.
"""

import csv
import math
import os
import time
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

try:
    from plyer import accelerometer
except Exception:
    accelerometer = None
try:
    from plyer import gyroscope
except Exception:
    gyroscope = None
try:
    from plyer import compass
except Exception:
    compass = None
try:
    from plyer import light
except Exception:
    light = None
try:
    from plyer import gps
except Exception:
    gps = None
try:
    from plyer import temperature
except Exception:
    temperature = None
try:
    from plyer import proximity
except Exception:
    proximity = None

CSV_FILE = "anomaly_v2_4.csv"
EVENT_FILE = "anomaly_events_v2_4.csv"

THRESHOLDS = {
    "accelerometer": 2.0,
    "gyroscope": 0.8,
    "magnetometer": 8.0,
    "light": 20.0,
    "temperature": 2.0,
    "proximity": 1.0,
}

SENSOR_NAMES = (
    "accelerometer", "gyroscope", "magnetometer",
    "light", "temperature", "proximity"
)

def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")

def magnitude(values):
    try:
        nums = [float(x) for x in values]
        return math.sqrt(sum(x*x for x in nums))
    except Exception:
        return None

def average(values):
    values = [x for x in values if x is not None]
    return sum(values) / len(values) if values else None

def append_csv(path, header, row):
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(header)
        w.writerow(row)

class Analyzer:
    def __init__(self):
        self.samples = {}
        self.baseline = {}
        self.event_id = 0
        self.last_event = 0

    def calibrate(self, data):
        for k, v in data.items():
            if v is not None:
                self.samples.setdefault(k, []).append(v)

    def finish(self):
        self.baseline = {
            k: average(v) for k, v in self.samples.items() if v
        }

    def analyze(self, data):
        score = 0.0
        active = []
        deviations = {}

        for k, v in data.items():
            base = self.baseline.get(k)
            threshold = THRESHOLDS.get(k)
            if v is None or base is None or threshold is None:
                continue
            d = abs(v - base)
            deviations[k] = d
            if d > threshold:
                score += min(22.0, 10.0 * d / threshold)
                active.append(k)

        n = len(set(active))
        if n >= 2:
            score += 12
        if n >= 4:
            score += 12
        if n >= 6:
            score += 14

        score = min(100.0, score)
        if score < 20:
            level = "NORMAL"
        elif score < 45:
            level = "BAJO"
        elif score < 70:
            level = "MEDIO"
        elif score < 85:
            level = "ALTO"
        else:
            level = "CRÍTICO"
        return score, level, sorted(set(active)), deviations

    def event_allowed(self, score):
        t = time.time()
        if score >= 70 and t - self.last_event >= 8:
            self.last_event = t
            self.event_id += 1
            return True
        return False

class Radar(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.score = 0
        self.bind(pos=self.draw, size=self.draw)

    def set_score(self, value):
        self.score = max(0, min(100, value))
        self.draw()

    def draw(self, *args):
        self.canvas.clear()
        cx, cy = self.center
        radius = min(self.width, self.height) * .38
        with self.canvas:
            Color(.2, .2, .2, 1)
            for f in (1.0, .72, .44):
                Line(circle=(cx, cy, radius*f), width=1.2)
            Line(points=(cx-radius, cy, cx+radius, cy), width=1)
            Line(points=(cx, cy-radius, cx, cy+radius), width=1)
            angle = math.radians(-90 + self.score * 3.6)
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            Color(.85, .85, .85, 1)
            Line(points=(cx, cy, x, y), width=3)
            Ellipse(pos=(cx-dp(5), cy-dp(5)), size=(dp(10), dp(10)))

class SensorBridge:
    def __init__(self, on_data, on_location):
        self.on_data = on_data
        self.on_location = on_location
        self.values = {}

    def start(self):
        self._start(accelerometer, "on_acceleration", self.accel)
        self._start(gyroscope, "on_gyroscope", self.gyro)
        self._start(compass, "on_compass", self.mag)
        self._start(light, "on_light", self.scalar("light"))
        self._start(temperature, "on_temperature", self.scalar("temperature"))
        self._start(proximity, "on_proximity", self.scalar("proximity"))
        if gps is not None:
            try:
                gps.configure(on_location=self.location, on_status=lambda *a, **k: None)
                gps.start(minTime=1000, minDistance=0)
            except Exception:
                pass

    def _start(self, obj, event, callback):
        if obj is None:
            return
        try:
            obj.enable()
            obj.bind(**{event: callback})
        except Exception:
            pass

    def stop(self):
        for obj in (accelerometer, gyroscope, compass, light, temperature, proximity):
            try:
                if obj is not None:
                    obj.disable()
            except Exception:
                pass
        try:
            if gps is not None:
                gps.stop()
        except Exception:
            pass

    def accel(self, instance, value):
        self.put("accelerometer", magnitude(value))

    def gyro(self, instance, value):
        self.put("gyroscope", magnitude(value))

    def mag(self, instance, *args):
        value = args[0] if args else None
        if isinstance(value, (list, tuple)):
            value = magnitude(value)
        try:
            value = abs(float(value))
        except Exception:
            value = None
        self.put("magnetometer", value)

    def scalar(self, name):
        def cb(instance, value):
            try:
                self.put(name, float(value))
            except Exception:
                pass
        return cb

    def put(self, name, value):
        if value is not None:
            self.values[name] = value
            self.on_data(dict(self.values))

    def location(self, **kwargs):
        self.on_location(dict(kwargs))

class Scanner(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.analyzer = Analyzer()
        self.data = {}
        self.location = {}
        self.running = True
        self.calibrating = True
        self.calibration_end = time.time() + 8
        self.bridge = SensorBridge(self.sensor_data, self.gps_data)

    def build(self):
        root = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(5))

        root.add_widget(Label(
            text="ANOMALY SCANNER V2.4", font_size=dp(22), bold=True,
            size_hint_y=None, height=dp(40)))

        self.mode = Label(text="CALIBRACIÓN 8 s", size_hint_y=None, height=dp(28))
        root.add_widget(self.mode)

        self.score = Label(text="0", font_size=dp(48), bold=True,
                           size_hint_y=None, height=dp(65))
        root.add_widget(self.score)

        self.level = Label(text="CALIBRANDO", font_size=dp(18), bold=True,
                           size_hint_y=None, height=dp(34))
        root.add_widget(self.level)

        self.radar = Radar(size_hint_y=.42)
        root.add_widget(self.radar)

        self.sensors = Label(text="Sensores: iniciando...", font_size=dp(11),
                             halign="left", valign="top")
        self.sensors.bind(size=self.sensors.setter("text_size"))
        root.add_widget(self.sensors)

        self.gps_label = Label(text="GPS: esperando...", font_size=dp(11),
                               size_hint_y=None, height=dp(40))
        root.add_widget(self.gps_label)

        self.events = Label(text="Eventos: ninguno", font_size=dp(11),
                            halign="left", valign="top")
        self.events.bind(size=self.events.setter("text_size"))
        root.add_widget(self.events)

        buttons = GridLayout(cols=3, size_hint_y=None, height=dp(55), spacing=dp(4))
        self.toggle_btn = Button(text="DETENER")
        self.toggle_btn.bind(on_press=self.toggle)
        buttons.add_widget(self.toggle_btn)

        b = Button(text="RECALIBRAR")
        b.bind(on_press=self.recalibrate)
        buttons.add_widget(b)

        g = Button(text="GPS")
        g.bind(on_press=self.refresh_gps)
        buttons.add_widget(g)
        root.add_widget(buttons)

        self.bridge.start()
        Clock.schedule_interval(self.ui_tick, .5)
        return root

    def sensor_data(self, data):
        self.data.update(data)

    def gps_data(self, data):
        self.location = data

    def toggle(self, *args):
        self.running = not self.running
        self.toggle_btn.text = "DETENER" if self.running else "INICIAR"
        self.mode.text = "ESCANEANDO" if self.running else "PAUSADO"
        if self.running:
            self.bridge.start()
        else:
            self.bridge.stop()

    def recalibrate(self, *args):
        self.analyzer = Analyzer()
        self.calibrating = True
        self.calibration_end = time.time() + 8
        self.score.text = "0"
        self.level.text = "CALIBRANDO"
        self.mode.text = "CALIBRACIÓN 8 s"
        self.events.text = "Eventos: nueva línea base"

    def refresh_gps(self, *args):
        if gps is None:
            self.gps_label.text = "GPS: Plyer no disponible"
            return
        try:
            gps.start(minTime=1000, minDistance=0)
        except Exception:
            pass

    def ui_tick(self, dt):
        if not self.running or not self.data:
            return

        if self.calibrating:
            self.analyzer.calibrate(self.data)
            remaining = max(0, int(self.calibration_end - time.time()))
            self.mode.text = f"CALIBRACIÓN: {remaining}s"
            if time.time() >= self.calibration_end:
                self.analyzer.finish()
                self.calibrating = False
                self.mode.text = "ESCANEANDO"
                self.level.text = "NORMAL"
            return

        score, level, active, dev = self.analyzer.analyze(self.data)
        self.score.text = f"{score:.0f}"
        self.level.text = level
        self.radar.set_score(score)

        labels = {
            "accelerometer": "Acel", "gyroscope": "Giro",
            "magnetometer": "Mag", "light": "Luz",
            "temperature": "Temp", "proximity": "Prox"
        }
        parts = []
        for k in SENSOR_NAMES:
            v = self.data.get(k)
            s = "N/D" if v is None else f"{v:.2f}"
            if k in dev:
                s += f" Δ{dev[k]:.2f}"
            parts.append(f"{labels[k]}={s}")
        self.sensors.text = " | ".join(parts) +             "\nDesviaciones: " + (", ".join(active) if active else "ninguna")

        lat = self.location.get("lat", self.location.get("latitude"))
        lon = self.location.get("lon", self.location.get("longitude"))
        acc = self.location.get("accuracy")
        if lat is not None and lon is not None:
            self.gps_label.text = f"GPS: {float(lat):.6f}, {float(lon):.6f} ±{acc if acc is not None else '--'}"
        else:
            self.gps_label.text = "GPS: esperando posición..."

        self.save(score, level, active)

        if self.analyzer.event_allowed(score):
            self.save_event(score, level, active)
            self.events.text = (
                f"EVENTO #{self.analyzer.event_id}\n"
                f"Índice {score:.1f} | {level}\n"
                f"Señales: {', '.join(active) if active else 'ninguna'}"
            )

    def save(self, score, level, active):
        append_scv(CSV_FILE,
            ["timestamp","score","level","active"] + list(SENSOR_NAMES) +
            ["latitude","longitude","accuracy"],
            [now(), f"{score:.2f}", level, "|".join(active)] +
            [self.data.get(k) for k in SENSOR_NAMES] +
            [self.location.get("lat", self.location.get("latitude")),
             self.location.get("lon", self.location.get("longitude")),
             self.location.get("accuracy")])

    def save_event(self, score, level, active):
        csv_append(EVENT_FILE,
            ["event_id","timestamp","score","level","active",
             "latitude","longitude","accuracy"],
            [self.analyzer.event_id, now(), f"{score:.2f}", level, "|".join(active),
             self.location.get("lat", self.location.get("latitude")),
             self.location.get("lon", self.location.get("longitude")),
             self.location.get("accuracy")])

    def on_stop(self):
        self.bridge.stop()

if __name__ == "__main__":
    Scanner().run()
