import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from app.ai import get_ai_provider
from app.ai.context import AIReviewContext
from app.ai.ollama import OllamaProvider
from app.core.config import settings


class TestGetAIProvider:
    def test_returns_ollama_provider(self):
        provider = get_ai_provider()
        assert isinstance(provider, OllamaProvider)
        assert provider.base_url == settings.ollama_base_url
        assert provider.model == settings.ollama_model
        assert provider.timeout == settings.ollama_timeout_seconds


class TestOllamaProvider:
    def test_constructor(self):
        p = OllamaProvider(base_url="http://ollama:11434", model="llama2")
        assert p.base_url == "http://ollama:11434"
        assert p.model == "llama2"

    def test_constructor_strips_trailing_slash(self):
        p = OllamaProvider(base_url="http://ollama:11434/")
        assert p.base_url == "http://ollama:11434"

    def test_review_directory_not_found(self):
        p = OllamaProvider(base_url=settings.ollama_base_url)
        result = p.review(Path("/nonexistent"))
        assert result.is_unavailable
        assert "not found" in result.errors[0]

    def test_review_no_source_files(self):
        p = OllamaProvider(base_url=settings.ollama_base_url)
        with TemporaryDirectory() as tmp:
            result = p.review(Path(tmp))
        assert result.is_unavailable
        assert "No source files" in result.errors[0]

    def test_review_unreachable_provider(self):
        p = OllamaProvider(base_url="http://localhost:1")
        with TemporaryDirectory() as tmp:
            f = Path(tmp) / "run.py"
            f.write_text("x = 1")
            result = p.review(Path(tmp))
        assert result.is_unavailable
        assert any("unreachable" in e for e in result.errors)

    @patch("app.ai.ollama.urllib.request.urlopen")
    def test_review_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {
                "response": json.dumps(
                    {
                        "summary": "Reads data and computes stats",
                        "assessment": "Appears appropriate for execution",
                        "assessment_confidence": "High",
                        "reviewer_notes": "No notable behaviours detected.",
                    }
                )
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        p = OllamaProvider(base_url=settings.ollama_base_url)
        with TemporaryDirectory() as tmp:
            f = Path(tmp) / "run.py"
            f.write_text(
                "import pandas\ndf = pd.read_csv('data.csv')\nprint(df.describe())"
            )
            result = p.review(Path(tmp))

        assert not result.is_unavailable
        assert result.summary == "Reads data and computes stats"
        assert result.assessment == "Appears appropriate for execution"
        assert result.assessment_confidence == "High"
        assert result.reviewer_notes == "No notable behaviours detected."

    @patch("app.ai.ollama.urllib.request.urlopen")
    def test_review_bad_json_from_ollama(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"response": "not valid json at all"}
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        p = OllamaProvider(base_url=settings.ollama_base_url)
        with TemporaryDirectory() as tmp:
            f = Path(tmp) / "run.py"
            f.write_text("x = 1")
            result = p.review(Path(tmp))

        assert result.is_unavailable
        assert any("parse" in e.lower() for e in result.errors)

    @patch("app.ai.ollama.urllib.request.urlopen")
    def test_review_missing_summary(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {
                "response": json.dumps(
                    {
                        "assessment": "None",
                        "assessment_confidence": "Low",
                        "reviewer_notes": "None",
                    }
                )
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        p = OllamaProvider(base_url=settings.ollama_base_url)
        with TemporaryDirectory() as tmp:
            f = Path(tmp) / "run.py"
            f.write_text("x = 1")
            result = p.review(Path(tmp))

        assert result.is_unavailable
        assert "missing summary" in result.errors[0].lower()

    @patch("app.ai.ollama.urllib.request.urlopen")
    def test_review_reads_multiple_source_files(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {
                "response": json.dumps(
                    {
                        "summary": "Multi-file analysis",
                        "assessment": "Appears appropriate",
                        "assessment_confidence": "Medium",
                        "reviewer_notes": "No notable behaviours detected.",
                    }
                )
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        p = OllamaProvider(base_url=settings.ollama_base_url)
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "run.py").write_text("print('hello')")
            (Path(tmp) / "lib.R").write_text("library(ggplot2)")
            (Path(tmp) / "data.txt").write_text("some data")
            result = p.review(Path(tmp))

        assert not result.is_unavailable
        assert result.summary == "Multi-file analysis"

    @patch("app.ai.ollama.urllib.request.urlopen")
    def test_review_includes_metadata_in_prompt(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {
                "response": json.dumps(
                    {
                        "summary": "Test",
                        "assessment": "None",
                        "assessment_confidence": "High",
                        "reviewer_notes": "None",
                    }
                )
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        p = OllamaProvider(base_url=settings.ollama_base_url)
        context = AIReviewContext(
            runtime="python-3.13",
            entrypoint="run.py",
            resource_identifiers=["demo-surveillance"],
        )
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "run.py").write_text("x = 1")
            p.review(Path(tmp), context=context)

        sent_body = json.loads(mock_urlopen.call_args[0][0].data)
        prompt = sent_body["prompt"]
        assert "Runtime:      python-3.13" in prompt
        assert "Entrypoint:   run.py" in prompt
        assert "demo-surveillance" in prompt
