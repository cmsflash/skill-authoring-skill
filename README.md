# skill-authoring

An agent skill for writing agent skills, matching how they are laid out and
published on this machine: one git repo per skill under `~/Programs/skills`,
symlinked through `~/.agents/skills` into `~/.claude/skills`, committed as the
personal identity, and pushed to `cmsflash`.

Authoring craft — progressive disclosure, degrees of freedom, when to split
into `references/` — is not duplicated here. That lives in
`~/.agents/skills/.system/skill-creator/`, which is good and thorough, but is
Codex-vendored (ignore its `agents/openai.yaml` requirement) and absent from
the skill catalog, so it has to be read by path.

## Usage

```bash
new_skill.py doctor                 # is this machine able to publish at all
new_skill.py init <name>            # -> <name>-skill, linked as <name>
new_skill.py check <name>-skill     # validate conventions; FAIL blocks publish
new_skill.py publish <name>-skill -m "Add <name> skill"
```

`init` takes the skill name; everything after it takes the directory name.
The directory and GitHub repo carry a `-skill` suffix so a checkout is
self-describing, while the frontmatter `name` and both symlinks stay plain
`<name>` — that is what agents reference, so renaming a directory never
changes what a skill is called.

`init` also sets the personal git identity on the new repo, since the global
default is the work address.

No dependencies beyond Python 3.10+, `git`, and `gh`.

## The trap it avoids

Publishing uses an HTTPS remote, because the `osxkeychain` credential for
`github.com` is the personal account.

The default SSH **key** is the work account, so an SSH remote to a personal
repo fails with `Repository not found` — which reads like the repo was never
created, when it was. `gh repo create --source --push` pushes over that same
key, so `publish` creates the repo and pushes as separate steps.

`publish --ssh` uses the `github.com-cmsflash` host alias instead, for when
the keychain credential is missing.

## Install

Symlinked into the central skill store:

```bash
ln -s ~/Programs/skills/skill-authoring-skill ~/.agents/skills/skill-authoring
ln -s ~/.agents/skills/skill-authoring ~/.claude/skills/skill-authoring
```
