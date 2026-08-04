from pathlib import Path

import imageio_ffmpeg
import pytest

from medibot.generation import ScriptPackage
from medibot.media import LocalVerticalVideoRenderer, require_publishable


def package() -> ScriptPackage:
    return ScriptPackage(
        "sleep-001",
        "Sleep health basics",
        "Sleep health basics. Keep a consistent schedule.",
        ("Sleep supports health.", "Keep a consistent sleep schedule."),
        ("https://example.test/sleep",),
        ("approval-1",),
    )


def test_local_renderer_creates_real_vertical_mp4(tmp_path: Path) -> None:
    renderer = LocalVerticalVideoRenderer(width=180, height=320, fps=4)

    result = renderer.render(package(), duration_seconds=1, output_path=tmp_path / "preview.mp4")

    payload = result.path.read_bytes()
    reader = imageio_ffmpeg.read_frames(str(result.path), pix_fmt="rgb24")
    metadata = next(reader)
    reader.close()
    assert b"ftyp" in payload[:64]
    assert result.size_bytes > 1_024
    assert len(result.sha256) == 64
    assert (result.width, result.height, result.fps) == (180, 320, 4)
    assert metadata["size"] == (180, 320)
    assert result.has_audio is False
    assert result.publishable is False
    with pytest.raises(ValueError, match="voice_track_missing"):
        require_publishable(result)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"width": 179, "height": 320, "fps": 10},
        {"width": 180, "height": 319, "fps": 10},
        {"width": 181, "height": 320, "fps": 10},
        {"width": 180, "height": 320, "fps": 0},
    ],
)
def test_renderer_rejects_invalid_configuration(kwargs: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        LocalVerticalVideoRenderer(**kwargs)


@pytest.mark.parametrize(
    ("duration", "name", "message"),
    [
        (0, "preview.mp4", "duration"),
        (301, "preview.mp4", "duration"),
        (1, "preview.webm", "MP4"),
    ],
)
def test_renderer_rejects_invalid_job(
    tmp_path: Path, duration: int, name: str, message: str
) -> None:
    renderer = LocalVerticalVideoRenderer(width=180, height=320, fps=4)
    with pytest.raises(ValueError, match=message):
        renderer.render(package(), duration_seconds=duration, output_path=tmp_path / name)


def test_renderer_requires_scene(tmp_path: Path) -> None:
    empty = ScriptPackage("empty", "Title", "", (), (), ())
    renderer = LocalVerticalVideoRenderer(width=180, height=320, fps=4)
    with pytest.raises(ValueError, match="scene"):
        renderer.render(empty, duration_seconds=1, output_path=tmp_path / "empty.mp4")
