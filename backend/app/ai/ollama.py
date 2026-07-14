import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path

from app.ai.base import AIProvider, AIReviewResult, ProviderStatus
from app.ai.context import AIReviewContext

logger = logging.getLogger("epibridge.ai.ollama")

SOURCE_EXTENSIONS = {".py", ".R", ".r", ".sh", ".js", ".ipynb", ".txt", ".md"}

REVIEW_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "assessment": {"type": "string"},
        "assessment_confidence": {
            "type": "string",
            "enum": ["High", "Medium", "Low"],
        },
        "reviewer_notes": {"type": "string"},
    },
    "required": [
        "summary",
        "assessment",
        "assessment_confidence",
        "reviewer_notes",
    ],
}

REVIEW_PROMPT = (
    "You are an assistant reviewing an uploaded Analysis Bundle "
    "for the EpiBridge secure research platform. "
    "Your purpose is to help researchers and platform reviewers "
    "understand what this bundle appears to do based only on "
    "the supplied metadata and source code. "
    "Do not speculate about unseen datasets, execution results, "
    "or outcomes.\n\n"
    "{bundle_metadata}\n\n"
    "Source files:\n\n"
    "{source_code}\n\n"
    "Provide:\n"
    "1. A short natural-language summary (2-3 sentences) "
    "of what the analysis appears to do.\n"
    "2. An advisory assessment: either that no behaviours "
    "were identified that would normally require additional "
    "manual review, or that one or more behaviours were "
    "identified that merit manual review before execution.\n"
    "3. Assessment confidence: How confident are you that your "
    "assessment accurately reflects the uploaded Analysis Bundle "
    "based solely on the supplied metadata and source code? "
    "(High, Medium, or Low — not confidence that the code is "
    "correct or safe, only confidence in your interpretation "
    "of the bundle.)\n"
    "4. Reviewer notes describing observable behaviours that "
    "influenced your assessment (external process execution, "
    "shell commands, network access, unusual filesystem access, "
    "dynamic code execution, unusual dependencies). "
    "If nothing notable, return a sentence stating that "
    'clearly (e.g. "No notable behaviours observed."). '
    "Never leave this field empty.\n\n"
    "The assessment must be based solely on the supplied "
    "Analysis Bundle metadata and uploaded source code. "
    "Do not infer anything about the research data, "
    "execution results, scientific validity, or security "
    "beyond observable behaviour. "
    "The assessment is simply a recommendation about whether "
    "the bundle appears routine or whether its observable "
    "behaviour merits closer human inspection.\n\n"
    "Respond ONLY with valid JSON in this exact format "
    "(no markdown, no code fences):\n"
    '{{"summary": "...", "assessment": "...", '
    '"assessment_confidence": "High|Medium|Low", '
    '"reviewer_notes": "..."}}'
)


class OllamaProvider(AIProvider):
    def __init__(self, base_url: str, model: str = "llama3.2", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def review(
        self, analysis_dir: Path, context: AIReviewContext | None = None
    ) -> AIReviewResult:
        if not analysis_dir.is_dir():
            logger.warning("Analysis directory not found: %s", analysis_dir)
            return AIReviewResult(
                errors=[f"Analysis directory not found: {analysis_dir}"]
            )

        source_code = self._read_source_files(analysis_dir)
        if not source_code.strip():
            logger.warning(
                "No source files found in analysis bundle at %s", analysis_dir
            )
            return AIReviewResult(errors=["No source files found in analysis bundle"])

        metadata = self._build_metadata(context or AIReviewContext())
        prompt = REVIEW_PROMPT.format(
            bundle_metadata=metadata,
            source_code=source_code,
        )

        try:
            response = self._call_ollama(prompt)
        except urllib.error.URLError:
            logger.warning("AI provider unreachable at %s", self.base_url)
            return AIReviewResult(errors=["AI provider unreachable"])
        except urllib.error.HTTPError as e:
            logger.warning("AI provider returned HTTP %d", e.code)
            return AIReviewResult(errors=[f"AI provider returned HTTP {e.code}"])
        except OSError:
            logger.warning("AI provider unreachable (OS error) at %s", self.base_url)
            return AIReviewResult(errors=["AI provider unreachable"])

        try:
            data = json.loads(response)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Failed to parse AI response: invalid JSON")
            return AIReviewResult(errors=["Failed to parse AI response"])

        summary = data.get("summary", "")
        assessment = data.get("assessment", "")
        assessment_confidence = data.get("assessment_confidence", "")
        reviewer_notes = data.get("reviewer_notes", "")

        if not summary:
            logger.warning("AI response missing summary")
            return AIReviewResult(errors=["AI response missing summary"])

        if assessment_confidence not in ("High", "Medium", "Low"):
            assessment_confidence = "Medium"

        return AIReviewResult(
            summary=summary,
            assessment=assessment,
            assessment_confidence=assessment_confidence,
            reviewer_notes=reviewer_notes,
        )

    def check_status(self) -> ProviderStatus:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            models = [m["name"] for m in data.get("models", [])]
            model_available = any(m.startswith(self.model) for m in models)
            if not model_available:
                logger.info("AI model %s not found in provider", self.model)
                return ProviderStatus(ready=False, reason="model_missing")
            return ProviderStatus(ready=True, reason=None)
        except urllib.error.URLError:
            logger.warning("AI provider unreachable at %s", self.base_url)
            return ProviderStatus(ready=False, reason="provider_unreachable")
        except Exception:
            logger.warning("AI provider status check failed", exc_info=True)
            return ProviderStatus(ready=False, reason="provider_error")

    def _build_metadata(self, context: AIReviewContext) -> str:
        lines = ["Analysis Bundle"]
        lines.append(f"Runtime:      {context.runtime}")
        lines.append(f"Entrypoint:   {context.entrypoint}")
        if context.resource_identifiers:
            lines.append("Declared Data Resources:")
            for r in context.resource_identifiers:
                lines.append(f"  - {r}")
        return "\n".join(lines)

    def _read_source_files(self, analysis_dir: Path) -> str:
        parts = []
        for root, _dirs, files in os.walk(analysis_dir):
            for fname in sorted(files):
                ext = os.path.splitext(fname)[1]
                if ext not in SOURCE_EXTENSIONS:
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", errors="replace") as f:
                        content = f.read()
                except Exception:
                    continue
                rel = os.path.relpath(fpath, analysis_dir)
                parts.append(f"--- {rel} ---\n{content}")
        return "\n\n".join(parts)

    def _call_ollama(self, prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": REVIEW_RESPONSE_SCHEMA,
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        return result.get("response", "")
