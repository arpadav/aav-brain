---
name: naming-audit
description: "Audit and fix names so each file, module, folder, type, service, unit, route and CLI verb says what it does from its name alone - no metaphors (door.py), no vague nouns (utils, model.py), no near-twins - in any language. Load it when arpad asks 'what is X.py?', 'rename', 'these names are bad', 'naming audit', or questions a name; when a plan introduces new files, modules or commands (check them before the plan is shown); and before a build is called done. Lists every failing name with alternatives and a pick, then renames everything and its references in one pass."
---

# naming-audit: every name says what it does

the rule lives in ONE place. READ IT FIRST, in full, before judging any name:
`$AVB/store/principles/principle-76-names-say-what-it-does.md`. an audit run without reading it is
not this skill. [[principle-22-lexical-conventions]] is the lexical layer (casing, imports, `of`/`_x`);
read it too when renaming symbols inside files.

## 1. list every name in scope
not just the new ones, and private names too. one deterministic listing per kind, never eyeballed:
```bash
cd <repo>
git ls-files -co --exclude-standard | while read -r f; do [ -e "$f" ] && echo "$f"; done   # files, incl. new and renamed
git ls-files -co --exclude-standard | grep / | sed 's#/[^/]*$##' | sort -u                 # folders
git branch --format='%(refname:short)'                                                      # branches
```
then the kinds no file listing shows, each by grep over the tree: types (`class `/`struct `/`enum `/
`interface `/`trait `), CLI subcommands (argparse `add_parser`, clap `#[command]`, ...), routes (the
router's match arms or decorators), config keys (the config type's fields), and service/unit files.
private names (`_File`) count: they are read in stack traces and diffs too.

## 2. run the test on each
read only the name and write the one plain sentence of what it does. a name fails if that sentence
needs the code, if it is a metaphor or a vague noun, if it has a near-twin, if it no longer matches
the job, or if a path stutters. each failure gets:
- what it actually does (read the code to find out), in one sentence
- 2-3 alternatives and the pick, e.g. `door.py` -> `version_proxy.py` (pick) / `release_switch.py` / `front_proxy.py`
- the split, when no honest name fits: the thing does two jobs
- a MOVE instead of a rename, when the name is honest but the place is not (a bootstrap that sits in
  `links/` but is not a link) - that half is [[principle-27-organization-reorg]]

twins fail together but only one usually moves: rename the one whose name is less specific to its job,
and keep a name P76 records as an accepted fix unless its job has changed since.
a field's own term passes (`router`, `proxy`, `queue`, `cache`, `kill switch`); a private name
follows [[principle-22-lexical-conventions]] too, so dropping a leading underscore must not create a twin.

## 3. report, then rename
an explicit "report only" always wins: list, rename nothing. otherwise, in a relay or phone session,
take the picks and go (questions ride in the reply); anywhere else show the table and rename on his go.
a rename is one pass:
1. plain `mv` (never `git mv` unless he asked for staging), file and its test together;
2. every reference: imports, the tests, docs and comments, systemd units, scripts, CLI help and
   routes (grep the old name, case-insensitively, across the whole repo and its plans);
   and what lives outside the repo: a renamed config key needs a migration of the existing config
   (keep the old key readable once, then retire it), an installed unit is reinstalled under its new
   name, and outside callers of a renamed CLI verb are found and updated;
3. the project's full test command must pass; a grep of the old name must find only intended
   history (a changelog, a plan describing the rename).
never commit; he commits.

## output
the rename table, ordered files and folders first, then types, then units/commands/routes/config keys,
then private names: old -> pick, the alternatives, one line of why. then anything kept on purpose with
its one-line reason. no prose tour.
