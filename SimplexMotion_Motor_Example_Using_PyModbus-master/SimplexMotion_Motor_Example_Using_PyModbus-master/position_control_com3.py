import argparse
import logging
import time

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Interactive Simplex Motion position control test.")
    parser.add_argument("--port", default="COM3", help="Windows COM port, default: COM3")
    parser.add_argument("--slave", type=int, default=1, help="Modbus slave address, default: 1")
    parser.add_argument("--baudrate", type=int, default=57600, help="Modbus baud rate, default: 57600")
    parser.add_argument("--speed", type=int, default=90, help="Ramp speed limit in deg/s, default: 90")
    parser.add_argument("--acc", type=int, default=180, help="Ramp acceleration in deg/s^2, default: 180")
    parser.add_argument("--dec", type=int, default=180, help="Ramp deceleration in deg/s^2, default: 180")
    parser.add_argument("--no-reset", action="store_true", help="Keep the current MotorPosition reference at startup")
    parser.add_argument(
        "--restore-last-position",
        action="store_true",
        help="Restore saved MotorPosition at startup. Use only if the shaft did not move while powered off.",
    )
    parser.add_argument(
        "--zero-state-file",
        default=DEFAULT_STATE_FILE,
        help=f"Position reference record file, default: {DEFAULT_STATE_FILE}",
    )
    return parser


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


def enable_position_ramp_at_current_position(motor: SimplexMotor) -> None:
    motor.set_target_source_register()
    current_counts = motor.get_position_counts()
    motor.set_target_position_counts(current_counts)
    motor.set_mode(regmap.MODE_POSITION_RAMP)
    time.sleep(0.2)


def set_zero_point(motor: SimplexMotor, state_file) -> None:
    print("")
    print("Setting current shaft position as software zero.")
    print(f"Important: {SOFTWARE_REFERENCE_NOTE}")
    previous_counts = motor.get_position_counts()
    print(f"Current before zero: {counts_to_degrees(previous_counts, motor.cpr):.3f} deg")

    motor.set_mode(regmap.MODE_OFF)
    time.sleep(0.2)
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
        event="zero_set",
        zero_set=True,
        previous_position_counts=previous_counts,
    )
    print("Zero point set.")
    enable_position_ramp_at_current_position(motor)


def restore_saved_position_reference(motor: SimplexMotor, state_file) -> bool:
    record = load_motor_record(state_file, motor.port, motor.slave_id)
    if not record:
        print("No saved position reference record for this port/slave.")
        return False

    saved_counts = record.get("last_position_counts")
    if not isinstance(saved_counts, int):
        print("Saved record has no valid last_position_counts.")
        return False

    print("")
    print("Restoring saved software position reference.")
    print(f"Saved position: {counts_to_degrees(saved_counts, motor.cpr):.3f} deg ({saved_counts} counts)")
    print(f"Saved at: {record.get('last_saved_at', 'unknown')}")
    print("Only use this if the shaft did not move while motor/controller power was off.")

    motor.set_mode(regmap.MODE_OFF)
    time.sleep(0.2)
    motor.set_motor_position_counts(saved_counts)
    motor.set_target_position_counts(saved_counts)
    save_current_position_record(motor, state_file, "restore_saved_reference")
    return True


def main() -> None:
    args = build_parser().parse_args()
    state_file = resolve_state_file(args.zero_state_file)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("pymodbus").setLevel(logging.WARNING)

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

        if args.restore_last_position:
            restore_saved_position_reference(motor, state_file)
        elif not args.no_reset:
            print("Resetting motor position reference to 0 degrees...")
            motor.set_mode(regmap.MODE_RESET)
            time.sleep(0.5)
        else:
            print("Keeping current MotorPosition reference.")

        motor.set_target_source_register()
        motor.set_ramp_speed_max(args.speed)
        motor.set_ramp_acc_dec_max(args.acc, args.dec)

        print("Enabling position ramp mode...")
        enable_position_ramp_at_current_position(motor)

        print("")
        print("Position control ready.")
        print("Enter an absolute target position in degrees from the current zero, for example: 30, -30, 0")
        print("Commands: p = read position, z = set current position as zero, s = save record, r = restore saved reference, q = quit.")

        while True:
            user_input = input("Target position deg > ").strip()
            if user_input.lower() == "q":
                break
            if user_input.lower() == "p":
                motor.get_position()
                continue
            if user_input.lower() == "z":
                set_zero_point(motor, state_file)
                continue
            if user_input.lower() == "s":
                save_current_position_record(motor, state_file, "manual_save")
                continue
            if user_input.lower() == "r":
                if restore_saved_position_reference(motor, state_file):
                    enable_position_ramp_at_current_position(motor)
                continue

            try:
                target_deg = float(user_input)
            except ValueError:
                print("Invalid input. Please enter a number, 'p', or 'q'.")
                continue

            motor.set_position(target_deg)
            time.sleep(0.3)
            motor.get_position()

    finally:
        print("Disabling motor...")
        try:
            save_current_position_record(motor, state_file, "program_exit_before_reset")
        except Exception as exc:
            print(f"Could not save position record during shutdown: {exc}")
        try:
            motor.set_mode(regmap.MODE_RESET)
        finally:
            motor.close()


if __name__ == "__main__":
    main()
