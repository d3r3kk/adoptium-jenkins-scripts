#!/usr/bin/env python3
"""
Script to extract spawned pipeline jobs from Jenkins console output.

This script parses Jenkins console output to find pipeline jobs that were
spawned during a pipeline run, extracting information like pipeline name,
run number, URL, and result status.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


class JenkinsConsoleParser:
    """Parser for Jenkins console output to extract spawned pipeline information."""

    def __init__(self) -> None:
        # Common patterns for Jenkins pipeline job triggers and results
        self.patterns = {
            # Pattern for pipeline job triggers (various formats)
            "job_trigger": [
                r"Starting build job (\S+) #(\d+)",
                r"Triggering downstream project (\S+)",
                r"Scheduling project: (\S+)",
                r"Build (\S+) #(\d+) started",
                r"(\S+) #(\d+) started",
            ],
            # Pattern for job URLs
            "job_url": [
                r"(https?://[^\s]+/job/[^/\s]+/\d+)/?",
                r"Console output: (https?://[^\s]+/job/[^/\s]+/\d+)",
            ],
            # Pattern for job results
            "job_result": [
                r"(\S+) #(\d+) completed: (\w+)",
                r"Finished: (\w+)",
                r"Build (\S+) #(\d+) completed with result (\w+)",
                r"(\S+) #(\d+): (\w+)",
            ],
            # Pattern for parent pipeline information
            "parent_info": [
                r'Started by upstream project "([^"]+)" build number (\d+)',
                r"Running on (.+)",
                r"Pipeline: (.+)",
            ],
        }

    def parse_console_output(self, console_content: str) -> Dict[str, Any]:
        """
        Parse Jenkins console output to extract spawned pipeline information.

        Args:
            console_content: The content of the Jenkins console output

        Returns:
            Dictionary containing parent pipeline info and spawned jobs
        """
        lines = console_content.split("\n")

        # Extract parent pipeline information
        parent_info = self._extract_parent_info(lines)

        # Extract spawned jobs information
        spawned_jobs = self._extract_spawned_jobs(lines)

        return {"parent": parent_info, "spawned_jobs": spawned_jobs}

    def _extract_parent_info(self, lines: List[str]) -> Dict[str, Any]:
        """Extract information about the parent pipeline."""
        parent_info = {
            "name": "Unknown",
            "build_number": "Unknown",
            "url": None,
            "node": None,
        }

        for line in lines:
            # Look for parent pipeline indicators
            for pattern in self.patterns["parent_info"]:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    if "upstream project" in pattern:
                        parent_info["name"] = match.group(1)
                        parent_info["build_number"] = match.group(2)
                    elif "Running on" in pattern:
                        parent_info["node"] = match.group(1)
                    elif "Pipeline" in pattern:
                        parent_info["name"] = match.group(1)

        return parent_info

    def _extract_spawned_jobs(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract information about spawned jobs from console output."""
        jobs_dict = {}  # To track jobs by name and build number

        for line in lines:
            # Look for job triggers
            job_info = self._extract_job_trigger(line)
            if job_info:
                job_name = job_info["name"]
                build_number = job_info.get("build_number", "unknown")
                job_key = f"{job_name}#{build_number}"

                # Initialize or update job entry
                if job_key not in jobs_dict:
                    jobs_dict[job_key] = {
                        "name": job_name,
                        "build_number": build_number,
                        "url": None,
                        "result": None,
                    }

            # Look for job URLs
            url = self._extract_job_url(line)
            if url:
                # Try to extract job name and build number from URL
                url_match = re.search(r"/job/([^/]+)/(\d+)", url)
                if url_match:
                    job_name = url_match.group(1)
                    build_number = url_match.group(2)
                    job_key = f"{job_name}#{build_number}"
                    if job_key in jobs_dict:
                        jobs_dict[job_key]["url"] = url
                    else:
                        # Create new entry if not found
                        jobs_dict[job_key] = {
                            "name": job_name,
                            "build_number": build_number,
                            "url": url,
                            "result": None,
                        }

            # Look for job results
            result_info = self._extract_job_result(line)
            if (
                result_info
                and result_info.get("name")
                and result_info.get("build_number")
            ):
                job_name = result_info["name"]
                build_number = result_info["build_number"]
                job_key = f"{job_name}#{build_number}"

                if job_key in jobs_dict:
                    jobs_dict[job_key]["result"] = result_info["result"]
                else:
                    # Create new entry if not found
                    jobs_dict[job_key] = {
                        "name": job_name,
                        "build_number": build_number,
                        "url": None,
                        "result": result_info["result"],
                    }

        # Convert dict to list and filter out jobs with unknown build numbers
        # if better entries exist
        spawned_jobs = []
        processed_names = set()

        # First pass: add jobs with known build numbers
        for _job_key, job_info in jobs_dict.items():
            if job_info["build_number"] != "unknown":
                spawned_jobs.append(job_info)
                processed_names.add(job_info["name"])

        # Second pass: add jobs with unknown build numbers only if no better
        # entry exists
        for _job_key, job_info in jobs_dict.items():
            if (
                job_info["build_number"] == "unknown"
                and job_info["name"] not in processed_names
            ):
                spawned_jobs.append(job_info)

        return spawned_jobs

    def _extract_job_trigger(self, line: str) -> Optional[Dict[str, Any]]:
        """Extract job trigger information from a line."""
        for pattern in self.patterns["job_trigger"]:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                job_info = {"name": match.group(1)}
                if len(match.groups()) > 1 and match.group(2):
                    job_info["build_number"] = match.group(2)
                job_info["url"] = None
                job_info["result"] = None
                return job_info
        return None

    def _extract_job_url(self, line: str) -> Optional[str]:
        """Extract job URL from a line."""
        for pattern in self.patterns["job_url"]:
            match = re.search(pattern, line)
            if match:
                return match.group(1)
        return None

    def _extract_job_result(self, line: str) -> Optional[Dict[str, Any]]:
        """Extract job result information from a line."""
        for pattern in self.patterns["job_result"]:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 3:
                    return {
                        "name": groups[0],
                        "build_number": groups[1],
                        "result": groups[2],
                        "url": None,
                    }
                elif len(groups) == 1:
                    return {"result": groups[0]}
        return None


def main() -> None:
    """Main function to handle command line arguments and execute the script."""
    parser = argparse.ArgumentParser(
        description="Extract spawned pipeline jobs from Jenkins console output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i console_output.txt -o spawned_jobs.json
  %(prog)s --input /path/to/console.txt --output /path/to/output.json
        """,
    )

    parser.add_argument(
        "-i",
        "--input",
        required=True,
        type=str,
        help="Path to the Jenkins console output file",
    )

    parser.add_argument(
        "-o", "--output", required=True, type=str, help="Path for the output JSON file"
    )

    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{args.input}' does not exist.", file=sys.stderr)
        sys.exit(1)

    if not input_path.is_file():
        print(f"Error: '{args.input}' is not a file.", file=sys.stderr)
        sys.exit(1)

    # Create output directory if it doesn't exist
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Read console output
        with open(input_path, encoding="utf-8") as f:
            console_content = f.read()

        # Parse console output
        console_parser = JenkinsConsoleParser()
        result = console_parser.parse_console_output(console_content)

        # Write JSON output
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(
            f"Successfully parsed console output and saved results to '{args.output}'"
        )
        print(f"Found {len(result['spawned_jobs'])} spawned jobs")

    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
