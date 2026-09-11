# SimplexMotion Motor Control over RS485

A Python toolkit and experiment record for communicating with SimplexMotion motors through Modbus RTU over RS485. It brings low-level register access together with interactive tools for position control, multiple motors, and device-address management.

## Purpose

The project makes motor behavior easier to inspect and control from a computer. It translates the device's register-oriented interface into reusable Python functions and focused command-line tools, while preserving wiring notes and observations from physical tests.

## Main capabilities

- Read and write motor registers through a serial Modbus connection.
- Select operating modes and work with motor status and control values.
- Experiment with position control and position-reference handling.
- Control multiple addressed motors on an RS485 bus.
- Change, store, and verify a motor's slave address.
- Access common operations through an interactive menu.

## Repository guide

The implementation files are inside the nested [example project directory](SimplexMotion_Motor_Example_Using_PyModbus-master/SimplexMotion_Motor_Example_Using_PyModbus-master).

| File or directory | Responsibility |
| --- | --- |
| `simplexMotor.py` | Motor communication and control abstraction |
| `reg_map.py` | Register definitions |
| `motor_control_menu.py` | Interactive control interface |
| `multi_motor_control.py` | Multi-motor workflow |
| `position_control_com3.py`, `position_reference.py` | Position-control and reference experiments |
| `change_slave_id.py` | Address-change workflow |
| [docs](docs) | Wiring, test records, operating modes, and detailed tool guides |

## Technical focus and context

The code uses PyModbus and serial communication, with explicit handling of register addresses, units, modes, and persistent settings. The record is particularly useful for understanding how application-level commands map onto a motor controller's protocol.

These tools issue real motor commands; their behavior depends on the connected device, wiring, configured address, and operating mode. Detailed controls, parameter ranges, and the original test notes are preserved below rather than duplicated in this overview.

## Original project notes

The original documentation is retained below as a personal development record, including its original language, credits, illustrations, and historical instructions. Dates, paths, and environment details describe the original work.

<details>
<summary>Read the original documentation</summary>

# Simplex Motion RS485 Python Test Notes

This project is for testing Simplex Motion motors through the SC/SM-Comboard RS485 interface using Python and Modbus RTU.

Current focus:

- Single motor first
- COM port: `COM3`
- Modbus slave address: `1`
- Position control first, then speed/freewheel/torque/basic mode tests

## 1. Wiring Summary

For one motor, the minimum control wiring is:

| Signal | Connect To |
| --- | --- |
| RS485 A | Motor pin 7, `RS485A` |
| RS485 B | Motor pin 8, `RS485B` |
| +24 V | Motor pin 13 and/or pin 14 |
| GND | Motor pin 11 and/or pin 12 |

Notes:

- Use the Comboard blue screw terminal or DC jack for board power input.
- Do not use a breadboard or thin Dupont jumpers for the motor `24V/GND` power path.
- Dupont wires are acceptable for short RS485 A/B signal tests.
- The Comboard/RS485 side and motor power supply must share GND because the RS485 interface is not isolated.
- If communication fails but COM port, baud rate, power, and address are correct, try swapping A/B.

More wiring notes:

```text
docs/rs485_wiring_record.md
```

## 2. Python Environment

Use the existing virtual environment:

```powershell
.\motionENV\Scripts\python.exe
```

Install the required pip packages from the project root:

```powershell
.\motionENV\Scripts\python.exe -m pip install --upgrade pip
.\motionENV\Scripts\python.exe -m pip install -r requirements.txt
```

If you need to recreate the virtual environment:

```powershell
py -3.11 -m venv motionENV
.\motionENV\Scripts\python.exe -m pip install --upgrade pip
.\motionENV\Scripts\python.exe -m pip install -r requirements.txt
```

Runtime requirements:

| Package | Version | Used For |
| --- | --- | --- |
| `pymodbus` | `3.8.6` | Modbus RTU serial communication |
| `pyserial` | `3.5` | COM port access and serial port listing |

Check serial ports:

```powershell
.\motionENV\Scripts\python.exe -m serial.tools.list_ports
```

Default communication settings:

| Setting | Value |
| --- | --- |
| Port | `COM3` |
| Slave address | `1` |
| Baud rate | `57600` |
| Parity | Even |
| Data bits | 8 |
| Stop bits | 1 |

## 3. Recommended Main Program

Use this interactive menu for most tests:

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\motor_control_menu.py" --port COM3 --slave 1
```

Recommended first test order:

```text
1  Show status
2  Configure ramp speed/acc/dec
3  Position ramp test
```

For the first position movement, enter small values:

```text
10
-10
0
```

The menu resets/disables the motor when exiting.

For manual shaft turning or mechanical resistance checks, use menu `13 Manual turn check (Off mode)` instead of `5 Freewheel mode`. Freewheel can still apply overspeed limiting above `RampSpeedMax`, which may feel like vibration when turning the shaft by hand.

For a neutral-style test where you push the shaft by hand and watch the live angle, use menu `14 Neutral angle monitor (Off + live position)`. This removes active holding/control torque, but it cannot remove the motor's permanent-magnet cogging torque.

For absolute position work, use menu `16 Set zero point`, `17 Absolute position test`, and `18 Restore saved position reference`. The zero point is written to `MotorPosition` register `200/201`; the local record is saved in `motor_state/position_reference.json`.

Important limitation: `MotorPosition` resets to zero at motor startup and in Reset mode. The software restore feature is valid only if the shaft did not move while powered off. If the shaft can move while unpowered, use homing or an external absolute reference for true power-up absolute position.

`motor_control_menu.py` command-line options:

| Option | Default | Input Unit / Range | Meaning |
| --- | ---: | --- | --- |
| `--port` | `COM3` | Windows COM port name | Serial port connected to the SC/SM-Comboard |
| `--slave` | `1` | Modbus slave id, normally `1..126` | Motor address on the RS485 bus |
| `--baudrate` | `57600` | bit/s | Modbus RTU baud rate |
| `--speed` | `90` | deg/s | Default `RampSpeedMax` for position and speed tests |
| `--acc` | `180` | deg/s^2 | Default ramp acceleration |
| `--dec` | `180` | deg/s^2 | Default ramp deceleration |
| `--torque-limit-mnm` | `30` | mNm | Default `MotorTorqueMax` used by menu `15` |
| `--torque-speed-limit` | `15` | deg/s | Default `RampSpeedMax` used as the torque-mode speed limit |
| `--torque-percent-limit` | `2.0` | percent of raw torque scale | Bench soft limit for torque target input |
| `--torque-pulse-seconds` | `0.5` | seconds | Duration before each torque command is automatically returned to zero |
| `--zero-state-file` | `motor_state/position_reference.json` | file path | Local software position-reference record |
| `--restore-last-position` | off | flag | Restore saved `MotorPosition` at startup; only use if the shaft did not move while powered off |
| `--allow-dangerous-modes` | off | flag | Allows raw special modes and removes torque bench soft blocks |

## 4. Torque Control Test

Torque control is available through menu `15 Torque control test` in `motor_control_menu.py`. It is the recommended torque example because it sets conservative limits, monitors feedback, and automatically writes the torque target back to zero.

Start with:

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\motor_control_menu.py" --port COM3 --slave 1 --torque-limit-mnm 30 --torque-speed-limit 15 --torque-percent-limit 2 --torque-pulse-seconds 0.5
```

Then choose:

```text
15
```

Recommended first torque inputs:

```text
Torque limit MotorTorqueMax in mNm: 30
Torque mode speed limit deg/s: 15
torque target % > 0.5
torque target % > 0
torque target % > -0.5
torque target % > 0
torque target % > b
```

Torque control input units:

| Input / Setting | Unit | Default | Meaning |
| --- | --- | ---: | --- |
| `MotorTorqueMax` prompt | mNm | `30` | Torque limit written to manual register `#204` |
| `Torque mode speed limit` prompt | deg/s | `15` | `RampSpeedMax` written to manual register `#351`; torque mode uses it as a speed limit |
| `torque target %` prompt | percent | none | Percent of the raw signed torque target scale, not Nm |
| `--torque-percent-limit` | percent | `2.0` | Maximum accepted target percent without `--allow-dangerous-modes` |
| `--torque-pulse-seconds` | seconds | `0.5` | Time the target is held before auto-zero |
| `s` command | no unit | n/a | Print mode, raw target, measured torque, measured speed, torque limit, and speed limit |
| `limit` command | mNm | current value | Change `MotorTorqueMax` while staying inside the torque test |
| `speed` command | deg/s | current value | Change torque-mode speed limit while staying inside the torque test |
| `b` / `q` command | no unit | n/a | Write torque target `0`, reset/disable, and return to the menu |

Important torque conversions and limits:

```text
target_raw = torque_percent * 32767 / 100
```

- `MotorTorqueMax` is in `mNm`.
- `MotorTorque` feedback is in `mNm`.
- Torque-mode `TargetInput` is not `mNm`; it is a signed raw target scale from `-32767` to `+32767`.
- The code writes torque targets to the 32-bit `TargetInput` register pair `#450/451`.
- Without `--allow-dangerous-modes`, `MotorTorqueMax` above `200 mNm` and target percent above `+/-2%` are blocked.
- If measured speed or measured torque exceeds the safety threshold during a pulse, the script writes target `0` and requests `MODE_RESET`.

## 5. Dedicated Position Control Test

There is also a simpler position-only script:

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\position_control_com3.py"
```

Optional:

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\position_control_com3.py" --port COM3 --slave 1 --speed 60 --acc 120 --dec 120
```

Interactive commands:

| Input | Input Unit | Meaning |
| --- | --- | --- |
| `10` | degrees | Move to absolute target position +10 degrees |
| `-10` | degrees | Move to -10 degrees |
| `0` | degrees | Move back to zero |
| `p` | no unit | Read current position |
| `z` | no unit | Set current position as software zero |
| `s` | no unit | Save current position reference record |
| `r` | no unit | Restore saved position reference |
| `q` | no unit | Quit and reset/disable motor |

## 6. Position Control Parameters

`position_control_com3.py` command-line options:

| Option / Parameter | Default | Input Unit / Range | Meaning |
| --- | ---: | --- | --- |
| Mode | `21` | fixed mode value | Uses `MODE_POSITION_RAMP` |
| `--port` | `COM3` | Windows COM port name | Serial port connected to the SC/SM-Comboard |
| `--slave` | `1` | Modbus slave id, normally `1..126` | Motor address on the RS485 bus |
| `--baudrate` | `57600` | bit/s | Modbus RTU baud rate |
| `--speed` | `90` | deg/s | Maximum position movement speed |
| `--acc` | `180` | deg/s^2 | Ramp acceleration limit |
| `--dec` | `180` | deg/s^2 | Ramp deceleration limit |
| `--no-reset` | off | flag | Keeps the current `MotorPosition` reference at startup |
| `--restore-last-position` | off | flag | Restores saved `MotorPosition` at startup; only use if the shaft did not move while powered off |
| `--zero-state-file` | `motor_state/position_reference.json` | file path | Local software position-reference record |
| Interactive target input | n/a | degrees | Script converts degrees to motor counts |

The script resets the motor at startup by default, so the starting position becomes the zero reference for that test.

For software absolute-position restore, use:

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\position_control_com3.py" --port COM3 --slave 2 --restore-last-position
```

Only use `--restore-last-position` when the shaft did not move while powered off.

Position conversion:

```text
target_counts = target_degrees * CPR / 360
```

Default CPR is usually `4096 counts/rev`, but the code reads the actual CPR from `MotorOptions`.

Speed and ramp-speed conversion uses the manual's fixed speed unit of `4096 positions/rev`.

## 7. Multi-Motor RS485 Control

Use this program when several motors share the same SC/SM-Comboard RS485 A/B bus:

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\multi_motor_control.py" --port COM3 --slaves 1-3
```

For six motors later:

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\multi_motor_control.py" --port COM3 --slaves 1-6
```

The program opens one serial connection to COM3 and talks to each slave id sequentially. It can show status per motor, configure ramp settings, set software zero points, run single-motor absolute position moves, run group absolute position moves, and reset/off selected motors.

`multi_motor_control.py` command-line options:

| Option | Default | Input Unit / Range | Meaning |
| --- | ---: | --- | --- |
| `--port` | `COM3` | Windows COM port name | Serial port connected to the SC/SM-Comboard |
| `--slaves` | `1-3` | list or range, for example `1,3,5` or `1-6` | Slave ids to scan and control |
| `--baudrate` | `57600` | bit/s | Modbus RTU baud rate |
| `--timeout` | `0.5` | seconds | Per-request serial timeout |
| `--speed` | `60` | deg/s | Default ramp speed for selected motors |
| `--acc` | `120` | deg/s^2 | Default ramp acceleration for selected motors |
| `--dec` | `120` | deg/s^2 | Default ramp deceleration for selected motors |
| `--strict` | off | flag | Fail startup if any requested slave does not respond |
| `--debug` | off | flag | Enable verbose motor logs |
| `--keep-enabled-on-exit` | off | flag | Do not reset/disable connected motors when the program exits |
| `--zero-state-file` | `motor_state/position_reference.json` | file path | Local software position-reference record |

## 8. How To Choose Position Parameters

Start conservative:

| Situation | Ramp Speed | Acc/Dec | Target Step |
| --- | ---: | ---: | ---: |
| First bench test, no load | 30-90 deg/s | 60-180 deg/s^2 | 5-10 deg |
| Smooth unloaded test | 90-180 deg/s | 180-360 deg/s^2 | 10-45 deg |
| Light mechanism attached | 30-120 deg/s | 60-240 deg/s^2 | Small at first |
| Unknown load/inertia | 15-60 deg/s | 30-120 deg/s^2 | 2-5 deg |

Use lower deceleration when the load has high inertia. Fast deceleration can regenerate energy back into the supply and raise the 24 V bus voltage.

Good first command:

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\position_control_com3.py" --speed 60 --acc 120 --dec 120
```

Then try:

```text
10
-10
0
```

## 9. Basic Mode Settings

The motor mode is manual register `<Mode>` number `400`. In the Python code it is address `399`, because the Modbus library uses zero-based addresses.

Common modes:

| Mode | Constant | Use |
| ---: | --- | --- |
| 0 | `MODE_OFF` | Stop/disable motor |
| 1 | `MODE_RESET` | Reset drive and running data |
| 5 | `MODE_QUICKSTOP` | Controlled stop, then off |
| 19 | `MODE_FREEWHEEL` | Motor shaft can rotate freely |
| 21 | `MODE_POSITION_RAMP` | Recommended position control |
| 33 | `MODE_SPEED_RAMP` | Recommended speed control |
| 35 | `MODE_SPEED_LOW_RAMP` | Low-speed speed control |
| 60 | `MODE_BEEP` | Make sound |
| 70 | `MODE_HOMING` | Run configured homing sequence |

Note: `MODE_FREEWHEEL` is not the same as guaranteed zero torque forever. The manual describes it as freewheeling up to `RampSpeedMax`; above that, the motor may use `MotorTorqueMax` to slow down. If freewheel causes vibration, use `MODE_RESET` or `MODE_OFF` for bench safety.

Avoid these for casual bench testing:

| Mode | Constant | Reason |
| ---: | --- | --- |
| 6 | `MODE_FIRMWARE` | Firmware update mode |
| 7 | `MODE_FACTORY` | Factory reset |
| 9 | `MODE_STORE` | Writes current settings to flash |
| 10 | `MODE_PWM` | Open-loop, no regulator/ramping |
| 20 | `MODE_POSITION` | Position control without ramp |
| 32 | `MODE_SPEED` | Speed control without ramp |
| 40 | `MODE_TORQUE` | Needs careful torque/speed limits |

The menu program blocks the dangerous/special modes by default. To intentionally allow them:

```powershell
--allow-dangerous-modes
```

## 10. Basic Function Usage

Main class:

```python
from simplexMotor import SimplexMotor
import reg_map as regmap

motor = SimplexMotor(port="COM3", slave_id=1)
motor.connect()
```

Constructor parameters:

| Parameter | Default in class | Input Unit / Range | Meaning |
| --- | ---: | --- | --- |
| `port` | `COM12` | Windows COM port name | Serial port used by `pymodbus` |
| `baudrate` | `57600` | bit/s | Modbus RTU baud rate |
| `slave_id` | `1` | Modbus slave id, normally `1..126` | Motor address on the RS485 bus |
| `timeout` | `1.0` | seconds | Serial request timeout |
| `parity` | `E` | serial parity code | Even parity for the current setup |
| `stopbits` | `1` | serial stop bits | Stop-bit setting for Modbus RTU |
| `debug` | `True` | boolean | Enables detailed register logs |

Position ramp example:

```python
motor.set_ramp_speed_max(60)
motor.set_ramp_acc_dec_max(120, 120)
motor.set_position(motor.get_position())
motor.set_mode(regmap.MODE_POSITION_RAMP)
motor.set_position(10)
motor.set_position(0)
motor.set_mode(regmap.MODE_RESET)
motor.close()
```

Speed ramp example:

```python
motor.set_ramp_acc_dec_max(120, 120)
motor.set_target_source_register()
motor.set_target_speed(0)
motor.set_mode(regmap.MODE_SPEED_RAMP)
motor.set_target_speed(64)  # raw speed target, about 90 deg/s at 4096 CPR
motor.set_target_speed(0)
motor.set_mode(regmap.MODE_RESET)
motor.close()
```

Torque control API example:

```python
import time

motor.set_target_source_register()
motor.set_target_torque_raw(0)
motor.set_torque_max_mNm(30)
motor.set_ramp_speed_max(15)
motor.set_mode(regmap.MODE_TORQUE)
motor.set_target_torque_percent(0.5)
time.sleep(0.5)
motor.set_target_torque_raw(0)
motor.set_mode(regmap.MODE_RESET)
motor.close()
```

For real bench testing, prefer menu `15` because it monitors measured torque and speed during each pulse. The direct API example above only shows the minimum register sequence.

Important: `<TargetInput>` is a 32-bit value using two Modbus registers. The code writes speed targets as 32-bit values. Do not change speed target writing back to a single-register write, or a small speed command can become a very large target.

Lifecycle functions:

| Function | Inputs / Units | Result |
| --- | --- | --- |
| `connect()` | no input | Opens the Modbus serial connection and reads CPR from `MotorOptions` |
| `close()` | no input | Closes the serial connection |

Read functions:

| Function | Inputs / Units | Return Unit | Meaning |
| --- | --- | --- | --- |
| `get_mode()` | no input | mode value | Reads current operating mode from manual register `#400` |
| `get_position_counts()` | no input | counts | Reads signed 32-bit `MotorPosition` from register `#200/201` |
| `get_position()` | no input | degrees | Converts `MotorPosition` counts using current CPR |
| `get_speed()` | no input | deg/s | Reads measured motor speed |
| `get_ramp_speed_max()` | no input | deg/s | Reads `RampSpeedMax` |
| `get_ramp_acc_dec_max()` | no input | deg/s^2 | Reads ramp acceleration and deceleration limits |
| `get_torque_max()` | no input | Nm | Reads `MotorTorqueMax`; register is mNm, function returns Nm |
| `get_torque_mNm()` | no input | mNm | Reads measured motor torque |
| `get_PID_gains()` | no input | raw int16 values | Reads `(Kp, Ki, Kd)` |
| `get_address()` | no input | slave id | Reads manual register `#50 Address` |
| `get_counters_per_rev()` | no input | counts/rev | Reads encoder resolution from `MotorOptions` |
| `get_target_input()` | no input | signed int32 raw | Reads 32-bit `TargetInput` register pair |
| `get_target_present()` | no input | signed int32 raw | Reads 32-bit `TargetPresent` register pair |
| `get_register_value(name, register)` | `name`: log label; `register`: zero-based Modbus address | raw uint16 | Reads one holding register |
| `get_register_int32(name, register)` | `name`: log label; `register`: zero-based address of MSW | signed int32 | Reads two registers as one signed 32-bit value |

Write/control functions:

| Function | Inputs / Units | Range / Notes | Meaning |
| --- | --- | --- | --- |
| `set_mode(mode)` | `mode`: mode value | Common values: `0`, `1`, `19`, `21`, `33`, `40`, `60`, `70` | Writes manual register `#400 Mode` |
| `set_position(position_deg)` | `position_deg`: degrees | Converted to counts with `CPR / 360` | Writes absolute position target to `TargetInput` |
| `set_target_position_counts(target_counts)` | `target_counts`: counts | signed int32 | Writes raw position target to `TargetInput` |
| `set_motor_position_counts(position_counts)` | `position_counts`: counts | signed int32 | Writes current `MotorPosition` reference; does not command movement |
| `set_motor_position_reference(position_deg=0.0)` | `position_deg`: degrees | Returns count value written | Writes current `MotorPosition` reference in degree units |
| `set_target_speed(target_speed)` | `target_speed`: raw signed speed target | `-32768..32767`; not deg/s | Writes speed-mode target to 32-bit `TargetInput` |
| `set_ramp_speed_max(ramp_speed_deg_s)` | `ramp_speed_deg_s`: deg/s | Converted using `4096 positions/rev` speed unit | Writes `RampSpeedMax` |
| `set_ramp_acc_dec_max(ramp_acc_deg_s2, ramp_dec_deg_s2)` | acceleration and deceleration in deg/s^2 | Converted using `4096 positions/rev` speed unit | Writes ramp acceleration/deceleration limits |
| `set_target_source_register()` | no input | Sets `TargetSelect=0` and `TargetFilter=0` | Uses `TargetInput` as the target source |
| `set_torque_max_mNm(torque_mNm)` | `torque_mNm`: mNm | Code range `0..2000`; start near `30 mNm` for bench tests | Writes `MotorTorqueMax` torque limit |
| `set_target_torque_raw(target_raw)` | `target_raw`: signed raw scale | `-32767..32767`; not mNm | Writes torque-mode target to 32-bit `TargetInput` |
| `set_target_torque_percent(percent)` | `percent`: percent of raw torque scale | `-100..100`; returns raw value written | Converts percent to raw torque target |
| `set_PID_gains(kp, ki, kd)` | raw int16 gains | each value must fit `-32768..32767` | Writes PID gain registers |
| `set_rev_resolution(mode)` | `mode`: resolution selector | `0=4096`, `1=8192`, `2=16384` counts/rev | Updates encoder resolution bits in `MotorOptions` |
| `set_address(new_address)` | `new_address`: Modbus slave id | `1..126`; use `MODE_STORE` and reset to persist/apply | Writes manual register `#50 Address` |
| `beep(duration_ms=500)` | `duration_ms`: ms | Target amplitude is fixed to `100` in code | Runs beep mode for the requested time |

## 11. Suggested Test Procedure

1. Wire one motor only.
2. Use current-limited 24 V supply.
3. Run the menu program.
4. Choose `1` to verify communication.
5. Choose `2` and set `60 / 120 / 120`.
6. Choose `3` position ramp test.
7. Try `10`, `-10`, `0`.
8. If stable, increase speed or acceleration gradually.
9. Quit with `q`, then confirm motor is reset/disabled.
10. For torque testing, choose menu `15` and start with `0.5`, `0`, `-0.5`, `0`.

## 12. More Detailed Notes

| File | Description |
| --- | --- |
| `docs/rs485_wiring_record.md` | Wiring and power notes |
| `docs/position_control_run_record.md` | Position-control run notes |
| `docs/absolute_position_zero_reference.md` | Absolute position, zero-point, and restore notes |
| `docs/simplexmotor_modes_and_functions.md` | Full mode/function list |
| `docs/motor_control_menu_README.md` | Interactive menu operation guide |
| `docs/multi_motor_control_README.md` | Multi-motor RS485 control guide |
| `docs/change_slave_id_README.md` | Change and store motor slave id |

## 13. Change Motor Slave Id

Use the standalone script:

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\change_slave_id.py" --port COM3 --current 1 --target 2
```

This writes manual register `#50 Address` using code address `49`, stores settings with `Mode=9`, then resets with `Mode=1` and verifies the new id.

`change_slave_id.py` command-line options:

| Option | Required | Input Unit / Range | Meaning |
| --- | --- | --- | --- |
| `--port` | no | Windows COM port name, default `COM3` | Serial port connected to the target motor |
| `--current` | yes | current slave id, `1..126` | Address currently used to communicate with the motor |
| `--target` | yes | new slave id, `1..126` | Address to write into manual register `#50` |
| `--baudrate` | no | bit/s, default `57600` | Modbus RTU baud rate |
| `--timeout` | no | seconds, default `1.0` | Serial request timeout |
| `--yes` | no | flag | Skip the interactive `CHANGE` confirmation |
| `--debug` | no | flag | Enable verbose motor logs |

</details>
