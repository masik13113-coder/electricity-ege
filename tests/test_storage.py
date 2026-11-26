from pathlib import Path

import pytest

from app.config import PASS_PERCENT
from app.storage import ProgressStore, StorageError

ARTIFACTS = Path(__file__).resolve().parents[1] / ".test-artifacts"


@pytest.fixture()
def memory_store():
    store = ProgressStore(":memory:")
    try:
        yield store
    finally:
        if not store.closed:
            store.close()


def test_new_store_is_empty(memory_store):
    assert memory_store.closed is False
    assert memory_store.best_percent("charge") == 0
    assert memory_store.progress_map() == {}
    assert memory_store.attempts_count() == 0
    assert memory_store.overall() == (0, 0, 0)
    assert memory_store.recent() == []


def test_save_attempt_and_best_score(memory_store):
    percent, record = memory_store.save_attempt("charge", 4, 5)
    assert (percent, record) == (80, True)
    assert memory_store.best_percent("charge") == 80
    assert memory_store.attempts_count("charge") == 1
    assert memory_store.overall() == (1, 1, 80)
    assert 80 >= PASS_PERCENT

    percent, record = memory_store.save_attempt("charge", 3, 5)
    assert (percent, record) == (60, False)
    assert memory_store.best_percent("charge") == 80
    assert memory_store.attempts_count("charge") == 2

    percent, record = memory_store.save_attempt("charge", 5, 5)
    assert (percent, record) == (100, True)
    assert memory_store.best_percent("charge") == 100
    assert memory_store.attempts_count("charge") == 3

    recent = memory_store.recent(2)
    assert len(recent) == 2
    assert recent[0]["percent"] == 100
    assert recent[1]["percent"] == 60
    assert set(recent[0]) == {
        "lesson_id",
        "correct",
        "total",
        "percent",
        "created_at",
    }


@pytest.mark.parametrize(
    "correct, total, expected",
    [
        (0, 5, 0),
        (1, 3, 33),
        (1, 2, 50),
        (2, 3, 67),
        (4, 5, 80),
        (5, 5, 100),
        (5, 8, 63),
    ],
)
def test_percent_rounding(correct, total, expected):
    store = ProgressStore(":memory:")
    try:
        percent, _ = store.save_attempt("x", correct, total)
        assert percent == expected
    finally:
        store.close()


def test_invalid_attempt_is_rejected(memory_store):
    with pytest.raises(ValueError):
        memory_store.save_attempt("charge", 1, 0)
    with pytest.raises(ValueError):
        memory_store.save_attempt("charge", -1, 5)
    with pytest.raises(ValueError):
        memory_store.save_attempt("charge", 6, 5)
    with pytest.raises(ValueError):
        memory_store.save_attempt("", 1, 5)


def test_reset_clears_everything(memory_store):
    memory_store.save_attempt("charge", 4, 5)
    memory_store.save_attempt("field", 5, 5)
    memory_store.reset()
    assert memory_store.progress_map() == {}
    assert memory_store.attempts_count() == 0
    assert memory_store.overall() == (0, 0, 0)


def test_overall_counts_completed_topics(memory_store):
    memory_store.save_attempt("charge", 4, 5)  # 80
    memory_store.save_attempt("emf", 2, 5)  # 40
    memory_store.save_attempt("field", 5, 5)  # 100
    completed, attempted, average = memory_store.overall()
    assert completed == 2
    assert attempted == 3
    assert average == 73


def test_store_closes_and_rejects_use(memory_store):
    memory_store.save_attempt("charge", 5, 5)
    memory_store.close()
    assert memory_store.closed
    with pytest.raises(StorageError):
        memory_store.best_percent("charge")
    with pytest.raises(StorageError):
        memory_store.progress_map()
    memory_store.close()  # повторное закрытие безопасно


def test_file_store_persists_between_sessions():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / "progress_persistence.sqlite3"
    for suffix in ("", "-wal", "-shm"):
        target = Path(str(path) + suffix)
        if target.exists():
            target.unlink()

    first = ProgressStore(path)
    first.save_attempt("circuits", 5, 6)
    first.save_attempt("circuits", 3, 6)
    first.close()

    second = ProgressStore(path)
    try:
        assert second.best_percent("circuits") == 83
        assert second.attempts_count("circuits") == 2
        assert second.recent(1)[0]["correct"] == 3
    finally:
        second.close()

    for suffix in ("", "-wal", "-shm"):
        target = Path(str(path) + suffix)
        if target.exists():
            target.unlink()
