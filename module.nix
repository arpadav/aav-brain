{
  pkgs,
  config,
  lib,
  ...
}:
let
  # --------------------------------------------------
  # every link, and every command's wrapper, points into
  # the live checkout, out of the store, so an edit to a
  # principle, skill or script is live without a switch; a new
  # script needs one to become a command
  # --------------------------------------------------
  root = config.aav.brain.root;
  edit = config.aav.brain.edit;
  agentsRoot = "${root}/agents";
  skillsRoot = "${root}/skills";
  codexAgents = "${root}/.generated/codex/agents";
  live = path: config.lib.file.mkOutOfStoreSymlink path;
  # --------------------------------------------------
  # one skill dir per skill, linked into every agent
  # surface that reads skills
  # --------------------------------------------------
  folders = dir: builtins.attrNames (lib.filterAttrs (_: t: t == "directory") (builtins.readDir dir));
  skills =
    if builtins.pathExists skillsRoot
    then folders skillsRoot
    else throw "aav.brain.root = ${root} holds no skills/ - point it at a brain checkout";
  skillLinks = prefix: builtins.listToAttrs (map (name: {
    name = "${prefix}/${name}";
    value.source = live "${skillsRoot}/${name}";
  }) skills);
  # --------------------------------------------------
  # one link per agent folder, claude reading agents
  # from every folder under ~/.claude/agents
  # --------------------------------------------------
  agentLinks =
    if builtins.pathExists agentsRoot
    then builtins.listToAttrs (map (name: {
      name = ".claude/agents/${name}";
      value.source = live "${agentsRoot}/${name}";
    }) (folders agentsRoot))
    else throw "aav.brain.root = ${root} holds no agents/ - point it at a brain checkout";
  # --------------------------------------------------
  # one command per brain script, read off the checkout,
  # so a new script needs no edit here, only its flags
  # row in COMMANDS (bin/brainlib/cli.py). the rule
  # `Layout.scripts` (bin/brainlib/paths.py) spells: a
  # `b-?*.py` file in bin/ or a folder directly under
  # it but brainlib and __pycache__, neither a symlink
  # (readDir types one "symlink"). its name is the file
  # stem, as `Layout.command` spells it. two scripts
  # with one name stop the switch. each runs under
  # `python3 -I`, the isolation `Layout.private_command`
  # also spells
  # --------------------------------------------------
  binDirs =
    if builtins.pathExists "${root}/bin"
    then builtins.attrNames (lib.filterAttrs
      (dir: type: type == "directory" && !(builtins.elem dir [ "brainlib" "__pycache__" ]))
      (builtins.readDir "${root}/bin"))
    else throw "aav.brain.root = ${root} holds no bin/ - point it at a brain checkout";
  scriptDirs = [ "bin" ] ++ map (dir: "bin/${dir}") binDirs;
  scriptsIn = dir: map (file: "${root}/${dir}/${file}") (builtins.attrNames (lib.filterAttrs
    (file: type: type == "regular" && lib.hasPrefix "b-" file && lib.hasSuffix ".py" file
      && file != "b-.py")
    (builtins.readDir "${root}/${dir}")));
  scripts = lib.concatMap scriptsIn scriptDirs;
  command = script: lib.removeSuffix ".py" (baseNameOf script);
  sharing = lib.filterAttrs (_: same: builtins.length same > 1) (lib.groupBy command scripts);
  commands =
    if sharing != { }
    then throw "aav.brain: scripts share a command: ${lib.concatStringsSep "; " (lib.mapAttrsToList
      (name: same: "${name} <- ${lib.concatStringsSep ", " same}") sharing)}"
    else builtins.listToAttrs (map (script: {
      name = ".local/bin/${command script}";
      value = {
        executable = true;
        text = ''
          #!/usr/bin/env bash
          exec ${pkgs.python3}/bin/python3 -I ${lib.escapeShellArg script} "$@"
        '';
      };
    }) scripts);
  # --------------------------------------------------
  # the edit brain's per-machine data dir, `logs/local`,
  # which ignores itself so none of it is ever staged.
  # the .gitignore's bytes match LOCAL_GITIGNORE in
  # bin/brainlib/paths.py
  # --------------------------------------------------
  local = "${edit}/logs/local";
  ignoreAll = pkgs.writeText "gitignore" "# self-ignoring: per-machine brain data, never committed\n*\n";
in
{
  # --------------------------------------------------
  # where the checkout lives. imported straight off
  # disk, this file's own directory is that checkout; a
  # flake copy of it sits in the store, so a flake sets it
  # --------------------------------------------------
  options.aav.brain.root = lib.mkOption {
    type = lib.types.str;
    default = toString ./.;
    description = "absolute path of the live brain checkout every link points into";
  };
  options.aav.brain.edit = lib.mkOption {
    type = lib.types.nullOr lib.types.str;
    default = null;
    description = "absolute path of the edit copy's brain, where all brain data lives; null when there is none";
  };

  # --------------------------------------------------
  # links into the live checkout, forced: older hand-made
  # symlinks sit where these go, and without force every
  # switch stops on them
  # --------------------------------------------------
  config = {
    home.file = lib.mapAttrs (_: file: file // { force = true; }) (
      skillLinks ".claude/skills"
      // skillLinks ".agents/skills"
      // skillLinks ".codex/skills"
      // agentLinks
      // {
        ".codex/agents".source = live codexAgents;
      }
      // commands
    );
    # --------------------------------------------------
    # his shells and the skills' and agents' text read a
    # brain file off these; the flake reads `AVB` at
    # switch time. no script reads any of them
    #   AVB  the brain everything runs from
    #   AVE  the brain you edit
    # --------------------------------------------------
    home.sessionVariables = {
      AVB = root;
    } // lib.optionalAttrs (edit != null) {
      AVE = edit;
    };
    warnings = lib.optional (edit == null)
      "no edit copy - run /home-setup (or set edit in $XDG_CONFIG_HOME/aav/repos.toml, else ~/.config/aav/repos.toml)";
    # --------------------------------------------------
    # before any link is written, the edit brain's
    # per-machine data dir is made and its self-ignoring
    # .gitignore written, once the logs submodule is
    # checked out
    # --------------------------------------------------
    home.activation.brainData = lib.mkIf (edit != null) (lib.hm.dag.entryBefore [ "writeBoundary" ] ''
      if [ -e ${lib.escapeShellArg "${edit}/logs/.git"} ]; then
        if [ ! -d ${lib.escapeShellArg local} ]; then
          run mkdir -p ${lib.escapeShellArg local}
        fi
        if ! cmp -s ${ignoreAll} ${lib.escapeShellArg "${local}/.gitignore"}; then
          run install -m 644 ${ignoreAll} ${lib.escapeShellArg "${local}/.gitignore"}
        fi
      else
        warnEcho ${lib.escapeShellArg "${edit}/logs is not a checkout of the logs submodule - no brain data dir made"}
      fi
    '');
    # --------------------------------------------------
    # compile codex TOML agents on every switch, under
    # the `-I` every command runs with
    # --------------------------------------------------
    home.activation.brainCompile = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      run ${pkgs.python3}/bin/python3 -I ${lib.escapeShellArg "${root}/bin/render/b-compile.py"} \
        || warnEcho "codex agent compile failed; .generated/ may be stale"
    '';
  };
}
