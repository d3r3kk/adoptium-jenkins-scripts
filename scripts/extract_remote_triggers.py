#!/usr/bin/env python3
"""
Script to extract remote trigger information from Jenkins HTML log files.

This script parses Jenkins HTML console output to find remote trigger configurations,
extracting information about job names, parameters, remote Jenkins instances, and
trigger settings.
"""

import json
import logging
import pprint
import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

import click
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

__VERSION__ = "1.0.0"


# String patterns to use to discover the remote trigger parameters and job details with.
REMOTE_TRIGGER_JOB_PATTERN = "- job:"
REMOTE_TRIGGER_REMOTE_JENKINS_NAME_PATTERN = "- remoteJenkinsName:"
REMOTE_TRIGGER_PARAMETERS_PATTERN = "- parameters:"
REMOTE_TRIGGER_BLOCK_BUILD_UNTIL_COMPLETE_PATTERN = "- blockBuildUntilComplete:"
REMOTE_TRIGGER_CONNECTION_RETRY_LIMIT_PATTERN = "- connectionRetryLimit:"
REMOTE_TRIGGER_TRUST_ALL_CERTIFICATES_PATTERN = "- trustAllCertificates:"
REMOTE_TRIGGER_REMOTE_JOB_URL_PATTERN = "Triggering parameterized remote job"

# Parameter names that we want to extract from the remote trigger configuration.
REMOTE_TRIGGER_PARAMETER_KEYS = [
    "SDK_RESOURCE",
    "CUSTOMIZED_SDK_URL",
    "PLATFORMS",
    "cause",
    "APPLICATION_OPTIONS",
    "NUM_MACHINES",
    "AUTO_AQA_GEN",
    "RERUN_FAILURE",
    "LABEL_ADDITION",
    "PIPELINE_DISPLAY_NAME",
    "RERUN_ITERATIONS",
    "SETUP_JCK_RUN",
    "TARGETS",
    "EXTRA_OPTIONS",
    "JCK_GIT_REPO",
    "JDK_VERSIONS",
    "PARALLEL",
]

# Filter BeautifulSoup warnings for URL-like strings
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")
log = logging.getLogger(__name__)


@dataclass
class RemoteTrigger:
    """Data class to represent a remote trigger configuration."""

    job_name: str
    remote_jenkins_name: str
    parameters: Dict[str, Any]
    remote_job_url: str
    block_build_until_complete: Optional[bool] = None
    connection_retry_limit: Optional[int] = None
    trust_all_certificates: Optional[bool] = None


class RemoteTriggerEncoder(json.JSONEncoder):
    """Custom JSON encoder for RemoteTrigger objects."""

    def default(self, o: Any) -> Any:
        if isinstance(o, RemoteTrigger):
            return {
                "job_name": o.job_name,
                "remote_jenkins_name": o.remote_jenkins_name,
                "parameters": o.parameters,
                "block_build_until_complete": o.block_build_until_complete,
                "connection_retry_limit": o.connection_retry_limit,
                "trust_all_certificates": o.trust_all_certificates,
                "remote_job_url": o.remote_job_url,
            }
        return super().default(o)


class JenkinsLogParser:
    """Parser for Jenkins HTML log files to extract remote trigger information."""

    def extract_remote_trigger_segments(self, lines: List[str]) -> List[List[str]]:
        current_segment = []
        consuming = False
        segments = []

        # Capture segments of lines between the start of a remote trigger and the execution of that trigger.
        for line in lines:
            if consuming:
                current_segment.append(line.strip())
                consuming = "Triggering parameterized remote job" not in line
                if not consuming:
                    segments.append(current_segment)
                    current_segment = []
            elif "Parameterized Remote Trigger Configuration:" in line:
                # capture this line, but only from the end of the phrase "Parameterized Remote Trigger Configuration:"
                start_index = line.index("Parameterized Remote Trigger Configuration:") + len(
                    "Parameterized Remote Trigger Configuration:"
                )
                current_segment = [line[start_index:].strip()]
                consuming = True

        return segments

    def parse_html_log(self, html_content: str) -> List[RemoteTrigger]:
        """
        Parse Jenkins HTML log content to extract remote trigger information.

        Args:
            html_content: The content of the Jenkins HTML log file

        Returns:
            Dictionary containing extracted remote trigger information
        """
        # get the remote trigger segments from the overall document so we can focus on just parsing the relevant parts.
        remote_trigger_segments = self.extract_remote_trigger_segments(html_content.split("\n"))

        # From each segment of lines that are relevant to remote triggers, extract the details.
        remote_triggers: List[RemoteTrigger] = []
        for remote_trigger_segment in remote_trigger_segments:
            rt = self.extract_remote_trigger(lines=remote_trigger_segment)
            if rt:
                remote_triggers.append(rt)

        return remote_triggers

    def parse_parameters(self, line: str, keys: List[str]) -> Dict[str, str]:
        """The line contains the keys in the format 'key=value,' parse out all keys and their values as a dict."""
        parameters = {}
        for key in keys:
            pattern = re.compile(rf"{key}\s*=\s*([^,]+)")
            match = pattern.search(line)
            if match:
                parameters[key] = match.group(1).strip()
        return parameters

    def extract_remote_trigger(self, lines: List[str]) -> Optional[RemoteTrigger]:
        """Extract remote trigger information from console log lines."""
        rt_details = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if REMOTE_TRIGGER_JOB_PATTERN in line:
                rt_details["job_name"] = line.split(REMOTE_TRIGGER_JOB_PATTERN, 1)[1].strip()

            elif REMOTE_TRIGGER_REMOTE_JENKINS_NAME_PATTERN in line:
                rt_details["remote_jenkins_name"] = line.split(REMOTE_TRIGGER_REMOTE_JENKINS_NAME_PATTERN, 1)[1].strip()

            elif REMOTE_TRIGGER_PARAMETERS_PATTERN in line:
                # Extract parameters from the line
                params_str = line.split(REMOTE_TRIGGER_PARAMETERS_PATTERN, 1)[1].strip()
                params = self.parse_parameters(line=params_str, keys=REMOTE_TRIGGER_PARAMETER_KEYS)
                rt_details["parameters"] = params

            elif REMOTE_TRIGGER_BLOCK_BUILD_UNTIL_COMPLETE_PATTERN in line:
                value = line.split(REMOTE_TRIGGER_BLOCK_BUILD_UNTIL_COMPLETE_PATTERN, 1)[1].strip()
                rt_details["block_build_until_complete"] = value.lower() == "true" if value else None

            elif REMOTE_TRIGGER_CONNECTION_RETRY_LIMIT_PATTERN in line:
                value = line.split(REMOTE_TRIGGER_CONNECTION_RETRY_LIMIT_PATTERN, 1)[1].strip()
                rt_details["connection_retry_limit"] = int(value) if value.isdigit() else None

            elif REMOTE_TRIGGER_TRUST_ALL_CERTIFICATES_PATTERN in line:
                value = line.split(REMOTE_TRIGGER_TRUST_ALL_CERTIFICATES_PATTERN, 1)[1].strip()
                rt_details["trust_all_certificates"] = value.lower() == "true" if value else None

            elif REMOTE_TRIGGER_REMOTE_JOB_URL_PATTERN in line:
                # extract the rest of the line after the phrase
                _trigger_url = line.split(REMOTE_TRIGGER_REMOTE_JOB_URL_PATTERN, 1)[1].strip()
                # parse the trigger url using bs4
                lparse = BeautifulSoup(_trigger_url, "html.parser")
                # there will only be one link.
                link = lparse.find_all("a", href=True)[0]
                rt_details["remote_job_url"] = link.get("href", "")

        # if rt_details has information in it, attempt to create a RemoteTrigger object
        if rt_details:
            try:
                remote_trigger = RemoteTrigger(
                    job_name=rt_details["job_name"],
                    remote_jenkins_name=rt_details["remote_jenkins_name"],
                    remote_job_url=rt_details["remote_job_url"],
                    parameters=rt_details["parameters"],
                    block_build_until_complete=rt_details.get("block_build_until_complete", False),
                    connection_retry_limit=rt_details.get("connection_retry_limit", ""),
                    trust_all_certificates=rt_details.get("trust_all_certificates", False),
                )
                return remote_trigger

            except Exception as e:
                log.error(
                    f"Failed to create RemoteTrigger object from details:\n"
                    f"{pprint.pformat(rt_details)}"
                    f"\nException:\n"
                    f"{pprint.pformat(e)}"
                )
        return None

    def _extract_config_value(self, line: str) -> Optional[str]:
        """Extract value from a configuration line."""
        # Split on colon and get everything after it
        parts = line.split(":", 1)
        if len(parts) > 1:
            return parts[1].strip()
        return None

    def _parse_parameters(self, line: str) -> Dict[str, Any]:
        """Parse the parameters from a parameters line."""
        parameters = {}

        # Extract the parameters section (everything after the opening brace)
        param_match = re.search(r"\{(.+)\}", line)
        if not param_match:
            return parameters

        param_string = param_match.group(1)

        # Parse parameters - handle both simple key=value and complex values with URLs
        current_key = None
        current_value = ""
        i = 0

        while i < len(param_string):
            char = param_string[i]

            if char == "=" and current_key is None:
                # Found key=value separator
                current_key = current_value.strip().rstrip(",").strip()
                current_value = ""

            elif char == "," and current_key is not None:
                # End of current parameter
                # Check if this is actually the end or part of a URL
                if self._is_parameter_end(param_string, i):
                    parameters[current_key] = self._clean_parameter_value(current_value.strip())
                    current_key = None
                    current_value = ""
                else:
                    current_value += char

            else:
                current_value += char

            i += 1

        # Handle the last parameter
        if current_key is not None:
            parameters[current_key] = self._clean_parameter_value(current_value.strip())

        return parameters

    def _is_parameter_end(self, param_string: str, comma_index: int) -> bool:
        """Determine if a comma marks the end of a parameter or is part of a URL."""
        # Look ahead to see if the next non-space character sequence looks like a parameter key
        i = comma_index + 1
        while i < len(param_string) and param_string[i].isspace():
            i += 1

        if i >= len(param_string):
            return True

        # Look for the pattern: word characters followed by =
        next_chars = param_string[i : i + 50]  # Look ahead up to 50 chars
        return bool(re.match(r"[A-Z_][A-Z0-9_]*\s*=", next_chars))

    def _clean_parameter_value(self, value: str) -> str:
        """Clean parameter value by removing HTML tags and unescaping URLs."""
        # Remove HTML tags
        soup = BeautifulSoup(value, "html.parser")
        text_value = soup.get_text()

        # Unescape URL encoding if it looks like a URL
        if text_value.startswith("http"):
            try:
                text_value = unquote(text_value)
            except Exception:
                pass  # Keep original if unquoting fails

        return text_value.strip()


@click.command()
@click.help_option("--help", "-h")
@click.version_option(__VERSION__, "--version", "-v", message="%(prog)s version %(version)s")
@click.option(
    "-i",
    "--input",
    "input_file",
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Path to the Jenkins HTML log file",
)
@click.option(
    "-o",
    "--output",
    "output_file",
    required=True,
    type=click.Path(path_type=Path),
    help="Path for the output JSON file",
)
@click.option(
    "-V",
    "--verbose",
    required=False,
    type=bool,
    default=False,
    is_flag=True,
    help="Enable verbose logging in console output.",
)
def main(input_file: Path, output_file: Path, verbose: bool) -> None:
    """Extract remote trigger information from Jenkins HTML log files.

    Examples:
      extract_remote_triggers.py -i jenkins.html.log -o triggers.json -V
      extract_remote_triggers.py --input /path/to/log.html --output /path/to/output.json
    """

    if verbose:
        log.setLevel(logging.DEBUG)

    # Create output directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Read HTML log file
    log.debug(f"Reading HTML log file: {input_file}")
    html_content = input_file.read_text(encoding="utf-8")

    # Parse HTML log
    log.debug("Parsing HTML log for remote trigger information")
    parser = JenkinsLogParser()
    result = parser.parse_html_log(html_content)

    if result and len(result) > 0:
        # Write JSON output
        log.debug(f"Writing results to: {output_file}")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, cls=RemoteTriggerEncoder)

        log.info("Successfully extracted remote trigger information")
        log.info(f"    Found {len(result)} remote triggers")
    else:
        log.warning("No remote triggers found in the provided log file, not writing output file.")


if __name__ == "__main__":
    main()
