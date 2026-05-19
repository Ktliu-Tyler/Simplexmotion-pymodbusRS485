# Simplex Motion Position Control Run Record

Date: 2026-05-18

## Test Script

Created script:

```text
SimplexMotion_Motor_Example_Using_PyModbus-master/
  SimplexMotion_Motor_Example_Using_PyModbus-master/
    position_control_com3.py
```

This script is for an interactive single-motor position control test over Modbus RTU.

Default settings:

| Setting | Value |
| --- | --- |
| COM port | COM3 |
| Modbus slave address | 1 |
| Baud rate | 57600 |
| Parity | Even |
| Stop bits | 1 |
| Position mode | Position ramp, mode 21 |
| Ramp speed limit | 90 deg/s |
| Ramp acceleration | 180 deg/s^2 |
| Ramp deceleration | 180 deg/s^2 |

## How To Run

From the project root:

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\position_control_com3.py"
```

Optional arguments:

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\position_control_com3.py" --port COM3 --slave 1 --speed 60 --acc 120 --dec 120
```

## Interactive Commands

After the script starts:

| Input | Meaning |
| --- | --- |
| `30` | Move to absolute target position +30 degrees |
| `-30` | Move to absolute target position -30 degrees |
| `0` | Move back to 0 degrees |
| `p` | Read current position |
| `q` | Quit and reset/disable motor |

The script resets the motor position reference at startup, so the entered position is relative to that reset point.

## Safety Notes

- Start with the motor unloaded.
- Keep the first moves small, for example `10`, `-10`, then `0`.
- Make sure the motor is mechanically free to rotate.
- Keep one hand near the power switch or current-limited supply control.
- If motion direction or distance is unexpected, quit with `q` or cut motor power.

## Checks Done

- `COM3` was visible from `pyserial`.
- `pymodbus` version in the virtual environment: 3.8.6.
- `position_control_com3.py --help` ran successfully.
- `compileall` syntax check passed.
