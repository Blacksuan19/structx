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


def process_changelog(file_path=Path("docs/changelog.md")):
    """
    Process the changelog to remove empty releases and group by date

    Args:
        file_path: Path to the changelog file (default: docs/changelog.md)
    """
    try:
        # Convert to Path object if string was passed
        file_path = Path(file_path)

        # Ensure the directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

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
                # Extract all commit lines
                commit_lines = re.findall(r"- .+`[a-f0-9]+`.*", changes)
                date_groups[date_str].append((version, commit_lines))

        # Build the new changelog content
        new_content = header

        # Add unreleased section if it exists (only once)
        if unreleased and "## [Unreleased]" not in new_content:
            new_content += unreleased

        # Sort dates in reverse chronological order
        for date_str in sorted(date_groups.keys(), reverse=True):
            versions_data = date_groups[date_str]

            # Add date header
            new_content += f"## {date_str}\n\n"

            # Sort versions in descending order
            sorted_versions = sorted(
                versions_data,
                key=lambda x: [int(p) for p in x[0].split(".")],
                reverse=True,
            )

            # Get the highest and lowest versions for this date
            highest_version = sorted_versions[0][0]
            lowest_version = sorted_versions[-1][0]

            # Create a version range header if there are multiple versions
            if highest_version != lowest_version:
                # Order should be lowest to highest for the range display
                version_header = f"### [{lowest_version} - {highest_version}]"

                # Find the version before the lowest version for the compare URL
                # First, extract all versions from the content
                all_versions = re.findall(r"## \[(\d+\.\d+\.\d+)\]", content)
                all_versions = sorted(
                    all_versions, key=lambda v: [int(p) for p in v.split(".")]
                )

                # Find the version before the lowest version in this group
                try:
                    lowest_version_index = all_versions.index(lowest_version)
                    if lowest_version_index > 0:
                        version_before_lowest = all_versions[lowest_version_index - 1]
                        compare_url = f"(https://github.com/Blacksuan19/structx/compare/{version_before_lowest}...{highest_version})"
                        version_header += compare_url
                except (ValueError, IndexError):
                    # Fallback if we can't determine the previous version
                    pass
            else:
                # Just one version for this day
                version_header = f"### [{highest_version}]"

                # Try to get compare URL
                compare_match = re.search(
                    r"\[" + re.escape(highest_version) + r"\]\((.*?)\)", content
                )

                if compare_match:
                    compare_url = compare_match.group(1)
                    version_header += f"({compare_url})"

            new_content += f"{version_header}\n\n"

            # Collect all commit lines from all versions for this date
            all_commits = []
            for _, commits in sorted_versions:
                for commit in commits:
                    # Fix formatting in commit messages
                    fixed_commit = re.sub(r"### ", "", commit)
                    all_commits.append(fixed_commit)

            # Remove duplicates while preserving order
            unique_commits = []
            seen = set()
            for commit in all_commits:
                # Use hash part as key to identify duplicates
                hash_match = re.search(r"`([a-f0-9]+)`", commit)
                if hash_match:
                    hash_key = hash_match.group(1)
                    if hash_key not in seen:
                        seen.add(hash_key)
                        unique_commits.append(commit)
                else:
                    # No hash found, keep it anyway
                    unique_commits.append(commit)

            # Add all unique commits
            new_content += "\n".join(unique_commits) + "\n\n"

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
