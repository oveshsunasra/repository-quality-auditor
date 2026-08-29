# Repository Quality Auditor

An evidence-backed agentic system that evaluates an unfamiliar software repository.

## Project Purpose

This project aims to build an automated system for analyzing software repositories to assess their quality, security, maintainability, and other important characteristics. The system collects evidence, analyzes it using specialized analyzers, and generates comprehensive audit reports.

## Setup

1. **Prerequisites**: Python 3.12 or higher

2. **Installation**:
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd repository-quality-auditor

   # Install in development mode
   pip install -e .
   ```

3. **Usage**:
   ```bash
   # Basic usage
   auditor /path/to/repository --format json --output report.json

   # Text output (default to stdout)
   auditor /path/to/repository --format text
   ```

## Current Scope (Baseline Implementation)

This initial implementation provides the foundation for the Repository Quality Auditor:

### ✅ Completed Components
- **Project Structure**: Clean `src/` layout with organized packages
- **Data Models**: Pydantic models for:
  - `RepositoryProfile`: Repository metadata and characteristics
  - `Evidence`: Collected data points during analysis
  - `Finding`: Discovered issues or observations
  - `AuditReport`: Complete audit results
- **CLI Interface**: Basic command-line entry point (`auditor`)
- **Testing**: Unit tests for data models
- **Configuration**: `pyproject.toml`, `.gitignore`, `.env.example`

### 🔜 Planned Enhancements
- Analyzer modules for different aspects (security, performance, etc.)
- Agent system for coordinated analysis
- Scoring mechanism for quantitative assessment
- Multi-agent workflow implementation
- Enhanced evidence collection mechanisms
- Additional output formats and reporting options

## Repository Analysis Engine v0.2

The Repository Analysis Engine transforms factual evidence from the Repository Scanner into structured, deterministic findings using rule-based analysis.

### What it does
- Analyzes repository profile and evidence to identify quality characteristics
- Applies deterministic rules to generate structured findings
- Links findings to supporting evidence for traceability
- Produces both JSON and human-readable output formats

### Current Rule IDs
- **DOC-001**: README file is missing (documentation, medium severity)
- **TEST-001**: No test files detected (testing, high severity)
- **CONT-001**: Dockerfile is missing (containerization, low severity)
- **DEP-001**: No recognized dependency manifest detected (dependency, medium severity)
- **STRUCT-001**: No source files detected (structure, medium severity)

### Finding Categories
- `structure`: Repository file and directory organization
- `documentation`: Presence and quality of documentation
- `testing`: Test coverage and test file organization
- `dependency`: Dependency management and package files
- `containerization`: Container support (Docker, etc.)

### Severity Levels
- `low`: Minor issues or missing enhancements
- `medium`: Important improvements that should be considered
- `high`: Significant gaps that may affect maintainability
- `critical`: Severe issues requiring immediate attention

### Evidence-Backed Design
Each finding references the specific evidence that supports it, ensuring traceability and transparency in the analysis process.

### Deterministic Behavior
For the same repository state, the analyzer always produces identical findings with consistent IDs, categories, severity, and evidence references.

### What it intentionally does NOT do
- No LLM integration
- No agent coordination
- No scoring or quantitative assessment
- No subjective repository quality judgment

## Quality Scoring Engine v0.3

The Quality Scoring Engine calculates a deterministic quality score from audit findings using a explainable, rule-based approach.

### What it does
- Consumes structured findings from the Repository Analyzer
- Applies severity-based deductions to calculate a numerical score (0-100)
- Assigns letter grades based on score ranges
- Provides detailed deduction breakdown for explainability
- Maintains deterministic behavior (same inputs always produce same score)

### Scoring Policy
Each finding severity contributes a fixed deduction from the maximum score of 100:
- **CRITICAL**: -25 points
- **HIGH**: -15 points  
- **MEDIUM**: -8 points
- **LOW**: -3 points
- **INFO**: -0 points (no deduction)

**Score Calculation**: `score = max(0, 100 - total_deductions)`

### Grade Bands
- **90–100 → A**
- **80–89  → B**
- **70–79  → C**
- **60–69  → D**
- **0–59   → F**

### Example Calculation
For findings: 1 HIGH (-15), 1 MEDIUM (-8), 1 LOW (-3):
- Total deductions: 15 + 8 + 3 = 26
- Final score: 100 - 26 = 74
- Grade: C

### Evidence-Backed Design
Each deduction references the specific finding rule_id that contributed to it, ensuring traceability and transparency in the scoring process.

### Deterministic Behavior
For the same set of findings, the scorer always produces identical scores, grades, and deduction ordering (sorted by severity priority, then rule_id).

### What it intentionally does NOT do
- No LLM integration
- No agent coordination
- No subjective quality assessment
- No filesystem scanning inside the scorer
- No external service calls
- No random or non-deterministic elements

## Architecture Overview

```
src/
└── auditor/
    ├── __init__.py
    ├── cli.py              # Command-line interface
    ├── models/             # Pydantic data models
    ├── analyzers/          # Analysis modules (to be implemented)
    ├── agents/             # AI agents (to be implemented)
    ├── providers/          # External service integrations (to be implemented)
    └── scoring/            # Scoring algorithms (to be implemented)
```

## Development Guidelines

- Follow clean architecture principles
- Maintain separation of concerns
- Write comprehensive tests
- Use type hints throughout
- Keep dependencies minimal
- Prioritize extensibility over immediate functionality

## License

MIT License - see LICENSE file for details.