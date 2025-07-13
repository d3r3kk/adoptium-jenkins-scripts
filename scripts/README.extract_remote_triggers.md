# Remote Trigger Extraction Script

The `extract_remote_triggers.py` script extracts remote trigger information from Jenkins HTML log files.

## Features

- **Multiple Trigger Types**: Extracts three types of remote triggers:
  - `eclipse_temurin_announcement`: Initial announcements of Eclipse Temurin AQA test triggers
  - `simple`: Simple remote trigger lines with target specifications
  - `detailed`: Full parameterized remote trigger configurations

- **Comprehensive Data Extraction**: For detailed triggers, extracts:
  - Job name and remote Jenkins instance name
  - All trigger parameters (SDK URLs, platforms, test targets, etc.)
  - Configuration settings (retry limits, certificates, etc.)
  - Authentication and security information

- **JSON Output**: All extracted information is saved in structured JSON format

## Usage

```bash
python scripts/extract_remote_triggers.py -i <input_html_log> -o <output_json>
```

### Examples

```bash
# Extract from JDK8 Windows build log
python scripts/extract_remote_triggers.py -i tmp/jdk8-windows-x86-32.html.log -o tmp/jdk8-triggers.json

# Extract from JDK21 Alpine Linux build log  
python scripts/extract_remote_triggers.py -i tmp/jdk21-alpine-linux-aarch64.html.log -o tmp/jdk21-triggers.json
```

## Output Format

The script outputs a JSON file with the following structure:

```json
{
  "remote_triggers": [
    {
      "trigger_type": "eclipse_temurin_announcement",
      "timestamp": "2025-07-11T12:51:08.934Z", 
      "job_name": "AQA_Test_Pipeline",
      "parameters": {
        "PLATFORMS": "x86-32_windows",
        "JDK_VERSION": "jdk8u"
      }
    },
    {
      "trigger_type": "detailed",
      "job_name": "AQA_Test_Pipeline",
      "remote_jenkins_name": "temurin-compliance", 
      "parameters": {
        "SDK_RESOURCE": "customized",
        "CUSTOMIZED_SDK_URL": "https://ci.adoptium.net/...",
        "PLATFORMS": "x86-32_windows",
        "TARGETS": "sanity.jck,extended.jck,special.jck,dev.jck",
        // ... additional parameters
      },
      "block_build_until_complete": false,
      "connection_retry_limit": 5,
      "trust_all_certificates": false,
      "remote_job_url": "https://ci.eclipse.org/temurin-compliance/job/AQA_Test_Pipeline",
      "authentication_user": "tc-trigger-bot@eclipse.org",
      "csrf_protection_enabled": true
    }
  ],
  "total_triggers": 3
}
```

## Dependencies

- `click`: Command line interface
- `beautifulsoup4`: HTML parsing
- `logging`: Console output
