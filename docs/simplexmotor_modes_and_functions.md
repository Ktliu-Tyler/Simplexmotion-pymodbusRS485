# SimplexMotor Modes And Functions Guide

Date: 2026-05-18

This note documents the current Python example under:

```text
SimplexMotion_Motor_Example_Using_PyModbus-master/
  SimplexMotion_Motor_Example_Using_PyModbus-master/
```

## Recommended Main Program

Use this new interactive menu program for bench testing:

```text
motor_control_menu.py
```

Run from the project root:

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\motor_control_menu.py" --port COM3 --slave 1
```

Default communication settings:

| Setting | Value |
| --- | --- |
| Port | COM3 |
| Slave address | 1 |
| Baud rate | 57600 |
| Parity | Even |
| Stop bits | 1 |
| Data bits | 8 |

Useful optional arguments:

```powershell
--port COM3
--slave 1
--baudrate 57600
--speed 90
--acc 180
--dec 180
```

The menu supports:

| Menu | Function |
| --- | --- |
| 1 | Show status |
| 2 | Configure ramp speed, acceleration, deceleration |
| 3 | Position ramp test |
| 4 | Speed ramp test |
| 5 | Freewheel mode |
| 6 | Reset/disable motor |
| 7 | Off mode |
| 8 | Beep |
| 9 | Read manual register |
| 10 | List modes |
| 11 | Set common test mode by value |
| 12 | Set raw/advanced mode |

Start with menu `1`, then `2`, then `3`. For the first position test, use small targets such as `10`, `-10`, and `0`.

## Mode Register Notes

The motor manual names this as register `<Mode>` number 400. In this Python code, `reg_map.MODE = 399` because the Modbus library uses zero-based register addresses.

When the menu asks for a manual register number, enter the manual number. For example, enter `400` to read `<Mode>`.

## Modes In reg_map.py

| Constant | Value | Meaning | Bench Test Note |
| --- | ---: | --- | --- |
| MODE_OFF | 0 | Stop / disable motor | Safe |
| MODE_RESET | 1 | Reset drive and running data | Safe, also resets position reference |
| MODE_SHUTDOWN | 4 | Shutdown state after error | Usually not manually used |
| MODE_QUICKSTOP | 5 | Controlled stop, then off | Useful for stop behavior |
| MODE_FIRMWARE | 6 | Firmware upgrade mode | Blocked by default |
| MODE_FACTORY | 7 | Factory reset | Blocked by default |
| MODE_RELOAD | 8 | Reload stored parameters | Advanced |
| MODE_STORE | 9 | Store current registers to flash | Blocked by default |
| MODE_PWM | 10 | Open-loop PWM | Dangerous for general testing |
| MODE_FREEWHEEL | 19 | Motor rotates freely | Useful for checking mechanics |
| MODE_POSITION | 20 | Position control without ramp | Avoid for step target tests |
| MODE_POSITION_RAMP | 21 | Position control with ramp | Recommended position mode |
| MODE_ROTARY | 23 | Position ramp with wraparound | Needs rotary config first |
| MODE_SPEED | 32 | Speed control without ramp | Avoid for step target tests |
| MODE_SPEED_RAMP | 33 | Speed control with ramp | Recommended speed mode |
| MODE_SPEED_LOW | 34 | Low-speed control without ramp | Advanced |
| MODE_SPEED_LOW_RAMP | 35 | Low-speed control with ramp | Useful for slow tests |
| MODE_TORQUE | 40 | Torque control | No dedicated wrapper yet |
| MODE_SEQ_POS | 51 | Sequence position ramp | Needs sequence table setup |
| MODE_SEQ_POS_INT | 52 | Sequence position interpolation | Needs sequence table setup |
| MODE_SEQ_POS_FIN | 54 | Sequence position finished | State/result mode |
| MODE_SEQ_SPEED | 55 | Sequence speed ramp | Needs sequence table setup |
| MODE_SEQ_SPEED_INT | 56 | Sequence speed interpolation | Needs sequence table setup |
| MODE_SEQ_SPEED_FIN | 59 | Sequence speed finished | State/result mode |
| MODE_BEEP | 60 | Beep mode | Wrapped by `beep()` |
| MODE_HOMING | 70 | Run configured homing sequence | Needs homing registers configured |
| MODE_DEMO_ON | 200 | Demo panel mode on | Uses demo panel inputs |
| MODE_DEMO_OFF | 201 | Demo mode off | Returns to reset |

The interactive program blocks Firmware, Factory, Store, PWM, Position without ramp, Speed without ramp, and Torque from raw mode unless `--allow-dangerous-modes` is passed.

## Public Functions In simplexMotor.py

### Connection

| Function | Purpose |
| --- | --- |
| `connect()` | Open Modbus serial connection and read motor CPR |
| `close()` | Close serial connection |

### Read Functions

| Function | Return | Purpose |
| --- | --- | --- |
| `get_torque_max()` | Nm | Read torque limit |
| `get_torque_mNm()` | mNm | Read measured motor torque |
| `get_address()` | int | Read Modbus slave id from manual register #50 |
| `get_counters_per_rev()` | int | Read encoder resolution from MotorOptions |
| `get_position_counts()` | counts | Read raw 32-bit motor position |
| `get_position()` | degrees | Read position converted to degrees |
| `get_register_value(name, register)` | raw int | Read one holding register |
| `get_speed()` | deg/s | Read measured speed |
| `get_PID_gains()` | `(kp, ki, kd)` | Read PID gains |
| `get_mode()` | int | Read current mode |
| `get_ramp_speed_max()` | deg/s | Read ramp speed limit |
| `get_ramp_acc_dec_max()` | `(acc, dec)` deg/s^2 | Read ramp acceleration/deceleration |

### Write / Control Functions

| Function | Input | Purpose |
| --- | --- | --- |
| `set_rev_resolution(mode)` | 0, 1, or 2 | Set position resolution: 4096, 8192, 16384 CPR |
| `set_target_position_counts(target_counts)` | signed int32 counts | Write position target directly |
| `set_position(position_deg)` | degrees | Write target position in degrees |
| `set_mode(mode)` | mode value | Change motor operating mode |
| `set_PID_gains(kp, ki, kd)` | raw int16 values | Write PID gains |
| `set_ramp_speed_max(ramp_speed_deg_s)` | deg/s | Set ramp speed limit |
| `set_ramp_acc_dec_max(acc, dec)` | deg/s^2 | Set ramp acceleration/deceleration |
| `beep(duration_ms=500)` | ms | Make the motor beep |
| `set_target_source_register()` | none | Set TargetSelect=Register and TargetFilter=0 |
| `set_target_speed(target_speed)` | raw signed speed value | Write speed target to 32-bit TargetInput |
| `set_torque_max_mNm(torque_mNm)` | mNm | Set MotorTorqueMax torque limit |
| `set_target_torque_raw(target_raw)` | signed raw scale | Write torque target to 32-bit TargetInput |
| `set_target_torque_percent(percent)` | percent | Write torque target as percent of raw +/-32767 scale |
| `set_address(new_address)` | 1..126 | Write Modbus slave id in RAM; call Store and Reset to apply |

## Typical Position Test Flow

The safe position test pattern is:

1. Connect.
2. Set ramp speed and acceleration.
3. Write current position as target.
4. Set mode to `MODE_POSITION_RAMP` (`21`).
5. Write small absolute target positions using `set_position()`.
6. Reset/disable before exiting.

Equivalent code pattern:

```python
motor.set_ramp_speed_max(90)
motor.set_ramp_acc_dec_max(180, 180)
motor.set_position(motor.get_position())
motor.set_mode(regmap.MODE_POSITION_RAMP)
motor.set_position(10)
motor.set_position(-10)
motor.set_position(0)
motor.set_mode(regmap.MODE_RESET)
```

## Typical Speed Test Flow

The safe speed test pattern is:

1. Connect.
2. Set ramp acceleration/deceleration.
3. Set `TargetSelect=Register` and `TargetFilter=0`.
4. Write 32-bit `TargetInput = 0`.
5. Set mode to `MODE_SPEED_RAMP` (`33`).
6. Convert deg/s to raw speed target.
7. Write target speed as 32-bit `TargetInput`.
8. Write `0` before exiting.

The menu does the deg/s to raw conversion internally:

```text
raw = speed_deg_s * 4096 / (16 * 360)
```

The speed/ramp-speed unit is fixed to 4096 positions per revolution in the motor manual.

For this conversion:

| Target | Raw |
| ---: | ---: |
| 90 deg/s | 64 |
| 360 deg/s | 256 |
| 1 rev/s | 256 |

Important: `<TargetInput>` is an `int32` register pair, manual registers `450/451`. Even for speed mode, write both registers. Writing only one register can accidentally write the high 16 bits and create a target value 65536 times larger than intended.

## Typical Torque Test Flow

Torque mode should be tested through `motor_control_menu.py` menu `15`, not by raw mode switching.

Register mapping:

| Manual Register | Code Address | Name | Unit |
| ---: | ---: | --- | --- |
| 203 | 202 | MotorTorque | mNm |
| 204 | 203 | MotorTorqueMax | mNm |
| 351 | 350 | RampSpeedMax | speed limit |
| 400 | 399 | Mode | 40 = Torque |
| 450/451 | 449 | TargetInput | int32 register pair |
| 452 | 451 | TargetSelect | 0 = Register |

Safe torque setup pattern:

```python
motor.set_target_source_register()
motor.set_target_torque_raw(0)
motor.set_torque_max_mNm(30)
motor.set_ramp_speed_max(15)
motor.set_mode(regmap.MODE_TORQUE)
motor.set_target_torque_percent(0.5)
time.sleep(0.5)
motor.set_target_torque_percent(0)
motor.set_mode(regmap.MODE_RESET)
```

Important torque units:

- `MotorTorqueMax` is in `mNm`.
- `MotorTorque` feedback is in `mNm`.
- Torque-mode `TargetInput` is not `mNm`; it is signed raw target scale `-32767..32767`, written as 32-bit `TargetInput`.
- Menu `15` asks for percent of this raw target scale, applies a low `MotorTorqueMax` limit, and sends short torque pulses that automatically return to zero.

## Absolute Position And Zero Reference

The current code supports a software zero point:

- Menu `16` writes current `MotorPosition` register `200/201` to `0`.
- Menu `17` runs absolute position moves from the current zero.
- Menu `18` restores the last saved software position reference.
- `position_control_com3.py` supports `z` to set zero, `s` to save, and `r` to restore.

Manual limitation: `MotorPosition` resets to zero at startup and in `MODE_RESET`. The saved restore flow is only valid if the shaft did not move while powered off. For true absolute startup position, configure homing or use an absolute external reference.

See `docs/absolute_position_zero_reference.md` for the detailed workflow.

## Files Added Or Updated

| File | Purpose |
| --- | --- |
| `motor_control_menu.py` | Interactive main menu for mode and function testing |
| `multi_motor_control.py` | Multi-slave RS485 control menu |
| `position_control_com3.py` | Simple dedicated position-control test |
| `position_reference.py` | Software zero/position reference record helper |
| `reg_map.py` | Added the rest of the manual mode constants |
| `simplexMotor.py` | Motor control helper methods and register writes |
| `docs/absolute_position_zero_reference.md` | Absolute position and zero-reference guide |
| `docs/multi_motor_control_README.md` | Multi-motor RS485 control guide |
| `docs/simplexmotor_modes_and_functions.md` | This guide |
