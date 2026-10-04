import unittest

from amatista_engine import create_default_engine
from amatista_engine.models import (
    PracticeDefinition,
    SceneObject,
    SceneState,
    TargetDefinition,
)


class EngineTests(unittest.TestCase):
    def test_progress_is_weighted(self):
        practice = PracticeDefinition(
            schema="amatista.practice/1",
            id="test",
            title="Test",
            level=1,
            targets=(
                TargetDefinition(
                    id="a",
                    validator="role.count",
                    params={"role": "pata", "equals": 4},
                    weight=75,
                ),
                TargetDefinition(
                    id="b",
                    validator="file.saved",
                    params={},
                    weight=25,
                ),
            ),
        )

        scene = SceneState(
            blender_version="test",
            file_path="file.blend",
            file_saved=True,
            objects=(
                SceneObject("P1", "MESH", roles=("pata",)),
                SceneObject("P2", "MESH", roles=("pata",)),
                SceneObject("P3", "MESH", roles=("pata",)),
            ),
        )

        report = create_default_engine().evaluate(practice, scene)

        self.assertEqual(report.progress, 25.0)
        self.assertFalse(report.completed)


if __name__ == "__main__":
    unittest.main()
