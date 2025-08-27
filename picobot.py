import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pygetwindow as gw
import time
import serial
import serial.tools.list_ports
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
        # Try to auto-select the Pico DATA port on startup (force override any prior selection)
        self.auto_select_pico_port_async(force=True)

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

        # --- Options ---
        self.pin_var = tk.BooleanVar(value=True)
        self.pin_check = tk.Checkbutton(root, text="Pin window (always on top)", variable=self.pin_var, command=self.toggle_always_on_top)
        self.pin_check.pack(padx=10, anchor="w")
        # Default to always-on-top on first launch; load_config may override
        try:
            self.root.attributes("-topmost", True)
        except Exception:
            pass

        # --- Controls ---
        self.control_frame = tk.Frame(root)
        self.control_frame.pack(padx=10, pady=5, fill="x")
        self.start_button = tk.Button(self.control_frame, text="START", command=self.start_macro, font=("Helvetica", 12, "bold"), bg="#4CAF50", fg="white", state=tk.NORMAL)
        self.start_button.pack(side=tk.LEFT, fill="x", expand=True)

        # --- Status Bar ---
        self.status_text = tk.StringVar(value="Status: Idle. Click START to begin. Switch windows to stop.")
        self.status_bar = tk.Label(root, textvariable=self.status_text, relief=tk.SUNKEN, anchor="w", padx=5)
        self.status_bar.pack(side=tk.BOTTOM, fill="x")

        # --- Initial Setup ---
        self.load_config()
        self.refresh_windows() # Refresh windows after loading config

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.selected_window.set(config.get("last_window", ""))
                    self.macro_folder_path.set(config.get("last_folder", "No folder selected."))
                    # Apply always-on-top preference
                    aot = config.get("always_on_top", True)
                    self.pin_var.set(aot)
                    try:
                        self.root.attributes("-topmost", bool(aot))
                    except Exception:
                        pass
                    print("Configuration loaded.")
        except Exception as e:
            print(f"Could not load config file: {e}")

    def save_config(self, event=None):
        config = {
            "last_window": self.selected_window.get(),
            "last_folder": self.macro_folder_path.get(),
            "always_on_top": bool(self.pin_var.get()),
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            print("Configuration saved.")
        except Exception as e:
            print(f"Could not save config file: {e}")

    def toggle_always_on_top(self):
        try:
            self.root.attributes("-topmost", bool(self.pin_var.get()))
        except Exception as e:
            print(f"Could not set always-on-top: {e}")
        # Persist preference
        self.save_config()

    def select_macro_folder(self):
        folderpath = filedialog.askdirectory(title="Select Folder Containing Macros")
        if folderpath:
            self.macro_folder_path.set(folderpath)
            self.save_config()

    def start_macro(self):
        if self.is_playing:
            return
        
        port = self.selected_port.get()
        window_title = self.selected_window.get()
        macro_folder = self.macro_folder_path.get()

        if (not port) or ("No COM" in port) or not window_title or ("No folder" in macro_folder):
            messagebox.showerror("Error", "Please select a COM port, a target window, and a macro folder.")
            return

        try:
            if not [f for f in os.listdir(macro_folder) if f.endswith('.txt')]:
                messagebox.showerror("Error", "No '.txt' macro files found in the folder.")
                return
        except Exception as e:
            messagebox.showerror("Folder Error", f"Could not read macro folder.\nError: {e}")
            return

        print("Starting macro loop...")
        self.start_button.config(state=tk.DISABLED)
        self.macro_thread = threading.Thread(target=self.play_macro_thread, args=(port, window_title, macro_folder))
        self.macro_thread.daemon = True
        self.macro_thread.start()

    def interruptible_sleep(self, duration):
        end_time = time.time() + duration
        while time.time() < end_time:
            if not self.is_playing:
                return False
            time.sleep(0.01)
        return True

    def find_data_port(self, exclude_port=None):
        """Scan COM ports to find the Pico DATA CDC port by eliciting PICO_READY.
        Returns the port string if found, else None.
        """
        candidates = list(serial.tools.list_ports.comports())
        for info in candidates:
            p = info.device
            if exclude_port and p == exclude_port:
                continue
            try:
                ser = serial.Serial(p, 115200, timeout=0.5, write_timeout=0.5)
                try:
                    ser.dtr = False
                    time.sleep(0.05)
                    ser.dtr = True
                    ser.rts = False
                except Exception:
                    pass
                time.sleep(0.1)

                got_ready = False
                found_console = False

                # Read a couple of lines, see if console banner appears or we already have PICO_READY
                t0 = time.time()
                while time.time() - t0 < 1.0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line:
                        continue
                    lower = line.lower()
                    if ("circuitpython" in lower) or ("repl" in lower) or lower.startswith(">>>"):
                        found_console = True
                        break
                    if line == "PICO_READY":
                        got_ready = True
                        break

                if not got_ready and not found_console:
                    try:
                        ser.write(b"hello|handshake\n")
                        ser.flush()
                    except Exception:
                        pass
                    t1 = time.time()
                    while time.time() - t1 < 1.5:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line == "PICO_READY":
                            got_ready = True
                            break
                        if line:
                            lower = line.lower()
                            if ("circuitpython" in lower) or ("repl" in lower) or lower.startswith(">>>"):
                                found_console = True
                                break

                ser.close()
                if got_ready and not found_console:
                    return p
            except Exception:
                continue
        return None

    def play_macro_thread(self, port, window_title, macro_folder):
        self.is_playing = True
        self.status_text.set("Status: Playing...")
        self.keys_currently_down.clear()

        try:
            target_windows = gw.getWindowsWithTitle(window_title)
            if not target_windows:
                print(f"Error: Target window '{window_title}' not found.")
                self.is_playing = False
                # Ensure GUI resets cleanly
                self.root.after(0, self.on_macro_thread_exit)
                return
            target_windows[0].activate()
        except Exception as e:
            print(f"Error activating window: {e}")
            self.is_playing = False
            self.root.after(0, self.on_macro_thread_exit)
            return
        
        time.sleep(1)

        while self.is_playing:
            # 1. Get all macro files and create a new randomized playlist
            try:
                all_macro_files = [f for f in os.listdir(macro_folder) if f.endswith('.txt')]
                if not all_macro_files:
                    print("Error: No '.txt' files found in folder. Stopping loop.")
                    break
                
                # Separate START_ files from the rest
                start_files = [f for f in all_macro_files if f.startswith('START_')]
                other_files = [f for f in all_macro_files if not f.startswith('START_')]

                # Shuffle both lists independently
                random.shuffle(start_files)
                random.shuffle(other_files)

                # Combine them, with START_ files first
                current_playlist = start_files + other_files
                print(f"\n--- New randomized playlist created: {current_playlist} ---")

            except Exception as e:
                print(f"Error creating playlist: {e}. Stopping loop.")
                break

            # 2. Play through the current playlist
            for chosen_macro_name in current_playlist:
                if not self.is_playing:
                    break

                print(f"--- Playing from sequence: {chosen_macro_name} ---")
                macro_file_path = os.path.join(macro_folder, chosen_macro_name)
                
                events = self.parse_macro_file(macro_file_path)
                if events is None:
                    continue

                ser = None
                try:
                    ser = serial.Serial(port, 115200, timeout=5) # Generous timeout for handshake
                    # Ensure DTR toggled so usb_cdc.data.connected goes True on the Pico
                    try:
                        ser.dtr = False
                        time.sleep(0.05)
                        ser.dtr = True
                        ser.rts = False
                    except Exception:
                        pass
                    time.sleep(0.1)

                    # --- Handshake on DATA port --- #
                    print("Waiting for PICO_READY signal...")
                    ready_signal_received = False
                    start_time = time.time()
                    hello_sent = False
                    try:
                        ser.timeout = 0.2
                    except Exception:
                        pass
                    while time.time() - start_time < 12: # up to 12s total for handshake
                        line = ser.readline().decode('utf-8').strip()
                        if line == "PICO_READY":
                            print("PICO_READY signal received. Starting macro.")
                            ready_signal_received = True
                            break
                        elif line:
                            print(f"Pico startup message: {line}") # Log other messages
                            lower = line.lower()
                            if ("circuitpython" in lower) or ("repl" in lower) or lower.startswith(">>>"):
                                print("Detected the console CDC port. Please select the other Pico COM port (Data).")
                                self.is_playing = False
                                break

                        # After 1 second with no PICO_READY, try explicit HELLO on DATA port
                        if (not hello_sent) and (time.time() - start_time >= 1.0):
                            try:
                                ser.write(b"hello|handshake\n")
                                ser.flush()
                                hello_sent = True
                            except Exception:
                                pass
                    
                    if not ready_signal_received:
                        # Try auto-detect other COM ports for DATA port
                        auto_port = self.find_data_port(exclude_port=port)
                        if auto_port and auto_port != port:
                            print(f"Auto-detected Pico DATA port: {auto_port}. Retrying handshake...")
                            try:
                                ser.close()
                            except Exception:
                                pass
                            port = auto_port
                            # Retry once on detected port
                            try:
                                ser = serial.Serial(port, 115200, timeout=5)
                                try:
                                    ser.dtr = False
                                    time.sleep(0.05)
                                    ser.dtr = True
                                    ser.rts = False
                                except Exception:
                                    pass
                                time.sleep(0.1)
                                print("Waiting for PICO_READY signal...")
                                ready_signal_received = False
                                start_time = time.time()
                                hello_sent = False
                                try:
                                    ser.timeout = 0.2
                                except Exception:
                                    pass
                                while time.time() - start_time < 12:
                                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                                    if line == "PICO_READY":
                                        print("PICO_READY signal received. Starting macro.")
                                        ready_signal_received = True
                                        break
                                    elif line:
                                        print(f"Pico startup message: {line}")
                                    if (not hello_sent) and (time.time() - start_time >= 1.0):
                                        try:
                                            ser.write(b"hello|handshake\n")
                                            ser.flush()
                                            hello_sent = True
                                        except Exception:
                                            pass
                            except Exception as _:
                                ready_signal_received = False

                        if not ready_signal_received:
                            print("Error: Timed out waiting for PICO_READY signal.")
                            self.is_playing = False
                            try:
                                ser.close()
                            except Exception:
                                pass
                            continue # Skip to the next macro file
                    for i, event in enumerate(events):
                        # --- Pre-command checks ---
                        # 1. Check for manual stop
                        if not self.is_playing:
                            break

                        # 2. Check if the active window has changed
                        try:
                            active_window_title = gw.getActiveWindowTitle()
                            if active_window_title != window_title:
                                print(f"\nWindow focus lost. Expected '{window_title}', got '{active_window_title}'. Stopping macro.")
                                self.is_playing = False # This will trigger a clean stop
                                break
                        except Exception as e:
                            print(f"Could not get active window title: {e}. Stopping macro.")
                            self.is_playing = False
                            break

                        # --- Execute command ---
                        # Apply delay before this event
                        if i > 0:
                            delay = event['time'] - events[i-1]['time']
                            if not self.interruptible_sleep(delay):
                                break # Stop signal received during sleep

                        # Send command and wait for ACK
                        command = f"{event['type']}|{event['key']}\n"
                        ser.write(command.encode('utf-8'))
                        try:
                            ack = ser.readline().decode('utf-8').strip()
                            if ack != "ACK":
                                print(f"Warning: Expected ACK, got '{ack}'. Stopping to prevent de-sync.")
                                self.is_playing = False
                                break
                        except serial.SerialTimeoutException:
                            print("Error: Timeout waiting for ACK from Pico. Stopping.")
                            self.is_playing = False
                            break

                        # Update key state
                        if event['type'] == 'down':
                            self.keys_currently_down.add(event['key'])
                        elif event['key'] in self.keys_currently_down:
                            self.keys_currently_down.discard(event['key'])

                except serial.SerialException as e:
                    print(f"Serial Error: {e}. Stopping macro.")
                    self.is_playing = False
                finally:
                    if ser and self.keys_currently_down:
                        print("Releasing stuck keys...")
                        for key in list(self.keys_currently_down):
                            command = f"up|{key}\n"
                            ser.write(command.encode('utf-8'))
                            try:
                                ser.readline() # Wait for ACK
                                print(f"Sent release for {key} and received ACK.")
                            except serial.SerialTimeoutException:
                                print(f"Warning: Timeout on final release ACK for key '{key}'.")
                        self.keys_currently_down.clear()
                    if ser:
                        ser.close()

            # Small delay before starting the next full loop
            if self.is_playing:
                time.sleep(1)
        
        print("Macro thread is finishing.")
        # Schedule the final GUI update on the main thread
        self.root.after(0, self.on_macro_thread_exit)

    def on_macro_thread_exit(self):
        """Safely updates GUI elements from the main thread after the macro thread has finished."""
        self.is_playing = False # Ensure state is final
        self.status_text.set("Status: Stopped. Ready to start.")
        self.start_button.config(state=tk.NORMAL)
        print("GUI updated. Macro has fully stopped.")

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

    def auto_select_pico_port_async(self, force=False):
        """Background auto-detect of the Pico DATA port. If found, select it in the combobox.
        force=True will always set the detected port; otherwise only when selection is empty/invalid.
        """
        def worker():
            # 1) Quick heuristic: interface index 2 usually maps to DATA CDC (location endswith 'x.2')
            port = self.quick_guess_pico_data_port()
            # 2) Fallback to active handshake probing across ports
            if not port:
                port = self.find_data_port()
            if port:
                self.root.after(0, lambda p=port: self._set_selected_port_if_appropriate(p, force))
            else:
                # Leave selection empty and inform user
                self.root.after(0, lambda: self.status_text.set("Status: No Pico DATA port detected. Connect and click Refresh."))
        threading.Thread(target=worker, daemon=True).start()

    def quick_guess_pico_data_port(self):
        """Return device name of Pico DATA port using USB interface location hint (x.2), else None."""
        try:
            for info in serial.tools.list_ports.comports():
                loc = getattr(info, 'location', '') or ''
                # On Windows, CircuitPython typically enumerates CDC console as x.0 and DATA as x.2
                if loc.endswith('x.2'):
                    return info.device
        except Exception:
            pass
        return None

    def _set_selected_port_if_appropriate(self, port, force):
        try:
            values = list(self.port_menu['values'])
        except Exception:
            values = []
        if port not in values:
            values.append(port)
            self.port_menu['values'] = values
        current = self.selected_port.get()
        if force or (not current) or ("No COM" in current) or (current not in values):
            self.selected_port.set(port)
            try:
                self.status_text.set(f"Status: Auto-selected Pico DATA port {port}.")
            except Exception:
                pass

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        # Populate list but do not auto-select any port
        self.port_menu['values'] = ports
        try:
            self.port_menu.set("")  # clear any previous selection in the widget
        except Exception:
            pass
        self.selected_port.set("")   # ensure state variable is empty
        # After listing, kick off background auto-detection to pick the DATA port if present
        self.auto_select_pico_port_async(force=False)

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
