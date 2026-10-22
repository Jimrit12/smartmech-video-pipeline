"""Quality Control (QC) gates, metrics, and report models."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class QCGateStatus(StrEnum):
    """Status of an individual QC gate or overall QC report."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class QCMetrics(BaseModel):
    """Computed technical video and audio metrics."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    width: int = Field(ge=1)
    height: int = Field(ge=1)
    fps: float = Field(ge=1.0)
    duration_seconds: float = Field(ge=0.0)
    loudness_lufs: float
    av_duration_delta_seconds: float = Field(default=0.0, ge=0.0)
    av_sync_offset_ms: float = 0.0
    black_frame_count: int = 0
    frozen_frame_count: int = 0
    duplicate_frame_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    is_portrait: bool = True


class VLMCritique(BaseModel):
    """Advisory Vision-Language Model critique (never gates alone)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    photorealism_score: float = Field(ge=0.0, le=10.0)
    temporal_consistency_score: float = Field(ge=0.0, le=10.0)
    architectural_fidelity_score: float = Field(ge=0.0, le=10.0)
    advisory_notes: str = ""


class GateEvaluation(BaseModel):
    """Evaluation result of a single quality gate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    status: QCGateStatus
    detail: str = Field(min_length=1)


class QCReport(BaseModel):
    """Aggregate quality evaluation report."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    overall_status: QCGateStatus
    gates: list[GateEvaluation]
    metrics: QCMetrics
    vlm_critique: VLMCritique | None = None

    @classmethod
    def evaluate(cls, metrics: QCMetrics, vlm_critique: VLMCritique | None = None) -> "QCReport":
        gates: list[GateEvaluation] = []
        overall = QCGateStatus.PASS

        # 1. Resolution: 1080x1920
        if metrics.width == 1080 and metrics.height == 1920:
            gates.append(
                GateEvaluation(
                    name="Resolution", status=QCGateStatus.PASS, detail="1080x1920 portrait"
                )
            )
        else:
            gates.append(
                GateEvaluation(
                    name="Resolution",
                    status=QCGateStatus.FAIL,
                    detail=f"Expected 1080x1920, got {metrics.width}x{metrics.height}",
                )
            )
            overall = QCGateStatus.FAIL

        # 2. Duration: 30-40 s
        if 30.0 <= metrics.duration_seconds <= 40.0:
            gates.append(
                GateEvaluation(
                    name="Duration",
                    status=QCGateStatus.PASS,
                    detail=f"{metrics.duration_seconds:.2f} s within [30.0, 40.0] s",
                )
            )
        else:
            gates.append(
                GateEvaluation(
                    name="Duration",
                    status=QCGateStatus.FAIL,
                    detail=f"{metrics.duration_seconds:.2f} s outside [30.0, 40.0] s range",
                )
            )
            overall = QCGateStatus.FAIL

        # 3. FPS: >= 24
        if metrics.fps >= 23.97:
            gates.append(
                GateEvaluation(
                    name="FPS", status=QCGateStatus.PASS, detail=f"{metrics.fps:.2f} fps >= 24"
                )
            )
        else:
            gates.append(
                GateEvaluation(
                    name="FPS", status=QCGateStatus.FAIL, detail=f"{metrics.fps:.2f} fps below 24"
                )
            )
            overall = QCGateStatus.FAIL

        # 4. Loudness: -14 LUFS (+/- 1.5 LUFS)
        if -15.5 <= metrics.loudness_lufs <= -12.5:
            gates.append(
                GateEvaluation(
                    name="Loudness",
                    status=QCGateStatus.PASS,
                    detail=f"{metrics.loudness_lufs:.1f} LUFS within target (-14 ± 1.5)",
                )
            )
        elif -17.0 <= metrics.loudness_lufs <= -11.0:
            gates.append(
                GateEvaluation(
                    name="Loudness",
                    status=QCGateStatus.WARN,
                    detail=f"{metrics.loudness_lufs:.1f} LUFS slightly off target",
                )
            )
            if overall != QCGateStatus.FAIL:
                overall = QCGateStatus.WARN
        else:
            gates.append(
                GateEvaluation(
                    name="Loudness",
                    status=QCGateStatus.FAIL,
                    detail=f"{metrics.loudness_lufs:.1f} LUFS outside acceptable tolerance",
                )
            )
            overall = QCGateStatus.FAIL

        # 5. Black frames: 0
        if metrics.black_frame_count == 0:
            gates.append(
                GateEvaluation(
                    name="BlackFrames", status=QCGateStatus.PASS, detail="Zero black frames"
                )
            )
        else:
            gates.append(
                GateEvaluation(
                    name="BlackFrames",
                    status=QCGateStatus.FAIL,
                    detail=f"{metrics.black_frame_count} black frames detected",
                )
            )
            overall = QCGateStatus.FAIL

        # 6. Frozen frames: 0
        if metrics.frozen_frame_count == 0:
            gates.append(
                GateEvaluation(
                    name="FrozenFrames", status=QCGateStatus.PASS, detail="Zero frozen frames"
                )
            )
        else:
            gates.append(
                GateEvaluation(
                    name="FrozenFrames",
                    status=QCGateStatus.FAIL,
                    detail=f"{metrics.frozen_frame_count} frozen frames detected",
                )
            )
            overall = QCGateStatus.FAIL

        # 7. Orientation
        if metrics.is_portrait:
            gates.append(
                GateEvaluation(
                    name="Orientation", status=QCGateStatus.PASS, detail="Portrait orientation 9:16"
                )
            )
        else:
            gates.append(
                GateEvaluation(
                    name="Orientation",
                    status=QCGateStatus.FAIL,
                    detail="Landscape orientation inside portrait container",
                )
            )
            overall = QCGateStatus.FAIL

        # 8. Audio/Video Duration Delta
        if metrics.av_duration_delta_seconds <= 1.0:
            gates.append(
                GateEvaluation(
                    name="AudioVideoDelta",
                    status=QCGateStatus.PASS,
                    detail=f"{metrics.av_duration_delta_seconds:.3f} s delta <= 1.0 s",
                )
            )
        else:
            gates.append(
                GateEvaluation(
                    name="AudioVideoDelta",
                    status=QCGateStatus.FAIL,
                    detail=f"{metrics.av_duration_delta_seconds:.3f} s delta exceeds 1.0 s threshold",
                )
            )
            overall = QCGateStatus.FAIL

        return cls(
            overall_status=overall,
            gates=gates,
            metrics=metrics,
            vlm_critique=vlm_critique,
        )
