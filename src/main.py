#!/usr/bin/env python3 
import os
import json
import csv
import time
import sys
import threading
import subprocess
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
from kivy.properties import ObjectProperty, StringProperty, NumericProperty, ListProperty, BooleanProperty
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy_garden.graph import Graph, MeshLinePlot 

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

# --- SCREENS ---
class MonitorScreen(Screen):
    pass

class ChartScreen(Screen):
    pass

# --- NEW TABBED SETTINGS SCREENS ---
class SettingsMasterScreen(Screen):
    btn_3_text = StringProperty("CHECK")
    btn_3_visible = BooleanProperty(False)
    
    btn_4_text = StringProperty("RESTART")
    btn_4_visible = BooleanProperty(False)
    
    current_tab = StringProperty('settings_general')

    def select_tab(self, tab_name):
        self.ids.content_manager.transition = SlideTransition(direction='left')
        self.ids.content_manager.current = tab_name
        self.current_tab = tab_name
        
        # Configure Footer based on Tab
        if tab_name == 'settings_updates':
            self.btn_3_visible = True
            self.btn_4_text = "RESTART"
            self.btn_4_visible = True
        else:
            self.btn_3_visible = False
            self.btn_4_visible = False

    def exit_settings(self):
        self.manager.transition.direction = 'right'
        self.manager.current = 'monitor'

    def show_help(self):
        print(f"[Settings] Help requested for {self.current_tab}")

    def on_btn_3(self):
        # Slot 3: CHECK / INSTALL
        if self.current_tab == 'settings_updates':
            screen = self.ids.content_manager.get_screen('settings_updates')
            if self.btn_3_text == "CHECK":
                screen.check_updates()
            elif self.btn_3_text == "INSTALL":
                screen.install_updates()

    def on_btn_4(self):
        # Slot 4: RESTART
        if self.current_tab == 'settings_updates':
            screen = self.ids.content_manager.get_screen('settings_updates')
            screen.restart_app()

class GeneralSettingsScreen(Screen):
    pass

class UpdatesSettingsScreen(Screen):
    log_text = StringProperty("Ready to check for updates.\n")
    is_working = BooleanProperty(False)
    install_enabled = BooleanProperty(False)

    def check_updates(self):
        self.log_text = "Checking for updates...\n"
        self.is_working = True
        self.install_enabled = False
        threading.Thread(target=self._run_update_process, args=(["--check"], True)).start()

    def install_updates(self):
        self.log_text += "\nStarting Install Process...\n"
        self.is_working = True
        self.install_enabled = False
        threading.Thread(target=self._run_update_process, args=([], False)).start()

    def _run_update_process(self, flags, is_check_mode):
        src_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(src_dir)
        script_path = os.path.join(project_root, "update.sh")

        if not os.path.exists(script_path):
            self._append_log(f"Error: Could not find script at:\n{script_path}")
            self._finish_work(enable_install=False)
            return

        cmd = ["bash", script_path] + flags
        try:
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                bufsize=1
            )

            update_available = False
            
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    self._append_log(line)
                    lower = line.lower()
                    if "update available" in lower or "fast-forward" in lower or "file changed" in lower:
                        update_available = True

            return_code = process.poll()

            if is_check_mode:
                if update_available:
                    self._append_log("\n[Check Complete] Updates available.")
                    self._finish_work(enable_install=True)
                else:
                    self._append_log("\n[Check Complete] System is up to date.")
                    self._finish_work(enable_install=False)
            else:
                if return_code == 0:
                    self._append_log("\n[Success] Update installed. Please restart.")
                else:
                    self._append_log(f"\n[Failed] Process exited with code {return_code}")
                self._finish_work(enable_install=False)

        except Exception as e:
            self._append_log(f"\n[Error] Exception running update: {e}")
            self._finish_work(enable_install=False)

    def _append_log(self, text):
        Clock.schedule_once(lambda dt: self._update_log_text(text))

    def _update_log_text(self, text):
        self.log_text += text

    def _finish_work(self, enable_install):
        def _reset(dt):
            self.is_working = False
            self.install_enabled = enable_install
            
            # Safely fetch the master screen via the app root instead of fragile .parent chains
            app = App.get_running_app()
            if app and app.root and app.root.has_screen('sys_settings'):
                master = app.root.get_screen('sys_settings')
                if enable_install:
                    master.btn_3_text = "INSTALL"
                else:
                    master.btn_3_text = "CHECK"
        Clock.schedule_once(_reset)

    def restart_app(self):
        print("[System] Restarting application...")
        python = sys.executable
        script = os.path.abspath(sys.argv[0])
        args = sys.argv[1:]
        cmd_args = [python, script] + args
        os.execv(python, cmd_args)

class AboutScreen(Screen):
    pass


# --- MAIN APP ---
class TempMonitorApp(App):
    product_temp = StringProperty("--.-")
    ambient_temp = StringProperty("--.-")
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
        """Retrieves sensor IDs from the new General Settings tab"""
        if not self.root: return None, None
        
        try:
            sys_settings = self.root.get_screen('sys_settings')
            gen_screen = sys_settings.ids.content_manager.get_screen('settings_general')
            prod_id = gen_screen.ids.spinner_product.text
            amb_id = gen_screen.ids.spinner_ambient.text
            return prod_id, amb_id
        except Exception as e:
            # Fallback for when the UI is still booting up and hasn't loaded the screen tree
            default_prod = self.sensor_ids[0] if self.sensor_ids else "No Sensor"
            default_amb = self.sensor_ids[1] if len(self.sensor_ids) > 1 else default_prod
            return default_prod, default_amb

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
        current_max_y = graph.ymax
        current_min_y = graph.ymin
        needs_y_update = False
        
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
