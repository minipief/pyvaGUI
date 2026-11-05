"""Child-process entry point for asynchronous solver execution."""

import json
import os
import sys
import traceback
from pathlib import Path

import numpy as np

from pyvagui.model.layup import Layup
from pyvagui.model.materials import material_from_dict
from pyvagui.model.solvers import SolverSpec
from pyvagui.services.worker import CalculationWorker


_message_stream = None


def _send(message: dict) -> None:
    """Append one JSON message for the parent process to read."""
    if _message_stream is None:
        return
    _message_stream.write(json.dumps(message, allow_nan=True) + "\n")
    _message_stream.flush()


def _result_values(values: np.ndarray) -> tuple[list, bool]:
    """Encode real or complex numeric arrays for JSON transport."""
    if np.iscomplexobj(values):
        encoded = [
            [float(value.real), float(value.imag)] for value in values
        ]
        return encoded, True
    return values.tolist(), False


def _send_layup_result(result) -> None:
    """Serialize one completed layup and its real or complex values."""
    values, is_complex = _result_values(result.values)
    _send({
        "type": "layup_result",
        "layup_id": result.layup_id,
        "layup_name": result.layup_name,
        "values": values,
        "complex": is_complex,
    })


def main(payload_path: str | Path, message_path: str | Path) -> int:
    """Read model data and write progress messages to a file."""
    global _message_stream
    try:
        with Path(message_path).open("w", encoding="utf-8") as message_file:
            _message_stream = message_file
            payload_text = Path(payload_path).read_text(encoding="utf-8")
            payload = json.loads(payload_text)
            solver = SolverSpec.from_dict(payload["solver"])
            layups = [Layup.from_dict(item) for item in payload["layups"]]
            material_specs = {
                material.id: material
                for material in map(
                    material_from_dict,
                    payload["materials"],
                )
            }
            worker = CalculationWorker(solver, layups, material_specs)
            frequencies = worker.solver.frequencies.frequencies()
            _send({
                "type": "started",
                "solver_id": worker.solver.id,
                "solver_name": worker.solver.name,
                "solver_type": worker.solver.solver_type.value,
                "frequencies": frequencies.tolist(),
                "labels": worker.solver.frequencies.labels(),
                "reference_impedance": worker.reference_impedance,
                "angle_deg": worker.solver.angle_deg,
            })
            worker.layup_result.connect(_send_layup_result)
            worker.layup_finished.connect(
                lambda message: _send({"type": "message", "text": message})
            )
            worker.progress.connect(
                lambda done, total: _send({
                    "type": "progress",
                    "done": done,
                    "total": total,
                })
            )
            worker.finished.connect(
                lambda result: _send({"type": "finished"})
            )
            worker.failed.connect(
                lambda message: _send({"type": "failed", "message": message})
            )
            if sys.stdout is None:
                sys.stdout = open(os.devnull, "w", encoding="utf-8")
            if sys.stderr is None:
                sys.stderr = sys.stdout
            worker.run()
    except Exception:
        _send({"type": "failed", "message": traceback.format_exc()})
        return 1
    finally:
        _message_stream = None
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Expected payload and message file paths")
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
