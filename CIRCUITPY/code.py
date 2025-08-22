import sys
import supervisor
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

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

# --- Main Loop ---
while True:
    # Check if there's any data waiting in the USB serial buffer.
    if supervisor.runtime.serial_bytes_available:
        # Read all available bytes at once.
        data = sys.stdin.read(supervisor.runtime.serial_bytes_available)
        # The last command might be incomplete, so we look for the last full line.
        lines = data.strip().split('\n')
        if lines:
            # Get the very last complete command received.
            last_command = lines[-1]
            print(f"Processing last command: '{last_command}'")
            try:
                command, key_str = last_command.split('|', 1)
                key_to_act = KEY_MAP.get(key_str.lower())

                if key_to_act:
                    if command == "down":
                        keyboard.press(key_to_act)
                    elif command == "up":
                        keyboard.release(key_to_act)
                else:
                    print(f"Warning: Key '{key_str}' not found in KEY_MAP.")
            except (ValueError, IndexError) as e:
                print(f"Could not parse command: '{last_command}'. Error: {e}")