# Repository Quality Auditor

An evidence-backed agentic system that evaluates an unfamiliar software repository.

## Project Purpose

This project aims to build an automated system for analyzing software repositories to assess their quality, security, maintainability, and other important characteristics. The system collects evidence, analyzes it using specialized agents, and generates comprehensive audit reports.

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