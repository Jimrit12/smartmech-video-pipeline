"""Fake planner adapter generating valid deterministic construction timelapse plans."""

from smartmech.domain.adapter_identity import AdapterIdentity
from smartmech.domain.capabilities import AdapterCapabilities
from smartmech.domain.concept import (
    Concept,
    Keyframe,
    Plan,
    Script,
    ShotList,
    SiteBible,
    Transition,
)
from smartmech.ports.planner import PlannerPort


class FakePlannerAdapter(PlannerPort):
    """Generates synthetic, deterministic plans satisfying all domain invariants."""

    def __init__(
        self,
        capabilities: AdapterCapabilities | None = None,
        identity: AdapterIdentity | None = None,
    ) -> None:
        self._capabilities = capabilities or AdapterCapabilities(
            aspect_ratios=["9:16"],
            min_duration_seconds=30.0,
            max_duration_seconds=40.0,
            supports_first_frame=True,
            supports_last_frame=True,
            supports_native_audio=False,
        )
        self._identity = identity or AdapterIdentity(
            port="planner",
            adapter_name="fake_planner",
            model_or_version="stub_v1",
            cost_estimate_per_call=0.0,
        )

    @property
    def identity(self) -> AdapterIdentity:
        return self._identity

    @property
    def cost_estimate_per_call(self) -> float:
        return self._identity.cost_estimate_per_call

    @property
    def capabilities(self) -> AdapterCapabilities:
        return self._capabilities

    async def plan(self, prompt: str, seed: int) -> Plan:
        site_bible = SiteBible(
            location="Neo-Tokyo Industrial Bay",
            camera_rig="Heavy-duty locked crane rig",
            lens="24mm anamorphic lens",
            height="15 meters above ground level",
            weather="Clear skies transitioning to dusk",
            light_direction="Low golden hour sun from western azimuth",
            palette=["#3A3D40", "#D35400", "#BDC3C7"],
            materials=["Structural steel", "Reinforced concrete", "Double-glazed tempered glass"],
        )

        concept = Concept(
            title=f"The Rise of Sky-Tower {seed}",
            premise=f"Witness the hyper-realistic assembly of a futuristic 50-story modular skyscraper: {prompt}",
            building_type="Commercial High-Rise",
            target_duration_seconds=35.0,
        )

        continuity_suffix = (
            f"Location: {site_bible.location}. Camera Rig: {site_bible.camera_rig}. "
            f"Lens: {site_bible.lens}. Height: {site_bible.height}. Weather: {site_bible.weather}. "
            f"Light: {site_bible.light_direction}. Hyper-realistic construction site, clean composition, architectural render."
        )

        stages = [
            (
                "Foundation Excavation",
                0.0,
                "Deep subterranean excavation with heavy piling rigs and earthmovers.",
            ),
            (
                "Sub-structure Pouring",
                20.0,
                "Massive concrete raft slab poured with dense rebar grids.",
            ),
            (
                "Steel Superstructure Core",
                40.0,
                "Twin tower cranes lifting prefabricated steel I-beams into place.",
            ),
            (
                "Mid-level Floor Assemblies",
                60.0,
                "Floor decks cast in place while lower facade curtain walls attach.",
            ),
            (
                "Full Facade Enclosure",
                80.0,
                "Reflective curtain-wall glass panels installed up to the crown.",
            ),
            (
                "Completed Architectural Pinnacle",
                100.0,
                "Finished modular tower illuminated at twilight, crane dismantled.",
            ),
        ]

        keyframes = [
            Keyframe(
                index=i,
                title=title,
                prompt=f"{desc} {continuity_suffix}",
                construction_progress_pct=pct,
            )
            for i, (title, pct, desc) in enumerate(stages)
        ]

        # 5 transitions totaling exactly 35.0 seconds (7.0 s each)
        transitions = [
            Transition(
                index=i,
                from_keyframe_idx=i,
                to_keyframe_idx=i + 1,
                duration_seconds=7.0,
                motion_prompt=f"Smooth hyper-realistic construction timelapse from {stages[i][0]} to {stages[i + 1][0]}.",
            )
            for i in range(5)
        ]

        shot_list = ShotList(keyframes=keyframes, transitions=transitions)

        # Script <= 100 words
        script_text = (
            "From the foundation deep beneath the bedrock to the towering glass pinnacle in the evening sky, "
            "modern engineering turns vision into reality. Every steel beam, every poured slab, and every facade panel "
            "rises in perfect synchrony. Witness fifty stories assembled with millimeter precision in thirty seconds."
        )
        script = Script(text=script_text, pacing_words_per_minute=145)

        return Plan(
            concept=concept,
            site_bible=site_bible,
            shot_list=shot_list,
            script=script,
        )
