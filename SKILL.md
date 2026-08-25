---
name: skill-authoring
description: "Write a new agent skill the way this machine expects: one git repo per skill under ~/Programs/skills, symlinked through ~/.agents/skills into ~/.claude/skills, committed as the personal identity, and pushed to the cmsflash GitHub account. Use when asked to write, create, add, or publish a skill, or when a repeated workflow is worth capturing as one. Triggers: 'write a skill', 'make a skill for this', 'turn this into a skill', 'add a skill', 'publish the skill'."
---

# Skill authoring

This skill covers **where a skill lives on this machine and how it gets
published**. For authoring craft — progressive disclosure, degrees of
freedom, naming, when to split into `references/` — read
`~/.agents/skills/.system/skill-creator/SKILL.md`, which is thorough and
not duplicated here.

Two caveats on that file: it is Codex-vendored, so ignore its
`agents/openai.yaml` requirement (no skill here has one), and it is not in
the skill catalog, so it must be read by path rather than loaded by name.

## Layout

Each skill is **its own git repository**:

```
~/Programs/skills/<name>-skill/
├── SKILL.md      # frontmatter + body
├── README.md     # human-facing, ends with an Install section
├── .gitignore    # __pycache__/ and *.pyc
└── scripts/      # only if the skill ships executables
```

**The directory carries a `-skill` suffix; the skill name does not.** The
directory and GitHub repo are `<name>-skill`, so a bare checkout is
self-describing. The frontmatter `name` and both symlinks are plain `<name>`,
because that is what agents reference — keeping it free of the suffix means
renaming a directory or repo never changes what a skill is called.

Installed through a two-hop symlink chain, named for the skill:

```
~/Programs/skills/<name>-skill  ←  ~/.agents/skills/<name>  ←  ~/.claude/skills/<name>
```

The second hop points at the `~/.agents` link, not at the source. `~/.agents`
is the single hub every harness resolves through, so moving or renaming a
skill directory is repointed in exactly one place.

## The workflow

`scripts/new_skill.py` does the mechanical steps. Run `doctor` once on a new
machine to confirm SSH and `gh` are usable before you need them.

### 1. Understand the request first

Do not scaffold yet. A skill is worth writing only if it captures something
an agent cannot infer: a local convention, a trap, a required ordering. Get
concrete trigger examples from the human — the phrases they would actually
type — because those become the description, which is the only thing that
decides whether the skill ever loads.

Ask before writing when the answer would change the structure. Prefer a few
sharp questions over a long interview.

### 2. Read the neighbours

Before writing, skim one or two existing skills in `~/Programs/skills/`.
They are the real style reference: ~140-200 line bodies, a README of ~45
lines, no ceremony. Match them rather than inventing a house style.

### 3. Scaffold

```bash
python3 ~/.agents/skills/skill-authoring/scripts/new_skill.py init <name> --scripts
```

Pass the **skill name**, without the suffix. Creates
`~/Programs/skills/<name>-skill/`, both files, `.gitignore`, runs `git init`,
sets the **personal** identity on that repo, and symlinks both hops as
`<name>`. Names are lowercase-hyphenated.

Later commands take the **directory** name (`check <name>-skill`), since that
is what you see in `ls`.

### 4. Write the description last

Write the body first, then the description, because you cannot summarize
what you have not written.

The description is the whole triggering surface. An agent sees only `name`
and `description` when deciding whether to load the skill — never the body.
The house pattern, 350-650 characters:

1. What it does, third person, leading with a verb.
2. When to use it: "Use when …".
3. Literal trigger phrases: "Triggers: 'write a skill', …".

Include the phrases a human would actually type, including the sloppy ones.
A precise description that omits real phrasing simply never fires.

### 5. Write the body for a competent stranger

Assume the reader is a capable agent that has never seen this machine. Do
not explain what a git worktree is; do explain that worktrees belong at
`<repo>/.worktrees/`. Every line should be something that cannot be
inferred.

State traps as prohibitions with the reason attached — "do not X, because
Y" survives contact with a model looking for a shortcut, where a bare
"prefer Y" does not.

If a step is fragile or must happen in an exact order, put it in a script
instead of prose. Prose invites improvisation.

### 6. Validate

```bash
python3 ~/.agents/skills/skill-authoring/scripts/new_skill.py check <name>-skill
```

Checks name/directory agreement, description shape, leftover `TODO`s,
body length, that scripts compile and are executable, and that both
symlinks exist. `FAIL` blocks publishing; `warn` is advisory.

Then actually run whatever the skill tells an agent to do. A skill whose
commands were never executed is a guess.

### 7. Publish

```bash
python3 ~/.agents/skills/skill-authoring/scripts/new_skill.py publish <name>-skill \
  -m "Add <name> skill" --description "One line for the repo"
```

Commits, creates `cmsflash/<name>-skill` (private by default) matching the
directory name, sets an HTTPS remote, and pushes. Re-running is safe: an
existing repo is reused.

**Why HTTPS and not SSH.** The `osxkeychain` credential for `github.com` is
the personal account, so HTTPS just works. The default SSH *key* is the
**work** account, so an SSH remote to a personal repo fails with
`Repository not found` — which reads like the repo was never created, when
it was. `gh repo create --source --push` pushes over that same default key,
so the script creates the repo and pushes as separate steps.

`--ssh` switches to the `github.com-cmsflash` host alias, for when the
keychain credential is missing. `doctor` reports both.

## Rewriting an existing skill

Out of scope for the automation, but two things still hold: keep SKILL.md
and README.md in sync (they drift, and the README is what a human reads
first), and re-run `check` afterwards. The two skills predating this one
(`branch-tree`, `coding-preferences`) are committed under the *work* email
and have no remote; leave that alone unless asked to publish them.

## What not to do

- **Do not put the skill anywhere but `~/Programs/skills/`.** Not in the
  repo it happens to be about, not in `~/.agents/skills/` directly — that
  directory holds symlinks, and a real directory there is invisible to the
  source-of-truth layout.
- **Do not write the description as a title.** "Git branch utilities" never
  triggers. Name the situation and quote the phrasing.
- **Do not pad the body to look thorough.** Context is shared with the
  actual task; every line that restates general knowledge costs the reader
  attention for no gain.
- **Do not add `agents/openai.yaml`.** `skill-creator` asks for it; nothing
  on this machine reads it.
- **Do not report a skill as done without running its own instructions.**
