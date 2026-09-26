import copy
import json

import pytest

from h3_apple import compute
from h3_apple.assets import identity


@pytest.fixture
def fixture(monkeypatch):
    hardware = dict(native=dict(cpu="Apple M5 Max", matrix_cores=True, macos="26.6.1"),
                    gpus=[dict(model="Apple M5 Max", cores="40", metal="metal4")],
                    machine="arm64", kernel="25.6.0")
    monkeypatch.setattr(compute, "hardware_identity", lambda *_: copy.deepcopy(hardware))
    assets = dict(engine_capabilities=["stable-compute-v1"], identity="model",
                  adapter=dict(sha256="adapter"), recipe=dict(steps=4),
                  binary=dict(sha256="binary"), library=dict(sha256="library"))
    request = dict(prompt="Picture 1 walks.", seed=7, reference_images=["/original.png"])
    prepared = [dict(index=1, width=1024, height=576, sha256="pixels", path="/prepared.png")]
    return hardware, assets, request, prepared


LOG = ("replayed research qmm plan: test\n"
       "[h3-plan] dit M=26033 N=5376 K=14336 route=u8-w8-cm1 split=2\n"
       "[h3-plan] vae M=303 N=1024 K=27648 route=bf16-n256 split=0\n")


def saved_plan(tmp_path, fixture):
    _, assets, request, prepared = fixture
    directory = tmp_path / "first"
    directory.mkdir()
    environment = {}
    plan, replay = compute.prepare(request, assets, prepared, directory, environment)
    assert replay is None
    assert environment["VPIPE_H3_COMPUTE_POLICY"] == "m5max-v1"
    return compute.complete(plan, None, LOG, directory)


def test_plan_is_self_contained_without_diagnostics(tmp_path, fixture):
    result = saved_plan(tmp_path, fixture)
    assert result["sha256"] == identity({k: v for k, v in result.items() if k != "sha256"})
    assert result["qmm"]["shapes"][-1]["i8_splits"] == 2
    assert "/original.png" not in json.dumps(result)
    assert "/prepared.png" not in json.dumps(result)
    assert json.loads((tmp_path / "first/compute-plan.json").read_text()) == result


def test_replay_allows_new_paths_but_checks_actual_dispatch(tmp_path, fixture):
    result = saved_plan(tmp_path, fixture)
    _, assets, request, prepared = fixture
    request["reference_images"] = ["/relocated.png"]
    prepared[0]["path"] = "/new/prepared.png"
    directory = tmp_path / "second"
    directory.mkdir()
    plan, replay = compute.prepare(request, assets, prepared, directory, {}, replay=result)
    assert compute.complete(plan, replay, LOG + LOG, directory) == result
    with pytest.raises(RuntimeError, match="Actual compute routes"):
        compute.complete(plan, replay, LOG.replace("split=2", "split=0"), directory)


@pytest.mark.parametrize("change", ["hardware", "model", "adapter", "recipe", "library", "prompt", "seed", "pixels"])
def test_replay_rejects_changed_execution_identity_before_native_launch(tmp_path, fixture, change):
    result = saved_plan(tmp_path, fixture)
    hardware, assets, request, prepared = fixture
    if change == "hardware": hardware["kernel"] = "changed"
    elif change == "model": assets["identity"] = "changed"
    elif change in ("adapter", "library"): assets[change]["sha256"] = "changed"
    elif change == "recipe": assets["recipe"]["steps"] = 8
    elif change == "pixels": prepared[0]["sha256"] = "changed"
    else: request[change] = "changed"
    directory = tmp_path / "second"
    directory.mkdir()
    with pytest.raises(ValueError, match="incompatible"):
        compute.prepare(request, assets, prepared, directory, {}, replay=result)
    assert not (directory / "qmm-plan.json").exists()


def test_cannot_replay_tampered_plan_or_skip_native_confirmation(tmp_path, fixture):
    result = saved_plan(tmp_path, fixture)
    _, assets, request, prepared = fixture
    result["qmm"]["shapes"][0]["i8_splits"] = 12
    with pytest.raises(ValueError, match="invalid or changed"):
        compute.prepare(request, assets, prepared, tmp_path, {}, replay=result)
    with pytest.raises(RuntimeError, match="did not confirm"):
        compute.complete({}, None, "baked AdaLN for 4 steps", tmp_path)


def test_policy_scope_does_not_guess_on_other_devices(tmp_path, fixture):
    hardware, assets, request, prepared = fixture
    hardware["gpus"][0]["cores"] = "32"
    with pytest.raises(RuntimeError, match="40-core M5 Max"):
        compute.prepare(request, assets, prepared, tmp_path, {})


def test_replay_rejects_wrapper_changes(tmp_path, fixture, monkeypatch):
    result = saved_plan(tmp_path, fixture)
    _, assets, request, prepared = fixture
    monkeypatch.setattr(compute, "source_identity", lambda: "changed")
    with pytest.raises(ValueError, match="incompatible"):
        compute.prepare(request, assets, prepared, tmp_path, {}, replay=result)
    assert not (tmp_path / "qmm-plan.json").exists()
