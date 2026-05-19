import argparse
import logging
import sys
import time

from serial.tools import list_ports

import reg_map as regmap
from simplexMotor import SimplexMotor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Change and store a Simplex Motion motor Modbus slave id."
    )
    parser.add_argument("--port", default="COM3", help="Windows COM port, default: COM3")
    parser.add_argument("--current", type=int, required=True, help="Current motor slave id")
    parser.add_argument("--target", type=int, required=True, help="New target slave id")
    parser.add_argument("--baudrate", type=int, default=57600, help="Modbus baud rate, default: 57600")
    parser.add_argument("--timeout", type=float, default=1.0, help="Serial timeout seconds")
    parser.add_argument("--yes", action="store_true", help="Skip interactive confirmation")
    parser.add_argument("--debug", action="store_true", help="Enable verbose motor logs")
    return parser


def validate_slave_id(value: int, label: str) -> None:
    if not (1 <= value <= 126):
        raise ValueError(f"{label} slave id must be in range [1, 126]")


def print_available_ports() -> None:
    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return

    print("Available serial ports:")
    for port in ports:
        desc = f" - {port.description}" if port.description else ""
        print(f"  {port.device}{desc}")


def confirm_change(port: str, current: int, target: int) -> bool:
    print("")
    print("About to change Simplex Motion Modbus slave id:")
    print(f"  Port:       {port}")
    print(f"  Current id: {current}")
    print(f"  Target id:  {target}")
    print("")
    print("Make sure only the motor with the current id is being addressed.")
    print("If several motors still share the same id, disconnect the others first.")
    answer = input("Type CHANGE to continue: ").strip()
    return answer == "CHANGE"


def open_motor(args: argparse.Namespace, slave_id: int) -> SimplexMotor:
    motor = SimplexMotor(
        port=args.port,
        baudrate=args.baudrate,
        slave_id=slave_id,
        timeout=args.timeout,
        parity="E",
        stopbits=1,
        debug=args.debug,
    )
    motor.connect()
    return motor


def try_set_mode(motor: SimplexMotor, mode: int, fallback_slave_id: int | None = None) -> None:
    try:
        motor.set_mode(mode)
        return
    except Exception:
        if fallback_slave_id is None:
            raise

    original_slave_id = motor.slave_id
    motor.slave_id = fallback_slave_id
    try:
        motor.set_mode(mode)
    except Exception:
        motor.slave_id = original_slave_id
        raise


def main() -> int:
    args = build_parser().parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("pymodbus").setLevel(logging.WARNING)

    validate_slave_id(args.current, "current")
    validate_slave_id(args.target, "target")

    if args.current == args.target:
        print("Current id and target id are the same. Nothing to change.")
        return 0

    print_available_ports()

    if not args.yes and not confirm_change(args.port, args.current, args.target):
        print("Cancelled.")
        return 1

    motor: SimplexMotor | None = None
    verifier: SimplexMotor | None = None

    try:
        print("")
        print(f"Connecting with current slave id {args.current}...")
        motor = open_motor(args, args.current)

        current_address = motor.get_address()
        print(f"Address register currently reads: {current_address}")

        if current_address != args.current:
            print("")
            print("WARNING: Address register does not match the id used for communication.")
            print("The script will continue, but verify the wiring/id before changing multiple motors.")

        print("")
        print(f"Writing Address register #50 -> {args.target}...")
        motor.set_address(args.target)

        print("Storing settings to non-volatile memory with Mode=9 Store...")
        try_set_mode(motor, regmap.MODE_STORE, fallback_slave_id=args.target)
        time.sleep(1.0)

        print("Applying new address with Mode=1 Reset...")
        try_set_mode(motor, regmap.MODE_RESET, fallback_slave_id=args.target)
        time.sleep(1.5)

        motor.close()
        motor = None

        print("")
        print(f"Verifying communication with new slave id {args.target}...")
        verifier = open_motor(args, args.target)
        verified_address = verifier.get_address()
        print(f"New address register reads: {verified_address}")

        if verified_address != args.target:
            print("")
            print("ERROR: New id responded, but Address register did not match target.")
            return 2

        print("")
        print("Slave id change completed and verified.")
        return 0

    except Exception as exc:
        print("")
        print(f"ERROR: failed to change slave id: {exc}")
        print("")
        print("Recovery notes:")
        print("- If the write/store succeeded but verification failed, power cycle the motor.")
        print(f"- Then try connecting with --current {args.target}.")
        print(f"- If that fails, try the original id --current {args.current}.")
        return 2

    finally:
        if motor is not None:
            motor.close()
        if verifier is not None:
            verifier.close()


if __name__ == "__main__":
    sys.exit(main())
