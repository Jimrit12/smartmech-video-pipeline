"""Typed FFmpeg filtergraph builder for video concatenation, tail trimming, and subtitles."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from smartmech.domain.strategy import TailTrimPolicy


class FiltergraphSpec(BaseModel):
    """Specification of inputs, trimming, audio, and subtitles for FFmpeg encoding."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    clip_paths: list[str] = Field(min_length=1)
    clip_durations: list[float] = Field(min_length=1)
    audio_path: str
    ass_path: str
    output_path: str
    tail_trim_policy: TailTrimPolicy = Field(default_factory=TailTrimPolicy)
    target_width: int = 1080
    target_height: int = 1920
    target_fps: int = 30
    target_lufs: float = -14.0
    measured_i: float | None = None
    measured_tp: float | None = None
    measured_lra: float | None = None
    measured_thresh: float | None = None
    target_offset: float | None = None

    def build_command(self) -> list[str]:
        """Build deterministic, single-encode FFmpeg command arguments."""
        cmd: list[str] = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]

        # Add video clip inputs
        for path in self.clip_paths:
            cmd.extend(["-i", path])

        # Add audio input (last input index)
        audio_idx = len(self.clip_paths)
        cmd.extend(["-i", self.audio_path])

        # Build filtergraph
        filter_chains: list[str] = []
        concat_inputs: list[str] = []

        # 1. Video tail trims
        for i, dur in enumerate(self.clip_durations):
            trimmed_dur = self.tail_trim_policy.calculate_trimmed_duration(dur)
            out_label = f"v{i}"
            filter_chains.append(
                f"[{i}:v]trim=start=0:end={trimmed_dur:.3f},setpts=PTS-STARTPTS[{out_label}]"
            )
            concat_inputs.append(f"[{out_label}]")

        # 2. Concat video clips
        concat_label = "vconcat"
        filter_chains.append(
            f"{''.join(concat_inputs)}concat=n={len(self.clip_paths)}:v=1:a=0[{concat_label}]"
        )

        # 3. ASS subtitles overlay with escaped path
        # In FFmpeg ass filter on Windows, colons and backslashes must be escaped
        escaped_ass = Path(self.ass_path).as_posix().replace(":", r"\:")
        sub_label = "vout"
        filter_chains.append(f"[{concat_label}]ass='{escaped_ass}'[{sub_label}]")

        # 4. Audio EBU R128 loudness normalization (two-pass if measured stats provided)
        audio_label = "aout"
        if self.measured_i is not None and self.measured_tp is not None:
            lra = self.measured_lra if self.measured_lra is not None else 7.0
            thresh = self.measured_thresh if self.measured_thresh is not None else -24.0
            offset = self.target_offset if self.target_offset is not None else 0.0
            loudnorm_filter = (
                f"loudnorm=I={self.target_lufs:.1f}:LRA=7:tp=-1.5:"
                f"measured_I={self.measured_i:.2f}:measured_TP={self.measured_tp:.2f}:"
                f"measured_LRA={lra:.2f}:measured_thresh={thresh:.2f}:"
                f"offset={offset:.2f}:linear=true"
            )
        else:
            loudnorm_filter = f"loudnorm=I={self.target_lufs:.1f}:LRA=7:tp=-1.5"
        filter_chains.append(f"[{audio_idx}:a]{loudnorm_filter}[{audio_label}]")

        filtergraph = "; ".join(filter_chains)

        cmd.extend(
            [
                "-filter_complex",
                filtergraph,
                "-map",
                f"[{sub_label}]",
                "-map",
                f"[{audio_label}]",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(self.target_fps),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                self.output_path,
            ]
        )
        return cmd
