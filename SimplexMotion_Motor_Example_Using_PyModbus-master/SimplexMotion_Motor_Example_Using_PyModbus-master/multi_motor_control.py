import argparse
import logging
import time

from pymodbus.client import ModbusSerialClient
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


SAFE_MODE_TABLE = [
    (regmap.MODE_OFF, "Off", "Stop/disable motor"),
    (regmap.MODE_RESET, "Reset", "Reset running data, then return to Off"),
    (regmap.MODE_QUICKSTOP, "Quickstop", "Controlled stop, then Off"),
    (regmap.MODE_POSITION_RAMP, "PositionRamp", "Position control with ramp"),
    (regmap.MODE_SPEED_RAMP, "SpeedRamp", "Speed control with target forced to 0 first"),
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-slave Simplex Motion RS485 control menu.")
    parser.add_argument("--port", default="COM3", help="Windows COM port, default: COM3")
    parser.add_argument("--slaves", default="1-3", help="Slave ids, for example 1-3 or 1,2,3, default: 1-3")
    parser.add_argument("--baudrate", type=int, default=57600, help="Modbus baud rate, default: 57600")
    parser.add_argument("--timeout", type=float, default=0.5, help="Per-request timeout in seconds")
    parser.add_argument("--speed", type=int, default=60, help="Default ramp speed in deg/s")
    parser.add_argument("--acc", type=int, default=120, help="Default ramp acceleration in deg/s^2")
    parser.add_argument("--dec", type=int, default=120, help="Default ramp deceleration in deg/s^2")
    parser.add_argument("--strict", action="store_true", help="Fail if any requested slave does not respond")
    parser.add_argument("--debug", action="store_true", help="Enable debug logs")
    parser.add_argument(
        "--keep-enabled-on-exit",
        action="store_true",
        help="Do not reset/disable motors on program exit",
    )
    parser.add_argument(
        "--zero-state-file",
        default=DEFAULT_STATE_FILE,
        help=f"Position reference record file, default: {DEFAULT_STATE_FILE}",
    )
    return parser


def parse_slaves(text: str) -> list[int]:
    slaves: list[int] = []
    for token in text.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start = int(start_text.strip())
            end = int(end_text.strip())
            step = 1 if end >= start else -1
            slaves.extend(range(start, end + step, step))
        else:
            slaves.append(int(token))

    unique = sorted(set(slaves))
    for slave in unique:
        if not (1 <= slave <= 126):
            raise ValueError(f"Slave id {slave} is outside expected range 1..126")
    return unique


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


def print_available_ports() -> None:
    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return

    print("Available serial ports:")
    for port in ports:
        desc = f" - {port.description}" if port.description else ""
        print(f"  {port.device}{desc}")


def make_shared_motor(client: ModbusSerialClient, args: argparse.Namespace, slave_id: int) -> SimplexMotor:
    motor = SimplexMotor(
        port=args.port,
        baudrate=args.baudrate,
        slave_id=slave_id,
        timeout=args.timeout,
        parity="E",
        stopbits=1,
        debug=args.debug,
    )
    motor.client = client
    motor.cpr = motor.get_counters_per_rev()
    return motor


def connect_bus(args: argparse.Namespace, slave_ids: list[int]) -> tuple[ModbusSerialClient, dict[int, SimplexMotor]]:
    print_available_ports()
    print("")
    print(f"Opening one shared RS485 bus on {args.port}, {args.baudrate} baud...")

    client = ModbusSerialClient(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
        parity="E",
        stopbits=1,
        bytesize=8,
    )
    if not client.connect():
        raise RuntimeError(f"Can NOT open {args.port}.")

    motors: dict[int, SimplexMotor] = {}
    print(f"Checking slaves: {', '.join(str(s) for s in slave_ids)}")
    for slave_id in slave_ids:
        try:
            motor = make_shared_motor(client, args, slave_id)
            address = motor.get_address()
            motors[slave_id] = motor
            print(f"  slave {slave_id}: OK, register Address={address}, CPR={motor.cpr}")
        except Exception as exc:
            print(f"  slave {slave_id}: no response or error: {exc}")
            if args.strict:
                client.close()
                raise

    if not motors:
        client.close()
        raise RuntimeError("No requested slaves responded.")

    return client, motors


def parse_motor_selection(text: str, motors: dict[int, SimplexMotor], allow_all: bool = True) -> list[int]:
    normalized = text.strip().lower()
    if allow_all and normalized in ("all", "a", "*"):
        return sorted(motors)

    selected = parse_slaves(normalized)
    missing = [slave for slave in selected if slave not in motors]
    if missing:
        raise ValueError(f"Not connected: {missing}. Connected slaves: {sorted(motors)}")
    return selected


def prompt_motor_selection(motors: dict[int, SimplexMotor], label: str, allow_all: bool = True) -> list[int]:
    default = "all" if allow_all else str(sorted(motors)[0])
    while True:
        text = prompt_text(label, default)
        try:
            return parse_motor_selection(text, motors, allow_all=allow_all)
        except ValueError as exc:
            print(exc)


def ensure_mode(motor: SimplexMotor, expected_mode: int) -> None:
    actual_mode = motor.get_mode()
    if actual_mode != expected_mode:
        raise RuntimeError(f"Slave {motor.slave_id}: expected mode {expected_mode}, got {actual_mode}")


def prepare_position_ramp(motor: SimplexMotor) -> float:
    motor.set_target_source_register()
    current_counts = motor.get_position_counts()
    motor.set_target_position_counts(current_counts)
    motor.set_mode(regmap.MODE_POSITION_RAMP)
    time.sleep(0.15)
    ensure_mode(motor, regmap.MODE_POSITION_RAMP)
    return counts_to_degrees(current_counts, motor.cpr)


def save_current_position_record(motor: SimplexMotor, state_file, event: str) -> None:
    position_counts = motor.get_position_counts()
    save_motor_position_record(
        state_file,
        port=motor.port,
        slave_id=motor.slave_id,
        baudrate=motor.baudrate,
        cpr=motor.cpr,
        position_counts=position_counts,
        event=event,
    )


def show_status_one(motor: SimplexMotor) -> None:
    mode = motor.get_mode()
    position = motor.get_position()
    speed = motor.get_speed()
    torque = motor.get_torque_mNm()
    ramp_speed = motor.get_ramp_speed_max()
    print(
        f"{motor.slave_id:>5}  {mode:>5}  {position:>11.3f}  "
        f"{speed:>11.3f}  {torque:>9}  {ramp_speed:>12.3f}"
    )


def show_status(motors: dict[int, SimplexMotor], selected: list[int] | None = None) -> None:
    selected = selected or sorted(motors)
    print("")
    print("Slave   Mode     Pos(deg)   Speed(deg/s)  Torque(mNm)  RampSpeed")
    print("-----  -----  -----------  ------------  -----------  ---------")
    for slave_id in selected:
        try:
            show_status_one(motors[slave_id])
        except Exception as exc:
            print(f"{slave_id:>5}  ERROR  {exc}")


def configure_ramp(motors: dict[int, SimplexMotor], selected: list[int], default_speed: int, default_acc: int, default_dec: int) -> None:
    speed = prompt_int("Ramp speed max deg/s", default_speed)
    acc = prompt_int("Ramp acceleration deg/s^2", default_acc)
    dec = prompt_int("Ramp deceleration deg/s^2", default_dec)

    for slave_id in selected:
        motor = motors[slave_id]
        print(f"slave {slave_id}: writing ramp speed/acc/dec...")
        motor.set_ramp_speed_max(speed)
        motor.set_ramp_acc_dec_max(acc, dec)
    print("Ramp settings written.")


def set_zero(motor: SimplexMotor, state_file, require_confirm: bool = True) -> bool:
    previous_counts = motor.get_position_counts()
    previous_deg = counts_to_degrees(previous_counts, motor.cpr)
    print(f"slave {motor.slave_id}: current position before zero = {previous_deg:.3f} deg")

    if require_confirm and not confirm(f"slave {motor.slave_id}: set current position to 0 degrees now?"):
        print("Cancelled.")
        return False

    motor.set_target_source_register()
    motor.set_mode(regmap.MODE_OFF)
    time.sleep(0.15)
    ensure_mode(motor, regmap.MODE_OFF)
    motor.set_motor_position_counts(0)
    motor.set_target_position_counts(0)
    verified_counts = motor.get_position_counts()

    save_motor_position_record(
        state_file,
        port=motor.port,
        slave_id=motor.slave_id,
        baudrate=motor.baudrate,
        cpr=motor.cpr,
        position_counts=verified_counts,
        event="multi_zero_set",
        zero_set=True,
        previous_position_counts=previous_counts,
    )
    print(f"slave {motor.slave_id}: zero set.")
    return True


def set_zero_selected(motors: dict[int, SimplexMotor], selected: list[int], state_file) -> None:
    print("")
    print("Set software zero for selected motors.")
    print(SOFTWARE_REFERENCE_NOTE)
    if len(selected) > 1 and not confirm(f"Set zero for slaves {selected}?"):
        print("Cancelled.")
        return

    for slave_id in selected:
        set_zero(motors[slave_id], state_file, require_confirm=len(selected) == 1)


def restore_saved_reference(motor: SimplexMotor, state_file, require_confirm: bool = True) -> bool:
    record = load_motor_record(state_file, motor.port, motor.slave_id)
    if not record:
        print(f"slave {motor.slave_id}: no saved position reference record.")
        return False

    saved_counts = record.get("last_position_counts")
    if not isinstance(saved_counts, int):
        print(f"slave {motor.slave_id}: saved record has no valid last_position_counts.")
        return False

    saved_deg = counts_to_degrees(saved_counts, motor.cpr)
    print(f"slave {motor.slave_id}: saved position = {saved_deg:.3f} deg ({saved_counts} counts)")
    print("Only restore if this shaft did not move while powered off.")

    if require_confirm and not confirm(f"slave {motor.slave_id}: restore saved position now?"):
        print("Cancelled.")
        return False

    motor.set_target_source_register()
    motor.set_mode(regmap.MODE_OFF)
    time.sleep(0.15)
    ensure_mode(motor, regmap.MODE_OFF)
    motor.set_motor_position_counts(saved_counts)
    motor.set_target_position_counts(saved_counts)
    save_current_position_record(motor, state_file, "multi_restore_saved_reference")
    print(f"slave {motor.slave_id}: restored.")
    return True


def restore_selected(motors: dict[int, SimplexMotor], selected: list[int], state_file) -> None:
    if len(selected) > 1 and not confirm(f"Restore saved position reference for slaves {selected}?"):
        print("Cancelled.")
        return

    for slave_id in selected:
        restore_saved_reference(motors[slave_id], state_file, require_confirm=len(selected) == 1)


def position_one_motor(motors: dict[int, SimplexMotor], state_file) -> None:
    selected = prompt_motor_selection(motors, "Slave id", allow_all=False)
    motor = motors[selected[0]]
    current_deg = prepare_position_ramp(motor)

    print("")
    print(f"Position control for slave {motor.slave_id}. Current coordinate: {current_deg:.3f} deg")
    print("Commands: number = absolute target deg, p = status, z = set zero, r = restore saved, b/q = back")

    while True:
        text = input(f"slave {motor.slave_id} target deg > ").strip().lower()
        if text in ("b", "back", "q"):
            return
        if text == "p":
            show_status(motors, [motor.slave_id])
            continue
        if text == "z":
            if set_zero(motor, state_file):
                prepare_position_ramp(motor)
            continue
        if text == "r":
            if restore_saved_reference(motor, state_file):
                prepare_position_ramp(motor)
            continue

        try:
            target_deg = float(text)
        except ValueError:
            print("Please enter a number, p, z, r, b, or q.")
            continue

        motor.set_position(target_deg)
        time.sleep(0.25)
        print(f"slave {motor.slave_id}: position = {motor.get_position():.3f} deg")


def position_group(motors: dict[int, SimplexMotor]) -> None:
    selected = prompt_motor_selection(motors, "Slaves for group position, for example all or 1,3")
    mode = prompt_text("Target input style: same or each", "same").strip().lower()

    targets: dict[int, float] = {}
    if mode.startswith("e"):
        for slave_id in selected:
            text = prompt_text(f"slave {slave_id} target deg, blank to skip", "")
            if not text:
                continue
            try:
                targets[slave_id] = float(text)
            except ValueError:
                print(f"slave {slave_id}: skipped invalid target.")
    else:
        target_deg = prompt_float("Common absolute target deg", 0.0)
        targets = {slave_id: target_deg for slave_id in selected}

    if not targets:
        print("No targets entered.")
        return

    print("")
    print("Preparing position ramp at each motor's current position...")
    for slave_id in targets:
        current_deg = prepare_position_ramp(motors[slave_id])
        print(f"slave {slave_id}: ready at {current_deg:.3f} deg")

    print("Writing targets sequentially on RS485...")
    for slave_id, target_deg in targets.items():
        print(f"slave {slave_id}: target {target_deg:.3f} deg")
        motors[slave_id].set_position(target_deg)

    time.sleep(0.3)
    show_status(motors, sorted(targets))


def set_mode_selected(motors: dict[int, SimplexMotor], selected: list[int]) -> None:
    print("")
    print("Safe mode choices:")
    for value, name, note in SAFE_MODE_TABLE:
        print(f"  {value:>3}  {name:<14} {note}")

    mode = prompt_int("Mode value")
    safe_modes = {value for value, _name, _note in SAFE_MODE_TABLE}
    if mode not in safe_modes:
        print("Blocked: this multi-motor menu only allows safe/common modes.")
        return

    if len(selected) > 1 and not confirm(f"Set mode {mode} for slaves {selected}?"):
        print("Cancelled.")
        return

    for slave_id in selected:
        motor = motors[slave_id]
        if mode == regmap.MODE_POSITION_RAMP:
            prepare_position_ramp(motor)
        elif mode == regmap.MODE_SPEED_RAMP:
            motor.set_target_source_register()
            motor.set_target_speed(0)
            motor.set_mode(mode)
        else:
            motor.set_mode(mode)
        print(f"slave {slave_id}: mode set to {mode}")


def reset_or_off_selected(motors: dict[int, SimplexMotor], selected: list[int], mode: int, state_file) -> None:
    name = "Reset/disable" if mode == regmap.MODE_RESET else "Off"
    if len(selected) > 1 and not confirm(f"{name} slaves {selected}?"):
        print("Cancelled.")
        return

    for slave_id in selected:
        motor = motors[slave_id]
        try:
            save_current_position_record(motor, state_file, f"before_{name.lower()}")
        except Exception as exc:
            print(f"slave {slave_id}: could not save position record: {exc}")
        motor.set_mode(mode)
        print(f"slave {slave_id}: {name} requested.")


def beep_one(motors: dict[int, SimplexMotor]) -> None:
    selected = prompt_motor_selection(motors, "Slave id", allow_all=False)
    duration_ms = prompt_int("Beep duration ms", 300)
    motors[selected[0]].beep(duration_ms)


def read_manual_register(motors: dict[int, SimplexMotor]) -> None:
    selected = prompt_motor_selection(motors, "Slave id or all")
    manual_register = prompt_int("Manual register number, for example Mode=400")
    if manual_register < 1:
        print("Manual register number must be 1 or greater.")
        return

    code_address = manual_register - 1
    for slave_id in selected:
        try:
            value = motors[slave_id].get_register_value(f"Reg{manual_register}", code_address)
            print(f"slave {slave_id}: register {manual_register} / code address {code_address} = {value}")
        except Exception as exc:
            print(f"slave {slave_id}: read failed: {exc}")


def main() -> None:
    args = build_parser().parse_args()
    slave_ids = parse_slaves(args.slaves)
    state_file = resolve_state_file(args.zero_state_file)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("pymodbus").setLevel(logging.WARNING)

    client = None
    motors: dict[int, SimplexMotor] = {}

    try:
        client, motors = connect_bus(args, slave_ids)
        print("")
        print(f"Connected slaves: {sorted(motors)}")
        print(f"Position reference record: {state_file}")
        print("Tip: configure ramp first, then use small absolute targets like 10, 0, -10.")

        while True:
            print("")
            print("==== Simplex Multi Motor Control ====")
            print(f"Connected slaves: {', '.join(str(s) for s in sorted(motors))}")
            print("1. Show status all")
            print("2. Show status selected")
            print("3. Configure ramp selected")
            print("4. Set zero selected")
            print("5. Absolute position one motor")
            print("6. Absolute position group")
            print("7. Off selected")
            print("8. Reset/disable selected")
            print("9. Restore saved position reference selected")
            print("10. Set safe/common mode selected")
            print("11. Beep one motor")
            print("12. Read manual register selected")
            print("q. Quit")

            choice = input("> ").strip().lower()
            try:
                if choice == "1":
                    show_status(motors)
                elif choice == "2":
                    selected = prompt_motor_selection(motors, "Slave id or all")
                    show_status(motors, selected)
                elif choice == "3":
                    selected = prompt_motor_selection(motors, "Slave id or all")
                    configure_ramp(motors, selected, args.speed, args.acc, args.dec)
                elif choice == "4":
                    selected = prompt_motor_selection(motors, "Slave id or all")
                    set_zero_selected(motors, selected, state_file)
                elif choice == "5":
                    position_one_motor(motors, state_file)
                elif choice == "6":
                    position_group(motors)
                elif choice == "7":
                    selected = prompt_motor_selection(motors, "Slave id or all")
                    reset_or_off_selected(motors, selected, regmap.MODE_OFF, state_file)
                elif choice == "8":
                    selected = prompt_motor_selection(motors, "Slave id or all")
                    reset_or_off_selected(motors, selected, regmap.MODE_RESET, state_file)
                elif choice == "9":
                    selected = prompt_motor_selection(motors, "Slave id or all")
                    restore_selected(motors, selected, state_file)
                elif choice == "10":
                    selected = prompt_motor_selection(motors, "Slave id or all")
                    set_mode_selected(motors, selected)
                elif choice == "11":
                    beep_one(motors)
                elif choice == "12":
                    read_manual_register(motors)
                elif choice in ("q", "quit", "exit"):
                    break
                else:
                    print("Unknown choice.")
            except Exception as exc:
                print(f"Operation failed: {exc}")
                print("For safety, reset/disable the affected motor(s) from menu 8 if needed.")

    finally:
        if motors and not args.keep_enabled_on_exit:
            print("Saving positions and resetting connected motors...")
            for slave_id, motor in motors.items():
                try:
                    save_current_position_record(motor, state_file, "multi_program_exit_before_reset")
                    motor.set_mode(regmap.MODE_RESET)
                    print(f"slave {slave_id}: reset/disable requested.")
                except Exception as exc:
                    print(f"slave {slave_id}: shutdown reset failed: {exc}")
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()
