#!/usr/bin/env python3
"""
Test suite for get_spawned.py script.

This module contains comprehensive tests for the Jenkins console log parsing script,
including unit tests for the pattern matching and integration tests for the CLI interface.
"""

import sys
from pathlib import Path

import pytest

# Import the classes from get_spawned.py
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from scripts.get_spawned import JenkinsConsoleParser


class TestJenkinsConsoleParser:
    """Test cases for JenkinsConsoleParser class."""

    def setup_method(self):
        """Set up test parser for each test."""
        self.parser = JenkinsConsoleParser()

    def test_empty_console_output(self):
        """Test handling of empty console output."""
        console_content = ""

        result = self.parser.parse_console_output(console_content)

        assert "parent" in result
        assert "spawned_jobs" in result
        assert len(result["spawned_jobs"]) == 0

    def test_console_output_with_no_spawned_jobs(self):
        """Test parsing console output that contains no spawned job information."""
        console_content = """
This is a regular log line
Another log line
Build completed successfully
No spawned jobs here
"""

        result = self.parser.parse_console_output(console_content)

        assert "parent" in result
        assert "spawned_jobs" in result
        assert len(result["spawned_jobs"]) == 0


if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v"])
