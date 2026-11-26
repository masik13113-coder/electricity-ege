from app.markup import is_valid, strip_tags, validate


def test_valid_markup_with_sub_sup_and_color():
    text = "F = k·|q[sub]1[/sub]q[sub]2[/sub]|/r[sup]2[/sup]"
    assert validate(text) == ()
    assert is_valid("[color=#B42318]важно[/color] и [b]жирно[/b]")


def test_plain_text_is_valid():
    assert validate("Обычный текст без разметки") == ()


def test_unclosed_tag_is_reported():
    problems = validate("[b]не закрыт")
    assert problems
    assert any("не закрыт" in problem for problem in problems)


def test_mismatched_closing_tag_is_reported():
    problems = validate("[b]текст[/i]")
    assert problems
    assert any("/i" in problem for problem in problems)


def test_unknown_tag_is_reported():
    problems = validate("[quote]текст[/quote]")
    assert problems
    assert any("неизвестный тег" in problem for problem in problems)


def test_stray_bracket_is_reported():
    assert validate("10[sup]−19[/sup] и [лишняя скобка")
    assert validate("массив [1]")


def test_bad_color_value_is_reported():
    assert validate("[color=#fff]текст[/color]")
    assert validate("[color]текст[/color]")
    assert validate("[color=red]текст[/color]")


def test_ampersand_is_reported():
    assert validate("напряжение & ток")


def test_non_string_is_reported():
    assert validate(None)
    assert validate(123)


def test_strip_tags():
    assert strip_tags("q[sub]1[/sub] и [b]заряд[/b]") == "q1 и заряд"
