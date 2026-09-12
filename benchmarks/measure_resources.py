#!/usr/bin/env python3
"""Measure a real product command while reserving excess physical RAM on macOS.

The reservation is anonymous, touched, and mlocked. This does not emulate a
different GPU or change hw.memsize / Metal's device limits. No model code is
patched. Each invocation owns one new evidence directory and its child process.
"""

import argparse
import ctypes
import hashlib
import json
import mmap
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

GIB = 1024**3
LIB = ctypes.CDLL(None, use_errno=True)
PROC = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)


class RUsage(ctypes.Structure):
    # Darwin rusage_info_v4, also used by the existing research resource sampler.
    _fields_ = [("uuid", ctypes.c_uint8 * 16)] + [
        (name, ctypes.c_uint64) for name in (
            "user_time system_time pkg_idle_wkups interrupt_wkups pageins wired_size "
            "resident_size phys_footprint proc_start_abstime proc_exit_abstime "
            "child_user_time child_system_time child_pkg_idle_wkups child_interrupt_wkups "
            "child_pageins child_elapsed_abstime diskio_bytesread diskio_byteswritten "
            "cpu_time_qos_default cpu_time_qos_maintenance cpu_time_qos_background "
            "cpu_time_qos_utility cpu_time_qos_legacy cpu_time_qos_user_initiated "
            "cpu_time_qos_user_interactive billed_system_time serviced_system_time "
            "logical_writes lifetime_max_phys_footprint instructions cycles "
            "billed_energy serviced_energy interval_max_phys_footprint runnable_time"
        ).split()
    ]


PROC.proc_pid_rusage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(RUsage)]
PROC.proc_pid_rusage.restype = ctypes.c_int
PROC.proc_listchildpids.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
PROC.proc_listchildpids.restype = ctypes.c_int
LIB.mlock.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
LIB.munlock.argtypes = LIB.mlock.argtypes


def usage(pid):
    value = RUsage()
    if PROC.proc_pid_rusage(pid, 4, ctypes.byref(value)):
        return None
    return {name: int(getattr(value, name)) for name in (
        "wired_size", "resident_size", "phys_footprint", "lifetime_max_phys_footprint",
        "diskio_bytesread", "diskio_byteswritten", "pageins")}


def children(pid):
    buffer = (ctypes.c_int * 256)()
    count = PROC.proc_listchildpids(pid, buffer, ctypes.sizeof(buffer))
    if count < 0:
        return []
    if count >= len(buffer):
        raise RuntimeError("Child process inventory exceeded measurement capacity")
    # Unlike proc_listpids, this convenience API returns a PID count, not bytes.
    return [int(p) for p in buffer[:count] if p > 0]


def process_tree(pid):
    queue, found = [pid], {}
    while queue:
        current = queue.pop()
        if current in found:
            continue
        value = usage(current)
        if value is not None:
            found[current] = value
            queue.extend(children(current))
    return found


def host():
    raw = subprocess.check_output(["/usr/bin/vm_stat"], text=True, timeout=5)
    page_size = int(re.search(r"page size of (\d+) bytes", raw)[1])
    pages = {key: int(value) for key, value in re.findall(r"^([^:]+):\s+(\d+)\.", raw, re.M)}
    swap = subprocess.check_output(["/usr/sbin/sysctl", "-n", "vm.swapusage"], text=True, timeout=5)
    pressure = int(subprocess.check_output(
        ["/usr/sbin/sysctl", "-n", "kern.memorystatus_vm_pressure_level"], text=True, timeout=5))
    return {"page_size": page_size, "vm_pages": pages, "pressure": pressure,
            "swap_bytes": int(float(re.search(r"used\s*=\s*([0-9.]+)M", swap)[1]) * 1024**2)}


def disk(paths):
    seen, logical, allocated, count, free = set(), 0, 0, 0, {}
    for root in paths:
        existing = root
        while not existing.exists():
            existing = existing.parent
        free[str(root)] = shutil.disk_usage(existing).free
        if not root.exists():
            continue
        for directory, _, names in os.walk(root, followlinks=False):
            for name in names:
                path = Path(directory) / name
                try:
                    if path.is_symlink():
                        continue
                    stat = path.stat()
                except FileNotFoundError:
                    continue
                key = (stat.st_dev, stat.st_ino)
                if key not in seen:
                    seen.add(key)
                    logical += stat.st_size
                    allocated += stat.st_blocks * 512
                    count += 1
    return {"unique_logical_bytes": logical, "allocated_bytes": allocated,
            "files": count, "free_bytes": free}


class Reservation:
    def __init__(self):
        self.regions = []
        self.size = 0

    def add(self, size):
        region = mmap.mmap(-1, size)
        view = ctypes.c_char.from_buffer(region)
        address = ctypes.addressof(view)
        ctypes.memset(address, 0xA5, size)
        if LIB.mlock(address, size):
            error = OSError(ctypes.get_errno(), "mlock failed")
            del view
            region.close()
            raise error
        del view
        self.regions.append((region, address, size))
        self.size += size

    def close(self):
        while self.regions:
            region, address, size = self.regions.pop()
            LIB.munlock(address, size)
            region.close()
        self.size = 0


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget-gib", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--watch-dir", type=Path, action="append", default=[])
    parser.add_argument("--timeout", type=float, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required")
    physical = int(subprocess.check_output(["/usr/sbin/sysctl", "-n", "hw.memsize"], text=True))
    budget = round(args.budget_gib * GIB)
    if not 16 * GIB <= budget <= physical:
        parser.error("budget must be between 16 GiB and physical memory")
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    watch = [args.output, *(p.resolve() for p in args.watch_dir)]
    first = host()
    record = {"physical_memory_bytes": physical, "available_budget_bytes": budget,
              "reservation_target_bytes": physical - budget, "command": command,
              "python": sys.executable, "cwd": os.getcwd(), "initial_host": first,
              "initial_disk": disk(watch),
              "measurement_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "boundary": "Physical-page reservation on the recorded host; not another Mac or a change to Metal device limits."}
    write(args.output / "plan.json", record)
    reservation, process, failure = Reservation(), None, None
    started, ready, warning_since = time.monotonic(), None, None
    maximum_footprint, maximum_tree, maximum_disk = {}, 0, 0
    minimum_wired, maximum_swap = None, 0

    def interrupted(_signum, _frame):
        raise KeyboardInterrupt("Measurement interrupted")

    signal.signal(signal.SIGTERM, interrupted)
    try:
        if first["pressure"] != 1:
            raise RuntimeError("Initial memory pressure is not normal")
        before = usage(os.getpid())
        while reservation.size < physical - budget:
            reservation.add(min(GIB, physical - budget - reservation.size))
            state = host()
            if state["pressure"] != 1 or state["swap_bytes"] - first["swap_bytes"] > 256 * 1024**2:
                raise RuntimeError("Resource gate failed while reserving physical memory")
        own = usage(os.getpid())
        wired_delta = own["wired_size"] - before["wired_size"]
        if wired_delta < reservation.size:
            raise RuntimeError(f"Locked pages not verified: {wired_delta} < {reservation.size}")
        write(args.output / "reservation.json", {"bytes": reservation.size, "rusage_before": before,
              "rusage_ready": own, "ready_host": host(), "ready_seconds": time.monotonic() - started})
        print(json.dumps({"phase": "reservation_ready", "budget_gib": args.budget_gib,
                          "reserved_gib": reservation.size / GIB}), flush=True)
        with (args.output / "stdout.log").open("w") as stdout, (args.output / "stderr.log").open("w") as stderr:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                       start_new_session=True)
            ready = time.monotonic()
            write(args.output / "running.json", {"pid": process.pid, "monitor_pid": os.getpid()})
            with (args.output / "samples.jsonl").open("w") as samples:
                while process.poll() is None:
                    state = host()
                    own = usage(os.getpid())
                    values = process_tree(process.pid)
                    tree_footprint = sum(v["phys_footprint"] for v in values.values())
                    maximum_tree = max(maximum_tree, tree_footprint)
                    for pid, value in values.items():
                        maximum_footprint[pid] = max(maximum_footprint.get(pid, 0), value["lifetime_max_phys_footprint"])
                    space = disk(watch)
                    maximum_disk = max(maximum_disk, space["unique_logical_bytes"])
                    wired = own["wired_size"] - before["wired_size"]
                    minimum_wired = wired if minimum_wired is None else min(minimum_wired, wired)
                    maximum_swap = max(maximum_swap, state["swap_bytes"] - first["swap_bytes"])
                    sample = {"elapsed_seconds": time.monotonic() - ready, "host": state,
                              "reservation_wired_bytes": wired, "processes": values, "disk": space}
                    samples.write(json.dumps(sample) + "\n")
                    samples.flush()
                    if wired < reservation.size:
                        raise RuntimeError("Reserved pages lost their verified wired status")
                    if maximum_swap > 256 * 1024**2:
                        raise RuntimeError("System swap increased by more than 256 MiB")
                    if state["pressure"] >= 4:
                        raise RuntimeError("Critical system memory pressure")
                    if state["pressure"] >= 2:
                        warning_since = warning_since or time.monotonic()
                        if time.monotonic() - warning_since >= 2:
                            raise RuntimeError("System memory warning persisted for two seconds")
                    else:
                        warning_since = None
                    if time.monotonic() - ready > args.timeout:
                        raise TimeoutError("Command exceeded the declared timeout")
                    time.sleep(0.5)
            if process.returncode:
                raise RuntimeError(f"Product command exited {process.returncode}")
    except BaseException as error:
        failure = str(error) or type(error).__name__
    finally:
        reservation.close()
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
        result = {**record, "status": "failed" if failure else "complete", "error": failure,
                  "returncode": process.returncode if process else None,
                  "elapsed_seconds": time.monotonic() - (ready or started),
                  "peak_process_footprints_bytes": maximum_footprint,
                  "sampled_process_tree_peak_bytes": maximum_tree,
                  "minimum_reservation_wired_bytes": minimum_wired,
                  "maximum_swap_growth_bytes": maximum_swap,
                  "peak_watched_unique_logical_bytes": maximum_disk,
                  "final_host_after_release": host(), "reservation_released": reservation.size == 0}
        write(args.output / "result.json", result)
        print(json.dumps({key: result[key] for key in ("status", "error", "elapsed_seconds",
              "sampled_process_tree_peak_bytes", "maximum_swap_growth_bytes", "reservation_released")}), flush=True)
    return 1 if failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
