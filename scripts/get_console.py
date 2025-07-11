#!/usr/bin/env python3
"""
get_console.py - A script to pull console logs from Jenkins pipeline runs.

This script connects to a Jenkins server and retrieves console logs for a specific
pipeline run, then saves them to an output file.

Usage:
    python get_console.py --pipeline-name "release-openjdk21-pipeline" --run-number 48 --output console.log
    python get_console.py --token-file token.txt --url https://ci.adoptium.net/ --pipeline-name "build-scripts/release-openjdk21-pipeline" --run-number 48 --output logs/console_48.log
"""  # noqa: E501

import logging
from pathlib import Path
from urllib.parse import quote, urljoin

import click
import requests
from requests.auth import HTTPBasicAuth

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def read_token_from_file(token_file_path: Path) -> str:
    """Read Jenkins API token from a file."""
    try:
        return token_file_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        log.error(f"Error: Token file '{token_file_path}' not found.")
        raise
    except Exception as e:
        log.error(f"Error reading token file '{token_file_path}': {e}")
        raise


def get_console_log(jenkins_url: str, username: str, api_token: str, pipeline_name: str, run_number: int) -> str:
    """Retrieve console log from Jenkins pipeline run."""
    # Ensure jenkins_url ends with /
    if not jenkins_url.endswith("/"):
        jenkins_url += "/"

    # URL encode the pipeline name to handle special characters and slashes
    pipeline_parts = pipeline_name.split("/")
    encoded_parts = [quote(part, safe="") for part in pipeline_parts]
    encoded_pipeline = "/".join(encoded_parts)

    # Construct the console log URL
    # A full URL that we want to see looks like:
    # https://ci.adoptium.net/job/build-scripts/job/release-openjdk8-pipeline/85/console
    console_url = urljoin(
        jenkins_url,
        f"job/{encoded_pipeline}/{run_number}/timestamps/?time=HH:mm:ss&timeZone=GMT-7&appendLog&locale=en_US",
    )

    log.info(f"Attempting to retrieve console log from: {console_url}")

    try:
        # Make request with authentication
        response = requests.get(console_url, auth=HTTPBasicAuth(username, api_token), timeout=60)

        # Check if request was successful
        if response.status_code == 200:
            return response.text
        elif response.status_code == 401:
            raise requests.exceptions.HTTPError("Authentication failed. Please check your username and API token.")
        elif response.status_code == 404:
            raise requests.exceptions.HTTPError(
                f"Pipeline run not found. Please check that pipeline name '{pipeline_name}' and run "
                f"number '{run_number}' are correct."
            )
        else:
            raise requests.exceptions.HTTPError(
                f"Failed to retrieve console log. HTTP status code: {response.status_code}\nResponse: {response.text}"
            )

    except requests.exceptions.ConnectionError:
        log.error(f"Unable to connect to Jenkins server at '{jenkins_url}'. Please check the URL.")
        raise
    except requests.exceptions.Timeout:
        log.error("Request timed out. The Jenkins server may be slow to respond.")
        raise
    except requests.exceptions.RequestException as e:
        log.error(f"Request failed: {e}")
        raise


def write_console_log(console_log: str, output_file: Path) -> None:
    """Write console log content to output file."""
    try:
        # Create output directory if it doesn't exist
        output_dir = output_file.parent
        if output_dir and not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(console_log)

        log.info(f"Console log successfully written to: {output_file}")
        log.info(f"File size: {len(console_log.encode('utf-8'))} bytes")

    except Exception as e:
        log.error(f"Error writing to output file '{output_file}': {e}")
        raise


@click.command()
@click.option(
    "--url",
    default="https://ci.adoptium.net/",
    help="Jenkins server URL",
    show_default=True,
)
@click.option(
    "--username",
    default="anonymous",
    help="Jenkins username",
    show_default=True,
)
@click.option(
    "--token",
    help="Jenkins API token as string",
)
@click.option(
    "--token-file",
    type=click.Path(exists=True),
    path_type=Path,
    help="Path to file containing Jenkins API token",
)
@click.option(
    "--pipeline-name",
    required=True,
    help='Pipeline name (e.g., "release-openjdk21-pipeline" or "build-scripts/release-openjdk21-pipeline")',
)
@click.option(
    "--run-number",
    type=int,
    required=True,
    help="Pipeline run number (e.g., 48)",
)
@click.option(
    "--output",
    required=False,
    type=click.Path(),
    path_type=Path,
    default="output.log",
    help="Output file path/name for console log. Defaults to 'output.log'.",
)
def main(
    url: str,
    username: str,
    token: str,
    token_file: Path,
    pipeline_name: str,
    run_number: int,
    output: Path,
) -> None:
    """Pull console logs from Jenkins pipeline runs.

    \b
    Examples:
      python get_console.py --pipeline-name "release-openjdk21-pipeline" --run-number 48 --output console.log
      python get_console.py --token-file token.txt --pipeline-name "build-scripts/release-openjdk21-pipeline" \\
          --run-number 48 --output logs/console_48.log
      python get_console.py --token "your-api-token" --username jenkins-user --url https://ci.adoptium.net/ \\
          --pipeline-name "release-openjdk21-pipeline" --run-number 48
    """
    # Validate that either token or token-file is provided (mutually exclusive)
    if not token and not token_file:
        raise ValueError("Either --token or --token-file must be provided.")

    if token and token_file:
        raise ValueError("--token and --token-file are mutually exclusive.")

    # Get API token
    if token:
        api_token = token
    else:
        api_token = read_token_from_file(token_file)

    # Validate inputs
    if not api_token:
        raise ValueError("API token is empty.")

    if run_number < 1:
        raise ValueError("Run number must be a positive integer.")

    # Retrieve console log
    log.info(f"Connecting to Jenkins server: {url}")
    log.info(f"Pipeline: {pipeline_name}")
    log.info(f"Run number: {run_number}")
    log.info(f"Output file: {output}")
    log.info("")

    console_log = get_console_log(url, username, api_token, pipeline_name, run_number)

    # Write to output file
    write_console_log(console_log, output)


if __name__ == "__main__":
    main()
