#!/usr/bin/env python3
"""
get_console.py - A script to pull console logs from Jenkins pipeline runs.

This script connects to a Jenkins server and retrieves console logs for a specific
pipeline run, then saves them to an output file.

Usage:
    python get_console.py --pipeline-name "release-openjdk21-pipeline" --run-number 48 --output console.log
    python get_console.py --token-file token.txt --url https://ci.adoptium.net/ --pipeline-name "build-scripts/release-openjdk21-pipeline" --run-number 48 --output logs/console_48.log
"""  # noqa: E501

import argparse
import os
import sys
from urllib.parse import quote, urljoin

import requests
from requests.auth import HTTPBasicAuth


def read_token_from_file(token_file_path):
    """Read Jenkins API token from a file."""
    try:
        with open(token_file_path, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Error: Token file '{token_file_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading token file '{token_file_path}': {e}", file=sys.stderr)
        sys.exit(1)


def get_console_log(jenkins_url, username, api_token, pipeline_name, run_number):
    """Retrieve console log from Jenkins pipeline run."""
    # Ensure jenkins_url ends with /
    if not jenkins_url.endswith("/"):
        jenkins_url += "/"

    # URL encode the pipeline name to handle special characters and slashes
    pipeline_parts = pipeline_name.split("/")
    encoded_parts = [quote(part, safe="") for part in pipeline_parts]
    encoded_pipeline = "/".join(encoded_parts)

    # Construct the console log URL
    console_url = urljoin(jenkins_url, f"job/{encoded_pipeline}/{run_number}/consoleText")

    print(f"Attempting to retrieve console log from: {console_url}")

    try:
        # Make request with authentication
        response = requests.get(console_url, auth=HTTPBasicAuth(username, api_token), timeout=60)

        # Check if request was successful
        if response.status_code == 200:
            return response.text
        elif response.status_code == 401:
            print(
                "Error: Authentication failed. Please check your username and API token.",
                file=sys.stderr,
            )
            sys.exit(1)
        elif response.status_code == 404:
            print(
                f"Error: Pipeline run not found. Please check that pipeline name '{pipeline_name}' and run "
                f"number '{run_number}' are correct.",
                file=sys.stderr,
            )
            sys.exit(1)
        else:
            print(
                f"Error: Failed to retrieve console log. HTTP status code: {response.status_code}",
                file=sys.stderr,
            )
            print(f"Response: {response.text}", file=sys.stderr)
            sys.exit(1)

    except requests.exceptions.ConnectionError:
        print(
            f"Error: Unable to connect to Jenkins server at '{jenkins_url}'. Please check the URL.",
            file=sys.stderr,
        )
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(
            "Error: Request timed out. The Jenkins server may be slow to respond.",
            file=sys.stderr,
        )
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error: Request failed: {e}", file=sys.stderr)
        sys.exit(1)


def write_console_log(console_log, output_file):
    """Write console log content to output file."""
    try:
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(console_log)

        print(f"Console log successfully written to: {output_file}")
        print(f"File size: {len(console_log.encode('utf-8'))} bytes")

    except Exception as e:
        print(f"Error writing to output file '{output_file}': {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main function to parse arguments and execute console log retrieval."""
    parser = argparse.ArgumentParser(
        description="Pull console logs from Jenkins pipeline runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --pipeline-name "release-openjdk21-pipeline" --run-number 48 --output console.log
  %(prog)s --token-file token.txt --pipeline-name "build-scripts/release-openjdk21-pipeline" --run-number 48 --output logs/console_48.log
  %(prog)s --token "your-api-token" --username jenkins-user --url https://ci.adoptium.net/ --pipeline-name "release-openjdk21-pipeline" --run-number 48 --output console.log
        """,  # noqa: E501
    )

    # Jenkins server configuration
    parser.add_argument(
        "--url",
        default="https://ci.adoptium.net/",
        help="Jenkins server URL (default: https://ci.adoptium.net/)",
    )

    parser.add_argument("--username", default="anonymous", help="Jenkins username (default: anonymous)")

    # Authentication options (mutually exclusive)
    auth_group = parser.add_mutually_exclusive_group(required=True)
    auth_group.add_argument("--token", help="Jenkins API token as string")
    auth_group.add_argument("--token-file", help="Path to file containing Jenkins API token")

    # Pipeline identification
    parser.add_argument(
        "--pipeline-name",
        required=True,
        help=('Pipeline name (e.g., "release-openjdk21-pipeline" or "build-scripts/release-openjdk21-pipeline")'),
    )

    parser.add_argument("--run-number", type=int, required=True, help="Pipeline run number (e.g., 48)")

    # Output configuration
    parser.add_argument("--output", required=True, help="Output file path/name for console log")

    args = parser.parse_args()

    # Get API token
    if args.token:
        api_token = args.token
    else:
        api_token = read_token_from_file(args.token_file)

    # Validate inputs
    if not api_token:
        print("Error: API token is empty.", file=sys.stderr)
        sys.exit(1)

    if args.run_number < 1:
        print("Error: Run number must be a positive integer.", file=sys.stderr)
        sys.exit(1)

    # Retrieve console log
    print(f"Connecting to Jenkins server: {args.url}")
    print(f"Pipeline: {args.pipeline_name}")
    print(f"Run number: {args.run_number}")
    print(f"Output file: {args.output}")
    print()

    console_log = get_console_log(args.url, args.username, api_token, args.pipeline_name, args.run_number)

    # Write to output file
    write_console_log(console_log, args.output)


if __name__ == "__main__":
    main()
