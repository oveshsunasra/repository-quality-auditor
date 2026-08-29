"""Tests for LLM-assisted insights functionality."""

import json
import sys
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from auditor.llm.base import LLMProviderError, LLMApiKeyError, LLMResponseError, LLMProvider
from auditor.llm.openai_provider import OpenAIProvider
from auditor.llm.prompt_builder import build_llm_prompt
from auditor.llm.service import create_llm_service, LLMService
from auditor.models.llm_insight import (
    ExplanationItem,
    LLMInsight,
    LLMModelMetadata,
    LLMRiskFactor,
    RecommendationItem,
)
from auditor.models.models import (
    Evidence,
    EvidenceType,
    Finding,
    FindingCategory,
    FindingSeverity,
    RepositoryProfile,
)
from auditor.models.scan_result import QualityScore


def test_llm_insight_model():
    """Test LLMInsight model validation."""
    metadata = LLMModelMetadata(
        model_name="test-model",
        provider="test",
        timestamp=datetime.now(),
    )
    insight = LLMInsight(
        summary="Test summary",
        explanations=[ExplanationItem(rule_id="TEST-001", explanation="Test explanation")],
        recommendations=[RecommendationItem(rule_id="TEST-001", recommendation="Test recommendation")],
        risks=[LLMRiskFactor(description="Test risk", severity="low")],
        model_metadata=metadata,
    )
    assert insight.summary == "Test summary"
    assert len(insight.explanations) == 1
    assert insight.explanations[0].rule_id == "TEST-001"
    assert insight.explanations[0].explanation == "Test explanation"
    assert len(insight.recommendations) == 1
    assert insight.recommendations[0].rule_id == "TEST-001"
    assert insight.recommendations[0].recommendation == "Test recommendation"
    assert len(insight.risks) == 1
    assert insight.risks[0].description == "Test risk"
    assert insight.risks[0].severity == "low"
    assert insight.model_metadata == metadata


def test_llm_insight_model_missing_fields():
    """Test that missing required fields raise validation error."""
    with pytest.raises(Exception):  # Pydantic validation error
        LLMInsight(summary="Test")  # missing explanations, recommendations, risks, model_metadata


def test_build_llm_prompt():
    """Test prompt builder creates expected prompt structure."""
    # Create minimal audit context
    profile = RepositoryProfile(name="test-repo")
    evidence = [
        Evidence(
            id="test-evidence",
            type=EvidenceType.FILE_CONTENT,
            source="README.md",
            content="README exists",
            metadata={"detected": True},
        )
    ]
    findings = [
        Finding(
            id="test-finding",
            rule_id="TEST-001",
            title="Test Finding",
            description="Test description",
            severity=FindingSeverity.MEDIUM,
            category=FindingCategory.TESTING,
            evidence_ids=["test-evidence"],
        )
    ]
    quality_score = QualityScore(
        score=80,
        max_score=100,
        grade="B",
        deductions=[{"rule_id": "TEST-001", "severity": "medium", "points": 8}],
        finding_count=1,
    )

    prompt = build_llm_prompt(profile, evidence, findings, quality_score)

    # Check that prompt contains key sections
    assert "AUDIT CONTEXT:" in prompt
    assert "INSTRUCTIONS:" in prompt
    assert "RESPONSE FORMAT:" in prompt
    assert "test-repo" in prompt
    assert "TEST-001" in prompt
    assert "Test Finding" in prompt
    assert '"summary"' in prompt
    assert '"explanations"' in prompt
    assert '"recommendations"' in prompt
    assert '"risks"' in prompt


def test_openai_provider_init_without_api_key():
    """Test that OpenAIProvider raises error when API key missing."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(LLMApiKeyError):
            OpenAIProvider()


def test_openai_provider_init_with_api_key():
    """Test that OpenAIProvider initializes correctly with API key."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        provider = OpenAIProvider()
        assert provider.api_key == "test-key"
        assert provider.model == "gpt-3.5-turbo"  # default
        assert provider.temperature == 0.1
        assert provider.max_tokens == 1000
        assert provider.timeout == 30.0  # default from env or hardcoded


def test_openai_provider_timeout_config():
    """Test timeout configuration from environment and parameter."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key", "AUDITOR_LLM_TIMEOUT": "45.0"}):
        provider = OpenAIProvider()
        assert provider.timeout == 45.0

    # Parameter overrides environment
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key", "AUDITOR_LLM_TIMEOUT": "45.0"}):
        provider = OpenAIProvider(timeout=10.0)
        assert provider.timeout == 10.0

    # Invalid timeout in environment falls back to default
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key", "AUDITOR_LLM_TIMEOUT": "invalid"}):
        provider = OpenAIProvider()
        assert provider.timeout == 30.0  # fallback


def test_openai_provider_success_response():
    """Test successful response parsing."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        provider = OpenAIProvider()

        # Mock the OpenAI client response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "summary": "Test summary",
                "explanations": [{"rule_id": "TEST-001", "explanation": "Test explanation"}],
                "recommendations": [{"rule_id": "TEST-001", "recommendation": "Test recommendation"}],
                "risks": [{"description": "Test risk", "severity": "low"}],
            }
        )
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30

        with patch.object(provider.client.chat.completions, "create", return_value=mock_response):
            insight = provider.generate_insights(
                RepositoryProfile(name="test"),
                [],
                [],
                QualityScore(score=100, max_score=100, grade="A", deductions=[], finding_count=0),
            )

            assert insight.summary == "Test summary"
            assert len(insight.explanations) == 1
            assert insight.explanations[0].rule_id == "TEST-001"
            assert insight.explanations[0].explanation == "Test explanation"
            assert len(insight.recommendations) == 1
            assert insight.recommendations[0].rule_id == "TEST-001"
            assert insight.recommendations[0].recommendation == "Test recommendation"
            assert len(insight.risks) == 1
            assert insight.risks[0].description == "Test risk"
            assert insight.risks[0].severity == "low"
            assert insight.model_metadata.model_name == "gpt-3.5-turbo"
            assert insight.model_metadata.provider == "openai"
            assert insight.model_metadata.token_usage == {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            }


def test_openai_provider_timeout_error():
    """Test timeout error handling."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        provider = OpenAIProvider(timeout=5.0)

        with patch.object(
            provider.client.chat.completions, "create", side_effect=Exception("timeout")
        ) as mock_create:
            # We need to mock the specific exception type that the provider catches
            # For simplicity, we'll mock a generic exception and check that it's wrapped
            with patch("auditor.llm.openai_provider.APITimeoutError", Exception):
                with pytest.raises(Exception) as exc_info:
                    provider.generate_insights(
                        RepositoryProfile(name="test"),
                        [],
                        [],
                        QualityScore(score=100, max_score=100, grade="A", deductions=[], finding_count=0),
                    )
                # Check that our custom error is raised
                assert "OpenAI API request timed out" in str(exc_info.value)


def test_openai_provider_api_error():
    """Test API error handling."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        provider = OpenAIProvider()

        with patch.object(
            provider.client.chat.completions, "create", side_effect=Exception("API error")
        ):
            with patch("auditor.llm.openai_provider.APIError", Exception):
                with pytest.raises(Exception) as exc_info:
                    provider.generate_insights(
                        RepositoryProfile(name="test"),
                        [],
                        [],
                        QualityScore(score=100, max_score=100, grade="A", deductions=[], finding_count=0),
                    )
                assert "OpenAI API error" in str(exc_info.value)


def test_openai_provider_invalid_json():
    """Test handling of invalid JSON response."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        provider = OpenAIProvider()

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "invalid json"
        mock_response.usage = None

        with patch.object(provider.client.chat.completions, "create", return_value=mock_response):
            with pytest.raises(LLMResponseError, match="Invalid JSON response"):
                provider.generate_insights(
                    RepositoryProfile(name="test"),
                    [],
                    [],
                    QualityScore(score=100, max_score=100, grade="A", deductions=[], finding_count=0),
                )


def test_openai_provider_missing_fields():
    """Test handling of response missing required fields."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        provider = OpenAIProvider()

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {"summary": "Test"}  # missing explanations, recommendations, risks
        )
        mock_response.usage = None

        with patch.object(provider.client.chat.completions, "create", return_value=mock_response):
            with pytest.raises(LLMResponseError, match="Missing 'explanations' field"):
                provider.generate_insights(
                    RepositoryProfile(name="test"),
                    [],
                    [],
                    QualityScore(score=100, max_score=100, grade="A", deductions=[], finding_count=0),
                )


def test_create_llm_service_no_api_key():
    """Test that service creation returns None when no API key."""
    with patch.dict("os.environ", {}, clear=True):
        service = create_llm_service()
        assert service is None


def test_create_llm_service_with_api_key():
    """Test that service creation works with API key."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        service = create_llm_service()
        assert isinstance(service, LLMService)
        assert isinstance(service.provider, OpenAIProvider)


def test_llm_service_generate_insights_success():
    """Test LLM service successful insight generation."""
    mock_provider = Mock(spec=LLMProvider)
    mock_insight = Mock(spec=LLMInsight)
    mock_provider.generate_insights.return_value = mock_insight

    service = LLMService(mock_provider)
    insight = service.generate_insights(
        RepositoryProfile(name="test"),
        [],
        [],
        QualityScore(score=100, max_score=100, grade="A", deductions=[], finding_count=0),
    )

    assert insight == mock_insight
    mock_provider.generate_insights.assert_called_once()


def test_llm_service_generate_insights_failure():
    """Test LLM service returns None on provider failure."""
    mock_provider = Mock(spec=LLMProvider)
    mock_provider.generate_insights.side_effect = LLMProviderError("Provider error")

    service = LLMService(mock_provider)
    insight = service.generate_insights(
        RepositoryProfile(name="test"),
        [],
        [],
        QualityScore(score=100, max_score=100, grade="A", deductions=[], finding_count=0),
    )

    assert insight is None


def test_cli_deterministic_mode():
    """Test that CLI works in deterministic mode (no LLM)."""
    from auditor.cli import main
    import sys
    from io import StringIO
    from unittest.mock import patch

    # We'll test by mocking sys.argv with text format
    test_args = ["auditor", ".", "--format", "text"]

    # Save original stdout/stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    try:
        # Capture output
        sys.stdout = StringIO()
        sys.stderr = StringIO()

        # Mock sys.argv
        with patch.object(sys, 'argv', test_args):
            # Run the CLI (should work)
            # We'll use SystemExit to catch the exit call
            try:
                main()
            except SystemExit as e:
                # CLI calls sys.exit(0) on success
                assert e.code == 0

        output = sys.stdout.getvalue()
        error_output = sys.stderr.getvalue()

        # Check that we got a valid report
        assert "Repository Quality Auditor Report" in output
        assert "Findings" in output
        assert "Quality Score" in output
        # No LLM insights section when not requested
        assert "LLM Insights" not in output

    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def test_cli_llm_disabled_gracefully():
    """Test that CLI with --llm works gracefully when no API key is set."""
    from auditor.cli import main
    import sys
    from io import StringIO
    from unittest.mock import patch

    old_stdout = sys.stdout
    old_stderr = sys.stderr

    try:
        sys.stdout = StringIO()
        sys.stderr = StringIO()

        # Mock sys.argv and environment (no API key)
        test_args = ["auditor", ".", "--llm", "--format", "text"]
        with patch.object(sys, 'argv', test_args):
            with patch.dict("os.environ", {}, clear=True):
                try:
                    main()
                except SystemExit as e:
                    assert e.code == 0

        output = sys.stdout.getvalue()
        error_output = sys.stderr.getvalue()

        # Should still produce the deterministic report
        assert "Repository Quality Auditor Report" in output
        assert "Findings" in output
        assert "Quality Score" in output

        # Should show info message about LLM being disabled
        assert "Info: LLM insights disabled" in error_output

    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def test_cli_invalid_path():
    """Test that CLI handles invalid paths gracefully."""
    from auditor.cli import main
    import sys
    from io import StringIO
    from unittest.mock import patch

    old_stdout = sys.stdout
    old_stderr = sys.stderr

    try:
        sys.stdout = StringIO()
        sys.stderr = StringIO()

        # Mock sys.argv
        test_args = ["auditor", "/non/existent/path", "--format", "text"]
        with patch.object(sys, 'argv', test_args):
            try:
                main()
            except SystemExit as e:
                # Should exit with error code
                assert e.code == 1

        output = sys.stdout.getvalue()
        error_output = sys.stderr.getvalue()

        # Should show error message
        assert "Error:" in error_output
        assert "Repository path does not exist" in error_output

    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr