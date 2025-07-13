#!/usr/bin/env python3
"""
Script to extract spawned pipeline jobs from Jenkins console output.

This script parses Jenkins console output to find pipeline jobs that were
spawned during a pipeline run, extracting information like pipeline name,
run number, URL, and result status.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

# String patterns to use to match parent pipeline information in the console output.
PARENT_PIPELINE_START_PATTERN = "Started by upstream project "
PARENT_PIPELINE_EXTRA_MATCH_PHRASE = "build number"


@dataclass
class SpawnedJob:
    """Data class to represent a spawned job."""

    text: str
    number: str
    os: str
    arch: str
    jdk: str
    url: Optional[str] = None
    result: Optional[str] = None


class SpawnedJobEncoder(json.JSONEncoder):
    """Custom JSON encoder for SpawnedJob objects."""

    def default(self, o: Any) -> Any:
        if isinstance(o, SpawnedJob):
            return {
                "text": o.text,
                "number": o.number,
                "os": o.os,
                "arch": o.arch,
                "jdk": o.jdk,
                "url": o.url,
                "result": o.result,
            }
        return super().default(o)


class JenkinsConsoleParser:
    """Parser for Jenkins console output to extract spawned pipeline information."""

    def extract_spawned_jobs(self, lines: List[str]) -> Dict[str, SpawnedJob]:
        # Regex to match strings containing 'jdk[number]u', 'release', and 'temurin'
        spawns = [line for line in lines if "Starting building: " in line]

        spawned_jobs: Dict[str, SpawnedJob] = {}

        for line in spawns:
            lparsed = BeautifulSoup(line, "html.parser")
            if _link := lparsed.find_all("a", href=True):
                # It will be the first (and only) link in the line that we are interested in.
                link = _link[0]
                print(f"Finding spawned job information for line: {line}")
                extracted_jobname = [n for n in link.get("href").split("/") if "-release-" in n and "-temurin" in n]
                if len(extracted_jobname) == 1:
                    spawn_jobname = extracted_jobname[0]
                    print(f"  Found Job Name: {spawn_jobname}")
                    spawn_text = link.text
                    spawn_url = link.get("href", "")
                    spawn_jobnum = link.text.split("#")[1]
                    plat_info = spawn_jobname.split("-")
                    spawn_jdk = plat_info[0]
                    spawn_os = plat_info[2]
                    spawn_arch = "-".join(plat_info[3:-1])
                    spawned_jobs[spawn_jobname] = SpawnedJob(
                        text=spawn_text,
                        number=spawn_jobnum,
                        os=spawn_os,
                        arch=spawn_arch,
                        jdk=spawn_jdk,
                        url=spawn_url,
                        result=None,  # Result will be filled later if available
                    )
                else:
                    print("not a job we are interested in")

        return spawned_jobs

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
        parent_info = self.extract_parent_info(lines)

        # Extract spawned jobs information
        spawned_jobs = self.extract_spawned_jobs(lines)

        return {"parent": parent_info, "spawned_jobs": spawned_jobs}

    def extract_parent_info(self, lines: List[str]) -> Dict[str, Any]:
        """Extract information about the parent pipeline."""
        parent_info = {
            "pipeline_name": "Unknown",
            "pipeline_url": "",
            "build_number": "Unknown",
            "build_url": "",
        }

        # Look for the lines that contain "Started by upstream project", and
        # keep only the content after that phrase from each line.
        parent_lines = [
            line[line.find(PARENT_PIPELINE_START_PATTERN) + len(PARENT_PIPELINE_START_PATTERN) :]
            for line in lines
            if PARENT_PIPELINE_START_PATTERN in line and PARENT_PIPELINE_EXTRA_MATCH_PHRASE in line
        ]

        for line in parent_lines:
            # There should only be one parent pipeline info line, near the top. The line will look like:
            # Started by upstream project "path/to/job-name" build number 1234
            lparse = BeautifulSoup(line, "html.parser")
            links = lparse.find_all("a", href=True)
            if len(links) == 2:
                parent_info["pipeline_name"] = links[0].text.strip()
                parent_info["pipeline_url"] = links[0].get("href", "")
                parent_info["build_number"] = links[1].text.strip()
                parent_info["build_url"] = links[1].get("href", "")
            break

        return parent_info

    def extract_job_results(self, lines: List[str], jobs: List[SpawnedJob]) -> Optional[Dict[str, Any]]:
        """For each spawned job, find the result in the lines and update the job."""
        pass


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

    parser.add_argument("-o", "--output", required=True, type=str, help="Path for the output JSON file")

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
            json.dump(result, f, indent=2, ensure_ascii=False, cls=SpawnedJobEncoder)

        print(f"Successfully parsed console output and saved results to '{args.output}'")
        print(f"Found {len(result['spawned_jobs'])} spawned jobs")

    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
