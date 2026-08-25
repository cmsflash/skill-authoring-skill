#!/usr/bin/env python3
"""Scaffold, install, and publish a skill following this machine's conventions.

Handles the mechanical steps that are easy to get subtly wrong: the two-hop
symlink chain, the personal git identity, and the SSH host alias that the
personal GitHub account needs.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILLS_ROOT = Path(os.environ.get("SKILLS_ROOT", Path.home() / "Programs" / "skills"))
AGENTS_SKILLS = Path(os.environ.get("AGENTS_SKILLS", Path.home() / ".agents" / "skills"))
CLAUDE_SKILLS = Path(os.environ.get("CLAUDE_SKILLS", Path.home() / ".claude" / "skills"))

GIT_NAME = "Zhuoran Shen"
GIT_EMAIL = "cmsflash99@gmail.com"
GH_OWNER = "cmsflash"

# HTTPS, because the osxkeychain credential for github.com is the personal
# account. The default SSH key is the WORK account, so an SSH remote to a
# personal repo fails with a misleading "Repository not found"; SSH_ALIAS is
# the escape hatch if the keychain credential is ever absent.
SSH_ALIAS = "github.com-cmsflash"

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# An unfilled scaffold placeholder: TODO opening a line or a quoted value.
# Deliberately not a bare "TODO" substring, so a skill may discuss the word
# in prose or inline code without failing its own check.
PLACEHOLDER_RE = re.compile(r'(?m)^\s*(?:[-*]\s*)?TODO\b|^description:\s*"TODO\b')

GITIGNORE = "__pycache__/\n*.pyc\n"

SKILL_TEMPLATE = """---
name: {name}
description: "TODO one paragraph, 350-650 characters. Third person. What it \
does, then when to use it, then literal trigger phrases the human would type. \
This is the ONLY text an agent sees when deciding whether to load the skill."
---

# {title}

TODO: the body. Only loaded after the skill triggers.

Assume the reader is a competent agent that does not know THIS machine, THIS
repo, or THIS workflow. Write down what cannot be inferred: the trap, the
non-obvious ordering, the thing that looks right and is wrong.
"""

README_TEMPLATE = """# {name}

TODO: one or two sentences on what this does and why it exists.

## Usage

```bash
TODO
```

## Install

Symlinked into the central skill store:

```bash
ln -s {root}/{dir_name} ~/.agents/skills/{name}
ln -s ~/.agents/skills/{name} ~/.claude/skills/{name}
```
"""


def run(cmd: list[str], cwd: Path | None = None, check: bool = True, quiet: bool = False):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if check and proc.returncode != 0:
        sys.stderr.write(f"$ {' '.join(cmd)}\n{proc.stdout}{proc.stderr}")
        raise SystemExit(proc.returncode)
    if not quiet and proc.stdout.strip():
        print(proc.stdout.strip())
    return proc


def skill_name(dir_name: str) -> str:
    """The skill's own name, which is the directory minus the `-skill` suffix.

    They differ on purpose: the directory and GitHub repo carry the suffix so
    a checkout is self-describing, while the skill name (frontmatter and
    symlink) is what agents reference and must stay stable across a rename.
    """
    return dir_name[: -len("-skill")] if dir_name.endswith("-skill") else dir_name


def validate_name(name: str) -> str:
    if not NAME_RE.match(name) or len(name) > 64:
        raise SystemExit(
            f"Invalid skill name {name!r}. Use lowercase letters, digits, and "
            f"single hyphens (e.g. dev-servers), max 64 chars."
        )
    return name


def link(src: Path, dest: Path) -> None:
    """Create dest -> src, tolerating an identical existing link."""
    if dest.is_symlink():
        if dest.resolve() == src.resolve():
            print(f"  already linked: {dest}")
            return
        raise SystemExit(f"{dest} already exists and points elsewhere ({os.readlink(dest)}).")
    if dest.exists():
        raise SystemExit(f"{dest} already exists and is not a symlink.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.symlink_to(src)
    print(f"  linked {dest} -> {src}")


def cmd_init(args: argparse.Namespace) -> int:
    # Accept either form: the argument is the skill name, and the directory
    # gets the `-skill` suffix.
    name = skill_name(validate_name(args.name))
    dir_name = f"{name}-skill"
    path = SKILLS_ROOT / dir_name
    if path.exists():
        raise SystemExit(f"{path} already exists.")

    (path / "scripts").mkdir(parents=True)
    title = name.replace("-", " ").capitalize()
    (path / "SKILL.md").write_text(SKILL_TEMPLATE.format(name=name, title=title))
    (path / "README.md").write_text(
        README_TEMPLATE.format(name=name, dir_name=dir_name, root=SKILLS_ROOT)
    )
    (path / ".gitignore").write_text(GITIGNORE)
    if not args.scripts:
        (path / "scripts").rmdir()

    run(["git", "init", "-q"], cwd=path)
    run(["git", "config", "user.name", GIT_NAME], cwd=path)
    run(["git", "config", "user.email", GIT_EMAIL], cwd=path)
    print(f"Created {path} (skill name: {name}, git identity: {GIT_EMAIL})")

    if args.link:
        cmd_link(argparse.Namespace(name=dir_name))
    print(f"\nNext: write SKILL.md and README.md, then `new_skill.py check {dir_name}`.")
    return 0


def cmd_link(args: argparse.Namespace) -> int:
    name = validate_name(args.name)
    src = SKILLS_ROOT / name
    if not src.is_dir():
        raise SystemExit(f"{src} does not exist.")
    # The link is named for the SKILL, not the directory, so renaming the
    # directory or repo never changes what an agent references.
    linked = skill_name(name)
    print("Linking:")
    link(src, AGENTS_SKILLS / linked)
    # Claude links to the .agents copy, not the source, so ~/.agents stays the
    # single hub every harness resolves through.
    link(AGENTS_SKILLS / linked, CLAUDE_SKILLS / linked)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    name = validate_name(args.name)
    path = SKILLS_ROOT / name
    problems, warnings = [], []

    if not path.is_dir():
        raise SystemExit(f"{path} does not exist.")

    skill_md = path / "SKILL.md"
    readme = path / "README.md"

    if not skill_md.exists():
        problems.append("SKILL.md is missing")
    else:
        text = skill_md.read_text()
        if not text.startswith("---\n"):
            problems.append("SKILL.md does not start with YAML frontmatter")
        else:
            fm = text.split("---")[1]
            fm_name = re.search(r"^name:\s*(.+)$", fm, re.M)
            desc = re.search(r'^description:\s*"(.+?)"\s*$', fm, re.S | re.M)
            if not fm_name:
                problems.append("frontmatter has no name:")
            elif fm_name.group(1).strip() != skill_name(name):
                problems.append(
                    f"frontmatter name {fm_name.group(1).strip()!r} should be "
                    f"{skill_name(name)!r} for directory {name!r}"
                )
            if not desc:
                problems.append('frontmatter has no quoted description: "..."')
            else:
                d = desc.group(1)
                if len(d) < 200:
                    warnings.append(f"description is {len(d)} chars; aim for 350-650")
                if len(d) > 900:
                    warnings.append(f"description is {len(d)} chars; trim toward 650")
                if not any(k in d for k in ("Use when", "Use whenever", "Load before", "Triggers")):
                    warnings.append("description has no 'Use when' / 'Triggers' clause")
        if PLACEHOLDER_RE.search(text):
            problems.append("SKILL.md still contains a TODO placeholder")
        lines = len(text.splitlines())
        if lines > 500:
            problems.append(f"SKILL.md is {lines} lines; split into references/ under 500")
        elif lines > 250:
            warnings.append(f"SKILL.md is {lines} lines; the house range is ~140-200")

    if not readme.exists():
        problems.append("README.md is missing")
    else:
        rt = readme.read_text()
        if "## Install" not in rt:
            problems.append("README.md has no '## Install' section")
        if PLACEHOLDER_RE.search(rt):
            problems.append("README.md still contains a TODO placeholder")

    for script in (path / "scripts").glob("*.py") if (path / "scripts").is_dir() else []:
        if not os.access(script, os.X_OK):
            warnings.append(f"{script.name} is not executable (chmod +x)")
        proc = run([sys.executable, "-m", "py_compile", str(script)], check=False, quiet=True)
        if proc.returncode != 0:
            problems.append(f"{script.name} does not compile")

    linked = skill_name(name)
    for target, label in (
        (AGENTS_SKILLS / linked, "~/.agents"),
        (CLAUDE_SKILLS / linked, "~/.claude"),
    ):
        if not target.is_symlink():
            warnings.append(f"not linked into {label} (run `new_skill.py link {name}`)")

    for line in problems:
        print(f"FAIL  {line}")
    for line in warnings:
        print(f"warn  {line}")
    if not problems and not warnings:
        print(f"{name}: clean.")
    elif not problems:
        print(f"\n{name}: no blocking problems.")
    return 1 if problems else 0


def cmd_publish(args: argparse.Namespace) -> int:
    name = validate_name(args.name)
    path = SKILLS_ROOT / name
    if not path.is_dir():
        raise SystemExit(f"{path} does not exist.")
    if cmd_check(argparse.Namespace(name=name)) != 0:
        raise SystemExit("Fix the FAIL items above before publishing.")

    # The directory already carries the suffix, so the repo name matches it.
    repo = args.repo or name
    slug = f"{GH_OWNER}/{repo}"
    remote_url = (
        f"git@{SSH_ALIAS}:{slug}.git" if args.ssh else f"https://github.com/{slug}.git"
    )

    if not run(["git", "status", "--porcelain"], cwd=path, quiet=True).stdout.strip():
        if not run(["git", "log", "-1"], cwd=path, check=False, quiet=True).returncode == 0:
            raise SystemExit("Nothing committed and nothing to commit.")
    else:
        run(["git", "add", "-A"], cwd=path)
        run(["git", "commit", "-q", "-m", args.message], cwd=path)
        print(f"Committed: {args.message.splitlines()[0]}")

    if not shutil.which("gh"):
        raise SystemExit("gh is not installed.")

    exists = run(["gh", "api", f"repos/{slug}"], check=False, quiet=True).returncode == 0
    if not exists:
        # gh's "active account" is global mutable state that other tools flip,
        # so pin the token for this call instead of trusting whoever is active:
        # the work account cannot create a repo under the personal one.
        token = run(
            ["gh", "auth", "token", "--user", GH_OWNER], check=False, quiet=True
        ).stdout.strip()
        env = {**os.environ, "GH_TOKEN": token} if token else None
        if not token:
            print(f"warn  no stored gh token for {GH_OWNER}; using the active account")
        # Create only, then set the remote by hand: --source --push would push
        # over the default SSH key, which is the work account.
        visibility = "--public" if args.public else "--private"
        proc = subprocess.run(
            ["gh", "repo", "create", slug, visibility, "--description", args.description],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        if proc.returncode != 0:
            sys.stderr.write(proc.stdout + proc.stderr)
            raise SystemExit(proc.returncode)
        print(f"Created {slug}")

    current = run(["git", "remote"], cwd=path, quiet=True).stdout.split()
    if "origin" in current:
        run(["git", "remote", "set-url", "origin", remote_url], cwd=path)
    else:
        run(["git", "remote", "add", "origin", remote_url], cwd=path)

    branch = run(["git", "branch", "--show-current"], cwd=path, quiet=True).stdout.strip()
    run(["git", "push", "-u", "origin", branch], cwd=path)
    print(f"Pushed to https://github.com/{slug}")
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    """Check the machine can actually publish, before a skill needs it."""
    ok = True

    # The stored HTTPS credential is what an ordinary push uses, so this is
    # the check that predicts whether publishing works.
    cred = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        check=False,
    )
    user = re.search(r"^username=(.+)$", cred.stdout, re.M)
    if user and user.group(1).strip() == GH_OWNER:
        print(f"ok    https credential for github.com is {GH_OWNER}")
    else:
        ok = False
        found = user.group(1).strip() if user else "none"
        print(f"FAIL  https credential for github.com is {found!r}, expected {GH_OWNER}")
        print(f"      fall back to `publish --ssh` (alias {SSH_ALIAS}), or re-add the credential")

    proc = run(["ssh", "-T", f"git@{SSH_ALIAS}"], check=False, quiet=True)
    blob = proc.stdout + proc.stderr
    state = "ok   " if f"Hi {GH_OWNER}!" in blob else "warn "
    print(f"{state} ssh fallback {SSH_ALIAS} -> {GH_OWNER}")

    if shutil.which("gh"):
        who = run(["gh", "api", "user", "--jq", ".login"], check=False, quiet=True).stdout.strip()
        print(f"ok    gh installed (active account: {who or 'unknown'})")
        if who != GH_OWNER:
            print(f"      note: gh acts as {who!r}, but the slug is fully qualified, so")
            print(f"      repo creation still lands under {GH_OWNER}")
    else:
        ok = False
        print("FAIL  gh is not installed")

    for p in (SKILLS_ROOT, AGENTS_SKILLS, CLAUDE_SKILLS):
        print(f"{'ok   ' if p.is_dir() else 'FAIL '} {p}")
        ok = ok and p.is_dir()
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="scaffold a new skill and git-init it")
    p.add_argument("name")
    p.add_argument("--scripts", action="store_true", help="keep a scripts/ directory")
    p.add_argument("--no-link", dest="link", action="store_false", help="skip symlinking")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("link", help="symlink into ~/.agents/skills and ~/.claude/skills")
    p.add_argument("name")
    p.set_defaults(func=cmd_link)

    p = sub.add_parser("check", help="validate conventions before publishing")
    p.add_argument("name")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("publish", help="commit, create the GitHub repo, and push")
    p.add_argument("name")
    p.add_argument("-m", "--message", default="Add skill", help="commit message")
    p.add_argument("--repo", help=f"repo name (default: <name>-skill under {GH_OWNER})")
    p.add_argument("--description", default="", help="GitHub repo description")
    p.add_argument("--public", action="store_true", help="create a public repo (default private)")
    p.add_argument("--ssh", action="store_true", help=f"use git@{SSH_ALIAS} instead of HTTPS")
    p.set_defaults(func=cmd_publish)

    p = sub.add_parser("doctor", help="check credentials/gh/paths are ready to publish")
    p.set_defaults(func=cmd_doctor)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
