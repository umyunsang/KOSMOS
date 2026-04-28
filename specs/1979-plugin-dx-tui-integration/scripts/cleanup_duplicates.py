#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Clean up duplicate sub-issues #2246-#2287 created by an accidental
second run of create_issues.py. Detaches each from Epic #1979 then
closes as duplicate with a comment pointing at the canonical issue.
"""

from __future__ import annotations

import subprocess
import sys
import time

REPO = "umyunsang/KOSMOS"
EPIC_NUM = 1979

# Duplicate range — second-batch issue numbers
DUPLICATE_START = 2246
DUPLICATE_END = 2287

# Canonical batch — first-batch issue numbers (1:1 mapping by offset)
CANONICAL_START = 2204


def gh(*args: str) -> str:
    cmd = ["gh", *args]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"gh failed: {' '.join(cmd)}\nstderr: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def get_issue_node_id(num: int) -> str:
    return gh("api", f"repos/{REPO}/issues/{num}", "--jq", ".node_id")


def remove_subissue(epic_id: str, sub_id: str) -> None:
    """Detach sub-issue from Epic via GraphQL removeSubIssue mutation."""
    query = (
        "mutation($eid: ID!, $sid: ID!) { "
        "removeSubIssue(input: {issueId: $eid, subIssueId: $sid}) { "
        "issue { number } } }"
    )
    gh("api", "graphql", "-f", f"query={query}", "-F", f"eid={epic_id}", "-F", f"sid={sub_id}")


def close_as_duplicate(num: int, canonical_num: int) -> None:
    """Close issue with a comment marking it as duplicate."""
    body = (
        f"Duplicate of #{canonical_num}.\n\n"
        f"This issue was created by an accidental second run of `create_issues.py` "
        f"during /speckit-taskstoissues for Epic #1979. The canonical issue is "
        f"#{canonical_num}.\n\n"
        f"Closing as duplicate; detached from Epic #1979 sub-issues."
    )
    gh("issue", "comment", str(num), "--repo", REPO, "--body", body)
    gh("issue", "close", str(num), "--repo", REPO, "--reason", "not planned")


def main() -> None:
    print(f"Resolving Epic #{EPIC_NUM} GraphQL ID...", file=sys.stderr)
    epic_id = gh(
        "api", "graphql", "-f",
        f'query=query {{ repository(owner: "umyunsang", name: "KOSMOS") {{ issue(number: {EPIC_NUM}) {{ id }} }} }}',
        "--jq", ".data.repository.issue.id",
    )
    print(f"  Epic GraphQL ID: {epic_id}", file=sys.stderr)

    print(f"\nDetaching + closing duplicates #{DUPLICATE_START}-#{DUPLICATE_END}...", file=sys.stderr)
    for dup_num in range(DUPLICATE_START, DUPLICATE_END + 1):
        canonical_num = CANONICAL_START + (dup_num - DUPLICATE_START)
        try:
            sub_id = get_issue_node_id(dup_num)
            remove_subissue(epic_id, sub_id)
            close_as_duplicate(dup_num, canonical_num)
            print(f"  #{dup_num} → detached + closed (dup of #{canonical_num})", file=sys.stderr)
        except SystemExit:
            print(f"  #{dup_num} → SKIPPED (likely already detached/closed)", file=sys.stderr)
        time.sleep(0.3)

    print("\nVerifying final sub-issue count...", file=sys.stderr)
    final_count = gh(
        "api", "graphql", "-f",
        f'query=query {{ repository(owner: "umyunsang", name: "KOSMOS") {{ issue(number: {EPIC_NUM}) {{ subIssues {{ totalCount }} }} }} }}',
        "--jq", ".data.repository.issue.subIssues.totalCount",
    )
    print(f"Epic #{EPIC_NUM} now has {final_count} sub-issues (expected 42).", file=sys.stderr)


if __name__ == "__main__":
    main()
