# ADR-0012: Deferral and Rejection of TAIL_HANDOFF Chaining Strategy in Milestone M2

- **Status**: Accepted
- **Date**: 2026-10-22
- **Author**: Jimrit

## Context
Video generation across multiple keyframe transitions can follow several chaining strategies:
1. `ANCHOR_PARALLEL`: Clip $i$ starts from Keyframe $i$ and generates concurrently in parallel against fixed site keyframe anchors.
2. `FIRST_LAST`: Clip $i$ starts from Keyframe $i$ and constrains its ending to Keyframe $i+1$, subject to vendor capability negotiation (`supports_last_frame`).
3. `TAIL_HANDOFF`: Sequential generation where the final frame of Clip $i$ is extracted and dynamically fed as the starting frame of Clip $i+1$.

In Milestone M2 (Walking Skeleton), deterministic content-addressed caching, parallel execution, and strict per-step DBOS durability require that all transition inputs are known prior to clip generation. Under `TAIL_HANDOFF`, clip generation is strictly sequential, preventing parallel fan-out and introducing cross-run drift if clip rendering produces minor frame variations.

## Decision
For Milestones M0–M2, `TAIL_HANDOFF` is explicitly deferred and rejected at configuration time:
- Configuring `PipelineRunner` with `ChainStrategy.TAIL_HANDOFF` raises a descriptive `ValueError` explaining that `TAIL_HANDOFF` is deferred and directing callers to this ADR.
- The pipeline defaults to `ANCHOR_PARALLEL` and fully supports `FIRST_LAST` through adapter capability negotiation (`supports_last_frame`).
- `TAIL_HANDOFF` implementation will be considered in future milestones (M3+) when sequential clip-tail extraction and dynamic pipeline step dependencies are prioritized.

## Consequences
- Prevents runtime misconfiguration and undefined behavior when sequential handoffs are requested without requisite frame extraction infrastructure.
- Preserves full parallelization and deterministic content-addressed artifact hashing in M2.
