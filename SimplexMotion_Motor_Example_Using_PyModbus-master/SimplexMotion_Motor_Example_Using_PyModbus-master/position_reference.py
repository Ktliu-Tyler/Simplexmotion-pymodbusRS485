from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_STATE_FILE = "motor_state/position_reference.json"

SOFTWARE_REFERENCE_NOTE = (
    "Software position reference only. Restore is valid only if the shaft did "
    "not move while the motor/controller was powered off. For true absolute "
    "startup position, configure homing or use an absolute external reference."
)


def resolve_state_file(path_text: str) -> Path:
    return Path(path_text).expanduser()


def motor_state_key(port: str, slave_id: int) -> str:
    return f"{str(port).upper()}:{slave_id}"


def counts_to_degrees(position_counts: int, cpr: int) -> float:
    return position_counts * 360.0 / float(cpr)


def load_state(state_file: Path) -> dict[str, Any]:
    if not state_file.exists():
        return {}

    try:
        loaded = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if isinstance(loaded, dict):
        return loaded
    return {}


def save_state(state_file: Path, state: dict[str, Any]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_motor_record(state_file: Path, port: str, slave_id: int) -> dict[str, Any]:
    state = load_state(state_file)
    record = state.get(motor_state_key(port, slave_id), {})
    if isinstance(record, dict):
        return record
    return {}


def save_motor_position_record(
    state_file: Path,
    *,
    port: str,
    slave_id: int,
    baudrate: int,
    cpr: int,
    position_counts: int,
    event: str,
    zero_set: bool = False,
    previous_position_counts: int | None = None,
) -> dict[str, Any]:
    state = load_state(state_file)
    key = motor_state_key(port, slave_id)
    now = datetime.now().isoformat(timespec="seconds")

    record = state.get(key, {})
    if not isinstance(record, dict):
        record = {}

    record.update(
        {
            "port": port,
            "slave_id": slave_id,
            "baudrate": baudrate,
            "cpr": cpr,
            "last_position_counts": position_counts,
            "last_position_deg": counts_to_degrees(position_counts, cpr),
            "last_saved_at": now,
            "last_event": event,
            "note": SOFTWARE_REFERENCE_NOTE,
        }
    )

    if zero_set:
        record.update(
            {
                "zero_set_at": now,
                "zero_position_counts": 0,
                "previous_position_counts_before_zero": previous_position_counts,
                "previous_position_deg_before_zero": (
                    counts_to_degrees(previous_position_counts, cpr)
                    if previous_position_counts is not None
                    else None
                ),
            }
        )

    state[key] = record
    save_state(state_file, state)
    return record
