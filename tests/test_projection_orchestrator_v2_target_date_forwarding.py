"""Task 100 — `run_projection_v2(target_date=...)` forwards the date.

Confirms that ``services.projection_orchestrator_v2.run_projection_v2``
passes ``target_date`` through to its injected ``_projection_runner``.
This was the previous breakage: the projection chain accepted the
parameter but silently dropped it before the legacy orchestrator,
collapsing the historical replay onto today's snapshot.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.projection_orchestrator_v2 import run_projection_v2


class TestRunProjectionV2ForwardsTargetDate(unittest.TestCase):
    def test_target_date_is_forwarded_to_projection_runner(self) -> None:
        captured: dict[str, Any] = {}

        def fake_runner(**kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            # Raise to short-circuit the rest of the pipeline; we only care
            # about the kwargs the legacy runner received.
            raise RuntimeError("short-circuit")

        # run_projection_v2 catches the RuntimeError and returns a degraded
        # payload — that path also surfaces target_date in the output.
        result = run_projection_v2(
            symbol="AVGO",
            lookback_days=20,
            target_date="2023-06-15",
            _projection_runner=fake_runner,
        )

        self.assertEqual(captured.get("target_date"), "2023-06-15")
        self.assertEqual(captured.get("symbol"), "AVGO")
        self.assertEqual(captured.get("lookback_days"), 20)

        # The output payload should also echo target_date so downstream
        # storage / review can record the as-of date.
        self.assertEqual(result.get("target_date"), "2023-06-15")
        self.assertFalse(result.get("ready"), msg=f"expected degraded ready=False, got {result}")

    def test_target_date_none_remains_none_in_runner_call(self) -> None:
        captured: dict[str, Any] = {}

        def fake_runner(**kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            raise RuntimeError("short-circuit")

        run_projection_v2(
            symbol="AVGO",
            lookback_days=20,
            target_date=None,
            _projection_runner=fake_runner,
        )

        # When target_date is None, the legacy runner still receives the
        # kwarg explicitly as None — it then falls back to the live
        # "latest row" behaviour inside the orchestrator.
        self.assertIn("target_date", captured)
        self.assertIsNone(captured["target_date"])

    def test_two_different_target_dates_propagate_independently(self) -> None:
        capture_log: list[Any] = []

        def fake_runner(**kwargs: Any) -> dict[str, Any]:
            capture_log.append(kwargs.get("target_date"))
            raise RuntimeError("short-circuit")

        run_projection_v2(
            symbol="AVGO",
            lookback_days=20,
            target_date="2022-04-22",
            _projection_runner=fake_runner,
        )
        run_projection_v2(
            symbol="AVGO",
            lookback_days=20,
            target_date="2024-04-22",
            _projection_runner=fake_runner,
        )

        self.assertEqual(capture_log, ["2022-04-22", "2024-04-22"])


if __name__ == "__main__":
    unittest.main()
