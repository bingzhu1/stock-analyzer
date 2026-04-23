from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from ui.home_tab import _navigate_to_main_view


class HomeTabNavigationTests(unittest.TestCase):
    def test_navigate_to_main_view_sets_target_and_reruns(self) -> None:
        for target in ("scan", "predict", "review", "history"):
            with self.subTest(target=target):
                fake_st = types.SimpleNamespace()
                fake_st.session_state = {}
                fake_st.rerun_called = False

                def _rerun() -> None:
                    fake_st.rerun_called = True

                fake_st.rerun = _rerun

                with patch.dict(sys.modules, {"streamlit": fake_st}):
                    _navigate_to_main_view(target)

                self.assertEqual(fake_st.session_state["active_main_view"], target)
                self.assertTrue(fake_st.rerun_called)


if __name__ == "__main__":
    unittest.main()
