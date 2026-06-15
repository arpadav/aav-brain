# cutover: point `home` at the merged aav-brain (phases 4-5, arpad runs the git)

staged by brain-execute; NOT applied. phases 0-3 are done in the aav-brain working tree (agentic-files/
populated, agents decoupled, compile.py -> codex TOML, `.generated/` gitignored). this file is the
phase-4 nix rewrite + the phase-5 retire, in order. the brain does not commit, create remotes, touch
submodules, or run `re` - those are yours. do NOT run `re` until the submodule exists, or the live
config breaks mid-flight.

## one topology decision before you start
today home references the agents repo TWICE: the brain skills/bin via a live `mkOutOfStoreSymlink` to
`~/repos/personal/...`, and the `aav` agents via the `agents` git submodule. after the merge there is
ONE repo. pick how nix points at it:
- **A (recommended, matches the live-edit pattern):** nix `mkOutOfStoreSymlink`s point at the standalone
  `~/repos/personal/aav-brain`; the submodule under `home/` exists only to VERSION/pin it for fresh
  clones. edits stay live (the comment you already keep: "linked live so reload picks up edits").
- **B:** nix points at the submodule checkout `home/aav-brain`; one location, but edits require a
  submodule bump to go live (the friction you hit last session).
the nix below assumes **A** (`aavBrain = ~/repos/personal/aav-brain`). flip the one path for B.

## 1. home.nix `let` block - collapse the two refs into one, drop the agents submodule ref
```nix
  # the one transferable brain: cards + scripts + agentic files, linked live.
  aavBrain   = "${config.home.homeDirectory}/repos/personal/aav-brain";
  agentsRoot = "${aavBrain}/agentic-files/agents";
  skillsRoot = "${aavBrain}/agentic-files/skills";
  codexAgents = "${aavBrain}/.generated/codex/agents";   # compiled on switch (activation below)
  brainSkills = [
    "brain-plan" "brain-execute" "brain-review" "brain-self-refine"
    "brain-meta-drive" "brain-meta-recall" "brain-meta-learn" "brain-meta-intent"
    "brain-meta-author-prompt" "brain-meta-style" "brain-meta-curate" "brain-meta-commit"
  ];
  mkLinks = prefix: src: names: builtins.listToAttrs (map (name: {
    name = "${prefix}/${name}";
    value.source = config.lib.file.mkOutOfStoreSymlink "${src}/${name}";
  }) names);
  # skills are universal SKILL.md across all three surfaces; agents differ (claude .md, codex .toml).
  brainLinks =
    (mkLinks ".claude/skills" skillsRoot brainSkills)
    // (mkLinks ".agents/skills" skillsRoot brainSkills)
    // (mkLinks ".codex/skills" skillsRoot brainSkills);
```
removed: the old `brain = .../agents/brain` line, and the `brainAgents`/`compiled/codex` plumbing (codex
agents are now real TOML agents, not compiled skills).

## 2. home.file - claude agents flattened (D8), codex agents = the TOML dir
claude reads ONE subdir level under `.claude/agents/` (today: `aav`, `brain`). the repo keeps the
`lang/rust/` hierarchy; the symlink layer flattens it:
```nix
  home.file = brainLinks // {
    # ... keep nix.conf, helix runtime ...
    ".claude/agents/brain".source   = config.lib.file.mkOutOfStoreSymlink "${agentsRoot}/brain";
    ".claude/agents/general".source = config.lib.file.mkOutOfStoreSymlink "${agentsRoot}/general";
    ".claude/agents/rust".source    = config.lib.file.mkOutOfStoreSymlink "${agentsRoot}/lang/rust";
    ".claude/agents/custom".source  = config.lib.file.mkOutOfStoreSymlink "${agentsRoot}/custom";
    ".codex/agents".source          = config.lib.file.mkOutOfStoreSymlink codexAgents;
    # PRIVATE memory: the scripts write to the env-free XDG path; it is a symlink to
    # the aav-brain-private submodule (trace + evidence never touch the public repo).
    ".local/share/aav-brain".source = config.lib.file.mkOutOfStoreSymlink "${config.home.homeDirectory}/repos/personal/home/aav-brain-private";
    ".local/bin/brain-find" = {
      executable = true;
      text = ''
        #!/usr/bin/env bash
        exec python3 "${aavBrain}/bin/brain-find.py" "$@"
      '';
    };
  };
```
removed: `.claude/agents/aav` (-> `~/.config/home-manager/agents`) and `.claude/agents/brain`
(-> `.../agents/brain`); both now resolve under `agentsRoot`. (verify claude's recursion depth first; if
it reads deeper than one level, mirror the tree directly instead of flattening.)

## 3. activation - compile codex TOML on every switch (so `.generated/` is fresh)
```nix
  home.activation.brainCompile =
    config.lib.dag.entryAfter [ "writeBoundary" ] ''
      # $DRY_RUN_CMD is a no-op echo under `home-manager switch --dry-run`, so a
      # dry run never actually writes .generated/. a compile failure WARNS but does
      # NOT abort the switch (stale codex agents beat a bricked activation).
      $DRY_RUN_CMD ${pkgs.python3}/bin/python3 ${aavBrain}/bin/compile.py \
        || echo "warn: codex agent compile failed; .generated/ may be stale" >&2
    '';
```

## 4 + 4b. discovery + env minimization - ALREADY APPLIED (plans/FIND_BRAIN_AND_MINIMAL_ENV.md)
done in the working tree, nothing to do here:
- `find_brain()` now returns a SINGLE root Path; the 5 callers, `brain-find` (`--export` emits only
  `AAV_BRAIN`; `--agents`/`--skills` derive `<root>/agentic-files/...`), and `home.nix`
  sessionVariables (kept `AAV_BRAIN`; dropped `AAV_BRAIN_BIN` + `BRAIN_AGENTS`) are all edited.
- the 12 skills were migrated off the dropped `scripts/` symlinks to the documented mechanism:
  bootstrap via `brain-find` on PATH, every other call via `$AAV_BRAIN/bin/<x>.py`.
the only thing pending is that the home.nix env edit ACTIVATES on `re` (step c). NB pre-cutover: the one
live casualty is brain-self-refine's `$BRAIN_AGENTS` (unset until the agentic-files skills go live at
`re`) - don't run it before cutting over.

## 5. ordered runbook (YOURS - the brain never commits, P09)
already done by the brain (working tree): private memory MOVED to `~/.local/share/aav-brain/{evidence,
trace}`; scripts repointed to `find_data()` (XDG, env-free); `brain/evidence/` + `brain/trace/`
gitignored; aav-brain `brain/` now holds only doctrine. so `git add -A` on aav-brain is SAFE.

### a. private memory -> its own PRIVATE repo (aav-brain-private), submodule of `home`
the public brain must never gitlink to private data, so the private repo hangs off `home` (private),
not off `aav-brain`. seed it from the data already at the XDG dir:
```bash
cd ~/.local/share/aav-brain
git init -b main && git add -A && git commit -m "brain private memory: evidence + trace"
gh repo create arpadav/aav-brain-private --private --source=. --push     # PRIVATE - never flip public
cd ~/repos/personal/home
git submodule add git@github.com:arpadav/aav-brain-private.git aav-brain-private   # clones to home/aav-brain-private
rm -rf ~/.local/share/aav-brain          # data is safe in the submodule+remote; nix re-creates the symlink (§2)
# do NOT run any brain tooling between this rm and the `re` below (find_data would mkdir a stray real dir)
```

### b. public brain repo (aav-brain) - doctrine + scripts + agentic-files only
```bash
cd ~/repos/personal/aav-brain
git init -b main
git status                               # confirm NO evidence/ or trace/ (moved + gitignored)
git add -A                               # safe: private data is gone + gitignored
git diff --cached --name-only | grep -iE 'evidence|trace|secret' && echo "STOP: private staged" || echo "clean"
git commit -m "aav-brain: merge agents, decouple, codex templating, single-repo discovery, min env"
gh repo create arpadav/aav-brain --private --source=. --push    # start private; flip public later after a fresh-eyes pass
```

### c. wire `home` -> both submodules + nix, then switch
```bash
cd ~/repos/personal/home
git submodule add git@github.com:arpadav/aav-brain.git aav-brain
$EDITOR home.nix                         # apply doc sections 1-3 (wiring + activation) + the §2 XDG symlink
re                                       # home-manager switch (creates the .local/share/aav-brain symlink + builds .generated)
```

### d. verify BEFORE removing anything
```bash
brain-find --export                                          # one line: export AAV_BRAIN=...
readlink -e ~/.local/share/aav-brain                         # resolves into home/aav-brain-private
python3 "$AAV_BRAIN/bin/brain-trace.py" --against | head -3   # trace reads from the private memory
#   also: .claude/skills, .claude/agents/{brain,general,rust,custom}, .codex/agents resolve;
#   .generated/codex/agents/*.toml exist; dispatch one skill + one agent on claude AND codex.
```

### e. clean up - ONLY after d verifies
```bash
mv ~/repos/personal/agents ~/repos/personal/.archive-agents  # reversible; keep until certain
cd ~/repos/personal/home
git submodule deinit -f agents && git rm -f agents && rm -rf .git/modules/agents
git config -f .gitmodules --remove-section submodule.agents 2>/dev/null || true
git commit -m "drop agents submodule; superseded by aav-brain + aav-brain-private"
# rm -rf ~/repos/personal/.archive-agents   # only once everything has run clean for a while
```

## 6. post-cutover sweep (phase 5 acceptance)
```bash
# anchored: a bare 'repos/personal/agents' substring also matches 'agentic-files/agents' false-positives
grep -rnE 'repos/personal/agents($|[^a-z/-])' ~/.config/home-manager ~/.claude 2>/dev/null   # expect nothing
readlink -e ~/.claude/skills/* ~/.claude/agents/*/* ~/.codex/agents/* 2>/dev/null | head      # -e: each link RESOLVES
```
done when nothing references the old repo and both surfaces dispatch from the single submodule.
