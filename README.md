# picobot
HID keyboard macro project

## Disclaimer

This project is purely for educational purposes. 
Please use the following scripts at your own discretion and adhere to the official TOS agreements in whichever games you are using this macro/bot for. 
I will not be held liable for any damages or punishments that may come. 

## Requirements

Microcontroller

```
- Raspberry Pi Pico W (or any other microcontroller device that supports CircuitPython)
  - CircuitPython
  - Adafruit HID library
  - code.py
  - boot.py
```

Python + Package Dependencies on your Computer

```
- keyboard
- pygetwindow
- pyserial
```

## Usage Guide

- Make sure to run the scripts in administrator mode. 
- Each macro loop cycles through available macro.txt files in a randomized sequence in the selected macro folder. 
- If a macro file is prefixed with "START_", it will always be the first to play in a macro sequence. 
- Record the macros you need using the `macro_recorder.py` script. 
- Run `picobot.py`, configure your settings and click the START button to start a macro loop from a selected macro folder.
- To stop the macro, simply tab out of the target active window. A detection system is in place to stop the macro on active window change. 
