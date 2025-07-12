#!/usr/bin/env python3
"""
Test suite for get_console.py script.

This module contains comprehensive tests for the Jenkins console log retrieval script,
including unit tests for individual functions and integration tests for the CLI interface.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from click.testing import CliRunner

# Import the functions from get_console.py
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from scripts.get_console import (
    get_console_log,
    main,
    read_token_from_file,
    write_console_log,
)


class TestReadTokenFromFile:
    """Test cases for read_token_from_file function."""

    def test_read_token_from_file_success(self, tmp_path):
        """Test successful token reading from file."""
        token_file = tmp_path / "token.txt"
        token_content = "my-secret-token"
        token_file.write_text(token_content)

        result = read_token_from_file(token_file)
        assert result == token_content

    def test_read_token_from_file_with_whitespace(self, tmp_path):
        """Test token reading strips whitespace."""
        token_file = tmp_path / "token.txt"
        token_content = "  my-secret-token\n  "
        token_file.write_text(token_content)

        result = read_token_from_file(token_file)
        assert result == "my-secret-token"

    def test_read_token_from_file_not_found(self, tmp_path):
        """Test FileNotFoundError is raised when file doesn't exist."""
        token_file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            read_token_from_file(token_file)

    def test_read_token_from_file_permission_error(self, tmp_path):
        """Test exception handling for permission errors."""
        token_file = tmp_path / "token.txt"
        token_file.write_text("token")

        # Mock Path.read_text to raise PermissionError
        with patch.object(Path, "read_text", side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError):
                read_token_from_file(token_file)


class TestGetConsoleLog:
    """Test cases for get_console_log function."""

    @patch("requests.get")
    def test_get_console_log_success(self, mock_get):
        """Test successful console log retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Console log content"
        mock_get.return_value = mock_response

        result = get_console_log("https://ci.adoptium.net/", "testuser", "token123", "test-pipeline", 42)

        assert result == "Console log content"

        # Verify the URL construction
        expected_url = "https://ci.adoptium.net/job/test-pipeline/42/timestamps/?time=HH:mm:ss&timeZone=GMT-7&appendLog&locale=en_US"
        mock_get.assert_called_once()
        assert mock_get.call_args[0][0] == expected_url

    @patch("requests.get")
    def test_get_console_log_with_slashes_in_pipeline_name(self, mock_get):
        """Test console log retrieval with pipeline name containing slashes."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Console log content"
        mock_get.return_value = mock_response

        result = get_console_log(
            "https://ci.adoptium.net/", "testuser", "token123", "build-scripts/release-openjdk21-pipeline", 42
        )

        assert result == "Console log content"

        # Verify URL encoding of pipeline name with slashes
        expected_url = "https://ci.adoptium.net/job/build-scripts/release-openjdk21-pipeline/42/timestamps/?time=HH:mm:ss&timeZone=GMT-7&appendLog&locale=en_US"
        mock_get.assert_called_once()
        assert mock_get.call_args[0][0] == expected_url

    @patch("requests.get")
    def test_get_console_log_url_without_trailing_slash(self, mock_get):
        """Test URL handling when Jenkins URL doesn't end with slash."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Console log content"
        mock_get.return_value = mock_response

        get_console_log(
            "https://ci.adoptium.net",  # No trailing slash
            "testuser",
            "token123",
            "test-pipeline",
            42,
        )

        # Should still construct correct URL with slash added
        expected_url = "https://ci.adoptium.net/job/test-pipeline/42/timestamps/?time=HH:mm:ss&timeZone=GMT-7&appendLog&locale=en_US"
        mock_get.assert_called_once()
        assert mock_get.call_args[0][0] == expected_url

    @patch("requests.get")
    def test_get_console_log_authentication_failed(self, mock_get):
        """Test handling of authentication failure (401)."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError, match="Authentication failed"):
            get_console_log("https://ci.adoptium.net/", "testuser", "invalid-token", "test-pipeline", 42)

    @patch("requests.get")
    def test_get_console_log_pipeline_not_found(self, mock_get):
        """Test handling of pipeline not found (404)."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError, match="Pipeline run not found"):
            get_console_log("https://ci.adoptium.net/", "testuser", "token123", "nonexistent-pipeline", 42)

    @patch("requests.get")
    def test_get_console_log_server_error(self, mock_get):
        """Test handling of server errors (5xx)."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError, match="Failed to retrieve console log"):
            get_console_log("https://ci.adoptium.net/", "testuser", "token123", "test-pipeline", 42)

    @patch("requests.get")
    def test_get_console_log_connection_error(self, mock_get):
        """Test handling of connection errors."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with pytest.raises(requests.exceptions.ConnectionError):
            get_console_log("https://invalid-url.com/", "testuser", "token123", "test-pipeline", 42)

    @patch("requests.get")
    def test_get_console_log_timeout(self, mock_get):
        """Test handling of request timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        with pytest.raises(requests.exceptions.Timeout):
            get_console_log("https://ci.adoptium.net/", "testuser", "token123", "test-pipeline", 42)


class TestWriteConsoleLog:
    """Test cases for write_console_log function."""

    def test_write_console_log_success(self, tmp_path):
        """Test successful console log writing."""
        output_file = tmp_path / "console.log"
        console_content = "This is console log content\nLine 2\nLine 3"

        write_console_log(console_content, output_file)

        assert output_file.exists()
        assert output_file.read_text() == console_content

    def test_write_console_log_creates_directory(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        output_file = tmp_path / "logs" / "subdir" / "console.log"
        console_content = "Console log content"

        write_console_log(console_content, output_file)

        assert output_file.exists()
        assert output_file.read_text() == console_content
        assert output_file.parent.exists()

    def test_write_console_log_empty_content(self, tmp_path):
        """Test writing empty console log."""
        output_file = tmp_path / "empty.log"
        console_content = ""

        write_console_log(console_content, output_file)

        assert output_file.exists()
        assert output_file.read_text() == ""

    def test_write_console_log_unicode_content(self, tmp_path):
        """Test writing console log with unicode characters."""
        output_file = tmp_path / "unicode.log"
        console_content = "Console log with unicode: 🎉 ñ é ü"

        write_console_log(console_content, output_file)

        assert output_file.exists()
        assert output_file.read_text(encoding="utf-8") == console_content


class TestMainCLI:
    """Test cases for the main CLI interface."""

    def setup_method(self):
        """Set up test runner for each test."""
        self.runner = CliRunner()

    def test_help_output(self):
        """Test that help is displayed correctly."""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Pull console logs from Jenkins pipeline runs" in result.output
        assert "--pipeline-name" in result.output
        assert "--run-number" in result.output
        assert "--token" in result.output
        assert "--token-file" in result.output

    def test_missing_required_arguments(self):
        """Test CLI fails when required arguments are missing."""
        result = self.runner.invoke(main, [])
        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_mutually_exclusive_token_options_both_provided(self):
        """Test that providing both token options raises an error."""
        with self.runner.isolated_filesystem():
            # Create a temporary token file
            with open("token.txt", "w") as f:
                f.write("test-token")

            result = self.runner.invoke(
                main,
                [
                    "--token",
                    "direct-token",
                    "--token-file",
                    "token.txt",
                    "--pipeline-name",
                    "test-pipeline",
                    "--run-number",
                    "42",
                ],
            )
            assert result.exit_code != 0

    def test_no_token_provided(self):
        """Test that CLI fails when no token is provided."""
        result = self.runner.invoke(main, ["--pipeline-name", "test-pipeline", "--run-number", "42"])
        assert result.exit_code != 0

    def test_invalid_run_number(self):
        """Test that invalid run numbers are rejected."""
        result = self.runner.invoke(
            main,
            [
                "--token",
                "test-token",
                "--pipeline-name",
                "test-pipeline",
                "--run-number",
                "0",  # Invalid: must be positive
            ],
        )
        assert result.exit_code != 0

    def test_negative_run_number(self):
        """Test that negative run numbers are rejected."""
        result = self.runner.invoke(
            main,
            [
                "--token",
                "test-token",
                "--pipeline-name",
                "test-pipeline",
                "--run-number",
                "-1",  # Invalid: must be positive
            ],
        )
        assert result.exit_code != 0

    def test_nonexistent_token_file(self):
        """Test handling of nonexistent token file."""
        result = self.runner.invoke(
            main, ["--token-file", "nonexistent.txt", "--pipeline-name", "test-pipeline", "--run-number", "42"]
        )
        assert result.exit_code != 0

    @patch("get_console.get_console_log")
    def test_get_console_log_error_handling(self, mock_get):
        """Test handling of errors from get_console_log function."""
        mock_get.side_effect = requests.exceptions.HTTPError("Authentication failed")

        result = self.runner.invoke(
            main, ["--token", "invalid-token", "--pipeline-name", "test-pipeline", "--run-number", "42"]
        )

        assert result.exit_code != 0

    @patch("get_console.get_console_log")
    @patch("get_console.write_console_log")
    def test_write_console_log_error_handling(self, mock_write, mock_get):
        """Test handling of errors from write_console_log function."""
        mock_get.return_value = "Console log content"
        mock_write.side_effect = PermissionError("Permission denied")

        result = self.runner.invoke(
            main,
            [
                "--token",
                "test-token",
                "--pipeline-name",
                "test-pipeline",
                "--run-number",
                "42",
                "--output",
                "/root/readonly.log",  # Simulated permission error
            ],
        )

        assert result.exit_code != 0


class TestIntegration:
    """Integration tests that test multiple components together."""

    @patch("requests.get")
    def test_end_to_end_pipeline(self, mock_get, tmp_path):
        """Test complete pipeline from CLI to file output."""
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Sample console log output\nBuild completed successfully"
        mock_get.return_value = mock_response

        # Create token file
        token_file = tmp_path / "token.txt"
        token_file.write_text("my-api-token")

        # Create output file path
        output_file = tmp_path / "logs" / "console.log"

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "--url",
                "https://ci.adoptium.net/",
                "--username",
                "testuser",
                "--token-file",
                str(token_file),
                "--pipeline-name",
                "build-scripts/release-openjdk21-pipeline",
                "--run-number",
                "85",
                "--output",
                str(output_file),
            ],
        )

        # Verify successful execution
        assert result.exit_code == 0

        # Verify the HTTP request was made correctly
        mock_get.assert_called_once()
        called_url = mock_get.call_args[0][0]
        assert "build-scripts/release-openjdk21-pipeline/85" in called_url

        # Verify the output file was created with correct content
        assert output_file.exists()
        assert output_file.read_text() == "Sample console log output\nBuild completed successfully"


if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v"])
