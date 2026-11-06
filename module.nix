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
  agentsRoot = "${root}/agentic-files/agents";
  skillsRoot = "${root}/agentic-files/skills";
  codexAgents = "${root}/.generated/codex/agents";
  live = path: config.lib.file.mkOutOfStoreSymlink path;
  # --------------------------------------------------
  # one skill dir per skill, linked into every agent
  # surface that reads skills
  # --------------------------------------------------
  skills =
    if builtins.pathExists skillsRoot
    then builtins.attrNames (lib.filterAttrs (_: t: t == "directory") (builtins.readDir skillsRoot))
    else throw "aav.brain.root = ${root} holds no agentic-files/skills - point it at a brain checkout";
  skillLinks = prefix: builtins.listToAttrs (map (name: {
    name = "${prefix}/${name}";
    value.source = live "${skillsRoot}/${name}";
  }) skills);
  # --------------------------------------------------
  # one command per brain script, read off the checkout,
  # so a new script needs no edit here, only its flags
  # row in COMMANDS (bin/brainlib/tool.py). the rule
  # `Layout.scripts` (bin/brainlib/paths.py) spells: a
  # `brain-?*.py` file in bin/ or a folder directly
  # under it but brainlib and __pycache__, neither a
  # symlink (readDir types one "symlink"). its name is
  # `b-`, then the file stem past `brain-`, which must
  # match `Layout.command`. two scripts with one name
  # stop the switch. each runs under `python3 -I`, the
  # isolation `Layout.private_command` also spells
  # --------------------------------------------------
  binDirs =
    if builtins.pathExists "${root}/bin"
    then builtins.attrNames (lib.filterAttrs
      (dir: type: type == "directory" && !(builtins.elem dir [ "brainlib" "__pycache__" ]))
      (builtins.readDir "${root}/bin"))
    else throw "aav.brain.root = ${root} holds no bin/ - point it at a brain checkout";
  scriptDirs = [ "bin" ] ++ map (dir: "bin/${dir}") binDirs;
  scriptsIn = dir: map (file: "${root}/${dir}/${file}") (builtins.attrNames (lib.filterAttrs
    (file: type: type == "regular" && lib.hasPrefix "brain-" file && lib.hasSuffix ".py" file
      && file != "brain-.py")
    (builtins.readDir "${root}/${dir}")));
  scripts = lib.concatMap scriptsIn scriptDirs;
  command = script: "b-${lib.removePrefix "brain-" (lib.removeSuffix ".py" (baseNameOf script))}";
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
  # the per-machine data dirs under the data home
  # (`$XDG_DATA_HOME`, else ~/.local/share, the rule
  # the tools that wrote them used) and their place
  # under the edit brain's `logs/local`, which ignores
  # itself so none of it is ever staged. the dirs and
  # the .gitignore's bytes match the local layout and
  # LOCAL_GITIGNORE in bin/brainlib/paths.py
  # --------------------------------------------------
  local = "${edit}/logs/local";
  localData = {
    aav-brain-archive = "archive";
    aav-brain-gate = "gate";
    aav-brain-served = "sessions/recall";
    aav-brain-walked = "sessions/walk";
  };
  ignoreAll = pkgs.writeText "gitignore" "# self-ignoring: per-machine brain data, never committed\n*\n";
  moveData = lib.concatStrings (lib.mapAttrsToList (from: to: let
    target = "${local}/${to}";
  in ''
    if [ -e "$brainShared"/${lib.escapeShellArg from} ]; then
      if [ ! -e ${lib.escapeShellArg target} ]; then
        run mkdir -p ${lib.escapeShellArg (dirOf target)}
        run mv "$brainShared"/${lib.escapeShellArg from} ${lib.escapeShellArg target}
      else
        warnEcho "$brainShared"/${lib.escapeShellArg "${from} and ${target} both exist - merge them by hand"}
      fi
    fi
  '') localData);
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
      // {
        ".claude/agents/brain".source = live "${agentsRoot}/brain";
        ".claude/agents/general".source = live "${agentsRoot}/general";
        ".claude/agents/rust".source = live "${agentsRoot}/lang/rust";
        ".claude/agents/style".source = live "${agentsRoot}/style";
        ".codex/agents".source = live codexAgents;
      }
      // commands
    );
    # --------------------------------------------------
    # his shells and the skills' and agents' text read a
    # brain file off these; the flake reads `AAV_BRAIN`
    # at switch time. no script reads any of them
    #   AVB  the brain everything runs from
    #   AVE  the brain you edit
    # --------------------------------------------------
    home.sessionVariables = {
      AAV_BRAIN = root;
      AVB = root;
    } // lib.optionalAttrs (edit != null) {
      AVE = edit;
    };
    warnings = lib.optional (edit == null)
      "no edit copy - run /home-setup (or set edit in $XDG_CONFIG_HOME/aav/repos.toml, else ~/.config/aav/repos.toml)";
    # --------------------------------------------------
    # before any link is written, each per-machine data
    # dir moves under the edit brain's logs when its
    # target does not exist yet, so a second run moves
    # nothing; with both present it warns and moves
    # neither. home-manager's own cleanup of links an
    # older generation made removes the old
    # `.local/share/aav-brain` link
    # --------------------------------------------------
    home.activation.brainData = lib.mkIf (edit != null) (lib.hm.dag.entryBefore [ "writeBoundary" ] ''
      brainShared=''${XDG_DATA_HOME:-}
      brainShared=''${brainShared/#\~/$HOME}
      case $brainShared in
        /*) ;;
        *) brainShared=$HOME/.local/share ;;
      esac
      if [ -e ${lib.escapeShellArg "${edit}/logs/.git"} ]; then
        if [ ! -d ${lib.escapeShellArg local} ]; then
          run mkdir -p ${lib.escapeShellArg local}
        fi
        if ! cmp -s ${ignoreAll} ${lib.escapeShellArg "${local}/.gitignore"}; then
          run install -m 644 ${ignoreAll} ${lib.escapeShellArg "${local}/.gitignore"}
        fi
        ${moveData}
      else
        warnEcho ${lib.escapeShellArg "${edit}/logs is not a checkout of the logs submodule - brain data left under "}"$brainShared"
      fi
    '');
    # --------------------------------------------------
    # compile codex TOML agents on every switch, under
    # the `-I` every command runs with
    # --------------------------------------------------
    home.activation.brainCompile = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      run ${pkgs.python3}/bin/python3 -I ${lib.escapeShellArg "${root}/bin/store/brain-compile.py"} \
        || warnEcho "codex agent compile failed; .generated/ may be stale"
    '';
  };
}
