"""Environment provider interface (ADR 0020).

A provider takes the mission (its window: launch date and design life) and the environment
parameters (which hold the orbit and the attitude modes, ADR 0023) and returns the stage's
result, or the preview of one orbit while the parameters are edited.
Each result records the provider and version that produced it. The analytic provider lives in
``hestia_core.environment.analytic``; one based on Orekit (or another tool) would implement
this Protocol in ``hestia_adapters`` without touching the rest.

A provider declares the orbits it supports and rejects the others with ``InputRejectedError``
(stable problem codes such as ``eccentricity_out_of_range``): never a silently wrong result.
"""

from datetime import date
from typing import Protocol

from hestia_core.environment.parameters import EnvironmentParameters
from hestia_core.environment.result import EnvironmentResult, OrbitPreview
from hestia_core.mission import MissionArtifact


class EnvironmentProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str:
        """Bump whenever the same inputs would give a different result."""
        ...

    def compute(
        self, mission: MissionArtifact, parameters: EnvironmentParameters
    ) -> EnvironmentResult:
        """Result for a valid mission and valid parameters (both already validated).

        Raises ``hestia_core.forms.InputRejectedError`` for inputs outside its envelope.
        """
        ...

    def preview(
        self,
        mission: MissionArtifact,
        parameters: EnvironmentParameters,
        on: date | None,
        mode_id: str | None,
    ) -> OrbitPreview:
        """The nominal orbit on the date ``on`` (the launch date if None) in the attitude mode
        ``mode_id`` (the first valid one if None), without fluxes. Needs a valid mission window
        and a valid orbit; attitude modes with problems are left out.

        Raises ``hestia_core.forms.InputRejectedError`` for an orbit outside its envelope.
        """
        ...
