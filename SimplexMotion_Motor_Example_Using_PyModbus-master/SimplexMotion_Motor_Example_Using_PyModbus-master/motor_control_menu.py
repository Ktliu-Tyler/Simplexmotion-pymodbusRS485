import argparse
import logging
import msvcrt
import time

from serial.tools import list_ports

import reg_map as regmap
from position_reference import (
    DEFAULT_STATE_FILE,
    SOFTWARE_REFERENCE_NOTE,
    counts_to_degrees,
    load_motor_record,
    resolve_state_file,
    save_motor_position_record,
)
from simplexMotor import SimplexMotor


MODE_TABLE = [
    (regmap.MODE_OFF, "Off", "Stop/disable motor"),
    (regmap.MODE_RESET, "Reset", "Reset running data, then return to Off"),
    (regmap.MODE_QUICKSTOP, "Quickstop", "Controlled stop, then off"),
    (regmap.MODE_FREEWHEEL, "Freewheel", "Motor can rotate freely"),
    (regmap.MODE_POSITION_RAMP, "PositionRamp", "Recommended position control"),
    (regmap.MODE_SPEED_RAMP, "SpeedRamp", "Recommended speed control"),
    (regmap.MODE_SPEED_LOW_RAMP, "SpeedLowRamp", "Low speed control with ramp"),
    (regmap.MODE_BEEP, "Beep", "Sound output mode"),
    (regmap.MODE_HOMING, "Homing", "Run configured homing sequence"),
]

DANGEROUS_OR_SPECIAL_MODES = {
    regmap.MODE_FIRMWARE,
    regmap.MODE_FACTORY,
    regmap.MODE_STORE,
    regmap.MODE_PWM,
    regmap.MODE_POSITION,
    regmap.MODE_SPEED,
    regmap.MODE_TORQUE,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Interactive Simplex Motion test menu.")
    parser.add_argument("--port", default="COM3", help="Windows COM port, default: COM3")
    parser.add_argument("--slave", type=int, default=1, help="Modbus slave address, default: 1")
    parser.add_argument("--baudrate", type=int, default=57600, help="Modbus baud rate, default: 57600")
    parser.add_argument("--speed", type=int, default=90, help="Default ramp speed in deg/s")
    parser.add_argument("--acc", type=int, default=180, help="Default ramp acceleration in deg/s^2")
    parser.add_argument("--dec", type=int, default=180, help="Default ramp deceleration in deg/s^2")
    parser.add_argument("--torque-limit-mnm", type=int, default=30, help="Default torque limit in mNm")
    parser.add_argument("--torque-speed-limit", type=int, default=15, help="Default torque mode speed limit in deg/s")
    parser.add_argument("--torque-percent-limit", type=float, default=2.0, help="Soft limit for torque target percent")
    parser.add_argument("--torque-pulse-seconds", type=float, default=0.5, help="Torque command pulse duration in seconds")
    parser.add_argument(
        "--zero-state-file",
        default=DEFAULT_STATE_FILE,
        help=f"Position reference record file, default: {DEFAULT_STATE_FILE}",
    )
    parser.add_argument(
        "--restore-last-position",
        action="store_true",
        help="Restore saved MotorPosition at startup. Use only if the shaft did not move while powered off.",
    )
    parser.add_argument(
        "--allow-dangerous-modes",
        action="store_true",
        help="Allow raw special modes such as PWM, Factory, Firmware, Store, Torque",
    )
    return parser


def prompt_text(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    value = input(f"{label}{suffix}: ").strip()
    if not value and default is not None:
        return default
    return value


def prompt_int(label: str, default: int | None = None) -> int:
    while True:
        text = prompt_text(label, str(default) if default is not None else None)
        try:
            return int(text)
        except ValueError:
            print("Please enter an integer.")


def prompt_float(label: str, default: float | None = None) -> float:
    while True:
        text = prompt_text(label, str(default) if default is not None else None)
        try:
            return float(text)
        except ValueError:
            print("Please enter a number.")


def confirm(label: str, default_no: bool = True) -> bool:
    suffix = " [y/N]" if default_no else " [Y/n]"
    answer = input(f"{label}{suffix}: ").strip().lower()
    if not answer:
        return not default_no
    return answer in ("y", "yes")


def speed_deg_s_to_raw(motor: SimplexMotor, speed_deg_s: float) -> int:
    return int(round(speed_deg_s * regmap.SPEED_COUNTS_PER_REV / (16.0 * 360.0)))


def torque_percent_to_raw(percent: float) -> int:
    return int(round(percent * 32767.0 / 100.0))


def ensure_mode(motor: SimplexMotor, expected_mode: int) -> None:
    actual_mode = motor.get_mode()
    if actual_mode != expected_mode:
        raise RuntimeError(f"Mode change failed: expected {expected_mode}, got {actual_mode}")


def save_current_position_record(motor: SimplexMotor, state_file, event: str) -> None:
    position_counts = motor.get_position_counts()
    record = save_motor_position_record(
        state_file,
        port=motor.port,
        slave_id=motor.slave_id,
        baudrate=motor.baudrate,
        cpr=motor.cpr,
        position_counts=position_counts,
        event=event,
    )
    print(
        f"Saved position record: {record['last_position_deg']:.3f} deg "
        f"({position_counts} counts) -> {state_file}"
    )


def print_position_reference_record(motor: SimplexMotor, state_file) -> None:
    record = load_motor_record(state_file, motor.port, motor.slave_id)
    if not record:
        print("No saved position reference record for this port/slave yet.")
        return

    print("Saved position reference record:")
    print(f"  last position: {record.get('last_position_deg', 0.0):.3f} deg")
    print(f"  last saved at: {record.get('last_saved_at', 'unknown')}")
    print(f"  zero set at:   {record.get('zero_set_at', 'unknown')}")
    print(f"  state file:    {state_file}")


def prepare_position_ramp_at_current_position(motor: SimplexMotor) -> float:
    motor.set_target_source_register()
    current_counts = motor.get_position_counts()
    motor.set_target_position_counts(current_counts)
    motor.set_mode(regmap.MODE_POSITION_RAMP)
    time.sleep(0.2)
    ensure_mode(motor, regmap.MODE_POSITION_RAMP)
    return counts_to_degrees(current_counts, motor.cpr)


def set_zero_point(motor: SimplexMotor, state_file, require_confirm: bool = True) -> bool:
    print("")
    print("Set current shaft position as software zero.")
    print("This writes MotorPosition register #200/201 to 0 and does not move the motor.")
    print("Important:")
    print(f"  {SOFTWARE_REFERENCE_NOTE}")

    previous_counts = motor.get_position_counts()
    previous_deg = counts_to_degrees(previous_counts, motor.cpr)
    print(f"Current position before zero: {previous_deg:.3f} deg ({previous_counts} counts)")

    if require_confirm and not confirm("Set this current position to 0 degrees now?"):
        print("Cancelled.")
        return False

    motor.set_target_source_register()
    motor.set_mode(regmap.MODE_OFF)
    time.sleep(0.2)
    ensure_mode(motor, regmap.MODE_OFF)

    motor.set_motor_position_counts(0)
    motor.set_target_position_counts(0)
    verified_counts = motor.get_position_counts()

    record = save_motor_position_record(
        state_file,
        port=motor.port,
        slave_id=motor.slave_id,
        baudrate=motor.baudrate,
        cpr=motor.cpr,
        position_counts=verified_counts,
        event="zero_set",
        zero_set=True,
        previous_position_counts=previous_counts,
    )

    print(f"Zero point set. Current position: {record['last_position_deg']:.3f} deg")
    print(f"Record saved to: {state_file}")
    return True


def restore_saved_position_reference(motor: SimplexMotor, state_file, require_confirm: bool = True) -> bool:
    record = load_motor_record(state_file, motor.port, motor.slave_id)
    if not record:
        print("No saved position reference record for this port/slave.")
        return False

    saved_counts = record.get("last_position_counts")
    if not isinstance(saved_counts, int):
        print("Saved record has no valid last_position_counts.")
        return False

    saved_cpr = record.get("cpr")
    saved_deg = counts_to_degrees(saved_counts, motor.cpr)

    print("")
    print("Restore saved software position reference.")
    print(f"Saved position: {saved_deg:.3f} deg ({saved_counts} counts)")
    print(f"Saved at: {record.get('last_saved_at', 'unknown')}")
    if saved_cpr != motor.cpr:
        print(f"WARNING: saved CPR {saved_cpr}, current CPR {motor.cpr}. Check MotorOptions first.")
    print("Only use this if the shaft did not move while motor/controller power was off.")

    if require_confirm and not confirm("Write saved position back into MotorPosition now?"):
        print("Cancelled.")
        return False

    motor.set_target_source_register()
    motor.set_mode(regmap.MODE_OFF)
    time.sleep(0.2)
    ensure_mode(motor, regmap.MODE_OFF)
    motor.set_motor_position_counts(saved_counts)
    motor.set_target_position_counts(saved_counts)

    verified_counts = motor.get_position_counts()
    save_motor_position_record(
        state_file,
        port=motor.port,
        slave_id=motor.slave_id,
        baudrate=motor.baudrate,
        cpr=motor.cpr,
        position_counts=verified_counts,
        event="restore_saved_reference",
    )
    print(f"Restored MotorPosition to {counts_to_degrees(verified_counts, motor.cpr):.3f} deg.")
    return True


def print_available_ports() -> None:
    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return

    print("Available serial ports:")
    for port in ports:
        desc = f" - {port.description}" if port.description else ""
        print(f"  {port.device}{desc}")


def print_modes() -> None:
    print("")
    print("Common test modes:")
    for value, name, note in MODE_TABLE:
        print(f"  {value:>3}  {name:<14} {note}")
    print("")
    print("Special modes exist in reg_map.py, but some are blocked by default:")
    print("  6 Firmware, 7 Factory, 9 Store, 10 PWM, 20 Position(no ramp), 32 Speed(no ramp), 40 Torque")


def show_status(motor: SimplexMotor) -> None:
    print("")
    print("Reading motor status...")
    mode = motor.get_mode()
    position = motor.get_position()
    speed = motor.get_speed()
    ramp_speed = motor.get_ramp_speed_max()
    ramp_acc, ramp_dec = motor.get_ramp_acc_dec_max()
    torque_max = motor.get_torque_max()
    torque = motor.get_torque_mNm()
    kp, ki, kd = motor.get_PID_gains()
    print("")
    print(f"Mode: {mode}")
    print(f"Position: {position:.3f} deg")
    print(f"Speed: {speed:.3f} deg/s")
    print(f"Ramp speed max: {ramp_speed:.3f} deg/s")
    print(f"Ramp acc/dec max: {ramp_acc:.3f} / {ramp_dec:.3f} deg/s^2")
    print(f"Measured torque: {torque} mNm")
    print(f"Torque max: {torque_max:.3f} Nm")
    print(f"PID: Kp={kp}, Ki={ki}, Kd={kd}")


def configure_ramp(motor: SimplexMotor, default_speed: int, default_acc: int, default_dec: int) -> None:
    speed = prompt_int("Ramp speed max deg/s", default_speed)
    acc = prompt_int("Ramp acceleration deg/s^2", default_acc)
    dec = prompt_int("Ramp deceleration deg/s^2", default_dec)
    motor.set_ramp_speed_max(speed)
    motor.set_ramp_acc_dec_max(acc, dec)
    print("Ramp settings written.")


def position_ramp_test(motor: SimplexMotor) -> None:
    current_position = prepare_position_ramp_at_current_position(motor)

    print("")
    print("Position ramp test. Input target degrees in the current MotorPosition coordinate.")
    print(f"Current coordinate: {current_position:.3f} deg")
    print("Examples: 10, -10, 0. Input 'b' to go back.")
    while True:
        text = input("position deg > ").strip().lower()
        if text in ("b", "back", "q"):
            return
        try:
            target_deg = float(text)
        except ValueError:
            print("Please enter a number or 'b'.")
            continue

        motor.set_position(target_deg)
        time.sleep(0.3)
        motor.get_position()


def absolute_position_test(motor: SimplexMotor, state_file) -> None:
    current_position = prepare_position_ramp_at_current_position(motor)

    print("")
    print("Absolute position test.")
    print("Targets are absolute degrees from the current MotorPosition zero.")
    print(f"Current absolute position: {current_position:.3f} deg")
    print_position_reference_record(motor, state_file)
    print("")
    print("Commands:")
    print("  number  move to absolute target degrees, for example 10, -10, 0")
    print("  p       read current position")
    print("  z       set current position as zero")
    print("  r       restore saved position reference")
    print("  b/q     back to menu")

    while True:
        text = input("absolute position deg > ").strip().lower()
        if text in ("b", "back", "q"):
            return
        if text == "p":
            position = motor.get_position()
            target = motor.get_target_input()
            print(f"Position: {position:.3f} deg | TargetInput counts: {target}")
            continue
        if text == "z":
            if set_zero_point(motor, state_file):
                current_position = prepare_position_ramp_at_current_position(motor)
                print(f"Position ramp re-enabled at {current_position:.3f} deg.")
            continue
        if text == "r":
            if restore_saved_position_reference(motor, state_file):
                current_position = prepare_position_ramp_at_current_position(motor)
                print(f"Position ramp re-enabled at {current_position:.3f} deg.")
            continue

        try:
            target_deg = float(text)
        except ValueError:
            print("Please enter a number, p, z, r, b, or q.")
            continue

        motor.set_position(target_deg)
        time.sleep(0.3)
        position = motor.get_position()
        print(f"Current position: {position:.3f} deg")


def speed_ramp_test(motor: SimplexMotor) -> None:
    motor.set_target_source_register()
    motor.set_target_speed(0)
    motor.set_mode(regmap.MODE_SPEED_RAMP)
    time.sleep(0.2)
    ensure_mode(motor, regmap.MODE_SPEED_RAMP)

    print("")
    print("Speed ramp test. Input target speed in deg/s.")
    print("Examples: 90, -90, 0. Input 'b' to go back.")
    print("After each command, speed is monitored for 2 seconds.")
    while True:
        text = input("speed deg/s > ").strip().lower()
        if text in ("b", "back", "q"):
            motor.set_target_speed(0)
            return
        try:
            target_deg_s = float(text)
        except ValueError:
            print("Please enter a number or 'b'.")
            continue

        raw = speed_deg_s_to_raw(motor, target_deg_s)
        if not (-32768 <= raw <= 32767):
            print(f"Target is outside int16 range after conversion: {raw}")
            continue

        print(f"Writing TargetInput raw speed value: {raw}")
        motor.set_target_speed(raw)

        target_input = motor.get_target_input()
        target_present = motor.get_target_present()
        print(f"Target raw check: TargetInput={target_input}, TargetPresent={target_present}")

        safe_limit = max(abs(target_deg_s) * 3.0, abs(target_deg_s) + 360.0)
        samples = []
        start_time = time.monotonic()
        while time.monotonic() - start_time < 2.0:
            time.sleep(0.25)
            measured_speed = motor.get_speed()
            samples.append(measured_speed)
            print(f"  speed: {measured_speed:9.3f} deg/s")

            if abs(measured_speed) > safe_limit:
                print("")
                print("WARNING: measured speed is much higher than the requested target.")
                print(f"Requested: {target_deg_s:.3f} deg/s, measured: {measured_speed:.3f} deg/s")
                print("Writing speed target 0 and resetting motor now.")
                motor.set_target_speed(0)
                motor.set_mode(regmap.MODE_RESET)
                return

        if samples:
            final_speed = samples[-1]
            error = final_speed - target_deg_s
            print(f"Final sample: {final_speed:.3f} deg/s, error: {error:+.3f} deg/s")


def torque_control_test(
    motor: SimplexMotor,
    default_torque_limit_mNm: int,
    default_speed_limit_deg_s: int,
    torque_percent_limit: float,
    torque_pulse_seconds: float,
    allow_dangerous_modes: bool,
) -> None:
    print("")
    print("Torque control test.")
    print("Official manual notes:")
    print("  - Mode 40 = Torque control.")
    print("  - MotorTorqueMax register #204 is a torque limit in mNm.")
    print("  - TargetInput #450/451 is int32, but torque target uses signed raw scale +/-32767.")
    print("  - RampSpeedMax #351 is the speed limit used by torque mode.")
    print("")
    print("For safety, target input is percent of raw torque scale, not direct Nm.")
    print("Each torque command is applied as a short pulse and then returns to zero automatically.")

    if default_torque_limit_mNm > 200 and not allow_dangerous_modes:
        print("Default torque limit was above the bench soft limit; using 50 mNm.")
        default_torque_limit_mNm = 50

    torque_limit_mNm = prompt_int("Torque limit MotorTorqueMax in mNm", default_torque_limit_mNm)
    if torque_limit_mNm <= 0:
        print("Torque limit must be positive.")
        return
    if torque_limit_mNm > 200 and not allow_dangerous_modes:
        print("Torque limit above 200 mNm is blocked without --allow-dangerous-modes.")
        return

    speed_limit_deg_s = prompt_int("Torque mode speed limit deg/s", default_speed_limit_deg_s)
    if speed_limit_deg_s <= 0:
        print("Speed limit must be positive.")
        return

    motor.set_target_source_register()
    motor.set_target_torque_raw(0)
    motor.set_torque_max_mNm(torque_limit_mNm)
    motor.set_ramp_speed_max(speed_limit_deg_s)
    motor.set_mode(regmap.MODE_TORQUE)
    time.sleep(0.2)
    ensure_mode(motor, regmap.MODE_TORQUE)

    print("")
    print("Torque mode enabled.")
    print(f"Soft target percent limit: +/-{torque_percent_limit:.1f}%")
    print("Commands:")
    print("  number  target torque percent pulse, for example 0.5, -0.5, 1, 0")
    print("  s       status")
    print("  limit   change MotorTorqueMax mNm")
    print("  speed   change torque mode speed limit")
    print("  b/q     zero torque, reset, back to menu")

    try:
        while True:
            text = input("torque target % > ").strip().lower()
            if text in ("b", "back", "q"):
                return
            if text == "s":
                print(f"Mode: {motor.get_mode()}")
                print(f"TargetInput raw: {motor.get_target_input()}")
                print(f"TargetPresent raw: {motor.get_target_present()}")
                print(f"Measured torque: {motor.get_torque_mNm()} mNm")
                print(f"Measured speed: {motor.get_speed():.3f} deg/s")
                print(f"Torque limit: {motor.get_torque_max():.3f} Nm")
                print(f"Speed limit: {motor.get_ramp_speed_max():.3f} deg/s")
                continue
            if text == "limit":
                new_limit = prompt_int("New MotorTorqueMax in mNm", torque_limit_mNm)
                if new_limit <= 0:
                    print("Torque limit must be positive.")
                    continue
                if new_limit > 200 and not allow_dangerous_modes:
                    print("Torque limit above 200 mNm is blocked without --allow-dangerous-modes.")
                    continue
                torque_limit_mNm = new_limit
                motor.set_torque_max_mNm(torque_limit_mNm)
                continue
            if text == "speed":
                new_speed = prompt_int("New torque mode speed limit deg/s", speed_limit_deg_s)
                if new_speed <= 0:
                    print("Speed limit must be positive.")
                    continue
                speed_limit_deg_s = new_speed
                motor.set_ramp_speed_max(speed_limit_deg_s)
                continue

            try:
                percent = float(text)
            except ValueError:
                print("Please enter a percent number, s, limit, speed, b, or q.")
                continue

            if not (-100.0 <= percent <= 100.0):
                print("Torque target percent must be in range [-100, 100].")
                continue
            if abs(percent) > torque_percent_limit and not allow_dangerous_modes:
                print(f"Blocked: percent above +/-{torque_percent_limit:.1f}% without --allow-dangerous-modes.")
                continue

            raw = torque_percent_to_raw(percent)
            print(f"Writing torque target pulse: {percent:.3f}% -> raw {raw}")
            written_raw = motor.set_target_torque_percent(percent)

            target_input = motor.get_target_input()
            target_present = motor.get_target_present()
            print(f"Target raw check: written={written_raw}, TargetInput={target_input}, TargetPresent={target_present}")

            samples = []
            start_time = time.monotonic()
            tripped = False
            while time.monotonic() - start_time < torque_pulse_seconds:
                time.sleep(0.1)
                measured_torque = motor.get_torque_mNm()
                measured_speed = motor.get_speed()
                samples.append((measured_torque, measured_speed))
                print(f"  torque: {measured_torque:6d} mNm | speed: {measured_speed:9.3f} deg/s")

                speed_stop_limit = max(speed_limit_deg_s * 1.25, speed_limit_deg_s + 10.0)
                torque_stop_limit = max(torque_limit_mNm * 1.5, torque_limit_mNm + 50)
                if abs(measured_speed) > speed_stop_limit:
                    print("")
                    print("WARNING: speed exceeded torque-mode safety limit.")
                    print("Writing torque target 0 and resetting motor now.")
                    motor.set_target_torque_raw(0)
                    motor.set_mode(regmap.MODE_RESET)
                    tripped = True
                    return
                if abs(measured_torque) > torque_stop_limit:
                    print("")
                    print("WARNING: measured torque exceeded safety limit.")
                    print("Writing torque target 0 and resetting motor now.")
                    motor.set_target_torque_raw(0)
                    motor.set_mode(regmap.MODE_RESET)
                    tripped = True
                    return

            if not tripped:
                motor.set_target_torque_raw(0)
                time.sleep(0.2)

            if samples:
                final_torque, final_speed = samples[-1]
                print(f"Final sample before auto-zero: {final_torque} mNm, {final_speed:.3f} deg/s")
    finally:
        print("Leaving torque mode: target torque 0, reset/disable.")
        try:
            motor.set_target_torque_raw(0)
        finally:
            motor.set_mode(regmap.MODE_RESET)


def freewheel_test(motor: SimplexMotor) -> None:
    print("")
    print("Preparing freewheel mode...")
    print("Clearing speed target and waiting for the motor to settle first.")

    motor.set_target_source_register()
    motor.set_target_speed(0)
    time.sleep(0.5)
    measured_speed = motor.get_speed()

    if abs(measured_speed) > 30.0:
        print(f"Measured speed is still {measured_speed:.3f} deg/s.")
        print("Resetting instead of entering freewheel. Try again after the shaft stops.")
        motor.set_mode(regmap.MODE_RESET)
        return

    motor.set_mode(regmap.MODE_OFF)
    time.sleep(0.2)
    motor.set_mode(regmap.MODE_FREEWHEEL)
    time.sleep(0.2)
    ensure_mode(motor, regmap.MODE_FREEWHEEL)

    print("Freewheel mode set.")
    print("If the motor vibrates, choose 6 Reset/disable or 7 Off mode.")


def manual_turn_check(motor: SimplexMotor) -> None:
    print("")
    print("Entering Off mode for manual shaft turning...")
    print("This is usually better than Freewheel for checking mechanical resistance by hand.")

    motor.set_target_source_register()
    motor.set_target_speed(0)
    time.sleep(0.2)
    motor.set_mode(regmap.MODE_OFF)
    time.sleep(0.2)
    ensure_mode(motor, regmap.MODE_OFF)

    print("Off mode set. You can gently turn the shaft by hand.")
    print("If the mechanism has gravity load or stored energy, hold it before disabling the motor.")


def neutral_angle_monitor(motor: SimplexMotor, state_file) -> None:
    print("")
    print("Entering neutral angle monitor...")
    print("Mode: Off. Motor will not hold position or apply freewheel speed limiting.")
    print("You can push/turn the shaft by hand and watch the angle.")
    print("Keys: q/b = back to menu, z = reset current position reference to zero.")

    motor.set_target_source_register()
    motor.set_target_speed(0)
    time.sleep(0.2)
    motor.set_mode(regmap.MODE_OFF)
    time.sleep(0.2)
    ensure_mode(motor, regmap.MODE_OFF)

    print("")
    try:
        while True:
            position = motor.get_position()
            speed = motor.get_speed()
            print(f"\rPosition: {position:10.3f} deg | Speed: {speed:9.3f} deg/s | q/b: back | z: zero", end="")

            end_time = time.monotonic() + 0.2
            while time.monotonic() < end_time:
                if msvcrt.kbhit():
                    key = msvcrt.getwch().lower()
                    if key in ("q", "b"):
                        print("")
                        return
                    if key == "z":
                        print("")
                        set_zero_point(motor, state_file, require_confirm=False)
                        motor.set_mode(regmap.MODE_OFF)
                        time.sleep(0.2)
                        ensure_mode(motor, regmap.MODE_OFF)
                        print("")
                time.sleep(0.02)
    finally:
        print("")


def set_common_mode(motor: SimplexMotor) -> None:
    print_modes()
    mode = prompt_int("Mode value")
    common_values = {value for value, _name, _note in MODE_TABLE}
    if mode not in common_values:
        print("That is not in the common test mode list. Use raw/advanced mode instead.")
        return
    motor.set_mode(mode)
    print(f"Mode set to {mode}.")


def set_raw_mode(motor: SimplexMotor, allow_dangerous_modes: bool) -> None:
    print_modes()
    mode = prompt_int("Raw mode value")
    if mode in DANGEROUS_OR_SPECIAL_MODES and not allow_dangerous_modes:
        print("This mode is blocked by default for bench safety.")
        print("Restart with --allow-dangerous-modes if you intentionally need it.")
        return

    if not confirm(f"Set raw mode {mode} now?"):
        print("Cancelled.")
        return

    motor.set_mode(mode)
    print(f"Raw mode set to {mode}.")


def read_manual_register(motor: SimplexMotor) -> None:
    manual_register = prompt_int("Manual register number, for example Mode=400")
    if manual_register < 1:
        print("Manual register number must be 1 or greater. Example: Mode = 400.")
        return

    code_address = manual_register - 1
    value = motor.get_register_value(f"Reg{manual_register}", code_address)
    print(f"Register {manual_register} / code address {code_address}: {value}")


def main() -> None:
    args = build_parser().parse_args()
    state_file = resolve_state_file(args.zero_state_file)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("pymodbus").setLevel(logging.WARNING)

    print_available_ports()
    print("")
    print(f"Connecting to {args.port}, slave {args.slave}, {args.baudrate} baud...")
    print(f"Position reference record: {state_file}")

    motor = SimplexMotor(
        port=args.port,
        baudrate=args.baudrate,
        slave_id=args.slave,
        parity="E",
        stopbits=1,
        timeout=1.0,
        debug=True,
    )

    try:
        motor.connect()
        print("Connected.")
        if args.restore_last_position:
            restore_saved_position_reference(motor, state_file, require_confirm=False)
        print("Tip: start with status, ramp config, then small position moves like 10, -10, 0.")

        while True:
            print("")
            print("==== Simplex Motion Test Menu ====")
            print("1. Show status")
            print("2. Configure ramp speed/acc/dec")
            print("3. Position ramp test")
            print("4. Speed ramp test")
            print("5. Freewheel mode")
            print("6. Reset/disable motor")
            print("7. Off mode")
            print("8. Beep")
            print("9. Read manual register")
            print("10. List modes")
            print("11. Set common mode by value")
            print("12. Set raw/advanced mode")
            print("13. Manual turn check (Off mode)")
            print("14. Neutral angle monitor (Off + live position)")
            print("15. Torque control test")
            print("16. Set zero point (current position = 0)")
            print("17. Absolute position test (software zero)")
            print("18. Restore saved position reference")
            print("q. Quit")

            choice = input("> ").strip().lower()
            try:
                if choice == "1":
                    show_status(motor)
                elif choice == "2":
                    configure_ramp(motor, args.speed, args.acc, args.dec)
                elif choice == "3":
                    position_ramp_test(motor)
                elif choice == "4":
                    speed_ramp_test(motor)
                elif choice == "5":
                    freewheel_test(motor)
                elif choice == "6":
                    save_current_position_record(motor, state_file, "manual_reset_before_reset")
                    motor.set_mode(regmap.MODE_RESET)
                    print("Reset/disable requested.")
                elif choice == "7":
                    motor.set_mode(regmap.MODE_OFF)
                    print("Off mode set.")
                elif choice == "8":
                    duration_ms = prompt_int("Beep duration ms", 300)
                    motor.beep(duration_ms)
                elif choice == "9":
                    read_manual_register(motor)
                elif choice == "10":
                    print_modes()
                elif choice == "11":
                    set_common_mode(motor)
                elif choice == "12":
                    set_raw_mode(motor, args.allow_dangerous_modes)
                elif choice == "13":
                    manual_turn_check(motor)
                elif choice == "14":
                    neutral_angle_monitor(motor, state_file)
                elif choice == "15":
                    torque_control_test(
                        motor,
                        args.torque_limit_mnm,
                        args.torque_speed_limit,
                        args.torque_percent_limit,
                        args.torque_pulse_seconds,
                        args.allow_dangerous_modes,
                    )
                elif choice == "16":
                    set_zero_point(motor, state_file)
                elif choice == "17":
                    absolute_position_test(motor, state_file)
                elif choice == "18":
                    restore_saved_position_reference(motor, state_file)
                elif choice in ("q", "quit", "exit"):
                    break
                else:
                    print("Unknown choice.")
            except Exception as exc:
                print(f"Operation failed: {exc}")
                print("For safety, requesting Reset/disable.")
                try:
                    motor.set_mode(regmap.MODE_RESET)
                except Exception as reset_exc:
                    print(f"Reset/disable also failed: {reset_exc}")

    finally:
        print("Resetting and closing...")
        try:
            save_current_position_record(motor, state_file, "program_exit_before_reset")
        except Exception as exc:
            print(f"Could not save position record during shutdown: {exc}")
        try:
            motor.set_mode(regmap.MODE_RESET)
        except Exception as exc:
            print(f"Could not reset motor during shutdown: {exc}")
        motor.close()


if __name__ == "__main__":
    main()
