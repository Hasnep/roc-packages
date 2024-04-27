default: code_gen format check run

download:
    mkdir -p {{ justfile_directory() / "data" }}
    python3.12 {{ justfile_directory() / "scripts" / "get_data.py" }} --do-download

download_dummy:
    mkdir -p {{ justfile_directory() / "data" }}
    python3.12 {{ justfile_directory() / "scripts" / "get_data.py" }} --do-download --dummy

code_gen:
    python3.12 {{ justfile_directory() / "scripts" / "get_data.py" }} --do-code-gen
    roc format {{ justfile_directory() / "src" / "Data.roc" }}

format:
    roc format {{ justfile_directory() / "src" }}

check:
    roc check {{ justfile_directory() / "src" / "main.roc" }}

run:
    mkdir -p {{ justfile_directory() / "dist" }}
    roc dev {{ justfile_directory() / "src" / "main.roc" }}
    cp {{ justfile_directory() / "data" / "data.json" }} {{ justfile_directory() / "dist" / "data.json" }}
