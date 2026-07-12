from __future__ import annotations

import json
import unittest

from marketcore.presentation.workspace_v2.render_tree_http_v1 import (
    control_center_render_tree_http_v2,
)


class ControlCenterRenderTreeV2Test(unittest.TestCase):
    def test_vertical_slice_is_serializable_and_contains_fact_evidence(self) -> None:
        response = control_center_render_tree_http_v2()
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.body)
        self.assertEqual(payload["schema_version"], "marketcore.render_tree.v1")
        self.assertEqual(payload["root"]["type"], "workspace")

        encoded = response.body.decode("utf-8")
        self.assertIn("Центр управления", encoded)
        self.assertIn("Фабрика связей", encoded)
        self.assertIn("Воронка сигналов", encoded)
        self.assertIn("Причины и действия", encoded)
        self.assertIn("Shadow-сделки", encoded)
        self.assertIn("Нарушения", encoded)
        self.assertIn("Готовность", encoded)
        self.assertIn("OOS PASS", encoded)
        self.assertNotIn("<table", encoded)
        self.assertNotIn("<style", encoded)


if __name__ == "__main__":
    unittest.main()
