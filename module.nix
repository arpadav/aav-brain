{
  pkgs,
  config,
  lib,
  ...
}:
let
  # --------------------------------------------------
  # every link points into the live checkout, out of the
  # store, so an edit to a card or skill is live without
  # a switch
  # --------------------------------------------------
  root = config.aav.brain.root;
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
        ".local/share/aav-brain".source = live "${root}/logs";
        ".local/bin/brain-find" = {
          executable = true;
          text = ''
            #!/usr/bin/env bash
            exec ${pkgs.python3}/bin/python3 "${root}/bin/brain-find.py" "$@"
          '';
        };
      }
    );
    # --------------------------------------------------
    # scripts find the brain through this variable
    # --------------------------------------------------
    home.sessionVariables.AAV_BRAIN = root;
    # --------------------------------------------------
    # compile codex TOML agents on every switch
    # --------------------------------------------------
    home.activation.brainCompile = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      run ${pkgs.python3}/bin/python3 "${root}/bin/store/compile.py" \
        || warnEcho "codex agent compile failed; .generated/ may be stale"
    '';
  };
}
