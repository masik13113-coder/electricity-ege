"""Экраны приложения.

Тяжёлое содержимое (теория, варианты ответов, разбор ошибок) создаётся
только при входе на экран и уничтожается при выходе — см. ``release()``.
Сами экраны-контейнеры живут всё время, поэтому переходы не создают мусор.
"""
from __future__ import annotations

from typing import Optional

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from ..content import ContentError, load_formulas
from ..models import Formula, Lesson, QuizSummary, TopicMeta
from ..quiz import QuizSession
from ..units import parse_number
from . import theme as T
from .widgets import (
    CircuitDiagram,
    LinearProgress,
    OptionCard,
    RoundedButton,
    RoundedCard,
    TextButton,
    TopicRow,
    WrapLabel,
)


# --------------------------------------------------------------------- helpers
def _fit_label(text: str = "", **kwargs) -> Label:
    """Однострочная метка с выравниванием по левому краю."""
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("valign", "middle")
    kwargs.setdefault("color", T.TEXT)
    kwargs.setdefault("size_hint_y", None)
    kwargs.setdefault("markup", True)
    label = Label(text=text, **kwargs)
    label.bind(width=lambda *_: setattr(label, "text_size", (max(1, label.width), None)))
    return label


def _auto(widget: BoxLayout) -> BoxLayout:
    widget.bind(minimum_height=widget.setter("height"))
    return widget


def _heading(text: str, size: float = T.H3, color=None) -> WrapLabel:
    return WrapLabel(
        text=text,
        font_size=size,
        bold=True,
        color=color or T.TEXT,
        markup=True,
    )


def _paragraph(text: str, *, size: float = T.BODY, color=None, markup: bool = True) -> WrapLabel:
    return WrapLabel(
        text=text,
        font_size=size,
        color=color or T.TEXT,
        markup=markup,
    )


def _spacer(height: float) -> Label:
    return Label(size_hint_y=None, height=dp(height), text="")


class BaseScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._built = False

    def on_pre_enter(self, *args):
        self.ensure_built()
        self.refresh()

    def ensure_built(self):
        if not self._built:
            self.build_ui()
            self._built = True

    def build_ui(self):
        raise NotImplementedError

    def refresh(self):
        pass

    def release(self):
        pass


# ------------------------------------------------------------------------ home
class HomeScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app, name="home")
        self._topics_grid: Optional[BoxLayout] = None
        self._topics_scroll: Optional[ScrollView] = None
        self._rows: list = []
        self._count: Optional[Label] = None
        self._bar: Optional[LinearProgress] = None
        self._hint: Optional[WrapLabel] = None

    # ------------------------------------------------------------------- build
    def build_ui(self):
        root = BoxLayout(
            orientation="vertical",
            padding=[T.PAGE_X, dp(10), T.PAGE_X, dp(8)],
            spacing=dp(10),
        )
        self.add_widget(root)

        header = BoxLayout(
            orientation="vertical", size_hint_y=None, height=dp(56), spacing=0
        )
        header.add_widget(
            _fit_label(
                "Электричество · ЕГЭ",
                font_size=T.H1,
                bold=True,
                height=dp(32),
            )
        )
        self._subtitle = _fit_label(
            "Курс с нуля: теория, примеры, тесты",
            font_size=T.SMALL,
            color=T.TEXT_MUTED,
            height=dp(20),
        )
        header.add_widget(self._subtitle)
        root.add_widget(header)

        root.add_widget(self._build_progress())
        root.add_widget(
            _fit_label(
                "ТЕМЫ КУРСА",
                font_size=T.TINY,
                color=T.TEXT_MUTED,
                bold=True,
                height=dp(16),
            )
        )
        root.add_widget(self._build_topics())
        root.add_widget(self._build_footer())

    def _build_progress(self) -> RoundedCard:
        card = _auto(RoundedCard(size_hint_y=None, spacing=dp(6)))
        top = BoxLayout(size_hint_y=None, height=dp(20))
        top.add_widget(
            _fit_label("Ваш прогресс", font_size=T.SMALL, bold=True, height=dp(20))
        )
        self._count = _fit_label(
            "", font_size=T.SMALL, color=T.TEXT_MUTED, halign="right", height=dp(20)
        )
        top.add_widget(self._count)
        card.add_widget(top)

        self._bar = LinearProgress(value=0.0)
        card.add_widget(self._bar)

        self._hint = WrapLabel(
            text="Пройдите первый тест, чтобы увидеть статистику.",
            font_size=T.TINY,
            color=T.TEXT_MUTED,
        )
        card.add_widget(self._hint)
        return card

    def _build_topics(self) -> ScrollView:
        scroll = ScrollView(
            size_hint_y=1,
            bar_width=dp(2),
            bar_color=T.PRIMARY,
            bar_inactive_color=T.BORDER,
            scroll_type=["bars", "content"],
        )
        self._topics_grid = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(8),
        )
        self._topics_grid.bind(minimum_height=self._topics_grid.setter("height"))
        for index, topic in enumerate(self.app.repo.topics, start=1):
            row = TopicRow(
                meta=topic,
                number=index,
                open_callback=self._open_topic,
            )
            self._rows.append(row)
            self._topics_grid.add_widget(row)
        scroll.add_widget(self._topics_grid)
        self._topics_scroll = scroll
        return scroll

    def _build_footer(self) -> BoxLayout:
        row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(46), spacing=dp(8)
        )
        formulas = RoundedButton(
            text="Шпаргалка формул",
            size_hint_x=1,
            height=dp(46),
            bg_color=T.PRIMARY_SOFT,
            text_color=T.PRIMARY,
            font_size=T.SMALL,
        )
        formulas.bind(on_release=lambda *_: self.app.show_formulas())
        row.add_widget(formulas)

        reset = RoundedButton(
            text="Сброс",
            size_hint_x=None,
            width=dp(84),
            height=dp(46),
            bg_color=T.TRANSPARENT,
            text_color=T.TEXT_MUTED,
            font_size=T.SMALL,
        )
        reset.bind(on_release=lambda *_: self._confirm_reset())
        row.add_widget(reset)
        return row

    # ----------------------------------------------------------------- refresh
    def refresh(self):
        if not self._built or self.app.repo is None:
            return
        topics = self.app.repo.topics
        if self._subtitle is not None:
            self._subtitle.text = (
                f"Курс с нуля · {len(topics)} тем · {self.app.repo.total_questions} вопросов"
            )
        store = self.app.get_store()
        if store is None:
            return
        progress = store.progress_map()
        completed, attempted, average = store.overall()
        total = len(topics)
        self._count.text = f"{completed} из {total}"
        self._bar.value = (completed / total) if total else 0.0
        if attempted:
            self._hint.text = (
                f"Пройдено тем: {completed}. Средний лучший результат: {average}%. "
                "Цель — 85% и выше."
            )
        else:
            self._hint.text = "Пройдите первый тест, чтобы увидеть статистику."

        for row in self._rows:
            row.best = progress.get(row.meta.id, 0)

    def _open_topic(self, lesson_id: str):
        self.app.open_lesson(lesson_id)

    # ------------------------------------------------------------------ reset
    def _confirm_reset(self):
        content = BoxLayout(
            orientation="vertical", padding=dp(14), spacing=dp(12)
        )
        content.add_widget(
            WrapLabel(
                text="Все результаты тестов будут удалены. Это действие нельзя отменить.",
                font_size=T.BODY,
            )
        )
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        cancel = RoundedButton(
            text="Отмена",
            bg_color=T.PRIMARY_SOFT,
            text_color=T.PRIMARY,
            font_size=T.SMALL,
            height=dp(44),
        )
        confirm = RoundedButton(
            text="Сбросить",
            bg_color=T.DANGER,
            font_size=T.SMALL,
            height=dp(44),
        )
        row.add_widget(cancel)
        row.add_widget(confirm)
        content.add_widget(row)
        popup = Popup(
            title="Сбросить прогресс?",
            content=content,
            size_hint=(0.9, None),
            height=dp(220),
        )
        cancel.bind(on_release=lambda *_: popup.dismiss())
        confirm.bind(on_release=lambda *_: self._do_reset(popup))
        popup.open()

    def _do_reset(self, popup: Popup):
        popup.dismiss()
        self.app.reset_progress()


# ---------------------------------------------------------------------- lesson
class LessonScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app, name="lesson")
        self.meta: Optional[TopicMeta] = None
        self._lesson: Optional[Lesson] = None
        self._grid: Optional[BoxLayout] = None
        self._scroll: Optional[ScrollView] = None
        self._title: Optional[Label] = None
        self._subtitle: Optional[Label] = None
        self._cta: Optional[RoundedButton] = None

    def build_ui(self):
        root = BoxLayout(orientation="vertical")
        self.add_widget(root)

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            spacing=dp(4),
            padding=[dp(2), 0, dp(2), 0],
        )
        back = TextButton(
            text="‹",
            size_hint=(None, None),
            width=dp(42),
            height=dp(42),
            font_size=sp(28),
            text_color=T.PRIMARY,
        )
        back.bind(on_release=lambda *_: self.app.back())
        header.add_widget(back)
        titles = BoxLayout(orientation="vertical", spacing=0)
        self._title = _fit_label("", font_size=T.H2, bold=True, height=dp(24))
        self._subtitle = _fit_label(
            "", font_size=T.TINY, color=T.TEXT_MUTED, height=dp(16)
        )
        titles.add_widget(self._title)
        titles.add_widget(self._subtitle)
        header.add_widget(titles)
        root.add_widget(header)

        self._scroll = ScrollView(
            bar_width=dp(2),
            bar_color=T.PRIMARY,
            bar_inactive_color=T.BORDER,
            scroll_type=["bars", "content"],
        )
        self._grid = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=T.CARD_SPACING,
            padding=[T.PAGE_X, dp(2), T.PAGE_X, dp(16)],
        )
        self._grid.bind(minimum_height=self._grid.setter("height"))
        self._scroll.add_widget(self._grid)
        root.add_widget(self._scroll)

        footer = BoxLayout(
            size_hint_y=None,
            height=dp(66),
            padding=[T.PAGE_X, dp(6), T.PAGE_X, dp(8)],
        )
        self._cta = RoundedButton(text="Пройти тест")
        self._cta.bind(on_release=lambda *_: self._start_quiz())
        footer.add_widget(self._cta)
        root.add_widget(footer)

    # -------------------------------------------------------------------- data
    def open(self, meta: TopicMeta):
        self.ensure_built()
        lesson = self.app.repo.get(meta.id)
        self.meta = meta
        self._lesson = lesson
        self._title.text = meta.title
        self._subtitle.text = (
            f"{meta.minutes} мин · {len(lesson.questions)} вопросов"
        )
        self._build_content(lesson)
        self._cta.text = f"Пройти тест · {len(lesson.questions)} вопросов"
        self._cta.disabled = not lesson.questions
        self._scroll.scroll_y = 1
        Clock.schedule_once(lambda *_: setattr(self._scroll, "scroll_y", 1), 0)

    def _build_content(self, lesson: Lesson):
        self._grid.clear_widgets()
        for section in lesson.sections:
            card = _auto(
                RoundedCard(size_hint_y=None, spacing=dp(6))
            )
            card.add_widget(_heading(section.heading))
            card.add_widget(_paragraph(section.body))
            if section.diagram:
                card.add_widget(CircuitDiagram(mode=section.diagram))
            self._grid.add_widget(card)

        if lesson.formulas:
            card = _auto(
                RoundedCard(size_hint_y=None, spacing=dp(10))
            )
            card.add_widget(_heading("Формулы темы", size=T.H3))
            for formula in lesson.formulas:
                card.add_widget(self._formula_row(formula))
            self._grid.add_widget(card)

        if lesson.examples:
            self._grid.add_widget(_heading("Разобранные примеры", size=T.H2))
            for example in lesson.examples:
                card = _auto(
                    RoundedCard(size_hint_y=None, spacing=dp(6))
                )
                card.add_widget(_heading(example.title, size=T.H3))
                card.add_widget(
                    WrapLabel(
                        text=f"[b]Дано.[/b] {example.given}",
                        font_size=T.SMALL,
                        color=T.TEXT,
                    )
                )
                for number, step in enumerate(example.steps, start=1):
                    card.add_widget(
                        WrapLabel(
                            text=f"[b]{number}.[/b] {step}",
                            font_size=T.SMALL,
                            color=T.TEXT,
                        )
                    )
                card.add_widget(
                    WrapLabel(
                        text=f"[b]Ответ.[/b] {example.answer}",
                        font_size=T.SMALL,
                        color=T.SUCCESS,
                    )
                )
                self._grid.add_widget(card)

    @staticmethod
    def _formula_row(formula: Formula) -> BoxLayout:
        row = _auto(BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(1)))
        row.add_widget(
            WrapLabel(
                text=formula.name,
                font_size=T.TINY,
                color=T.TEXT_MUTED,
                bold=True,
            )
        )
        row.add_widget(
            WrapLabel(
                text=formula.expr,
                font_size=T.FORMULA,
                color=T.PRIMARY,
                bold=True,
            )
        )
        if formula.note:
            row.add_widget(
                WrapLabel(
                    text=formula.note,
                    font_size=T.TINY,
                    color=T.TEXT_MUTED,
                )
            )
        return row

    def _start_quiz(self):
        if self.meta is not None:
            self.app.start_quiz(self.meta.id)

    # ----------------------------------------------------------------- release
    def release(self):
        meta = self.meta
        self.meta = None
        self._lesson = None
        if self._grid is not None:
            self._grid.clear_widgets()
        if meta is not None and self.app.repo is not None:
            self.app.repo.release(meta.id)


# ------------------------------------------------------------------------ quiz
class QuizScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app, name="quiz")
        self.meta: Optional[TopicMeta] = None
        self._lesson: Optional[Lesson] = None
        self._session: Optional[QuizSession] = None
        self._question_card: Optional[RoundedCard] = None
        self._answers: Optional[BoxLayout] = None
        self._feedback: Optional[BoxLayout] = None
        self._options: list[OptionCard] = []
        self._input: Optional[TextInput] = None
        self._action: Optional[RoundedButton] = None
        self._counter: Optional[Label] = None
        self._bar: Optional[LinearProgress] = None
        self._title: Optional[Label] = None
        self._answered = False
        self._hint_button: Optional[TextButton] = None
        self._hint_label: Optional[WrapLabel] = None
        self._scroll: Optional[ScrollView] = None
        self._content: Optional[BoxLayout] = None

    def build_ui(self):
        root = BoxLayout(orientation="vertical")
        self.add_widget(root)

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            spacing=dp(4),
            padding=[dp(2), 0, dp(2), 0],
        )
        back = TextButton(
            text="‹",
            size_hint=(None, None),
            width=dp(42),
            height=dp(42),
            font_size=sp(28),
            text_color=T.PRIMARY,
        )
        back.bind(on_release=lambda *_: self.app.back())
        header.add_widget(back)
        self._title = _fit_label("", font_size=T.H3, bold=True, height=dp(24))
        header.add_widget(self._title)
        self._counter = _fit_label(
            "",
            font_size=T.TINY,
            color=T.TEXT_MUTED,
            halign="right",
            size_hint=(None, 1),
            width=dp(96),
        )
        header.add_widget(self._counter)
        root.add_widget(header)

        self._bar = LinearProgress(value=0.0)
        root.add_widget(self._bar)

        scroll = ScrollView(
            bar_width=dp(2),
            bar_color=T.PRIMARY,
            bar_inactive_color=T.BORDER,
            scroll_type=["bars", "content"],
        )
        self._content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(10),
            padding=[T.PAGE_X, dp(8), T.PAGE_X, dp(14)],
        )
        self._content.bind(minimum_height=self._content.setter("height"))
        self._question_card = _auto(
            RoundedCard(size_hint_y=None, spacing=dp(6))
        )
        self._answers = _auto(
            BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        )
        self._feedback = _auto(
            BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        )
        self._content.add_widget(self._question_card)
        self._content.add_widget(self._answers)
        self._content.add_widget(self._feedback)
        scroll.add_widget(self._content)
        self._scroll = scroll
        root.add_widget(scroll)

        footer = BoxLayout(
            size_hint_y=None,
            height=dp(66),
            padding=[T.PAGE_X, dp(6), T.PAGE_X, dp(8)],
        )
        self._action = RoundedButton(text="Ответить")
        self._action.bind(on_release=lambda *_: self._on_action())
        footer.add_widget(self._action)
        root.add_widget(footer)

    # -------------------------------------------------------------------- start
    def start(self, meta: TopicMeta):
        self.ensure_built()
        lesson = self.app.repo.get(meta.id)
        self.meta = meta
        self._lesson = lesson
        self._session = QuizSession(lesson)
        self._title.text = meta.title
        self._render()

    def _render(self):
        session = self._session
        if session is None:
            return
        question = session.current
        self._answered = False
        self._options = []
        self._input = None
        self._hint_button = None
        self._hint_label = None
        self._question_card.clear_widgets()
        self._answers.clear_widgets()
        self._feedback.clear_widgets()
        self._counter.text = f"Вопрос {session.number}/{session.total}"
        self._bar.value = session.position / session.total

        self._question_card.add_widget(
            _fit_label(
                f"ВОПРОС {session.number}",
                font_size=T.TINY,
                color=T.PRIMARY,
                bold=True,
                height=dp(16),
            )
        )
        self._question_card.add_widget(
            WrapLabel(text=question.text, font_size=T.BODY, color=T.TEXT)
        )
        if question.hint:
            hint_button = TextButton(
                text="Подсказка",
                size_hint=(None, None),
                width=dp(110),
                height=dp(32),
                font_size=T.SMALL,
                text_color=T.PRIMARY,
            )
            hint_button.bind(on_release=lambda *_: self._toggle_hint())
            self._hint_button = hint_button
            self._question_card.add_widget(hint_button)

        if question.kind == "choice":
            for index, option in enumerate(question.options):
                card = OptionCard(
                    index=index,
                    option_text=f"{index + 1}. {option}",
                    pick_callback=self._choose,
                )
                self._options.append(card)
                self._answers.add_widget(card)
            self._action.text = "Выберите ответ"
            self._action.disabled = True
        else:
            self._build_numeric_input()
            self._action.text = "Ответить"
            self._action.disabled = False

        self._scroll.scroll_y = 1

    def _build_numeric_input(self):
        holder = RoundedCard(
            orientation="vertical",
            size_hint_y=None,
            height=dp(58),
            padding=[dp(2), dp(2), dp(2), dp(2)],
            bg_color=T.rgba("#F8FAFC"),
        )
        self._input = TextInput(
            multiline=False,
            font_size=sp(19),
            input_type="number",
            hint_text="Введите число",
            background_normal="",
            background_active="",
            background_color=(0, 0, 0, 0),
            foreground_color=T.TEXT,
            cursor_color=T.PRIMARY,
            hint_text_color=T.TEXT_MUTED,
            padding=[dp(12), dp(14), dp(12), dp(10)],
        )
        holder.add_widget(self._input)
        self._answers.add_widget(holder)
        self._answers.add_widget(
            WrapLabel(
                text="Можно вводить 0,6 или 6·10^-1 или 6e-1",
                font_size=T.TINY,
                color=T.TEXT_MUTED,
            )
        )

    # ------------------------------------------------------------------ actions
    def _choose(self, index: int):
        if self._answered or self._session is None:
            return
        correct = self._session.submit(index)
        self._after_submit(
            correct, self._session.current.given_text(index), chosen=index
        )

    def _on_action(self):
        if self._session is None:
            return
        if self._answered:
            self._next()
            return
        if self._session.current.kind == "numeric":
            self._submit_numeric()

    def _submit_numeric(self):
        if self._input is None or self._session is None:
            return
        raw = self._input.text
        if parse_number(raw) is None:
            self._show_input_error("Не могу распознать число. Примеры: 2,5; 0,0002; 2·10^-4.")
            return
        correct = self._session.submit(raw)
        self._after_submit(correct, raw, chosen=None)

    def _show_input_error(self, message: str):
        self._feedback.clear_widgets()
        card = _auto(
            RoundedCard(
                size_hint_y=None,
                bg_color=T.DANGER_BG,
                padding=T.CARD_PADDING,
            )
        )
        card.add_widget(WrapLabel(text=message, font_size=T.SMALL, color=T.DANGER))
        self._feedback.add_widget(card)

    def _after_submit(self, correct: bool, given: str, chosen: Optional[int] = None):
        session = self._session
        if session is None:
            return
        self._answered = True
        question = session.current
        self._counter.text = f"Вопрос {session.number}/{session.total}"
        self._bar.value = (session.position + 1) / session.total
        if question.kind == "choice":
            for index, card in enumerate(self._options):
                if index == question.answer:
                    card.mark("correct")
                elif chosen is not None and index == chosen:
                    card.mark("wrong")
                card.locked = True
        if self._input is not None:
            self._input.readonly = True
            self._input.foreground_color = T.TEXT_MUTED
        if self._hint_label is not None:
            self._question_card.remove_widget(self._hint_label)
            self._hint_label = None
        if self._hint_button is not None:
            self._question_card.remove_widget(self._hint_button)
            self._hint_button = None
        self._show_feedback(correct, given)
        self._action.text = "Результат" if session.is_last else "Далее"
        self._action.disabled = False
        Clock.schedule_once(lambda *_: setattr(self._scroll, "scroll_y", 0), 0.05)

    def _show_feedback(self, correct: bool, given: str):
        session = self._session
        if session is None:
            return
        question = session.current
        self._feedback.clear_widgets()
        card = _auto(
            RoundedCard(
                size_hint_y=None,
                bg_color=T.SUCCESS_BG if correct else T.DANGER_BG,
                padding=T.CARD_PADDING,
                spacing=dp(4),
            )
        )
        color = T.SUCCESS if correct else T.DANGER
        card.add_widget(
            WrapLabel(
                text="Верно!" if correct else "Есть ошибка",
                font_size=T.H3,
                bold=True,
                color=color,
            )
        )
        card.add_widget(
            WrapLabel(
                text=f"Правильный ответ: [b]{question.correct_text()}[/b]",
                font_size=T.SMALL,
                color=T.TEXT,
            )
        )
        if question.kind == "numeric":
            card.add_widget(
                WrapLabel(
                    text=f"Ваш ответ: {given}",
                    font_size=T.TINY,
                    color=T.TEXT_MUTED,
                    markup=False,
                )
            )
        card.add_widget(
            WrapLabel(
                text=question.explanation,
                font_size=T.SMALL,
                color=T.TEXT,
            )
        )
        self._feedback.add_widget(card)

    def _toggle_hint(self):
        session = self._session
        if session is None:
            return
        if self._hint_label is not None:
            self._question_card.remove_widget(self._hint_label)
            self._hint_label = None
            if self._hint_button is not None:
                self._hint_button.text = "Подсказка"
            return
        label = WrapLabel(
            text=f"[b]Подсказка.[/b] {session.current.hint}",
            font_size=T.SMALL,
            color=T.TEXT_MUTED,
        )
        self._hint_label = label
        self._question_card.add_widget(label)
        if self._hint_button is not None:
            self._hint_button.text = "Скрыть подсказку"

    def _next(self):
        session = self._session
        if session is None or not self._answered:
            return
        if session.is_last:
            summary = session.summary()
            self.app.finish_quiz(summary)
            return
        session.advance()
        self._render()

    # ----------------------------------------------------------------- release
    def release(self):
        meta = self.meta
        self.meta = None
        self._lesson = None
        self._session = None
        self._options = []
        self._input = None
        self._hint_button = None
        self._hint_label = None
        if self._question_card is not None:
            self._question_card.clear_widgets()
        if self._answers is not None:
            self._answers.clear_widgets()
        if self._feedback is not None:
            self._feedback.clear_widgets()
        if meta is not None and self.app.repo is not None:
            self.app.repo.release(meta.id)


# ---------------------------------------------------------------------- result
class ResultScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app, name="result")
        self._summary: Optional[QuizSummary] = None
        self._record = False
        self._content: Optional[BoxLayout] = None
        self._scroll: Optional[ScrollView] = None

    def build_ui(self):
        root = BoxLayout(orientation="vertical")
        self.add_widget(root)

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            spacing=dp(4),
            padding=[dp(2), 0, dp(2), 0],
        )
        back = TextButton(
            text="‹",
            size_hint=(None, None),
            width=dp(42),
            height=dp(42),
            font_size=sp(28),
            text_color=T.PRIMARY,
        )
        back.bind(on_release=lambda *_: self.app.back())
        header.add_widget(back)
        header.add_widget(
            _fit_label("Результат", font_size=T.H2, bold=True, height=dp(28))
        )
        root.add_widget(header)

        self._scroll = ScrollView(
            bar_width=dp(2),
            bar_color=T.PRIMARY,
            bar_inactive_color=T.BORDER,
            scroll_type=["bars", "content"],
        )
        self._content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=T.CARD_SPACING,
            padding=[T.PAGE_X, dp(4), T.PAGE_X, dp(16)],
        )
        self._content.bind(minimum_height=self._content.setter("height"))
        self._scroll.add_widget(self._content)
        root.add_widget(self._scroll)

        footer = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(66),
            spacing=dp(8),
            padding=[T.PAGE_X, dp(6), T.PAGE_X, dp(8)],
        )
        retry = RoundedButton(text="Повторить", size_hint_x=1)
        retry.bind(on_release=lambda *_: self._retry())
        theory = RoundedButton(
            text="К теории",
            size_hint_x=1,
            bg_color=T.PRIMARY_SOFT,
            text_color=T.PRIMARY,
        )
        theory.bind(on_release=lambda *_: self._to_theory())
        footer.add_widget(retry)
        footer.add_widget(theory)
        root.add_widget(footer)

    def show(self, summary: QuizSummary, record: bool):
        self.ensure_built()
        self._summary = summary
        self._record = record
        self._render()

    def _render(self):
        summary = self._summary
        if summary is None:
            return
        self._content.clear_widgets()
        color = self._grade_color(summary.percent)
        card = _auto(
            RoundedCard(size_hint_y=None, padding=[dp(16), dp(16), dp(16), dp(16)])
        )
        percent = Label(
            text=f"{summary.percent}%",
            font_size=sp(46),
            bold=True,
            color=color,
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(56),
        )
        card.add_widget(percent)
        card.add_widget(
            WrapLabel(
                text=self._grade_text(summary.percent),
                font_size=T.H3,
                bold=True,
                color=color,
                halign="center",
            )
        )
        card.add_widget(
            WrapLabel(
                text=f"{summary.correct} из {summary.total} верно · {summary.title}",
                font_size=T.SMALL,
                color=T.TEXT_MUTED,
                halign="center",
            )
        )
        if self._record:
            card.add_widget(
                WrapLabel(
                    text="Новый лучший результат!",
                    font_size=T.SMALL,
                    bold=True,
                    color=T.SUCCESS,
                    halign="center",
                )
            )
        self._content.add_widget(card)

        if summary.wrongs:
            self._content.add_widget(
                _heading("Разбор ошибок", size=T.H2)
            )
            for index, result in enumerate(summary.wrongs, start=1):
                self._content.add_widget(self._wrong_card(index, result))
        else:
            success = _auto(
                RoundedCard(
                    size_hint_y=None,
                    bg_color=T.SUCCESS_BG,
                    padding=T.CARD_PADDING,
                    spacing=dp(4),
                )
            )
            success.add_widget(
                WrapLabel(
                    text="Все вопросы верно!",
                    font_size=T.H3,
                    bold=True,
                    color=T.SUCCESS,
                )
            )
            success.add_widget(
                WrapLabel(
                    text="Тема закрыта. Можно переходить к следующей или повторить её позже для закрепления.",
                    font_size=T.SMALL,
                    color=T.TEXT,
                )
            )
            self._content.add_widget(success)
        self._scroll.scroll_y = 1

    @staticmethod
    def _wrong_card(index: int, result) -> RoundedCard:
        question = result.question
        card = _auto(
            RoundedCard(size_hint_y=None, padding=T.CARD_PADDING, spacing=dp(4))
        )
        card.add_widget(
            _fit_label(
                f"ВОПРОС {index}",
                font_size=T.TINY,
                color=T.DANGER,
                bold=True,
                height=dp(16),
            )
        )
        card.add_widget(WrapLabel(text=question.text, font_size=T.SMALL, color=T.TEXT))
        card.add_widget(
            WrapLabel(
                text=f"Ваш ответ: {result.given_text}",
                font_size=T.TINY,
                color=T.TEXT_MUTED,
                markup=False,
            )
        )
        card.add_widget(
            WrapLabel(
                text=f"Правильно: [b]{question.correct_text()}[/b]",
                font_size=T.SMALL,
                color=T.SUCCESS,
            )
        )
        card.add_widget(
            WrapLabel(
                text=question.explanation,
                font_size=T.TINY,
                color=T.TEXT_MUTED,
            )
        )
        return card

    @staticmethod
    def _grade_text(percent: int) -> str:
        if percent >= 85:
            return "Отлично! Тема освоена уверенно."
        if percent >= 60:
            return "Хорошо. Ошибки стоит разобрать — и можно двигаться дальше."
        return "Пока слабо. Вернитесь к теории и примерам, затем повторите тест."

    @staticmethod
    def _grade_color(percent: int):
        if percent >= 85:
            return T.SUCCESS
        if percent >= 60:
            return T.WARNING
        return T.DANGER

    def _retry(self):
        if self._summary is not None:
            self.app.start_quiz(self._summary.lesson_id)

    def _to_theory(self):
        if self._summary is not None:
            self.app.open_lesson(self._summary.lesson_id)

    def release(self):
        self._summary = None
        if self._content is not None:
            self._content.clear_widgets()


# -------------------------------------------------------------------- formulas
class FormulasScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app, name="formulas")
        self._content: Optional[BoxLayout] = None

    def build_ui(self):
        root = BoxLayout(orientation="vertical")
        self.add_widget(root)

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            spacing=dp(4),
            padding=[dp(2), 0, dp(2), 0],
        )
        back = TextButton(
            text="‹",
            size_hint=(None, None),
            width=dp(42),
            height=dp(42),
            font_size=sp(28),
            text_color=T.PRIMARY,
        )
        back.bind(on_release=lambda *_: self.app.back())
        header.add_widget(back)
        header.add_widget(
            _fit_label("Шпаргалка", font_size=T.H2, bold=True, height=dp(28))
        )
        root.add_widget(header)

        scroll = ScrollView(
            bar_width=dp(2),
            bar_color=T.PRIMARY,
            bar_inactive_color=T.BORDER,
            scroll_type=["bars", "content"],
        )
        self._content = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=T.CARD_SPACING,
            padding=[T.PAGE_X, dp(4), T.PAGE_X, dp(16)],
        )
        self._content.bind(minimum_height=self._content.setter("height"))
        scroll.add_widget(self._content)
        root.add_widget(scroll)
        self._scroll = scroll

    def load(self):
        self.ensure_built()
        try:
            page = load_formulas()
        except ContentError as exc:
            self._content.clear_widgets()
            self._content.add_widget(
                WrapLabel(text=str(exc), font_size=T.BODY, color=T.DANGER)
            )
            return
        self._content.clear_widgets()
        self._content.add_widget(
            WrapLabel(
                text=page.subtitle,
                font_size=T.SMALL,
                color=T.TEXT_MUTED,
            )
        )
        for group in page.groups:
            self._content.add_widget(_heading(group.title, size=T.H2))
            card = _auto(RoundedCard(size_hint_y=None, spacing=dp(10)))
            for formula in group.items:
                row = _auto(
                    BoxLayout(
                        orientation="vertical", size_hint_y=None, spacing=dp(1)
                    )
                )
                row.add_widget(
                    WrapLabel(
                        text=formula.name,
                        font_size=T.TINY,
                        color=T.TEXT_MUTED,
                        bold=True,
                    )
                )
                row.add_widget(
                    WrapLabel(
                        text=formula.expr,
                        font_size=T.FORMULA,
                        color=T.PRIMARY,
                        bold=True,
                    )
                )
                if formula.note:
                    row.add_widget(
                        WrapLabel(
                            text=formula.note,
                            font_size=T.TINY,
                            color=T.TEXT_MUTED,
                        )
                    )
                card.add_widget(row)
            self._content.add_widget(card)
        self._scroll.scroll_y = 1

    def release(self):
        if self._content is not None:
            self._content.clear_widgets()
