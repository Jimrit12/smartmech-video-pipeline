"""Tests for Quality Control (QC) gate evaluations and status aggregation."""

from smartmech.domain.qc import QCGateStatus, QCMetrics, QCReport, VLMCritique


def test_qc_report_evaluation_pass() -> None:
    metrics = QCMetrics(
        width=1080,
        height=1920,
        fps=30.0,
        duration_seconds=35.0,
        loudness_lufs=-14.0,
        black_frame_count=0,
        frozen_frame_count=0,
        is_portrait=True,
    )
    report = QCReport.evaluate(metrics)
    assert report.overall_status == QCGateStatus.PASS
    assert len(report.gates) >= 5
    for gate in report.gates:
        assert gate.status == QCGateStatus.PASS


def test_qc_report_fails_on_landscape_orientation() -> None:
    metrics = QCMetrics(
        width=1920,
        height=1080,
        fps=30.0,
        duration_seconds=35.0,
        loudness_lufs=-14.0,
        black_frame_count=0,
        frozen_frame_count=0,
        is_portrait=False,
    )
    report = QCReport.evaluate(metrics)
    assert report.overall_status == QCGateStatus.FAIL


def test_qc_report_warns_on_marginal_loudness() -> None:
    metrics = QCMetrics(
        width=1080,
        height=1920,
        fps=30.0,
        duration_seconds=35.0,
        loudness_lufs=-16.5,  # Within WARN window (-17 to -11)
        black_frame_count=0,
        frozen_frame_count=0,
        is_portrait=True,
    )
    report = QCReport.evaluate(metrics)
    assert report.overall_status == QCGateStatus.WARN


def test_qc_report_fails_on_extreme_loudness() -> None:
    metrics = QCMetrics(
        width=1080,
        height=1920,
        fps=30.0,
        duration_seconds=35.0,
        loudness_lufs=-22.0,  # Below -17.0
        black_frame_count=0,
        frozen_frame_count=0,
        is_portrait=True,
    )
    report = QCReport.evaluate(metrics)
    assert report.overall_status == QCGateStatus.FAIL


def test_qc_report_fails_on_black_or_frozen_frames() -> None:
    metrics_black = QCMetrics(
        width=1080,
        height=1920,
        fps=30.0,
        duration_seconds=35.0,
        loudness_lufs=-14.0,
        black_frame_count=5,
        frozen_frame_count=0,
        is_portrait=True,
    )
    assert QCReport.evaluate(metrics_black).overall_status == QCGateStatus.FAIL

    metrics_frozen = QCMetrics(
        width=1080,
        height=1920,
        fps=30.0,
        duration_seconds=35.0,
        loudness_lufs=-14.0,
        black_frame_count=0,
        frozen_frame_count=3,
        is_portrait=True,
    )
    assert QCReport.evaluate(metrics_frozen).overall_status == QCGateStatus.FAIL


def test_qc_report_fails_on_low_fps_or_bad_duration() -> None:
    metrics_fps = QCMetrics(
        width=1080,
        height=1920,
        fps=15.0,  # Below 24
        duration_seconds=35.0,
        loudness_lufs=-14.0,
        black_frame_count=0,
        frozen_frame_count=0,
        is_portrait=True,
    )
    assert QCReport.evaluate(metrics_fps).overall_status == QCGateStatus.FAIL

    metrics_duration = QCMetrics(
        width=1080,
        height=1920,
        fps=30.0,
        duration_seconds=20.0,  # Outside 30-40s
        loudness_lufs=-14.0,
        black_frame_count=0,
        frozen_frame_count=0,
        is_portrait=True,
    )
    assert QCReport.evaluate(metrics_duration).overall_status == QCGateStatus.FAIL


def test_qc_vlm_critique_is_advisory() -> None:
    metrics = QCMetrics(
        width=1080,
        height=1920,
        fps=30.0,
        duration_seconds=35.0,
        loudness_lufs=-14.0,
        black_frame_count=0,
        frozen_frame_count=0,
        is_portrait=True,
    )
    critique = VLMCritique(
        photorealism_score=4.0,
        temporal_consistency_score=5.0,
        architectural_fidelity_score=5.0,
        advisory_notes="Lighting could be improved.",
    )
    report = QCReport.evaluate(metrics, vlm_critique=critique)
    assert report.overall_status == QCGateStatus.PASS
    assert report.vlm_critique is not None
