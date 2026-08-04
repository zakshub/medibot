"""Local vertical MP4 rendering and publishability gates."""

import textwrap
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

from medibot.generation import ScriptPackage


@dataclass(frozen=True, slots=True)
class VideoRenderResult:
    path: Path
    sha256: str
    size_bytes: int
    duration_seconds: float
    width: int
    height: int
    fps: int
    has_audio: bool
    publishable: bool
    blocking_reasons: tuple[str, ...]


class LocalVerticalVideoRenderer:
    def __init__(self, *, width: int = 360, height: int = 640, fps: int = 10) -> None:
        if width < 180 or height < 320 or width % 2 or height % 2:
            raise ValueError("video dimensions must be even and at least 180x320")
        if not 1 <= fps <= 60:
            raise ValueError("fps must be between 1 and 60")
        self.width = width
        self.height = height
        self.fps = fps

    @staticmethod
    def _font(size: int) -> ImageFont.ImageFont:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

    def _frame(self, package: ScriptPackage, scene: str, index: int, total: int) -> bytes:
        image = Image.new("RGB", (self.width, self.height), "#071f1d")
        draw = ImageDraw.Draw(image)
        margin = max(18, self.width // 16)
        accent = "#e6ba50"
        panel = "#123532"

        draw.rounded_rectangle(
            (margin, margin, self.width - margin, self.height - margin),
            radius=18,
            fill=panel,
            outline=accent,
            width=3,
        )
        draw.text(
            (margin * 2, margin * 2),
            f"MEDICAL VIDEO  {index:02d}/{total:02d}",
            fill=accent,
            font=self._font(max(13, self.width // 24)),
        )
        title_lines = textwrap.wrap(package.title, width=max(16, self.width // 18))
        draw.multiline_text(
            (margin * 2, margin * 4),
            "\n".join(title_lines),
            fill="#f7f0dc",
            font=self._font(max(22, self.width // 13)),
            spacing=7,
        )
        scene_lines = textwrap.wrap(scene, width=max(18, self.width // 15))
        draw.multiline_text(
            (margin * 2, self.height // 3),
            "\n".join(scene_lines),
            fill="#d8e6df",
            font=self._font(max(19, self.width // 16)),
            spacing=9,
        )
        progress_width = self.width - margin * 4
        draw.rounded_rectangle(
            (
                margin * 2,
                self.height - margin * 3,
                margin * 2 + progress_width,
                self.height - margin * 2.5,
            ),
            radius=4,
            fill="#31504c",
        )
        draw.rounded_rectangle(
            (
                margin * 2,
                self.height - margin * 3,
                margin * 2 + int(progress_width * index / total),
                self.height - margin * 2.5,
            ),
            radius=4,
            fill=accent,
        )
        return image.tobytes()

    def render(
        self,
        package: ScriptPackage,
        *,
        duration_seconds: float,
        output_path: Path,
    ) -> VideoRenderResult:
        if not 1 <= duration_seconds <= 300:
            raise ValueError("duration must be between 1 and 300 seconds")
        if output_path.suffix.casefold() != ".mp4":
            raise ValueError("local renderer output must be an MP4 file")
        if not package.scenes:
            raise ValueError("at least one scene is required")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        writer = imageio_ffmpeg.write_frames(
            str(output_path),
            (self.width, self.height),
            fps=self.fps,
            codec="libx264",
            pix_fmt_in="rgb24",
            output_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        )
        writer.send(None)
        total_frames = max(len(package.scenes), round(duration_seconds * self.fps))
        try:
            for frame_number in range(total_frames):
                scene_index = min(
                    len(package.scenes) - 1,
                    frame_number * len(package.scenes) // total_frames,
                )
                writer.send(
                    self._frame(
                        package,
                        package.scenes[scene_index],
                        scene_index + 1,
                        len(package.scenes),
                    )
                )
        finally:
            writer.close()

        payload = output_path.read_bytes()
        if len(payload) < 1_024 or b"ftyp" not in payload[:64]:
            raise RuntimeError("renderer did not produce a valid MP4 container")
        return VideoRenderResult(
            path=output_path,
            sha256=sha256(payload).hexdigest(),
            size_bytes=len(payload),
            duration_seconds=duration_seconds,
            width=self.width,
            height=self.height,
            fps=self.fps,
            has_audio=False,
            publishable=False,
            blocking_reasons=("voice_track_missing", "operator_publish_approval_missing"),
        )


def require_publishable(result: VideoRenderResult) -> None:
    if not result.publishable or result.blocking_reasons:
        reasons = ",".join(result.blocking_reasons) or "render_not_publishable"
        raise ValueError(f"video is not publishable: {reasons}")

