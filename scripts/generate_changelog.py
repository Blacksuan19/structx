#!/usr/bin/env python3
"""
Changelog Generator and Processor

This script:
1. Runs auto-changelog to generate the changelog using the repo's .auto-changelog config
2. Processes the changelog to:
    - Remove empty releases
    - Group releases from the same day
    - Fix formatting issues in commit messages
"""

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def run_auto_changelog(file_path: Path = Path("docs/changelog.md")):
    """Run auto-changelog with the existing configuration"""
    try:
        # Check if .auto-changelog exists
        if not Path(".auto-changelog").exists():
            print("Warning: .auto-changelog file not found. Using default settings.")

        # Run auto-changelog
        subprocess.run(
            ["auto-changelog", "-o", str(file_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        print("Generated changelog with auto-changelog")
    except subprocess.CalledProcessError as e:
        print(f"Error running auto-changelog: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(
            "Error: auto-changelog command not found. Please install it with 'npm install -g auto-changelog'",
            file=sys.stderr,
        )
        sys.exit(1)


def process_changelog(file_path: Path = Path("docs/changelog.md")):
    """Process the changelog to remove empty releases and group by date"""
    try:
        # Read the changelog file
        content = file_path.read_text()

        # Extract the header (everything before the first version)
        header_match = re.search(r"^(.*?)(?=## \[\d+\.\d+\.\d+\])", content, re.DOTALL)
        header = header_match.group(1) if header_match else ""

        # Extract unreleased section
        unreleased_match = re.search(
            r"(## \[Unreleased\].*?)(?=## \[|\Z)", content, re.DOTALL
        )
        unreleased = unreleased_match.group(1) if unreleased_match else ""

        # Extract all version blocks
        version_pattern = r"## \[(\d+\.\d+\.\d+)\](?:\(.*?\))? - (\d{4}-\d{2}-\d{2})\n\n(.*?)(?=## \[|\Z)"
        versions = re.findall(version_pattern, content, re.DOTALL)

        # Group versions by date
        date_groups = defaultdict(list)
        for version, date_str, changes in versions:
            # Check if this is an empty release (no actual commits)
            has_commits = bool(re.search(r"- .+`[a-f0-9]+`", changes))

            if has_commits:
                # Fix formatting in commit messages
                fixed_changes = changes

                # Replace ### at the beginning of commit messages
                fixed_changes = re.sub(r"- ### ", r"- ", fixed_changes)

                # Replace other instances of ### in commit messages
                fixed_changes = re.sub(r" ### ", r" ", fixed_changes)

                # Add to date group
                date_groups[date_str].append((version, fixed_changes.strip()))

        # Build the new changelog content
        new_content = header

        # Add unreleased section if it exists (only once)
        if unreleased and "## [Unreleased]" not in new_content:
            new_content += unreleased

        # Sort dates in reverse chronological order
        for date_str in sorted(date_groups.keys(), reverse=True):
            versions = date_groups[date_str]

            # Add date header
            new_content += f"## {date_str}\n\n"

            # Add each version under this date
            for version, changes in versions:
                # Extract the compare URL if it exists
                compare_url_match = re.search(
                    r"\[" + re.escape(version) + r"\]\((.*?)\)", content
                )
                compare_url = (
                    f"]({compare_url_match.group(1)})" if compare_url_match else "]"
                )

                new_content += f"### [{version}{compare_url}\n\n{changes}\n\n"

        # Write the updated changelog
        file_path.write_text(new_content)

        print(f"Successfully processed {file_path}:")
        print(f"- Removed empty releases")
        print(f"- Fixed formatting issues in commit messages")
        print(f"- Grouped {len(versions)} versions into {len(date_groups)} date groups")

    except Exception as e:
        print(f"Error processing changelog: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main function"""
    # Run auto-changelog with existing config
    run_auto_changelog()

    # Process the generated changelog
    process_changelog()

    print("Changelog generation and processing complete!")


if __name__ == "__main__":
    main()
