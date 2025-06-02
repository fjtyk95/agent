import unittest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from kpi_logger import KPIRecord, append_kpi, load_recent

class KPILoggerTests(unittest.TestCase):
    def test_append_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "kpi.jsonl"
            r1 = KPIRecord(datetime.now() - timedelta(hours=1), 100, 5, 0.1)
            r2 = KPIRecord(datetime.now(), 200, 10, 0.2)
            append_kpi(r1, path)
            append_kpi(r2, path)

            records = load_recent(1, path)
            self.assertEqual(len(records), 2)


if __name__ == "__main__":
    unittest.main()
