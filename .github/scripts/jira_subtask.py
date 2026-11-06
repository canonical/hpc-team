#!/usr/bin/env python3
"""Create JIRA subtasks for a PR: one per (story key x requested reviewer).

Primary trigger: a "/jira ABC-123, ABC-456" comment on a pull request.
Keys resolve in order: comment command > labeled body line ("JIRA: ...") > branch name.
The subtask assignee comes from the PR's CODEOWNERS review requests.
When done, posts a result comment on the PR (reactions don't notify subscribers).

Requires (env): JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, GITHUB_TOKEN, REPO,
PR_NUMBER, GITHUB_TO_JIRA (JSON: GitHub login -> JIRA accountId).
Optional env: COMMENT (command mode), FIRST_REVIEWER_ONLY ("true"/"false").
"""

import json
import os
import re
import sys
import time

import requests

JIRA = os.environ["JIRA_BASE_URL"].rstrip("/")
AUTH = (os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"])
USER_MAP = json.loads(os.environ.get("GITHUB_TO_JIRA", "{}"))
FIRST_ONLY = os.environ.get("FIRST_REVIEWER_ONLY", "false").lower() == "true"

REPO = os.environ["REPO"]
PR_NUMBER = os.environ["PR_NUMBER"]
GH_HEADERS = {
    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
    "Accept": "application/vnd.github+json",
}
COMMENT = os.environ.get("COMMENT", "").strip()  # set only by the command workflow
ACTION = os.environ.get("EVENT_ACTION", "opened")

KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")
LABEL_RE = re.compile(r"^\s*(?:JIRA|Fixes?|Resolves?|Closes?)\s*[:\s]\s*(.+)", re.IGNORECASE)

SUMMARY_MAX = 255  # JIRA summary length limit


RESULTS = []


def log(msg):
    print(f"jira-subtask: {msg}")
    RESULTS.append(msg)


def dedupe(keys):
    seen, ordered = set(), []
    for key in keys:
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def get_pr():
    r = requests.get(
        f"https://api.github.com/repos/{REPO}/pulls/{PR_NUMBER}",
        headers=GH_HEADERS, timeout=30,
    )
    r.raise_for_status()
    return r.json()


def find_keys(pr):
    """Story keys: /jira comment command, else labeled body lines, else branch."""
    if COMMENT:
        keys = KEY_RE.findall(COMMENT)
        if not keys:
            sys.exit(f"'/jira' given but no issue key found in: {COMMENT!r}")
        return dedupe(keys)
    keys = []
    for line in (pr.get("body") or "").splitlines():
        m = LABEL_RE.match(line)
        if m:
            keys += KEY_RE.findall(m.group(1))
    if not keys:
        keys = KEY_RE.findall(pr["head"]["ref"])
    return dedupe(keys)


def get_reviewers(pr):
    """Individual reviewers; CODEOWNERS requests land just after 'opened'."""
    reviewers = [u["login"] for u in pr.get("requested_reviewers", [])]
    if not reviewers and pr.get("requested_teams"):
        log(f"review requested from teams only: "
            f"{[t['name'] for t in pr['requested_teams']]}")
    tries = 3 if ACTION == "opened" else 0  # tolerate the CODEOWNERS race on 'opened'
    while not reviewers and tries:
        time.sleep(5)
        tries -= 1
        reviewers = [u["login"] for u in get_pr().get("requested_reviewers", [])]
    return reviewers[:1] if FIRST_ONLY else reviewers


def issue_exists(key):
    r = requests.get(f"{JIRA}/rest/api/3/issue/{key}", auth=AUTH,
                     params={"fields": "summary"}, timeout=30)
    return r.status_code == 200


def subtask_exists(key, reviewer):
    repo = REPO.split("/")[-1]
    jql = (f'parent = "{key}" AND summary ~ "PR #{PR_NUMBER}" '
           f'AND summary ~ "{reviewer}" AND summary ~ "{repo}"')
    r = requests.post(f"{JIRA}/rest/api/3/search/jql", auth=AUTH,
                      json={"jql": jql, "fields": ["key"], "maxResults": 1},
                      timeout=30)
    return r.ok and bool(r.json().get("issues"))


def create_subtask(key, reviewer):
    account_id = USER_MAP.get(reviewer)
    if not account_id:
        log(f"no JIRA mapping for '{reviewer}' — skipping subtask on {key}")
        return
    repo = REPO.split("/")[-1]
    summary = f"{repo}: PR #{PR_NUMBER} - {reviewer}"[:SUMMARY_MAX]
    payload = {
        "fields": {
            "project": {"key": key.split("-")[0]},
            "parent": {"key": key},
            "issuetype": {"name": "Sub-task"},
            "summary": summary,
            "assignee": {"accountId": account_id},
        }
    }
    r = requests.post(f"{JIRA}/rest/api/3/issue", json=payload, auth=AUTH,
                      headers={"Accept": "application/json"}, timeout=30)
    if r.status_code >= 300:
        sys.exit(f"create failed for {key}: {r.status_code} {r.text}")
    log(f"created {r.json()['key']} under {key} for {reviewer}")


def main():
    pr = get_pr()

    keys = find_keys(pr)
    if not keys:
        log(f"no story key in command, body, or branch '{pr['head']['ref']}' — nothing to do")
        return

    reviewers = get_reviewers(pr)
    if not reviewers:
        log("no individual review requests yet — nothing to do; "
            "re-run when a reviewer is requested")
        return

    for key in keys:
        if not issue_exists(key):
            log(f"'{key}' is not a real issue (false positive match?) — skipping")
            continue
        for reviewer in reviewers:
            if subtask_exists(key, reviewer):
                log(f"subtask for PR #{PR_NUMBER} / {reviewer} already exists on {key}")
                continue
            create_subtask(key, reviewer)


def post_comment(body):
    r = requests.post(
        f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments",
        headers=GH_HEADERS, json={"body": body}, timeout=30,
    )
    r.raise_for_status()


def report():
    lines = [msg.removeprefix("jira-subtask: ") for msg in RESULTS]
    body = "**JIRA subtask command**\n\n" + "\n".join(f"- {line}" for line in lines)
    run_url = os.environ.get("RUN_URL")
    if run_url:
        body += f"\n\n<sub>[Run logs]({run_url})</sub>"
    try:
        post_comment(body)
        gh_output = os.environ.get("GITHUB_OUTPUT")
        if gh_output:  # tells the workflow a comment was posted; no fallback needed
            with open(gh_output, "a") as f:
                f.write("comment_posted=true\n")
    except requests.RequestException as e:
        print(f"jira-subtask: failed to post result comment: {e}")


def run():
    failed = False
    try:
        main()
    except SystemExit as e:  # sys.exit(msg) from handled errors
        log(str(e.code) if e.code else "failed")
        failed = True
    except requests.RequestException as e:
        log(f"request failed: {e}")
        failed = True
    report()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    run()
