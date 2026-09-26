import json

import pytest

from h3_apple import host


@pytest.mark.parametrize("chip,cores,accepted", [
    ("Apple M5 Max", "40", True),
    ("Apple M5 Max", "32", False),
    ("Apple M5 Pro", "20", False),
    ("Apple M4 Max", "40", False),
])
def test_preparation_preflight_matches_supported_compute_device(monkeypatch, chip, cores, accepted):
    info = dict(system="Darwin", machine="arm64", chip=chip, macos="26.6.1",
                memory_bytes=128 * 1024**3)
    monkeypatch.setattr(host, "command", lambda *_: json.dumps(
        {"SPDisplaysDataType": [{"sppci_cores": cores}]}))
    if accepted:
        host.check_machine(info)
    else:
        with pytest.raises(RuntimeError, match="40-core M5 Max"):
            host.check_machine(info)
