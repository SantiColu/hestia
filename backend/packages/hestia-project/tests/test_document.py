import pytest

from hestia_project.catalog import StageType, TemplateId
from hestia_project.document import ProjectDocument
from hestia_project.errors import (
    InvalidOperationError,
    JustificationRequiredError,
    NothingToRedoError,
    NothingToUndoError,
)
from hestia_project.history import ActorKind, Author, Operation
from hestia_project.schematic import Blueprint, create_system, delete_system, rename_system

HUMAN = Author(kind=ActorKind.HUMAN, name="ana")
AGENT = Author(kind=ActorKind.AGENT, name="stefan")


def _with_phase0() -> ProjectDocument:
    doc = ProjectDocument.new()
    doc.apply(
        Operation.CREATE_SYSTEM,
        HUMAN,
        "start",
        lambda p: create_system(p, Blueprint(template=TemplateId.PHASE_0)),
    )
    return doc


def test_new_document_is_clean() -> None:
    doc = ProjectDocument.new()
    assert doc.project.name == "Sin título"
    state = doc.state()
    assert not state.dirty and not state.can_undo and not state.can_redo
    assert state.path is None


def test_apply_records_author_and_justification() -> None:
    doc = _with_phase0()
    change = doc.changes()[0]
    assert change.author == HUMAN
    assert change.justification == "start"
    assert change.operation is Operation.CREATE_SYSTEM
    assert change.seq == 1
    assert doc.dirty
    assert doc.state().undo_summary == change.summary


def test_failed_operation_changes_nothing() -> None:
    doc = _with_phase0()
    before = doc.project.model_copy(deep=True)
    with pytest.raises(InvalidOperationError):
        doc.apply(
            Operation.RENAME_SYSTEM,
            HUMAN,
            "",
            lambda p: rename_system(p, p.systems[0].id, " "),
        )
    assert doc.project == before
    assert len(doc.history) == 1


def test_agents_justify_destructive_operations() -> None:
    doc = _with_phase0()
    with pytest.raises(JustificationRequiredError):
        doc.apply(Operation.DELETE_SYSTEM, AGENT, "  ", lambda p: delete_system(p, p.systems[0].id))
    assert len(doc.project.systems) == 1


def test_humans_never_need_a_justification() -> None:
    doc = _with_phase0()
    doc.apply(Operation.DELETE_SYSTEM, HUMAN, "", lambda p: delete_system(p, p.systems[0].id))
    assert doc.project.systems == []
    assert doc.changes()[-1].justification == ""


def test_undo_redo_roundtrip() -> None:
    doc = _with_phase0()
    after_create = doc.project.model_copy(deep=True)
    doc.apply(
        Operation.RENAME_SYSTEM,
        HUMAN,
        "",
        lambda p: rename_system(p, p.systems[0].id, "base"),
    )
    renamed = doc.project.model_copy(deep=True)

    undo = doc.undo(AGENT, "revert rename")
    assert doc.project == after_create
    assert undo.operation is Operation.UNDO
    assert undo.author == AGENT
    assert undo.reverts == doc.changes()[1].id
    assert doc.state().can_redo

    doc.undo(HUMAN)
    assert doc.project.systems == []

    doc.redo(HUMAN)
    doc.redo(HUMAN)
    assert doc.project == renamed
    assert not doc.state().can_redo
    with pytest.raises(NothingToRedoError):
        doc.redo(HUMAN)
    # The history keeps every entry, undo and redo included.
    assert [c.operation for c in doc.changes()] == [
        Operation.CREATE_SYSTEM,
        Operation.RENAME_SYSTEM,
        Operation.UNDO,
        Operation.UNDO,
        Operation.REDO,
        Operation.REDO,
    ]


def test_new_change_clears_redo() -> None:
    doc = _with_phase0()
    doc.undo(HUMAN)
    assert doc.state().can_redo
    doc.apply(
        Operation.CREATE_SYSTEM,
        HUMAN,
        "",
        lambda p: create_system(p, Blueprint(stage=StageType.MISSION)),
    )
    assert not doc.state().can_redo


def test_nothing_to_undo() -> None:
    with pytest.raises(NothingToUndoError):
        ProjectDocument.new().undo(HUMAN)


def test_view_is_a_copy() -> None:
    doc = _with_phase0()
    view = doc.view()
    view.project.systems.clear()
    assert len(doc.project.systems) == 1
