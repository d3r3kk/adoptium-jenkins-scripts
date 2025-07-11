# get_console.py

A Python script to pull console logs from Jenkins pipeline runs.

## Overview

This script connects to a Jenkins server and retrieves console logs for a specific pipeline run, then saves them to an output file. It supports authentication via Jenkins API tokens and provides flexible configuration options.

## Requirements

- Python 3.6+
- requests library

Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python scripts/get_console.py --token "your-api-token" --pipeline-name "release-openjdk21-pipeline" --run-number 48 --output console.log
```

### Using Token File

```bash
echo "your-api-token" > token.txt
python scripts/get_console.py --token-file token.txt --pipeline-name "build-scripts/release-openjdk21-pipeline" --run-number 48 --output logs/console_48.log
```

### Custom Jenkins Server

```bash
python scripts/get_console.py --url https://your-jenkins.com/ --username your-username --token "your-api-token" --pipeline-name "your-pipeline" --run-number 123 --output console.log
```

## Arguments

### Required Arguments

- `--pipeline-name`: Name of the Jenkins pipeline (e.g., "release-openjdk21-pipeline" or "build-scripts/release-openjdk21-pipeline")
- `--run-number`: Build/run number (positive integer)
- `--output`: Output file path where console log will be saved
- `--token` OR `--token-file`: Jenkins API token (either as string or file path)

### Optional Arguments

- `--url`: Jenkins server URL (default: "https://ci.adoptium.net/")
- `--username`: Jenkins username (default: "anonymous")

## Examples

### Example 1: Basic console log retrieval
```bash
python scripts/get_console.py \
  --token "11abcdef1234567890abcdef1234567890" \
  --pipeline-name "release-openjdk21-pipeline" \
  --run-number 48 \
  --output console_48.log
```

### Example 2: Nested pipeline with token file
```bash
echo "11abcdef1234567890abcdef1234567890" > jenkins_token.txt
python scripts/get_console.py \
  --token-file jenkins_token.txt \
  --pipeline-name "build-scripts/release-openjdk21-pipeline" \
  --run-number 48 \
  --output logs/build_scripts_48.log
```

### Example 3: Custom Jenkins server
```bash
python scripts/get_console.py \
  --url "https://your-company-jenkins.com/" \
  --username "your-jenkins-user" \
  --token "your-api-token" \
  --pipeline-name "your-pipeline-name" \
  --run-number 123 \
  --output console_logs/run_123.log
```

## Jenkins API Token

To get your Jenkins API token:

1. Log into your Jenkins server
2. Go to your user profile (click your username in top right)
3. Click "Configure" 
4. In the "API Token" section, click "Add new Token"
5. Give it a name and click "Generate"
6. Copy the generated token (you won't be able to see it again)

## Pipeline Name Format

The pipeline name should match the path in the Jenkins URL. For example:

- URL: `https://ci.adoptium.net/job/build-scripts/job/release-openjdk21-pipeline/48/`
- Pipeline name: `build-scripts/release-openjdk21-pipeline`

- URL: `https://ci.adoptium.net/job/release-openjdk21-pipeline/48/`
- Pipeline name: `release-openjdk21-pipeline`

## Error Handling

The script provides helpful error messages for common issues:

- Invalid API token or authentication failure
- Pipeline or run number not found
- Connection issues with Jenkins server
- File permission errors when writing output
- Invalid arguments or missing required parameters

## Output

The script will:

1. Display connection information and parameters
2. Attempt to retrieve the console log
3. Save the log to the specified output file
4. Display success message with file size information

Example output:
```
Connecting to Jenkins server: https://ci.adoptium.net/
Pipeline: release-openjdk21-pipeline
Run number: 48
Output file: console.log

Attempting to retrieve console log from: https://ci.adoptium.net/job/release-openjdk21-pipeline/48/consoleText
Console log successfully written to: console.log
File size: 245632 bytes
```