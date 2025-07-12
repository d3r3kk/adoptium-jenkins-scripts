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

    def test_extract_job_trigger_starting_building_format(self):
        """Test extraction of job trigger information from 'Starting building:' format."""
        line = (
            "10:26:11  Starting building: build-scripts » jobs » release » jobs » jdk8u » "
            "jdk8u-release-linux-ppc64le-temurin #16"
        )

        result = self.parser._extract_job_trigger(line)

        assert result is not None
        assert result["name"] == "build-scripts/jobs/release/jobs/jdk8u/jdk8u-release-linux-ppc64le-temurin"
        assert result["build_number"] == "16"
        assert result["url"] is None
        assert result["result"] is None

    def test_extract_job_trigger_multiple_starting_building_lines(self):
        """Test extraction from multiple 'Starting building:' lines."""
        lines = [
            (
                "10:26:11  Starting building: build-scripts » jobs » release » jobs » jdk8u » "
                "jdk8u-release-linux-ppc64le-temurin #16"
            ),
            (
                "10:26:11  Starting building: build-scripts » jobs » release » jobs » jdk8u » "
                "jdk8u-release-linux-aarch64-temurin #17"
            ),
            (
                "10:26:12  Starting building: build-scripts » jobs » release » jobs » jdk8u » "
                "jdk8u-release-alpine-linux-x64-temurin #19"
            ),
        ]

        results = []
        for line in lines:
            result = self.parser._extract_job_trigger(line)
            if result:
                results.append(result)

        assert len(results) == 3
        assert results[0]["name"] == "build-scripts/jobs/release/jobs/jdk8u/jdk8u-release-linux-ppc64le-temurin"
        assert results[0]["build_number"] == "16"
        assert results[1]["name"] == "build-scripts/jobs/release/jobs/jdk8u/jdk8u-release-linux-aarch64-temurin"
        assert results[1]["build_number"] == "17"
        assert results[2]["name"] == "build-scripts/jobs/release/jobs/jdk8u/jdk8u-release-alpine-linux-x64-temurin"
        assert results[2]["build_number"] == "19"

    def test_extract_job_trigger_legacy_format_still_works(self):
        """Test that legacy job trigger formats still work."""
        line = "Starting build job my-pipeline-job #42"

        result = self.parser._extract_job_trigger(line)

        assert result is not None
        assert result["name"] == "my-pipeline-job"
        assert result["build_number"] == "42"

    def test_extract_job_trigger_no_match(self):
        """Test that lines without job triggers return None."""
        line = "This is just a regular log line with no job trigger information"

        result = self.parser._extract_job_trigger(line)

        assert result is None

    def test_parse_console_output_with_starting_building_format(self):
        """Test complete console output parsing with 'Starting building:' format."""
        console_content = """
10:26:11  Starting building: build-scripts » jobs » release » jobs » jdk8u » jdk8u-release-linux-ppc64le-temurin #16
10:26:11  Starting building: build-scripts » jobs » release » jobs » jdk8u » jdk8u-release-linux-aarch64-temurin #17
10:26:11  Starting building: build-scripts » jobs » release » jobs » jdk8u » jdk8u-release-aix-ppc64-temurin #16
Some other log line
10:26:12  Starting building: build-scripts » jobs » release » jobs » jdk8u » jdk8u-release-alpine-linux-x64-temurin #19
"""

        result = self.parser.parse_console_output(console_content)

        assert "parent" in result
        assert "spawned_jobs" in result
        assert len(result["spawned_jobs"]) == 4

        # Check specific job details
        spawned_jobs = result["spawned_jobs"]
        job_names = [job["name"] for job in spawned_jobs]

        expected_names = [
            "build-scripts/jobs/release/jobs/jdk8u/jdk8u-release-linux-ppc64le-temurin",
            "build-scripts/jobs/release/jobs/jdk8u/jdk8u-release-linux-aarch64-temurin",
            "build-scripts/jobs/release/jobs/jdk8u/jdk8u-release-aix-ppc64-temurin",
            "build-scripts/jobs/release/jobs/jdk8u/jdk8u-release-alpine-linux-x64-temurin",
        ]

        for expected_name in expected_names:
            assert expected_name in job_names

    def test_pipeline_name_separator_replacement(self):
        """Test that ' » ' is correctly replaced with '/' in pipeline names."""
        line = "10:26:11  Starting building: very » long » pipeline » name » with » many » parts #123"

        result = self.parser._extract_job_trigger(line)

        assert result is not None
        assert result["name"] == "very/long/pipeline/name/with/many/parts"
        assert result["build_number"] == "123"

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
