import unittest

from amatista_engine.errors import InvalidPracticeError
from amatista_engine.practice import parse_practice


class LoaderTests(unittest.TestCase):
    def test_rejects_unknown_schema(self):
        with self.assertRaises(InvalidPracticeError):
            parse_practice({
                "schema": "otro/1",
                "id": "x",
                "title": "X",
                "level": 1,
                "targets": [
                    {
                        "id": "t1",
                        "validator": "file.saved"
                    }
                ]
            })


if __name__ == "__main__":
    unittest.main()
