import pytest

from app.content import ContentRepository
from app.models import Lesson
from app.quiz import QuizSession


@pytest.fixture(scope="module")
def lesson():
    return ContentRepository().get("charge")


def test_session_starts_at_first_question(lesson):
    session = QuizSession(lesson, shuffle=False)
    assert session.total == 5
    assert session.position == 0
    assert session.number == 1
    assert session.current.id == "charge-q1"
    assert not session.answered
    assert session.correct_count == 0
    assert not session.finished


def test_full_quiz_flow(lesson):
    session = QuizSession(lesson, shuffle=False)

    assert session.submit(0) is True  # charge-q1: одноимённые
    assert session.answered
    assert session.correct_count == 1
    assert session.percent == 20
    assert session.advance() is True

    assert session.submit("2,0") is True  # charge-q2: 2 электрона
    assert session.advance() is True

    assert session.submit(1) is False  # charge-q3: неверный вариант
    assert session.correct_count == 2
    assert session.advance() is True

    assert session.submit(0) is True  # charge-q4: −3q
    assert session.advance() is True

    assert session.submit(5) is True  # charge-q5: 5 электронов
    assert session.advance() is False
    assert session.finished

    summary = session.summary()
    assert summary.lesson_id == "charge"
    assert summary.total == 5
    assert summary.correct == 4
    assert summary.percent == 80
    assert len(summary.wrongs) == 1
    wrong = summary.wrongs[0]
    assert wrong.question.id == "charge-q3"
    assert wrong.correct is False
    assert wrong.given_text


def test_guards_against_invalid_calls(lesson):
    session = QuizSession(lesson, shuffle=False)
    with pytest.raises(RuntimeError):
        session.advance()
    with pytest.raises(RuntimeError):
        session.summary()
    session.submit(0)
    with pytest.raises(RuntimeError):
        session.submit(0)


def test_wrong_numeric_answer(lesson):
    session = QuizSession(lesson, shuffle=False)
    session.submit(0)
    session.advance()
    assert session.submit("3") is False
    assert session.correct_count == 1


def test_empty_lesson_cannot_start():
    empty = Lesson("empty", "Пусто", "", 5, (), (), (), ())
    with pytest.raises(ValueError):
        QuizSession(empty, shuffle=False)


def test_shuffle_is_deterministic(lesson):
    first = QuizSession(lesson, shuffle=True, seed=42)
    second = QuizSession(lesson, shuffle=True, seed=42)
    assert [q.id for q in first.questions] == [q.id for q in second.questions]
    assert {q.id for q in first.questions} == {q.id for q in lesson.questions}


def test_choice_given_text_is_option_text(lesson):
    session = QuizSession(lesson, shuffle=False)
    session.submit(0)
    assert session.results[0].given_text == "Одноимённые"
