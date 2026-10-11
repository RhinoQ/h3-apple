"""Installed dependency checks must follow the release's declared requirements."""
import importlib.metadata

import pytest

from h3_apple.runtime.backend import check_dependencies


def test_installed_release_accepts_its_declared_dependencies():
    check_dependencies()


def test_old_torch_is_rejected(monkeypatch):
    actual_version = importlib.metadata.version
    monkeypatch.setattr(importlib.metadata, 'version',
                        lambda name: '2.11.0' if name == 'torch' else actual_version(name))
    with pytest.raises(RuntimeError, match='torch==2.14.1'):
        check_dependencies()


def test_missing_pin_is_rejected(monkeypatch):
    monkeypatch.setattr(importlib.metadata, 'requires', lambda _: [])
    with pytest.raises(RuntimeError, match='Missing mlx dependency pin'):
        check_dependencies()
