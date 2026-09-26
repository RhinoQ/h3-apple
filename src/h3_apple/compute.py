"""Internal, versioned arithmetic policy and self-contained replay records."""

import json
from copy import deepcopy
from pathlib import Path
import platform
import re
import subprocess

from .assets import data_file, identity
from .io import source_identity, write_json

SCHEMA = "h3-apple-compute/v1"


def hardware_identity(assets, environment):
    native = json.loads(subprocess.check_output(
        [assets["binary"]["path"], "--gpu-info"], env=environment,
        text=True, timeout=30))
    displays = json.loads(subprocess.check_output(
        ["/usr/sbin/system_profiler", "SPDisplaysDataType", "-json"],
        text=True, timeout=30))["SPDisplaysDataType"]
    gpus = [dict(model=g.get("sppci_model"), cores=g.get("sppci_cores"),
                 metal=g.get("spdisplays_mtlgpufamilysupport")) for g in displays]
    return dict(native=native, gpus=gpus, machine=platform.machine(),
                kernel=platform.release())


def prepare(request, assets, prepared, workspace, environment, *, replay=None):
    """Validate compatibility before launching model work; no public tuning UI."""
    if "stable-compute-v1" not in assets.get("engine_capabilities", ()):
        raise RuntimeError("The installed engine does not support the required compute policy.")
    policy = data_file("compute-policy.json")
    hardware = hardware_identity(assets, environment)
    if (hardware["native"].get("cpu") != policy["device"]["model"]
            or not hardware["native"].get("matrix_cores")
            or len(hardware["gpus"]) != 1
            or hardware["gpus"][0]["cores"] != policy["device"]["cores"]):
        raise RuntimeError("This candidate compute policy currently targets only the 40-core M5 Max.")
    # Content identity deliberately excludes filesystem paths and live RAM.
    inputs = {k: v for k, v in request.items() if k != "reference_images"}
    inputs["references"] = [{k: p[k] for k in ("index", "width", "height", "sha256")}
                            for p in prepared]
    context = dict(hardware=hardware, model=assets["identity"],
                   adapter=assets["adapter"]["sha256"], recipe=assets["recipe"],
                   package_source_sha256=source_identity(),
                   engine={k: assets[k]["sha256"] for k in ("binary", "library")},
                   policy_sha256=identity(policy), inputs=inputs)
    plan = deepcopy(dict(schema=SCHEMA, policy=policy["id"], context=context,
                         qmm=policy["qmm"], environment=policy["environment"]))
    if replay is not None:
        replay = json.loads(Path(replay).read_text()) if isinstance(replay, (str, Path)) else replay
        if (not isinstance(replay, dict) or replay.get("schema") != SCHEMA
                or replay.get("sha256") != identity({k: v for k, v in replay.items() if k != "sha256"})):
            raise ValueError("Compute replay record is invalid or changed.")
        if any(replay.get(k) != v for k, v in plan.items()):
            raise ValueError("Compute replay is incompatible with the hardware, build, policy or inputs.")
        if not replay.get("actual_routes"):
            raise ValueError("Compute replay has no executed route evidence.")
    qmm_path = Path(workspace) / "qmm-plan.json"
    with qmm_path.open("x") as stream:
        json.dump(plan["qmm"], stream, indent=2)
        stream.write("\n")
    environment.update(plan["environment"], VPIPE_H3_QMM_PLAN_INPUT=str(qmm_path))
    write_json(Path(workspace) / "compute-plan-pending.json", plan)
    return plan, replay


def complete(plan, replay, log, workspace):
    routes = sorted(set(re.findall(r"\[h3-plan\] ([^\r\n]+)", log)))
    if (not any(r.startswith("dit ") for r in routes)
            or not any(r.startswith("vae ") for r in routes)
            or "replayed research qmm plan:" not in log):
        raise RuntimeError("The engine did not confirm the complete compute policy.")
    if replay is not None and routes != replay["actual_routes"]:
        raise RuntimeError("Actual compute routes differ from the strict replay record.")
    result = dict(plan, actual_routes=routes)
    result["sha256"] = identity(result)
    write_json(Path(workspace) / "compute-plan.json", result)
    return result
