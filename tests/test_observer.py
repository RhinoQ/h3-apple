from h3_apple.runtime.observer import Observer


def test_disabled_diagnostics_never_build_arrays():
    observer = Observer(lambda event: None)
    def forbidden():
        raise AssertionError("Diagnostics prepared data while disabled")
    observer.capture("step-0", forbidden)
    assert observer.export_seconds == 0
