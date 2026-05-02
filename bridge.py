"""
bridge.py — GitHub ↔ Claude bridge for tfg_exam_grader

Usage:
    python bridge.py <mode> <file_path>

Modes:
    review    — Code review with issues and suggestions
    improve   — Rewrite / enhance the file
    explain   — Plain-language explanation of the file

Examples:
    python bridge.py review src/grader.py
    python bridge.py improve src/utils.py
    python bridge.py explain src/main.py

Environment variables (loaded from .env):
    GITHUB_TOKEN      — Personal Access Token with repo read access
    ANTHROPIC_API_KEY — Anthropic API key
    GITHUB_REPO       — Optional, "owner/repo" target. Defaults to the current repo.
"""

import argparse
import sys

import anthropic
import requests
from dotenv import load_dotenv
import os

load_dotenv()

REPO = os.environ.get("GITHUB_REPO", "Asdri02/TFG-Adriansolerrodriguez")
GITHUB_API = "https://api.github.com"

SYSTEM_PROMPTS = {
    "review": (
        "You are an expert Python code reviewer. "
        "Analyse the provided file and give structured feedback: "
        "1) Overall assessment, 2) Issues (with line references where possible), "
        "3) Concrete improvement suggestions. Be concise and actionable."
    ),
    "improve": (
        "You are an expert Python developer. "
        "Rewrite the provided file to improve readability, performance, and correctness. "
        "Return the full improved file inside a ```python``` block, "
        "followed by a short summary of changes."
    ),
    "explain": (
        "You are a patient software teacher. "
        "Explain the provided file in plain language: its purpose, how it works, "
        "and any important design decisions. Aim at a developer unfamiliar with the codebase."
    ),
}


def fetch_file(path: str) -> str:
    """Fetch raw file content from GitHub via the Contents API."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Error: GITHUB_TOKEN is not set.")

    url = f"{GITHUB_API}/repos/{REPO}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.raw+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code == 404:
        sys.exit(f"Error: '{path}' not found in {REPO}.")
    if not response.ok:
        sys.exit(f"GitHub API error {response.status_code}: {response.text}")

    return response.text


def call_claude(mode: str, file_path: str, content: str) -> None:
    """Stream a Claude response for the given mode and file content."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("Error: ANTHROPIC_API_KEY is not set.")

    client = anthropic.Anthropic(api_key=api_key)

    user_message = (
        f"File: `{file_path}` (from repo `{REPO}`)\n\n"
        f"```python\n{content}\n```"
    )

    print(f"\n[bridge] Mode: {mode} | File: {file_path}\n{'─' * 60}\n")

    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPTS[mode],
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)

    print(f"\n{'─' * 60}\n[bridge] Done.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bridge between GitHub files and Claude.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "mode",
        choices=list(SYSTEM_PROMPTS.keys()),
        help="Operation mode: review | improve | explain",
    )
    parser.add_argument(
        "file_path",
        help="Path to the file inside the repo (e.g. src/grader.py)",
    )
    args = parser.parse_args()

    content = fetch_file(args.file_path)
    call_claude(args.mode, args.file_path, content)


if __name__ == "__main__":
    main()
