from __future__ import annotations

import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ui.command_bar import _RESPONSE_CARD_SECTION_HEADINGS

try:
    import pandas  # noqa: F401
    from streamlit.testing.v1 import AppTest
except ModuleNotFoundError:
    AppTest = None


def _script() -> str:
    """Minimal embedded script that renders only the command bar."""
    return textwrap.dedent(
        f"""
        import sys
        sys.path.insert(0, {str(ROOT)!r})

        import streamlit as st
        from ui.command_bar import render_command_bar

        render_command_bar()
        """
    )


def _get_button(at, key: str):
    for btn in at.button:
        if btn.key == key:
            return btn
    raise AssertionError(f"Button with key {key!r} not found")


def _response_section_headings(at) -> list[str]:
    headings = []
    for item in at.markdown:
        value = str(item.value).strip()
        normalized = value.strip("*")
        if normalized in _RESPONSE_CARD_SECTION_HEADINGS:
            headings.append(normalized)
    return headings


def _markdown_texts(at) -> list[str]:
    return [str(item.value) for item in at.markdown]


@unittest.skipIf(AppTest is None, "streamlit AppTest or pandas is not installed")
class CommandBarAppTests(unittest.TestCase):

    def test_command_bar_renders_without_error(self) -> None:
        at = AppTest.from_string(_script()).run()
        self.assertFalse(at.exception, msg=f"App raised: {at.exception}")

    def test_parse_button_exists(self) -> None:
        at = AppTest.from_string(_script()).run()
        btn = _get_button(at, "cn_parse_btn")
        self.assertIsNotNone(btn)

    def test_parse_with_empty_input_shows_warning(self) -> None:
        at = AppTest.from_string(_script()).run()
        # Leave input empty, click parse
        at = _get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception)
        warning_texts = [w.value for w in at.warning]
        self.assertTrue(
            any("请先输入指令" in t for t in warning_texts),
            msg=f"Expected warning text not found. Warnings: {warning_texts}",
        )

    def test_parse_valid_query_shows_success(self) -> None:
        at = AppTest.from_string(_script()).run()
        at.text_input(key="cn_command_input").input("调出博通最近20天数据")
        at = _get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception)
        success_texts = [s.value for s in at.success]
        self.assertTrue(
            any("解析结果" in t for t in success_texts),
            msg=f"Expected success text not found. Successes: {success_texts}",
        )

    def test_parse_query_renders_fixed_response_sections(self) -> None:
        at = AppTest.from_string(_script()).run()
        at.text_input(key="cn_command_input").input("调出博通最近20天数据")
        at = _get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(
            _response_section_headings(at),
            list(_RESPONSE_CARD_SECTION_HEADINGS),
        )

    def test_parse_unknown_command_shows_error(self) -> None:
        at = AppTest.from_string(_script()).run()
        at.text_input(key="cn_command_input").input("帮我查一下今天天气")
        at = _get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception)
        error_texts = [e.value for e in at.error]
        self.assertTrue(
            any("解析错误" in t for t in error_texts),
            msg=f"Expected error text not found. Errors: {error_texts}",
        )

    def test_parse_compare_command_shows_success(self) -> None:
        at = AppTest.from_string(_script()).run()
        at.text_input(key="cn_command_input").input(
            "比较博通和英伟达最近20天最高价走势"
        )
        at = _get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception)
        success_texts = [s.value for s in at.success]
        self.assertTrue(
            any("解析结果" in t for t in success_texts),
            msg=f"Expected success not found. Successes: {success_texts}",
        )

    def test_compare_strength_command_does_not_crash(self) -> None:
        at = AppTest.from_string(_script()).run()
        at.text_input(key="cn_command_input").input("比较一下博通和英伟达最近20天强弱")
        at = _get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any("表格输出" in t for t in _markdown_texts(at)))

    def test_query_volume_command_renders_table_output(self) -> None:
        at = AppTest.from_string(_script()).run()
        at.text_input(key="cn_command_input").input("只看博通最近20天成交量")
        at = _get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any("表格输出" in t for t in _markdown_texts(at)))

    def test_stats_volume_average_command_renders_table_output(self) -> None:
        at = AppTest.from_string(_script()).run()
        at.text_input(key="cn_command_input").input("博通今天和最近20天平均成交量比怎么样")
        at = _get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception)
        text = "\n".join(_markdown_texts(at))
        self.assertIn("表格输出", text)
        self.assertIn("原始结果", text)

    def test_parse_review_command_shows_success(self) -> None:
        at = AppTest.from_string(_script()).run()
        at.text_input(key="cn_command_input").input("复盘昨天")
        at = _get_button(at, "cn_parse_btn").click().run()
        self.assertFalse(at.exception)
        success_texts = [s.value for s in at.success]
        self.assertTrue(
            any("解析结果" in t for t in success_texts),
            msg=f"Expected success not found. Successes: {success_texts}",
        )


if __name__ == "__main__":
    unittest.main()
