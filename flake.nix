{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    roc.url = "github:roc-lang/roc?rev=f8c6786502bc253ab202a55e2bccdcc693e549c8";
  };

  nixConfig = {
    extra-trusted-public-keys = "roc-lang.cachix.org-1:6lZeqLP9SadjmUbskJAvcdGR2T5ViR57pDVkxJQb8R4=";
    extra-trusted-substituters = "https://roc-lang.cachix.org";
  };

  outputs = inputs @ {
    self,
    nixpkgs,
    flake-parts,
    roc,
    ...
  }:
    flake-parts.lib.mkFlake {inherit inputs;} {
      systems = ["aarch64-darwin" "aarch64-linux" "x86_64-darwin" "x86_64-linux"];
      perSystem = {
        inputs',
        pkgs,
        ...
      }: {
        devShells.default = pkgs.mkShell {
          name = "roc-packages";
          packages = [
            inputs'.roc.packages.cli
            pkgs.actionlint
            pkgs.alejandra
            pkgs.check-jsonschema
            pkgs.just
            pkgs.nodePackages.prettier
            pkgs.pre-commit
            pkgs.python312
            pkgs.python312Packages.pre-commit-hooks
            pkgs.ruff
          ];
          shellHook = "pre-commit install --overwrite";
        };
        formatter = pkgs.alejandra;
      };
    };
}
