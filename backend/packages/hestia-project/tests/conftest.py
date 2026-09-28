import pytest

from hestia_project.catalog import TemplateId
from hestia_project.model import Project
from hestia_project.schematic import Blueprint, create_system


@pytest.fixture
def project() -> Project:
    return Project(id="p", name="test")


@pytest.fixture
def phase0(project: Project) -> Project:
    create_system(project, Blueprint(template=TemplateId.PHASE_0), name="F0")
    return project
