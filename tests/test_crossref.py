from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from core.config import load_settings
from core.utils import write_json
from ingestion.crossref import fetch_source_records, load_raw_records, parse_crossref_payload


SAMPLE_ITEM = {
    "DOI": "HTTPS://DOI.ORG/10.1000/Example",
    "title": ["  Agentic   RAG  "],
    "abstract": "<jats:p>A &amp; B <jats:bold>summary</jats:bold>.</jats:p>",
    "author": [{"given": "Ada", "family": "Lovelace"}],
    "subject": ["Artificial Intelligence", "Retrieval"],
    "type": "journal-article",
    "published": {"date-parts": [[2026, 8, 6]]},
    "indexed": {"date-time": "2026-08-06T10:00:00Z"},
    "URL": "https://doi.org/10.1000/example",
    "link": [{"URL": "https://example.test/paper.pdf", "content-type": "application/pdf"}],
    "container-title": ["Example Journal"],
}


class ParseCrossrefPayloadTests(unittest.TestCase):
    def test_parses_and_normalizes_crossref_fields(self) -> None:
        records = parse_crossref_payload({"message": {"items": [SAMPLE_ITEM]}})

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].paper_id, "10.1000/example")
        self.assertEqual(records[0].title, "Agentic RAG")
        self.assertEqual(records[0].summary, "A & B summary.")
        self.assertEqual(records[0].authors, ["Ada Lovelace"])
        self.assertEqual(records[0].primary_category, "Artificial Intelligence")
        self.assertEqual(records[0].published, "2026-08-06")
        self.assertEqual(records[0].pdf_url, "https://example.test/paper.pdf")
        self.assertEqual(records[0].comment, "Example Journal")

    def test_skips_invalid_and_duplicate_records(self) -> None:
        duplicate = {**SAMPLE_ITEM, "title": ["Duplicate"]}
        payload = {
            "message": {
                "items": [
                    SAMPLE_ITEM,
                    duplicate,
                    {"DOI": "10.1000/no-title"},
                    {"title": ["No DOI"]},
                    None,
                ]
            }
        }

        records = parse_crossref_payload(payload)

        self.assertEqual([record.paper_id for record in records], ["10.1000/example"])

    def test_rejects_payload_without_items(self) -> None:
        with self.assertRaisesRegex(ValueError, "message.items"):
            parse_crossref_payload({"message": {}})


class RawRecordTests(unittest.TestCase):
    def test_raw_records_round_trip(self) -> None:
        record = parse_crossref_payload({"message": {"items": [SAMPLE_ITEM]}})[0]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "records.json"
            write_json(path, [asdict(record)])

            loaded = load_raw_records(path)

        self.assertEqual(loaded, [record])

    @patch("ingestion.crossref.time.sleep")
    @patch("ingestion.crossref.requests.get")
    def test_fetch_retries_and_writes_both_artifacts(self, get: Mock, sleep: Mock) -> None:
        unavailable = Mock(status_code=503, headers={"Retry-After": "0"})
        success = Mock(status_code=200, headers={})
        success.json.return_value = {"message": {"items": [SAMPLE_ITEM]}}
        get.side_effect = [unavailable, success]

        with TemporaryDirectory() as directory:
            settings = load_settings(Path(directory))
            records = fetch_source_records(settings)

            self.assertTrue(settings.paths.raw_api_response.exists())
            self.assertTrue(settings.paths.raw_records_json.exists())
            self.assertEqual(load_raw_records(settings.paths.raw_records_json), records)

        self.assertEqual(get.call_count, 2)
        sleep.assert_called_once_with(1.0)

    @patch("ingestion.crossref.requests.get")
    def test_fetch_preserves_response_before_parse_failure(self, get: Mock) -> None:
        response = Mock(status_code=200, headers={})
        response.json.return_value = {"message": {}}
        get.return_value = response

        with TemporaryDirectory() as directory:
            settings = load_settings(Path(directory))
            with self.assertRaisesRegex(ValueError, "message.items"):
                fetch_source_records(settings)

            self.assertTrue(settings.paths.raw_api_response.exists())
            self.assertFalse(settings.paths.raw_records_json.exists())


if __name__ == "__main__":
    unittest.main()
