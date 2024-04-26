{
  inputs = {
    nixpkgs.url = "github:cachix/devenv-nixpkgs/rolling";
    systems.url = "github:nix-systems/default";
    devenv = {
      url = "github:cachix/devenv";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    roc = {
      url = "github:roc-lang/roc?rev=d67ba43d494c90b676fa485212947dd251570613";
    };
  };

  nixConfig = {
    extra-trusted-public-keys = [
      "devenv.cachix.org-1:w1cLUi8dv3hnoSPGAuibQv+f9TZLr6cv/Hm9XgU50cw="
      "roc-lang.cachix.org-1:6lZeqLP9SadjmUbskJAvcdGR2T5ViR57pDVkxJQb8R4="
    ];
    extra-trusted-substituters = ["https://devenv.cachix.org" "https://roc-lang.cachix.org"];
  };

  outputs = {
    self,
    nixpkgs,
    devenv,
    systems,
    roc,
    ...
  } @ inputs: let
    forEachSystem = nixpkgs.lib.genAttrs (import systems);
  in {
    packages = forEachSystem (system: {
      devenv-up = self.devShells.${system}.default.config.procfileScript;
    });

    devShells =
      forEachSystem
      (system: let
        pkgs = nixpkgs.legacyPackages.${system};
      in {
        default = devenv.lib.mkShell {
          inherit inputs pkgs;
          modules = [
            {
              # https://devenv.sh/reference/options/
              name = "roc-packages";
              packages = [
                roc.packages.${system}.cli
                pkgs.alejandra
                pkgs.just
                pkgs.pre-commit
                pkgs.python312
              ];
              enterShell = "pre-commit install";
            }
          ];
        };
      });
  };
}
