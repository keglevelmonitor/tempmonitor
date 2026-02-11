#!/usr/bin/env python3
import os
import json
import csv
import time
from datetime import datetime
from random import uniform

# --- 1. SETTINGS MANAGER & CONFIGURATION ---
class SettingsManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.csv_file = os.path.join(self.data_dir, 'templog.csv')
        self.settings_file = os.path.join(self.data_dir, 'tempmonitor_settings.json')
        
        # Default Settings
        self.defaults = {
            'window_width': 480,
            'window_height': 258,
            'window_top': None,
            'window_left': None,
            'units': 'C',          # 'C' or 'F'
            'frequency_unit': 'min', # 'sec' or 'min'
            'log_interval': 5,     
            'sensor_map': {}      
        }
        self.data = self.defaults.copy()
        self.load()

    def load(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    saved = json.load(f)
                    self.data.update(saved)
            except Exception as e:
                print(f"Error loading settings: {e}")

    def save(self):
        self.ensure_data_dir()
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.data, f, indent=4)
            print(f"Settings saved.")
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key):
        return self.data.get(key, self.defaults.get(key))

    def set(self, key, value):
        self.data[key] = value

    def ensure_data_dir(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as f:
                csv.writer(f).writerow(['timestamp', 'sensor_id', 'temperature'])

# Instantiate Global Manager
settings = SettingsManager()

# --- 2. APPLY WINDOW SETTINGS (PRE-KIVY) ---
# This prevents the startup flash and handles the restore logic
os.environ['KIVY_METRICS_DENSITY'] = '1'
os.environ['SDL_VIDEO_X11_WMCLASS'] = "TempMonitor"

from kivy.config import Config

# --- SET APP ICON ---
current_dir = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(current_dir, 'assets', 'thermometer.png')
Config.set('kivy', 'window_icon', icon_path)

# Safety Check: If window is too small, reset to default
min_w = 480
min_h = 258
safe_w = settings.get('window_width')
safe_h = settings.get('window_height')

if safe_w < min_w or safe_h < min_h:
    print("Window too small, resetting to defaults.")
    safe_w = min_w
    safe_h = min_h
    # Reset position to center
    settings.set('window_top', None)
    settings.set('window_left', None)

Config.set('graphics', 'width', str(safe_w))
Config.set('graphics', 'height', str(safe_h))
Config.set('graphics', 'resizable', '1')
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'borderless', '0')

top = settings.get('window_top')
left = settings.get('window_left')

if top is not None and left is not None:
    Config.set('graphics', 'position', 'custom')
    Config.set('graphics', 'top', str(top))
    Config.set('graphics', 'left', str(left))

# --- 3. STANDARD IMPORTS ---
from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.properties import ObjectProperty, StringProperty, NumericProperty, ListProperty
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy_garden.graph import Graph, MeshLinePlot 

class SettingsScreen(Screen):
    pass

# --- CUSTOM RESPONSIVE GRAPH ---
class ResponsiveGraph(Graph):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._trigger_font_update = Clock.create_trigger(self.update_fonts, 0.1)
        self.bind(height=self._trigger_font_update)
        Clock.schedule_once(self.update_fonts, 0.5)
        
    def update_fonts(self, *args):
        if self.height < 10: return
        new_size = max(12, self.height * 0.05)
        self.label_options = {
            'color': [1, 1, 1, 1],
            'bold': True,
            'font_size': new_size
        }

# --- SENSOR HANDLING ---
try:
    from w1thermsensor import W1ThermSensor
    if not W1ThermSensor.get_available_sensors():
        raise ImportError("No sensors found")
    IS_RASPBERRY_PI = True
except Exception:
    IS_RASPBERRY_PI = False
    print("Using MOCK SENSORS")
    class W1ThermSensor:
        def __init__(self, sensor_id=None):
            self.id = sensor_id or "28-00000TEST"
        @staticmethod
        def get_available_sensors():
            return [W1ThermSensor("28-MockProd"), W1ThermSensor("28-MockAmb")]
        def get_temperature(self):
            return round(uniform(20.0, 30.0), 2)

class MonitorScreen(Screen):
    pass

class ChartScreen(Screen):
    pass

class TempMonitorApp(App):
    product_temp = StringProperty("--.-")
    ambient_temp = StringProperty("--.-")
    # NEW: Range Properties
    product_range = StringProperty("Range: --.- - --.-")
    ambient_range = StringProperty("Range: --.- - --.-")
    
    sensor_ids = ListProperty([])
    
    # Settings Properties
    units = StringProperty(settings.get('units'))
    frequency_unit = StringProperty(settings.get('frequency_unit'))
    log_interval = NumericProperty(settings.get('log_interval')) 
    
    # Reset Button Properties
    reset_btn_text = StringProperty("RESET CSV DATA")
    reset_btn_color = ListProperty([0.8, 0.2, 0.2, 1])

    @property
    def time_factor(self):
        """Returns divisor: 60.0 for Minutes, 1.0 for Seconds"""
        return 60.0 if self.frequency_unit == 'min' else 1.0

    def build(self):
        settings.ensure_data_dir()
        self.root = Builder.load_file('app_layout.kv')
        
        # Initialize Sensors
        self.sensors = W1ThermSensor.get_available_sensors()
        self.sensor_ids = [s.id for s in self.sensors]
        
        # Initialize Range Trackers
        self.prod_min = None
        self.prod_max = None
        self.amb_min = None
        self.amb_max = None
        
        self.setup_graph()
        
        # Start Clock
        self.reschedule_log_event()
        
        # Immediate display update
        Clock.schedule_once(self.update_display_only, 1) 
        Clock.schedule_interval(self.update_display_only, 2) 
        
        return self.root

    def on_stop(self):
        """Save settings on exit."""
        settings.set('window_width', Window.width)
        settings.set('window_height', Window.height)
        settings.set('window_top', Window.top)
        settings.set('window_left', Window.left)
        settings.set('log_interval', self.log_interval)
        settings.set('units', self.units)
        settings.set('frequency_unit', self.frequency_unit)
        settings.save()

    # --- SETTINGS HANDLERS ---
    def set_units(self, unit):
        self.units = unit
        self.update_display_only()
        # Reload history to recalculate graph points and Min/Max ranges in new unit
        self.load_history_to_graph()

    def set_frequency_unit(self, unit):
        self.frequency_unit = unit
        self.reschedule_log_event()
        self.setup_graph()

    def update_log_interval(self, value):
        self.log_interval = int(value)
        self.reschedule_log_event()

    def reschedule_log_event(self):
        if hasattr(self, 'scheduled_event'):
            self.scheduled_event.cancel()
        
        interval_seconds = self.log_interval * self.time_factor
        self.scheduled_event = Clock.schedule_interval(self.log_data, interval_seconds)
        print(f"Logging every {self.log_interval} {self.frequency_unit} ({interval_seconds}s real time)")

    def on_reset_click(self):
        """Handles the safety 'Arm & Fire' logic for the reset button."""
        if self.reset_btn_text == "RESET CSV DATA":
            self.reset_btn_text = "CONFIRM RESET?"
            self.reset_btn_color = [1, 0.8, 0, 1] 
            Clock.schedule_once(self.reset_button_timeout, 3)
            
        elif self.reset_btn_text == "CONFIRM RESET?":
            self.clear_csv_data()
            self.reset_btn_text = "DATA CLEARED"
            self.reset_btn_color = [0.2, 0.8, 0.2, 1] 
            Clock.schedule_once(self.reset_button_timeout, 2)

    def reset_button_timeout(self, dt):
        self.reset_btn_text = "RESET CSV DATA"
        self.reset_btn_color = [0.8, 0.2, 0.2, 1]

    def clear_csv_data(self):
        """Wipes the CSV file and resets the graph."""
        try:
            with open(settings.csv_file, 'w', newline='') as f:
                csv.writer(f).writerow(['timestamp', 'sensor_id', 'temperature'])
            
            self.plot_product.points = []
            self.plot_ambient.points = []
            
            # Reset Range Trackers
            self.prod_min = None
            self.prod_max = None
            self.amb_min = None
            self.amb_max = None
            self.product_range = "Range: --.- - --.-"
            self.ambient_range = "Range: --.- - --.-"
            
            if self.root:
                chart_screen = self.root.get_screen('chart')
                graph = chart_screen.ids.main_graph
                graph.xmin = 0
                graph.xmax = 100
                graph.x_ticks_major = int(graph.xmax / 6) # Reset X ticks
                
                graph.ymin = 0
                graph.ymax = 40
                graph.y_ticks_major = (graph.ymax - graph.ymin) / 6 # Reset Y ticks
                
            print("CSV Log Cleared.")
        except Exception as e:
            print(f"Error clearing CSV: {e}")

    # --- HELPERS ---
    def get_temp_display(self, temp_c):
        """Converts C float to C or F string"""
        if self.units == 'F':
            val = (temp_c * 9/5) + 32
        else:
            val = temp_c
        return f"{val:.1f}"

    def get_spinner_ids(self):
        if not self.root: return None, None
        monitor_screen = self.root.get_screen('monitor')
        prod_id = monitor_screen.ids.spinner_product.text
        amb_id = monitor_screen.ids.spinner_ambient.text
        return prod_id, amb_id

    def setup_graph(self):
        chart_screen = self.root.get_screen('chart')
        graph = chart_screen.ids.main_graph 
        
        graph.xlabel = f'Time ({self.frequency_unit})' 
        
        graph.y_grid_label = True
        graph.precision = '%0.0f' 
        graph.x_grid_label = True
        graph.x_ticks_minor = 0
        
        # --- DYNAMIC Y-AXIS (Start Default) ---
        graph.ymin = 0
        graph.ymax = 40
        # Calculate ticks so we always have ~6 divisions
        graph.y_ticks_major = (graph.ymax - graph.ymin) / 6
        
        # --- DYNAMIC X-AXIS (Start Default) ---
        graph.x_ticks_major = 20 
        
        # Reset plots
        for plot in graph.plots:
            graph.remove_plot(plot)
            
        self.plot_product = MeshLinePlot(color=[1, 1, 0, 1])  # Yellow
        self.plot_ambient = MeshLinePlot(color=[0, 1, 0, 1])  # Green
        
        graph.add_plot(self.plot_product)
        graph.add_plot(self.plot_ambient)
        self.load_history_to_graph()

    def load_history_to_graph(self):
        if not self.root: return
        prod_id, amb_id = self.get_spinner_ids()
        pts_prod, pts_amb = [], []
        
        # Reset local trackers before recalculating from CSV
        self.prod_min = None
        self.prod_max = None
        self.amb_min = None
        self.amb_max = None
        
        try:
            if os.path.exists(settings.csv_file):
                with open(settings.csv_file, 'r') as f:
                    reader = csv.reader(f)
                    next(reader, None)
                    start_time = None
                    
                    for row in reader:
                        if len(row) < 3: continue
                        ts_str, s_id, temp_c_str = row
                        try:
                            temp_val = float(temp_c_str)
                            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError: continue

                        if start_time is None: start_time = dt
                        
                        x_val = (dt - start_time).total_seconds() / self.time_factor
                        
                        if self.units == 'F':
                            temp_val = (temp_val * 9/5) + 32

                        if s_id == prod_id: 
                            pts_prod.append((x_val, temp_val))
                            # Update Product Min/Max
                            if self.prod_min is None or temp_val < self.prod_min: self.prod_min = temp_val
                            if self.prod_max is None or temp_val > self.prod_max: self.prod_max = temp_val
                            
                        elif s_id == amb_id: 
                            pts_amb.append((x_val, temp_val))
                            # Update Ambient Min/Max
                            if self.amb_min is None or temp_val < self.amb_min: self.amb_min = temp_val
                            if self.amb_max is None or temp_val > self.amb_max: self.amb_max = temp_val
                            
            self.plot_product.points = pts_prod
            self.plot_ambient.points = pts_amb
            
            # Update Display Strings
            if self.prod_min is not None:
                self.product_range = f"Range: {self.prod_min:.1f} - {self.prod_max:.1f}"
            else:
                self.product_range = "Range: --.- - --.-"
                
            if self.amb_min is not None:
                self.ambient_range = f"Range: {self.amb_min:.1f} - {self.amb_max:.1f}"
            else:
                self.ambient_range = "Range: --.- - --.-"
            
            if pts_prod or pts_amb:
                all_pts = pts_prod + pts_amb
                
                chart_screen = self.root.get_screen('chart')
                graph = chart_screen.ids.main_graph
                
                # --- DYNAMIC SCALING (X & Y) ---
                max_x = max(p[0] for p in all_pts)
                min_y = min(p[1] for p in all_pts)
                max_y = max(p[1] for p in all_pts)
                
                graph.xmax = max(100, max_x + 10)
                graph.ymax = max_y + 5
                graph.ymin = max(0, min_y - 5)
                
                # Dynamic Ticks: Always keep roughly 6 labels
                graph.x_ticks_major = int(graph.xmax / 6)
                graph.y_ticks_major = (graph.ymax - graph.ymin) / 6
                
        except Exception as e:
            print(f"Error loading history: {e}")

    def update_display_only(self, dt=0):
        if not self.root: return
        prod_id, amb_id = self.get_spinner_ids()
        for sensor in self.sensors:
            try:
                temp_c = sensor.get_temperature()
                if sensor.id == prod_id: 
                    self.product_temp = self.get_temp_display(temp_c)
                elif sensor.id == amb_id: 
                    self.ambient_temp = self.get_temp_display(temp_c)
            except: pass

    def log_data(self, dt=0):
        if not self.root: return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prod_id, amb_id = self.get_spinner_ids()
        data_rows = []
        
        current_x = 0
        if self.plot_product.points:
            current_x = self.plot_product.points[-1][0] + self.log_interval
        elif self.plot_ambient.points:
            current_x = self.plot_ambient.points[-1][0] + self.log_interval

        for sensor in self.sensors:
            try:
                temp_c = sensor.get_temperature()
                data_rows.append([timestamp, sensor.id, temp_c])
                
                plot_val = temp_c
                if self.units == 'F':
                    plot_val = (temp_c * 9/5) + 32

                if sensor.id == prod_id:
                    self.plot_product.points.append((current_x, plot_val))
                    # Live Update Product Min/Max
                    if self.prod_min is None or plot_val < self.prod_min: self.prod_min = plot_val
                    if self.prod_max is None or plot_val > self.prod_max: self.prod_max = plot_val
                    self.product_range = f"Range: {self.prod_min:.1f} - {self.prod_max:.1f}"
                    
                elif sensor.id == amb_id:
                    self.plot_ambient.points.append((current_x, plot_val))
                    # Live Update Ambient Min/Max
                    if self.amb_min is None or plot_val < self.amb_min: self.amb_min = plot_val
                    if self.amb_max is None or plot_val > self.amb_max: self.amb_max = plot_val
                    self.ambient_range = f"Range: {self.amb_min:.1f} - {self.amb_max:.1f}"
                    
            except: pass
        
        with open(settings.csv_file, 'a', newline='') as f:
            csv.writer(f).writerows(data_rows)
            
        # --- DYNAMIC UPDATE ---
        chart_screen = self.root.get_screen('chart')
        graph = chart_screen.ids.main_graph
        
        # 1. Update X-Axis (if needed)
        if current_x > graph.xmax:
            graph.xmax = current_x + 20
            graph.x_ticks_major = int(graph.xmax / 6)
            
        # 2. Update Y-Axis (if needed)
        # Check all sensors to see if we breached the current view
        # (This is more efficient than scanning the whole list every second)
        current_max_y = graph.ymax
        current_min_y = graph.ymin
        needs_y_update = False
        
        # Collect recent plot values to check bounds
        # We only check the ones we just added to keep it fast
        recent_values = []
        if self.plot_product.points: recent_values.append(self.plot_product.points[-1][1])
        if self.plot_ambient.points: recent_values.append(self.plot_ambient.points[-1][1])
        
        for val in recent_values:
            if val > (current_max_y - 1): # Buffer of 1
                graph.ymax = val + 5
                needs_y_update = True
            if val < (current_min_y + 1): # Buffer of 1
                graph.ymin = max(0, val - 5)
                needs_y_update = True
                
        if needs_y_update:
            graph.y_ticks_major = (graph.ymax - graph.ymin) / 6
            
    def refresh_graph_mapping(self):
        self.load_history_to_graph()

if __name__ == '__main__':
    TempMonitorApp().run()
