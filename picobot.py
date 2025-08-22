import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pygetwindow as gw
import time
import serial
import serial.tools.list_ports
import keyboard
import threading
import os
import random
import json

# --- Configuration File ---
CONFIG_FILE = "config.json"

class MacroControllerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pico Continuous Macro Controller")
        self.root.geometry("500x380") # Increased height for buttons

        # --- State Variables ---
        self.is_playing = False
        self.macro_thread = None
        self.keys_currently_down = set()

        # --- Pico Connection ---
        self.pico_frame = tk.LabelFrame(root, text="1. Select Pico COM Port", padx=10, pady=10)
        self.pico_frame.pack(padx=10, pady=10, fill="x")
        self.selected_port = tk.StringVar(root)
        self.port_menu = ttk.Combobox(self.pico_frame, textvariable=self.selected_port, state="readonly")
        self.port_menu.pack(side=tk.LEFT, fill="x", expand=True)
        self.refresh_ports_button = tk.Button(self.pico_frame, text="Refresh", command=self.refresh_ports)
        self.refresh_ports_button.pack(side=tk.RIGHT, padx=(10, 0))
        self.refresh_ports()

        # --- Window Selection ---
        self.window_frame = tk.LabelFrame(root, text="2. Select Target Window", padx=10, pady=10)
        self.window_frame.pack(padx=10, pady=10, fill="x")
        self.selected_window = tk.StringVar(root)
        self.window_menu = ttk.Combobox(self.window_frame, textvariable=self.selected_window, state="readonly")
        self.window_menu.pack(side=tk.LEFT, fill="x", expand=True)
        self.window_menu.bind("<<ComboboxSelected>>", self.save_config) # Save on change
        self.refresh_win_button = tk.Button(self.window_frame, text="Refresh", command=self.refresh_windows)
        self.refresh_win_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # --- Macro Folder Selection ---
        self.macro_frame = tk.LabelFrame(root, text="3. Select Macro Folder", padx=10, pady=10)
        self.macro_frame.pack(padx=10, pady=10, fill="x")
        self.macro_folder_path = tk.StringVar(value="No folder selected.")
        self.select_button = tk.Button(self.macro_frame, text="Browse Folder...", command=self.select_macro_folder)
        self.select_button.pack(side=tk.LEFT, padx=(0, 10))
        self.macro_label = tk.Label(self.macro_frame, textvariable=self.macro_folder_path, anchor="w")
        self.macro_label.pack(side=tk.LEFT, fill="x", expand=True)

        # --- NEW: Control Buttons ---
        self.control_frame = tk.Frame(root)
        self.control_frame.pack(padx=10, pady=5, fill="x")
        self.start_button = tk.Button(self.control_frame, text="START", command=self.start_macro, font=("Helvetica", 12, "bold"), bg="#4CAF50", fg="white", state=tk.NORMAL)
        self.start_button.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 5))
        self.stop_button = tk.Button(self.control_frame, text="STOP", command=self.stop_macro, font=("Helvetica", 12, "bold"), bg="#F44336", fg="white", state=tk.DISABLED)
        self.stop_button.pack(side=tk.RIGHT, fill="x", expand=True, padx=(5, 0))

        # --- Status Bar ---
        self.status_text = tk.StringVar(value="Status: Idle. Use buttons or 'Pause' key to start/stop.")
        self.status_bar = tk.Label(root, textvariable=self.status_text, relief=tk.SUNKEN, anchor="w", padx=5)
        self.status_bar.pack(side=tk.BOTTOM, fill="x")

        # --- Initial Setup ---
        self.load_config()
        self.refresh_windows() # Refresh windows after loading config
        self.setup_hotkey()

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.selected_window.set(config.get("last_window", ""))
                    self.macro_folder_path.set(config.get("last_folder", "No folder selected."))
                    print("Configuration loaded.")
        except Exception as e:
            print(f"Could not load config file: {e}")

    def save_config(self, event=None):
        config = {
            "last_window": self.selected_window.get(),
            "last_folder": self.macro_folder_path.get()
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            print("Configuration saved.")
        except Exception as e:
            print(f"Could not save config file: {e}")

    def setup_hotkey(self):
        keyboard.add_hotkey('pause', self.toggle_macro, suppress=True)

    def select_macro_folder(self):
        folderpath = filedialog.askdirectory(title="Select Folder Containing Macros")
        if folderpath:
            self.macro_folder_path.set(folderpath)
            self.save_config()

    def toggle_macro(self):
        if self.is_playing:
            self.stop_macro()
        else:
            self.start_macro()

    def start_macro(self):
        if self.is_playing: return
        
        port = self.selected_port.get()
        window_title = self.selected_window.get()
        macro_folder = self.macro_folder_path.get()

        if "No COM" in port or not window_title or "No folder" in macro_folder:
            messagebox.showerror("Error", "Please select a COM port, a target window, and a macro folder.")
            return

        try:
            if not [f for f in os.listdir(macro_folder) if f.endswith('.txt')]:
                messagebox.showerror("Error", f"No '.txt' macro files found in the folder.")
                return
        except Exception as e:
            messagebox.showerror("Folder Error", f"Could not read macro folder.\nError: {e}")
            return

        print("Starting macro loop...")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.macro_thread = threading.Thread(target=self.play_macro_thread, args=(port, window_title, macro_folder))
        self.macro_thread.daemon = True
        self.macro_thread.start()

    def stop_macro(self):
        if not self.is_playing: return
        print("Stopping macro loop...")
        self.is_playing = False
        self.status_text.set("Status: Stopping...")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def interruptible_sleep(self, duration):
        end_time = time.time() + duration
        while time.time() < end_time:
            if not self.is_playing:
                return False
            time.sleep(0.01)
        return True

    def play_macro_thread(self, port, window_title, macro_folder):
        self.is_playing = True
        self.status_text.set("Status: Playing...")
        self.keys_currently_down.clear()

        try:
            target_windows = gw.getWindowsWithTitle(window_title)
            if not target_windows:
                print(f"Error: Target window '{window_title}' not found.")
                self.stop_macro(); return
            target_windows[0].activate()
        except Exception as e:
            print(f"Error activating window: {e}")
            self.stop_macro(); return
        
        time.sleep(1)
        
        while self.is_playing:
            time.sleep(0.001)
            try:
                macro_files = [f for f in os.listdir(macro_folder) if f.endswith('.txt')]
                if not macro_files:
                    print("Error: No '.txt' files found in folder. Stopping loop.")
                    break
                chosen_macro_name = random.choice(macro_files)
                macro_file_path = os.path.join(macro_folder, chosen_macro_name)
                print(f"\n--- Starting new macro: {chosen_macro_name} ---")
            except Exception as e:
                print(f"Error reading macro folder: {e}. Stopping loop.")
                break

            events = self.parse_macro_file(macro_file_path)
            if not events: continue

            ser = None
            try:
                ser = serial.Serial(port, 115200, timeout=1)
                for i, event in enumerate(events):
                    if not self.is_playing: break
                    if i > 0:
                        delay = event['time'] - events[i-1]['time']
                        if not self.interruptible_sleep(delay):
                            break
                    if not self.is_playing: break
                    command = f"{event['type']}|{event['key']}\n"
                    ser.write(command.encode('utf-8'))
                    if event['type'] == 'down': self.keys_currently_down.add(event['key'])
                    elif event['type'] == 'up': self.keys_currently_down.discard(event['key'])
            except serial.SerialException as e:
                print(f"Serial Error during macro '{chosen_macro_name}': {e}. Trying next macro.")
                time.sleep(1)
            finally:
                if ser:
                    if self.keys_currently_down:
                        print(f"Releasing stuck keys from '{chosen_macro_name}': {self.keys_currently_down}")
                        for key in list(self.keys_currently_down):
                            ser.write(f"up|{key}\n".encode('utf-8'))
                            time.sleep(0.01)
                        self.keys_currently_down.clear()
                    ser.close()
            if not self.is_playing: break
        
        print("Macro loop finished or was stopped.")
        self.stop_macro()

    def parse_macro_file(self, filename):
        events = []
        try:
            with open(filename, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 3:
                        timestamp, event_type, key = parts
                        events.append({'time': float(timestamp), 'type': event_type, 'key': key})
        except Exception as e:
            print(f"Warning: Could not parse macro file '{filename}'.\nError: {e}")
            return None
        return events

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_menu['values'] = ports if ports else ["No COM ports found"]
        if ports: self.port_menu.set(ports[0])
        else: self.port_menu.set("No COM ports found")

    def refresh_windows(self):
        window_list = [title for title in gw.getAllTitles() if title]
        self.window_menu['values'] = window_list if window_list else ["No windows found"]
        # Try to re-select the saved window if it's in the list
        saved_window = self.selected_window.get()
        if saved_window and saved_window in window_list:
            self.window_menu.set(saved_window)
        elif window_list:
            self.window_menu.set(window_list[0])
        else:
            self.window_menu.set("No windows found")

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroControllerApp(root)
    root.mainloop()