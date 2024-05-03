root_dir := justfile_directory()
data_dir := root_dir / "data"
src_dir := root_dir / "src"
dist_dir := root_dir / "dist"
scripts_dir := root_dir / "scripts"
get_data_script := scripts_dir / "get_data.py"

default: code_gen format check run

download:
    mkdir -p {{ data_dir }}
    python3.12 {{ get_data_script }} --do-download {{ if env("DUMMY") == "true" { "--dummy" } else { "" } }}

code_gen:
    python3.12 {{ get_data_script }} --do-code-gen
    roc format {{ src_dir / "Data.roc" }}

format:
    roc format {{ src_dir }}

check:
    roc check {{ src_dir / "main.roc" }}

run:
    mkdir -p {{ dist_dir }}
    roc dev {{ src_dir / "main.roc" }}
    cp {{ data_dir / "data.json" }} {{ dist_dir / "data.json" }}
