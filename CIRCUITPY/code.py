import time
import usb_hid
import usb_cdc
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# Add a delay to give the USB host time to get ready.
# This helps prevent a race condition on startup.
time.sleep(1)


# A comprehensive mapping from the string names used by the 'keyboard' library
# to the Keycode objects that CircuitPython's HID library understands.
KEY_MAP = {
    # Letters (Lowercase)
    'a': Keycode.A, 'b': Keycode.B, 'c': Keycode.C, 'd': Keycode.D, 'e': Keycode.E,
    'f': Keycode.F, 'g': Keycode.G, 'h': Keycode.H, 'i': Keycode.I, 'j': Keycode.J,
    'k': Keycode.K, 'l': Keycode.L, 'm': Keycode.M, 'n': Keycode.N, 'o': Keycode.O,
    'p': Keycode.P, 'q': Keycode.Q, 'r': Keycode.R, 's': Keycode.S, 't': Keycode.T,
    'u': Keycode.U, 'v': Keycode.V, 'w': Keycode.W, 'x': Keycode.X, 'y': Keycode.Y,
    'z': Keycode.Z,

    # Numbers (Top Row)
    '1': Keycode.ONE, '2': Keycode.TWO, '3': Keycode.THREE, '4': Keycode.FOUR,
    '5': Keycode.FIVE, '6': Keycode.SIX, '7': Keycode.SEVEN, '8': Keycode.EIGHT,
    '9': Keycode.NINE, '0': Keycode.ZERO,

    # Function Keys
    'f1': Keycode.F1, 'f2': Keycode.F2, 'f3': Keycode.F3, 'f4': Keycode.F4,
    'f5': Keycode.F5, 'f6': Keycode.F6, 'f7': Keycode.F7, 'f8': Keycode.F8,
    'f9': Keycode.F9, 'f10': Keycode.F10, 'f11': Keycode.F11, 'f12': Keycode.F12,

    # Punctuation and Symbols
    'enter': Keycode.ENTER,
    'esc': Keycode.ESCAPE,
    'backspace': Keycode.BACKSPACE,
    'tab': Keycode.TAB,
    'space': Keycode.SPACE,
    '-': Keycode.MINUS,
    '=': Keycode.EQUALS,
    '[': Keycode.LEFT_BRACKET,
    ']': Keycode.RIGHT_BRACKET,
    '\\': Keycode.BACKSLASH,
    ';': Keycode.SEMICOLON,
    "'": Keycode.QUOTE,
    '`': Keycode.GRAVE_ACCENT,
    ',': Keycode.COMMA,
    '.': Keycode.PERIOD,
    '/': Keycode.FORWARD_SLASH,

    # Modifier Keys
    'caps lock': Keycode.CAPS_LOCK,
    'shift': Keycode.LEFT_SHIFT,
    'ctrl': Keycode.LEFT_CONTROL,
    'alt': Keycode.LEFT_ALT,
    'cmd': Keycode.LEFT_GUI,
    'windows': Keycode.LEFT_GUI,
    'right shift': Keycode.RIGHT_SHIFT,
    'right ctrl': Keycode.RIGHT_CONTROL,
    'right alt': Keycode.RIGHT_ALT,

    # Navigation and Control Keys
    'print screen': Keycode.PRINT_SCREEN,
    'scroll lock': Keycode.SCROLL_LOCK,
    'pause': Keycode.PAUSE,
    'insert': Keycode.INSERT,
    'home': Keycode.HOME,
    'page up': Keycode.PAGE_UP,
    'delete': Keycode.DELETE,
    'end': Keycode.END,
    'page down': Keycode.PAGE_DOWN,
    'right': Keycode.RIGHT_ARROW,
    'left': Keycode.LEFT_ARROW,
    'down': Keycode.DOWN_ARROW,
    'up': Keycode.UP_ARROW,
}

print("Pico HID Command Executor")

try:
    keyboard = Keyboard(usb_hid.devices)
    print("HID Keyboard initialized. Ready for commands.")
except Exception as e:
    print(f"Error initializing HID Keyboard: {e}")
    while True: pass

# Track DATA serial connection state to re-emit readiness on new connections
data_was_connected = usb_cdc.data.connected
# Buffer for assembling newline-terminated commands from DATA port
rx_buffer = b""
# Periodic PICO_READY re-emit control
last_ready_sent = 0.0
commands_seen = False

# --- Main Loop ---
while True:
    # Emit PICO_READY on new DATA port connection
    now_connected = usb_cdc.data.connected
    if now_connected and not data_was_connected:
        try:
            usb_cdc.data.write(b"PICO_READY\n")
            print("[console] DATA connected; sent PICO_READY on DATA")
            last_ready_sent = time.monotonic()
            commands_seen = False
        except Exception:
            pass
    elif (not now_connected) and data_was_connected:
        print("[console] DATA disconnected")
    data_was_connected = now_connected

    # If still connected but host hasn't sent any command yet, periodically re-emit PICO_READY
    if now_connected and not commands_seen:
        if (time.monotonic() - last_ready_sent) >= 1.0:
            try:
                usb_cdc.data.write(b"PICO_READY\n")
                last_ready_sent = time.monotonic()
            except Exception:
                pass

    # Check if there's any data waiting in the DATA USB serial buffer.
    if usb_cdc.data.in_waiting > 0:
        # Read available bytes and append to buffer
        try:
            chunk = usb_cdc.data.read(usb_cdc.data.in_waiting)
        except Exception:
            chunk = None
        if chunk:
            rx_buffer += chunk

        # Process any complete lines
        while b"\n" in rx_buffer:
            line, rx_buffer = rx_buffer.split(b"\n", 1)
            command_line = line.decode("utf-8").strip()

            if command_line:
                # print(f"Processing: '{command_line}'") # Optional: for debugging
                try:
                    command, key_str = command_line.split('|', 1)
                    cmd = command.strip().lower()
                    key_name = key_str.strip().lower()

                    # Explicit handshake: respond to HELLO from host on DATA port
                    if cmd == "hello":
                        try:
                            usb_cdc.data.write(b"PICO_READY\n")
                            commands_seen = True
                        except Exception:
                            pass
                        continue

                    key_to_act = KEY_MAP.get(key_name)

                    if key_to_act:
                        if cmd == "down":
                            keyboard.press(key_to_act)
                        elif cmd == "up":
                            keyboard.release(key_to_act)
                    else:
                        print(f"Warning: Key '{key_str}' not found in KEY_MAP.")

                    commands_seen = True
                    # After processing, send an acknowledgement back to the host over DATA port.
                    try:
                        usb_cdc.data.write(b"ACK\n")
                    except Exception:
                        pass

                except (ValueError, IndexError) as e:
                    print(f"Could not parse command: '{command_line}'. Error: {e}")
    time.sleep(0.01)
