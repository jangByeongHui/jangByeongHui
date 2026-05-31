import os
import re
import sys
from datetime import datetime, timezone

import requests

USERNAME = os.environ.get("GITHUB_USERNAME", "jangByeongHui")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README_PATH = os.environ.get("README_PATH", "README.md")
MAX_PRS = 20
SECTION_START = "<!-- OSS_CONTRIBUTIONS_START -->"
SECTION_END = "<!-- OSS_CONTRIBUTIONS_END -->"


def search_merged_prs() -> list[dict]:
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    query = f"type:pr is:merged author:{USERNAME} -user:{USERNAME}"
    resp = requests.get(
        "https://api.github.com/search/issues",
        headers=headers,
        params={"q": query, "sort": "updated", "order": "desc", "per_page": MAX_PRS},
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"GitHub API {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp.json().get("items", [])


def parse_pr(raw: dict) -> dict:
    repo_name = "/".join(raw["repository_url"].split("/")[-2:])
    return {
        "repo": repo_name,
        "repo_url": f"https://github.com/{repo_name}",
        "pr_title": raw["title"],
        "pr_url": raw["html_url"],
        "pr_number": raw["number"],
    }


def group_by_repo(prs: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for pr in prs:
        grouped.setdefault(pr["repo"], []).append(pr)
    return grouped


def build_markdown(grouped: dict[str, list[dict]]) -> str:
    if not grouped:
        return "_아직 외부 오픈소스 기여 내역이 없습니다._\n"

    lines: list[str] = []
    for repo, prs in grouped.items():
        lines.append(f"**[{repo}]({prs[0]['repo_url']})**")
        for pr in prs:
            lines.append(f"- [#{pr['pr_number']} {pr['pr_title']}]({pr['pr_url']})")
        lines.append("")

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"<sub>Last updated: {updated}</sub>")
    return "\n".join(lines)


def update_readme(markdown: str) -> None:
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if SECTION_START not in content or SECTION_END not in content:
        print(f"마커를 찾을 수 없습니다: {SECTION_START}", file=sys.stderr)
        sys.exit(1)

    new_section = f"{SECTION_START}\n{markdown}\n{SECTION_END}"
    updated = re.sub(
        rf"{re.escape(SECTION_START)}.*?{re.escape(SECTION_END)}",
        new_section,
        content,
        flags=re.DOTALL,
    )

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"README 업데이트 완료: {README_PATH}")


def main() -> None:
    if not TOKEN:
        print("GITHUB_TOKEN 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    raw_prs = search_merged_prs()
    prs = [parse_pr(p) for p in raw_prs]
    grouped = group_by_repo(prs)
    markdown = build_markdown(grouped)
    update_readme(markdown)


if __name__ == "__main__":
    main()
