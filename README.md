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
```

Python + Package Dependencies on your Computer

```
- keyboard
- pygetwindow
- serial
- pyserial
```

## Usage Guide

Make sure to run the scripts in administrator mode. 

1. Record the macros you need using the `macro_recorder.py` script. 
2. Run `picobot.py`, configure your settings and click the START button to start the macro loop. 
3. The loop cycles through available macro.txt files in your configured macro folder. 
4. Click the STOP button to stop the loop. 

### WIP

Currently picobot does not detect whether or not the active window has changed. 
Please be careful to stop the bot before switching windows. 
Clicking the STOP button should reliably stop macro loops. 
You may use the hardcoded keyboard PAUSE button to start/stop the loops but they are unreliable. 

  
