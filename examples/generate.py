"""Run with the installed product's fixed Conda Python; writes a unique result."""

from h3_apple import generate


if __name__ == "__main__":
    result = generate(
        "A paper boat drifts across a quiet pond. Soft water sounds and birdsong.",
        resolution="576p",
        duration=5,
        seed=123,
        on_progress=lambda event: print(event),
    )
    print(result.video_path)
    print(f"Complete audio/video in {result.elapsed_seconds:.1f} seconds")
