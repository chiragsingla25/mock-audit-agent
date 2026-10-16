"""Tests never call OpenRouter or LangSmith (CLAUDE.md)."""

import os

os.environ["LANGSMITH_TRACING"] = "false"
os.environ.pop("LANGSMITH_API_KEY", None)
os.environ.pop("OPENROUTER_API_KEY", None)
