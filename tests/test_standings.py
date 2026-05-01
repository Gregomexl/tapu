from tapu.widgets.standings import _form_dots


def test_form_dots_all_results():
    result = _form_dots("WWDLW")
    assert "[$success]●[/$success]" in result
    assert "[$warning]●[/$warning]" in result
    assert "[$error]●[/$error]" in result


def test_form_dots_empty_string():
    assert _form_dots("") == ""


def test_form_dots_unknown_chars_skipped():
    result = _form_dots("WXW")
    assert result.count("[$success]●[/$success]") == 2
    assert "X" not in result


def test_form_dots_lowercase():
    result = _form_dots("wdl")
    assert "[$success]●[/$success]" in result
    assert "[$warning]●[/$warning]" in result
    assert "[$error]●[/$error]" in result


def test_form_dots_five_dots_joined_by_spaces():
    result = _form_dots("WWWWW")
    parts = result.split(" ")
    assert len(parts) == 5
