import math
from pathlib import Path

import pytest

from app import config, markup
from app.content import ContentRepository, load_formulas
from app.formulas import compute_scaled
from app.models import Example, Formula, Lesson, Question, Section, TopicMeta
from app.units import format_number, is_close, parse_number

EXPECTED_TOPIC_IDS = [
    "charge",
    "coulomb",
    "field",
    "potential",
    "capacitor",
    "current",
    "circuits",
    "power",
    "emf",
    "media",
    "exam",
]


@pytest.fixture(scope="module")
def repo():
    return ContentRepository()


def test_index_lists_all_topics(repo):
    assert [topic.id for topic in repo.topics] == EXPECTED_TOPIC_IDS
    assert len(repo.topics) == 11
    assert repo.total_questions == 57


def test_every_lesson_file_loads(repo):
    for topic in repo.topics:
        lesson = repo.get(topic.id)
        assert lesson.id == topic.id
        assert lesson.title
        assert lesson.subtitle
        assert len(lesson.questions) == topic.questions
        assert len(lesson.sections) >= 3
        assert len(lesson.examples) >= 2
        assert lesson.formulas


def test_question_ids_are_unique(repo):
    seen: set[str] = set()
    for topic in repo.topics:
        for question in repo.get(topic.id).questions:
            assert question.id not in seen, question.id
            seen.add(question.id)
    assert len(seen) == 57


def test_questions_are_well_formed(repo):
    for topic in repo.topics:
        for question in repo.get(topic.id).questions:
            assert question.id
            assert question.text
            assert question.explanation
            assert question.hint, f"у вопроса {question.id} нет подсказки"
            assert question.correct_text()
            if question.kind == "choice":
                assert 2 <= len(question.options) <= 6
                assert len(set(question.options)) == len(question.options)
                assert 0 <= question.answer < len(question.options)
                assert question.is_correct(question.answer)
                wrong = (question.answer + 1) % len(question.options)
                assert not question.is_correct(wrong)
            else:
                assert question.kind == "numeric"
                assert question.calc is not None
                assert question.unit
                assert 0.0001 <= question.tolerance <= 0.5
                assert question.is_correct(str(question.answer).replace(".", ","))
                assert not question.is_correct(str(question.answer * 2 + 1))


def test_numeric_answers_match_declared_formulas(repo):
    for topic in repo.topics:
        for question in repo.get(topic.id).questions:
            if question.kind != "numeric":
                continue
            computed = compute_scaled(question.calc)
            assert is_close(computed, question.answer, rel=1e-6, abs_epsilon=1e-12), (
                question.id,
                computed,
                question.answer,
            )


def test_examples_have_checked_arithmetic(repo):
    checked = 0
    for topic in repo.topics:
        for example in repo.get(topic.id).examples:
            assert example.calc is not None, example.title
            assert example.steps
            assert example.answer
            computed = compute_scaled(example.calc)
            declared = float(example.calc["value"])
            assert is_close(computed, declared, rel=1e-6, abs_epsilon=1e-12), (
                example.title,
                computed,
                declared,
            )
            checked += 1
    assert checked >= 20


def test_scales_are_powers_of_ten(repo):
    for topic in repo.topics:
        lesson = repo.get(topic.id)
        calcs = [example.calc for example in lesson.examples]
        calcs += [
            question.calc
            for question in lesson.questions
            if question.kind == "numeric"
        ]
        for calc in calcs:
            if "scale" not in calc:
                continue
            scale = float(calc["scale"])
            exponent = math.log10(scale)
            assert abs(exponent - round(exponent)) < 1e-9, calc
            assert 1 <= abs(round(exponent)) <= 12, calc


def test_explanations_are_not_short_placeholders(repo):
    for topic in repo.topics:
        for question in repo.get(topic.id).questions:
            assert len(question.explanation) >= 25, question.id
            assert len(question.hint) >= 10, question.id


def test_index_and_lesson_texts_have_valid_markup(repo):
    for topic in repo.topics:
        assert not markup.validate(topic.title)
        assert not markup.validate(topic.subtitle)
        lesson = repo.get(topic.id)
        assert not markup.validate(lesson.title)
        assert not markup.validate(lesson.subtitle)


def test_lesson_diagrams(repo):
    diagrams = {
        section.diagram
        for topic in repo.topics
        for section in repo.get(topic.id).sections
        if section.diagram
    }
    assert diagrams == {"series", "parallel", "emf"}


def test_formulas_page(repo):
    page = load_formulas()
    assert page.title
    assert len(page.groups) >= 5
    total = 0
    for group in page.groups:
        assert group.title
        assert group.items
        for formula in group.items:
            assert formula.name
            assert formula.expr
            assert not markup.validate(formula.name)
            assert not markup.validate(formula.expr)
            assert not markup.validate(formula.note)
            total += 1
    assert total >= 30


def test_audit_reports_no_errors(repo):
    assert repo.audit() == []


def test_cache_is_bounded(repo):
    for topic in repo.topics:
        repo.get(topic.id)
        assert repo.cache_size <= config.CONTENT_CACHE_LIMIT
    assert repo.cache_size == config.CONTENT_CACHE_LIMIT

    small = ContentRepository(cache_limit=1)
    for topic in small.topics:
        small.get(topic.id)
        assert small.cache_size == 1


def test_release_frees_cache(repo):
    repo.get("charge")
    repo.get("field")
    assert repo.cache_size == 2
    repo.release("charge")
    assert repo.cache_size == 1
    repo.release()
    assert repo.cache_size == 0


@pytest.mark.parametrize(
    "model", [TopicMeta, Formula, Section, Example, Question, Lesson]
)
def test_models_use_slots(model):
    assert "__slots__" in vars(model)
    assert "__dict__" not in vars(model)


def test_unknown_topic_raises(repo):
    from app.content import ContentError

    with pytest.raises(ContentError):
        repo.get("no-such-topic")
    with pytest.raises(ContentError):
        repo.topic("no-such-topic")


def test_numeric_question_accepts_different_input_forms(repo):
    question = next(
        item
        for item in repo.get("potential").questions
        if item.id == "potential-q3"
    )
    assert question.answer == pytest.approx(2e-4)
    for given in ("0,0002", "2e-4", "2·10^-4", "2*10^-4", "0.0002", "2·10⁻⁴"):
        assert question.is_correct(given), given
    for given in ("0,0003", "abc", "", None):
        assert not question.is_correct(given), given


def test_numeric_answers_are_typed_reproducibly(repo):
    for topic in repo.topics:
        for question in repo.get(topic.id).questions:
            if question.kind != "numeric":
                continue
            displayed = format_number(float(question.answer))
            parsed = parse_number(displayed)
            assert parsed is not None, (question.id, displayed)
            assert is_close(parsed, question.answer, rel=1e-3, abs_epsilon=1e-12), (
                question.id,
                displayed,
            )


def test_data_files_are_utf8_json():
    for path in sorted((config.DATA_DIR / "lessons").glob("*.json")):
        text = path.read_text(encoding="utf-8")
        assert '"id"' in text
        assert "\ufffd" not in text
    assert (config.DATA_DIR / "index.json").is_file()
    assert Path(config.DATA_DIR / "formulas.json").is_file()
