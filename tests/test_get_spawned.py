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

from scripts.get_spawned import JenkinsConsoleParser, load_job_platforms_config


class TestJenkinsConsoleParser:
    """Test cases for JenkinsConsoleParser class."""

    def setup_method(self):
        """Set up test parser for each test."""
        self.parser = JenkinsConsoleParser()

    def test_empty_console_output(self):
        """Test handling of empty console output."""
        console_content = ""
        job_platforms = {}

        result = self.parser.parse_console_output(console_content, job_platforms)

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
        job_platforms = {}

        result = self.parser.parse_console_output(console_content, job_platforms)

        assert "parent" in result
        assert "spawned_jobs" in result
        assert len(result["spawned_jobs"]) == 0

    def test_config_loading(self):
        """Test loading of job platform configuration."""
        config_path = Path(__file__).parent.parent / "config" / "jobs-platform-info.json"
        
        job_platforms = load_job_platforms_config(config_path)
        
        assert isinstance(job_platforms, dict)
        assert len(job_platforms) > 0
        
        # Test specific job entries from the config
        assert "jdk21u-release-alpine-linux-aarch64-temurin" in job_platforms
        assert job_platforms["jdk21u-release-alpine-linux-aarch64-temurin"]["os"] == "alpine-linux"
        assert job_platforms["jdk21u-release-alpine-linux-aarch64-temurin"]["arch"] == "aarch64"
        assert job_platforms["jdk21u-release-alpine-linux-aarch64-temurin"]["jdk"] == "jdk21"

    def test_spawned_job_extraction_with_config(self):
        """Test parsing console output with spawned jobs using config-based lookup."""
        console_content = '''Starting building: <a href="/path/to/jdk21u-release-alpine-linux-aarch64-temurin/42/">jdk21u-release-alpine-linux-aarch64-temurin #42</a>'''
        
        job_platforms = {
            "jdk21u-release-alpine-linux-aarch64-temurin": {
                "os": "alpine-linux",
                "arch": "aarch64", 
                "jdk": "jdk21"
            }
        }

        result = self.parser.parse_console_output(console_content, job_platforms)

        assert "spawned_jobs" in result
        assert len(result["spawned_jobs"]) == 1
        
        job_key = "jdk21u-release-alpine-linux-aarch64-temurin"
        assert job_key in result["spawned_jobs"]
        
        spawned_job = result["spawned_jobs"][job_key]
        assert spawned_job.os == "alpine-linux"
        assert spawned_job.arch == "aarch64"
        assert spawned_job.jdk == "jdk21"
        assert spawned_job.number == "42"

    def test_spawned_job_not_in_config(self):
        """Test that jobs not in config are skipped."""
        console_content = '''Starting building: <a href="/path/to/unknown-job-name/42/">unknown-job-name #42</a>'''
        
        job_platforms = {
            "jdk21u-release-alpine-linux-aarch64-temurin": {
                "os": "alpine-linux",
                "arch": "aarch64", 
                "jdk": "jdk21"
            }
        }

        result = self.parser.parse_console_output(console_content, job_platforms)

        assert "spawned_jobs" in result
        assert len(result["spawned_jobs"]) == 0


if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v"])
