import unittest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from kpi_logger import KPIRecord, append_kpi, load_recent


class TestKPILogger(unittest.TestCase):
    def test_append_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "kpi.jsonl"
            rec1 = KPIRecord(datetime.now() - timedelta(days=1), 100, 0, 1.0)
            rec2 = KPIRecord(datetime.now(), 200, 1, 2.0)
            append_kpi(rec1, path)
            append_kpi(rec2, path)
            records = load_recent(days=2, path=path)
            self.assertEqual(len(records), 2)


if __name__ == "__main__":
    unittest.main()
