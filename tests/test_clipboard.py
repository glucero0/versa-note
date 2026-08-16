"""Tests for clipboard / HTML table helpers."""

from __future__ import annotations

from versa_note.clipboard import (
    build_cf_html,
    build_html_table,
    parse_clipboard_grid,
    parse_html_table,
)


def test_build_html_table_escapes_cells() -> None:
    html = build_html_table([["a<b>", "x&y"], ['"q"', "ok"]])
    assert "<td>a&lt;b&gt;</td>" in html
    assert "<td>x&amp;y</td>" in html
    assert "<td>&quot;q&quot;</td>" in html
    assert html.startswith("<table><tbody>")
    assert html.endswith("</tbody></table>")


def test_parse_html_table_round_trip() -> None:
    rows = [["a", "b"], ["c", "d"]]
    assert parse_html_table(build_html_table(rows)) == rows


def test_parse_html_table_pads_ragged_rows() -> None:
    html = "<table><tr><td>a</td><td>b</td></tr><tr><td>c</td></tr></table>"
    assert parse_html_table(html) == [["a", "b"], ["c", ""]]


def test_parse_html_table_accepts_th() -> None:
    html = "<table><tr><th>H</th></tr><tr><td>1</td></tr></table>"
    assert parse_html_table(html) == [["H"], ["1"]]


def test_parse_html_table_no_table_returns_none() -> None:
    assert parse_html_table("<div>nope</div>") is None


def test_parse_html_table_empty_returns_none() -> None:
    assert parse_html_table("<table></table>") is None


def test_build_cf_html_offsets_are_consistent() -> None:
    fragment = "<b>hi</b>"
    payload = build_cf_html(fragment).decode("utf-8")
    assert payload.startswith("Version:0.9")
    assert "<!--StartFragment-->" in payload
    assert fragment in payload
    assert payload.index("<!--StartFragment-->") < payload.index(fragment)

    def offset(name: str) -> int:
        for line in payload.split("\r\n"):
            if line.startswith(f"{name}:"):
                return int(line.split(":", 1)[1])
        raise AssertionError(name)

    raw = build_cf_html(fragment)
    start_html = offset("StartHTML")
    end_html = offset("EndHTML")
    start_fragment = offset("StartFragment")
    end_fragment = offset("EndFragment")
    assert 0 <= start_html < start_fragment < end_fragment <= end_html == len(raw)
    assert raw[start_fragment:end_fragment].decode("utf-8") == fragment


def test_parse_clipboard_grid_empty() -> None:
    assert parse_clipboard_grid("") == [[""]]


def test_parse_clipboard_grid_tsv_keeps_commas() -> None:
    assert parse_clipboard_grid("a,b\tc\nd") == [["a,b", "c"], ["d"]]


def test_parse_clipboard_grid_crlf_and_trailing_newline() -> None:
    assert parse_clipboard_grid("a\tb\r\nc\td\r\n") == [["a", "b"], ["c", "d"]]


def test_parse_clipboard_grid_csv_fallback() -> None:
    assert parse_clipboard_grid('a,"b,c"\n1,2') == [["a", "b,c"], ["1", "2"]]
