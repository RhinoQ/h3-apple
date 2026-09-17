import pytest

from h3_apple import resolve
from h3_apple.host import check_machine


def mac(memory_gib=64, chip="Apple M5 Max"):
    return dict(system="Darwin", machine="arm64", macos="26.6.1", chip=chip,
                memory_bytes=memory_gib * 1024**3)


@pytest.mark.parametrize("chip", ["Apple M5 Pro", "Apple M5 Max"])
@pytest.mark.parametrize("resolution,duration", [("768p", 5), ("576p", 5), ("576p", 15)])
def test_64_gib_admission_is_limited_to_the_smaller_workloads(chip, resolution, duration):
    check_machine(mac(chip=chip), resolve("A boat.", resolution=resolution, duration=duration).to_dict())


@pytest.mark.parametrize("duration", [5 + 1 / 24, 10, 15])
def test_64_gib_native_long_request_has_actionable_error(duration):
    with pytest.raises(RuntimeError, match="--duration 5 or --resolution 576p"):
        check_machine(mac(), resolve("A boat.", duration=duration).to_dict())


@pytest.mark.parametrize("capacity", [96, 128])
def test_native_long_memory_boundary(capacity):
    check_machine(mac(capacity), resolve("A boat.").to_dict())


@pytest.mark.parametrize("capacity", [32, 36, 48, 63])
def test_insufficient_memory_is_rejected_for_preparation_and_short_generation(capacity):
    for request in [None, resolve("A boat.", resolution="576p", duration=5).to_dict()]:
        with pytest.raises(RuntimeError, match="at least 64 GiB"):
            check_machine(mac(capacity), request)


@pytest.mark.parametrize("field,value,reason", [
    ("chip", "Apple M4 Max", "M5 GPU kernels"),
    ("macos", "26.1", "macOS 26.2"),
    ("system", "Linux", "Apple Silicon Mac"),
    ("machine", "x86_64", "Apple Silicon Mac"),
])
def test_other_host_requirements_remain_enforced(field, value, reason):
    info = mac(128)
    info[field] = value
    with pytest.raises(RuntimeError, match=reason):
        check_machine(info)


@pytest.mark.parametrize("task", ["t2va", "fl2va", "ref2va"])
@pytest.mark.parametrize("missing", [None, "torch", "torchvision"])
def test_doctor_readiness_matches_reference_dependency_check(monkeypatch, tmp_path, task, missing):
    from h3_apple import host
    monkeypatch.setattr(host, "snapshot", lambda: mac(128))
    monkeypatch.setattr(host, "backend_identity", lambda: {})
    monkeypatch.setattr(host, "tool", lambda name: str(tmp_path / name))
    monkeypatch.setattr(host.importlib.util, "find_spec", lambda name: None if name == missing else object())
    monkeypatch.setattr("h3_apple.assets.load_assets", lambda _: dict(
        directory=str(tmp_path), identity="fixture", task=task))
    result = host.doctor(tmp_path)
    needs_extra = task != "t2va" and missing is not None
    assert result["ready"] is not needs_extra
    assert result["models"]["task"] == task
    if needs_extra:
        assert "./install.sh --ref2va" in result["errors"][0]
        with pytest.raises(RuntimeError, match="install.sh --ref2va"):
            host.check_reference_dependencies(task)
    else:
        host.check_reference_dependencies(task)
