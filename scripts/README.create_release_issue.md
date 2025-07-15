# Create Release Issue Script Documentation
This document provides an overview of the `create_release_issue.py` script, which automates the creation of GitHub issues for tracking JDK releases. The script is designed to streamline the process of managing JDK release issues by providing a standardized format and easy-to-use command-line interface.

🎯 Usage Examples:
The script is now production-ready with clean, maintainable code that follows Python best practices. Here are a few examples of how to use the script:

```bash
# Basic usage with direct token
python create_release_issue.py --month July --year 2025 --version 21.0.4+7 \
  --repo-owner adoptium --repo-name adoptium --token "ghp_..."

# Advanced usage with token file and labels
python create_release_issue.py --month October --year 2025 --version 8u462-b06 \
  --repo-owner myorg --repo-name jdk-releases \
  --token-file token.txt --labels "release,jdk8" --dry-run
```

## Contributing
We welcome contributions to the `create_release_issue.py` script, and all the other scripts in this repo. If you have suggestions for improvements or new features, please open an issue or submit a pull request. For more details, refer to the [CONTRIBUTING.md](../CONTRIBUTING.md) file.
