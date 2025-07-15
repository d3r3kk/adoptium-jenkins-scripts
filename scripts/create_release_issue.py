#!/usr/bin/env python3
"""
Script to create GitHub release issues based on a template.

This script creates GitHub issues for JDK releases with a standardized format
including platform tables and status tracking.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import requests

# Set up logging
log = logging.getLogger(__name__)


@dataclass
class Platform:
    """Data class to represent a platform configuration."""

    name: str
    is_major: bool = False


class GitHubIssueCreator:
    """Creator for GitHub release issues."""

    def __init__(self, repo_owner: str, repo_name: str, token: str) -> None:
        """Initialize the GitHub issue creator.

        Args:
            repo_owner: GitHub repository owner/organization
            repo_name: GitHub repository name
            token: GitHub personal access token
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.token = token
        self.base_url = "https://api.github.com"

    def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a GitHub issue.

        Args:
            title: Issue title
            body: Issue body content
            labels: Optional list of labels to add to the issue

        Returns:
            Dictionary containing the created issue information

        Raises:
            requests.RequestException: If the GitHub API request fails
        """
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/issues"

        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

        data: Dict[str, Any] = {"title": title, "body": body}

        if labels:
            data["labels"] = labels

        log.info(f"Creating GitHub issue: {title}")
        log.debug(f"POST {url}")

        response = requests.post(url, json=data, headers=headers, timeout=30)

        if response.status_code == 201:
            issue_data = response.json()
            log.info(f"Successfully created issue #{issue_data['number']}: {issue_data['html_url']}")
            return issue_data
        else:
            log.error(f"Failed to create issue. Status: {response.status_code}")
            log.error(f"Response: {response.text}")
            response.raise_for_status()

        return {}


class ReleaseIssueTemplate:
    """Template generator for release issues."""

    # Default platform configurations - can be extended/customized
    DEFAULT_PLATFORMS = [
        Platform("Alpine Linux aarch64", is_major=True),
        Platform("Alpine Linux x64", is_major=False),
        Platform("Linux aarch64", is_major=True),
        Platform("Linux armv7l", is_major=False),
        Platform("Linux ppc64le", is_major=False),
        Platform("Linux s390x", is_major=False),
        Platform("Linux x64", is_major=True),
        Platform("macOS aarch64", is_major=True),
        Platform("macOS x64", is_major=True),
        Platform("Windows aarch64", is_major=False),
        Platform("Windows x64", is_major=True),
        Platform("Windows x86-32", is_major=False),
    ]

    def __init__(self, platforms: Optional[List[Platform]] = None) -> None:
        """Initialize the template generator.

        Args:
            platforms: Optional list of Platform objects. If None, uses default platforms.
        """
        self.platforms = platforms or self.DEFAULT_PLATFORMS

    def generate_title(self, month: str, year: str, version: str) -> str:
        """Generate the issue title.

        Args:
            month: Month name (e.g., "July")
            year: Year (e.g., "2025")
            version: JDK version (e.g., "21.0.4+7")

        Returns:
            Formatted issue title
        """
        return f"{month} {year} JDK: {version}"

    def generate_body(self, version: str) -> str:
        """Generate the issue body content.

        Args:
            version: JDK version (e.g., "21.0.4+7")

        Returns:
            Formatted issue body with platform table
        """
        # Extract major version number from version string
        major_version = self._extract_major_version(version)

        # Generate the platform table
        table_rows = []

        # Header row
        header = (
            f"| Platform            | JDK{major_version} | Status :white_check_mark: | Jenkins job Owner | "
            "Auto-manuals Owner | Interactives Owner | Build links | Results Comment Link |\n"
            "| ------------------- | ---------- | ----- | ----- | ----- | ----- | ----- | ----- |"
        )

        table_rows.append(header)

        # Platform rows
        for platform in self.platforms:
            if platform.is_major:
                # Major platform row
                row = f"| **{platform.name}**       | All        |  |  |  | run | JDK / JRE | Results |"
            else:
                # Minor platform row
                row = f"| {platform.name}         |   |  |  |  | skip | JDK / JRE | Results |"
            table_rows.append(row)

        # Combine everything
        body = f"### JDK{major_version}\n\n" + "\n".join(table_rows)

        return body

    def _extract_major_version(self, version: str) -> str:
        """Extract the major version number from a version string.

        Args:
            version: Version string like "21.0.4+7", "8u462-b06", etc.

        Returns:
            Major version number as string (e.g., "21", "8")
        """
        # Handle different version formats
        # Format: 21.0.4+7 -> 21
        # Format: 8u462-b06 -> 8
        # Format: 11.0.24+8 -> 11

        if match := re.match(r"^(\d+)", version):
            return match.group(1)

        # Fallback - if we can't parse it, return "X"
        log.warning(f"Could not extract major version from: {version}")
        return "X"


@click.command()
@click.option("--month", required=True, help="Release month name (e.g., 'July')")
@click.option("--year", required=True, help="Release year (e.g., '2025')")
@click.option("--version", required=True, help="JDK version (e.g., '21.0.4+7', '8u462-b06')")
@click.option("--repo-owner", required=True, help="GitHub repository owner/organization")
@click.option("--repo-name", required=True, help="GitHub repository name")
@click.option("--token", help="GitHub personal access token")
@click.option(
    "--token-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Path to file containing GitHub personal access token",
)
@click.option("--labels", help="Comma-separated list of labels to add to the issue")
@click.option("--dry-run", is_flag=True, help="Preview the issue without creating it")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
def main(
    month: str,
    year: str,
    version: str,
    repo_owner: str,
    repo_name: str,
    token: Optional[str],
    token_file: Optional[Path],
    labels: Optional[str],
    dry_run: bool,
    verbose: bool,
) -> None:
    """Create a GitHub release issue based on a template.

    Creates a standardized GitHub issue for JDK releases with platform tracking tables.

    \b
    Examples:
      create_release_issue.py --month July --year 2025 --version 21.0.4+7 \\
        --repo-owner adoptium --repo-name adoptium --token "ghp_..."
      create_release_issue.py --month October --year 2025 --version 8u462-b06 \\
        --repo-owner myorg --repo-name jdk-releases \\
        --token-file token.txt --labels "release,jdk8"
    """
    # Configure logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Validate token arguments
    if token and token_file:
        raise click.ClickException("--token and --token-file are mutually exclusive")

    if not token and not token_file:
        raise click.ClickException("Either --token or --token-file must be provided")

    # Get GitHub token
    if token_file:
        try:
            with open(token_file, encoding="utf-8") as f:
                github_token = f.read().strip()
        except Exception as e:
            raise click.ClickException(f"Failed to read token file: {e}") from e
    else:
        github_token = token or ""

    if not github_token:
        raise click.ClickException("GitHub token is empty")

    # Parse labels
    label_list: List[str] = []
    if labels:
        label_list = [label.strip() for label in labels.split(",") if label.strip()]

    try:
        # Generate issue content
        template = ReleaseIssueTemplate()
        issue_title = template.generate_title(month, year, version)
        issue_body = template.generate_body(version)

        log.info(f"Generated issue title: {issue_title}")
        log.debug(f"Generated issue body:\n{issue_body}")

        if dry_run:
            # Preview mode - just print the issue content
            print("\n=== DRY RUN: Preview of GitHub Issue ===")
            print(f"Repository: {repo_owner}/{repo_name}")
            print(f"Title: {issue_title}")
            if label_list:
                print(f"Labels: {', '.join(label_list)}")
            print(f"\nBody:\n{issue_body}")
            print("\n=== End of Preview ===")
            return

        # Create the GitHub issue
        creator = GitHubIssueCreator(repo_owner, repo_name, github_token)
        issue_data = creator.create_issue(issue_title, issue_body, label_list)

        print("\n✅ Successfully created GitHub issue!")
        print(f"📋 Issue #{issue_data['number']}: {issue_data['title']}")
        print(f"🔗 URL: {issue_data['html_url']}")

        if label_list:
            print(f"🏷️  Labels: {', '.join(label_list)}")

    except requests.RequestException as e:
        log.error(f"GitHub API error: {e}")
        raise click.ClickException(f"Failed to create GitHub issue: {e}") from e
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        raise click.ClickException(f"Script failed: {e}") from e


if __name__ == "__main__":
    main()
