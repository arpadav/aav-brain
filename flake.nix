{
  # --------------------------------------------------
  # aav brain, installable on its own: skills + agents
  # linked into claude and codex, plus one command per
  # brain script (module.nix)
  # --------------------------------------------------
  description = "aav brain";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { nixpkgs, home-manager, ... }:
  let
    # --------------------------------------------------
    # the flake is evaluated from a store copy, so the live
    # checkout is named by the caller: $AAV_BRAIN, else the
    # directory the switch runs in
    # --------------------------------------------------
    fromEnv = name:
      let v = builtins.getEnv name;
      in if v != ""
      then v
      else throw "${name} is not set - this flake needs `--impure` and a login environment";
    checkout =
      let explicit = builtins.getEnv "AAV_BRAIN";
      in if explicit != "" then explicit else fromEnv "PWD";
  in
  {
    # --------------------------------------------------
    # the module, for another flake to import
    # --------------------------------------------------
    homeManagerModules.default = ./module.nix;
    # --------------------------------------------------
    # a home for a machine that has only the brain
    # --------------------------------------------------
    homeConfigurations.headless = home-manager.lib.homeManagerConfiguration {
      pkgs = import nixpkgs { system = builtins.currentSystem; };
      modules = [
        ./module.nix
        {
          aav.brain.root = checkout;
          home.username = fromEnv "USER";
          home.homeDirectory = fromEnv "HOME";
          home.stateVersion = "25.11";
          programs.home-manager.enable = true;
        }
      ];
    };
  };
}
