import json
from textwrap import dedent
import time

from typing import Mapping, Sequence, Set, TypedDict
import subprocess
from pathlib import Path
import logging
import shlex
from dataclasses import dataclass
import argparse
from datetime import UTC, datetime as DateTime


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def get_cli_args() -> tuple[bool, bool, bool]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--do-download", action="store_true")
    parser.add_argument("--do-code-gen", action="store_true")
    parser.add_argument("--dummy", action="store_true")
    args = parser.parse_args()
    return args.do_download, args.do_code_gen, args.dummy


KNOWN_ROC_REPOS = {
    "bhansconnect/roc-fuzz",
    "hasnep/roc-colors",
    "hasnep/roc-dataframes",
    "hasnep/roc-hex",
    "hasnep/roc-semver",
    "hasnep/roc-svg",
    "jancvanb/roc-random",
    "joseph-salmon/roc-audio-platform-test",
    "jwoudenberg/rvn",
    "kilianvounckx/roc_regex",
    "lukewilliamboswell/basic-ssg",
    "lukewilliamboswell/roc-ansi",
    "lukewilliamboswell/roc-cgi-server",
    "lukewilliamboswell/roc-graphics-mach",
    "lukewilliamboswell/roc-graphics",
    "lukewilliamboswell/roc-gui",
    "lukewilliamboswell/roc-htmx-playground",
    "lukewilliamboswell/roc-masonry-experiment",
    "lukewilliamboswell/roc-package-explorations",
    "lukewilliamboswell/roc-pdf-experiment",
    "lukewilliamboswell/roc-random",
    "lukewilliamboswell/roc-ray",
    "lukewilliamboswell/roc-sdl",
    "lukewilliamboswell/roc-serverless",
    "lukewilliamboswell/roc-tinvyvg",
    "lukewilliamboswell/roc-tui",
    "lukewilliamboswell/roc-wasm4",
    "lukewilliamboswell/roc-zig-package-experiment",
    "lukewilliamboswell/test_port_audio",
    "mulias/roc-array2d",
    "roc-lang/basic-cli",
    "roc-lang/unicode",
    "subtlesplendor/roc-data",
    "subtlesplendor/roc-parser",
}
API_DELAY = 0

Json = str | int | float | bool | Mapping[str, "Json"] | Sequence["Json"] | None
Roc = str | int | float | bool | Mapping[str, "Data"] | Sequence["Data"] | "Tag"


@dataclass
class Tag:
    name: str
    payload: Roc | None = None


def render_roc(data: Roc) -> str:
    match data:
        case Tag():
            return (
                f"{data.name} {render_roc(data.payload)}"
                if data.payload is not None
                else data.name
            )
        case str():
            return f'"{data}"'
        case int():
            return str(data)
        case float():
            return str(data)
        case bool():
            return "Bool.true" if data else "Bool.false"
        case list():
            return f"[{',\n'.join(render_roc(d) for d in data)}]"
        case dict():
            return (
                f"{{ {',\n'.join(f'{k} : {render_roc(v)}' for k, v in data.items())} }}"
            )


class RawRelease(TypedDict):
    tagName: str
    url: str
    assets: list[dict[str, Json]]


class Release:
    @classmethod
    def from_raw_release(cls, raw_release: RawRelease) -> "Release":
        return cls(
            version=raw_release["tagName"].removeprefix("v"),
            url=raw_release["url"],
            asset_url=next((a["url"] for a in raw_release["assets"]), None),
        )

    def __init__(self, version: str, url: str, asset_url: str | None):
        self.version = version
        self.url = url
        self.asset_url = asset_url

    def to_dict(self) -> Json:
        return {
            "version": self.version,
            "url": self.url,
            "asset_url": self.asset_url,
        }

    @classmethod
    def from_dict(cls, release_dict: dict[str, Json]):
        return cls(
            version=release_dict["version"],
            url=release_dict["url"],
            asset_url=release_dict["asset_url"],
        )

    def to_roc(self) -> Roc:
        return {
            "version": self.version,
            "asset": (
                Tag("Url", self.asset_url)
                if self.asset_url is not None
                else Tag("NoAssetUrl")
            ),
            "url": Tag("Url", self.url),
        }


def sort_releases(releases: list[Release]) -> list[Release]:
    return sorted(releases, key=lambda r: r.version, reverse=True)


class RawRepo(TypedDict):
    name: str
    owner: dict[str, str]
    description: str
    homepageUrl: str
    url: str
    releases: list[RawRelease]
    updatedAt: int
    licenseInfo: str | None
    stargazerCount: int


class Repo:
    @classmethod
    def from_raw_repo(cls, raw_repo: RawRepo) -> "Repo":
        return cls(
            name=raw_repo["name"],
            owner=raw_repo["owner"]["login"],
            description=raw_repo["description"],
            homepage_url=(
                raw_repo["homepageUrl"] if raw_repo["homepageUrl"] != "" else None
            ),
            github_url=raw_repo["url"],
            releases=[
                Release.from_raw_release(raw_release)
                for raw_release in raw_repo["releases"]
            ],
            updated_at=int(DateTime.fromisoformat(raw_repo["updatedAt"]).timestamp()),
        )

    def __init__(
        self,
        name: str,
        owner: str,
        description: str,
        homepage_url: str | None,
        github_url: str,
        releases: list[Release],
        updated_at: int,
    ):
        self.name = name
        self.owner = owner
        self.description = description
        self.homepage_url = homepage_url
        self.github_url = github_url
        self.releases = releases
        self.updated_at = updated_at

    def to_dict(self) -> Json:
        return {
            "name": self.name,
            "owner": self.owner,
            "description": self.description,
            "homepage_url": self.homepage_url,
            "github_url": self.github_url,
            "releases": [release.to_dict() for release in self.releases],
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, repo_dict: dict[str, Json]):
        return cls(
            name=repo_dict["name"],
            owner=repo_dict["owner"],
            description=repo_dict["description"],
            homepage_url=repo_dict["homepage_url"],
            github_url=repo_dict["github_url"],
            releases=[
                Release.from_dict(release_dict)
                for release_dict in repo_dict["releases"]
            ],
            updated_at=repo_dict["updated_at"],
        )

    def to_roc(self) -> Roc:
        return {
            "name": self.name,
            "owner": self.owner,
            "description": self.description,
            "homepage": (
                Tag("Url", self.homepage_url)
                if self.homepage_url is not None
                else Tag("NoHomepage")
            ),
            "github": Tag("Url", self.github_url),
            "updatedAt": self.updated_at,
            "releases": [release.to_roc() for release in sort_releases(self.releases)],
        }


class RawData(TypedDict):
    repos: list[RawRepo]
    updatedAt: str


class Data:
    @classmethod
    def from_raw_data(cls, raw_data: RawData) -> "Data":
        return cls(
            repos=[Repo.from_raw_repo(raw_data) for raw_data in raw_data["repos"]],
            updated_at=DateTime.fromisoformat(raw_data["updatedAt"]),
        )

    def __init__(self, repos: list[Repo], updated_at: DateTime) -> None:
        self.repos = repos
        self.updated_at = updated_at

    @classmethod
    def from_dict(cls, data_dict: dict[str, Json]) -> "Data":
        return cls(
            repos=[Repo.from_dict(repo_dict) for repo_dict in data_dict["repos"]],
            updated_at=DateTime.fromisoformat(data_dict["updatedAt"]),
        )

    def to_dict(self) -> dict[str, Json]:
        return {
            "repos": [repo.to_dict() for repo in self.repos],
            "updatedAt": self.updated_at.isoformat(),
        }

    def to_roc(self) -> Roc:
        return {
            "repos": [repo.to_roc() for repo in self.repos],
            "updatedAt": self.updated_at.strftime("%Y-%m-%d"),
        }


def run_gh_cli_command(*args: str) -> str:
    logger.debug(f"Running gh {' '.join(shlex.quote(a) for a in args)}.")
    try:
        result = subprocess.run(["gh", *args], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logger.exception(
            f"Output: {e.stdout.decode('utf-8')}\nError: {e.stderr.decode('utf-8')}"
        )
        raise
    time.sleep(API_DELAY)
    stdout = result.stdout.decode("utf-8")
    logger.debug(f"Output: {stdout}")
    return stdout


def get_repo_ids() -> Set[str]:
    logger.info("Getting repo ids.")
    stdout = run_gh_cli_command(
        "search", "repos", "--language=roc", "--limit=1000", "--json=fullName"
    )
    repos = json.loads(stdout)
    return {r["fullName"] for r in repos}


def get_repo_info(repo_id: str) -> RawRepo:
    logger.info(f"Getting info for {repo_id}.")
    stdout = run_gh_cli_command(
        "repo",
        "view",
        repo_id,
        "--json="
        + ",".join(["description", "homepageUrl", "updatedAt", "url", "owner", "name"]),
    )
    return {**json.loads(stdout), "releases": get_repo_releases(repo_id)}


def get_repo_releases(repo_id: str) -> list[RawRelease]:
    logger.info(f"Getting releases for {repo_id}.")
    stdout = run_gh_cli_command("release", "list", f"--repo={repo_id}")
    tags = [r.split("\t")[2] for r in stdout.splitlines()]
    return [get_release_info(repo_id, tag) for tag in tags]


def get_release_info(repo_id: str, tag: str) -> RawRelease:
    logger.info(f"Getting info for release {tag} in {repo_id}.")
    return json.loads(
        run_gh_cli_command(
            "release", "view", tag, f"--repo={repo_id}", "--json=tagName,assets,url"
        )
    )


def main():
    do_download, do_code_gen, is_dummy = get_cli_args()
    data_folder = Path() / "data"
    src_folder = Path() / "src"
    data_file = data_folder / "data.json"
    if do_download:
        if is_dummy:
            logger.info("Running in dummy mode.")
            data = Data(repos=[], updated_at=DateTime.now(tz=UTC))
        else:
            repo_ids = sorted(
                {repo_id.lower() for repo_id in {*get_repo_ids(), *KNOWN_ROC_REPOS}}
            )
            raw_repos = [get_repo_info(repo_id) for repo_id in repo_ids]
            repos = [Repo.from_raw_repo(raw_repo) for raw_repo in raw_repos]
            data = Data(repos=repos, updated_at=DateTime.now(tz=UTC))
        logger.info(f"Writing to {data_file}.")
        with data_file.open("w") as f:
            json.dump(
                data.to_dict(),
                f,
                indent=2,
            )
    else:
        with data_file.open() as f:
            data_dict = json.load(f)
            data = Data.from_dict(data_dict)

    if do_code_gen:
        roc_output_file = src_folder / "Data.roc"
        logger.info(f"Writing to {roc_output_file}.")
        with roc_output_file.open("w") as f:
            f.write(
                dedent(
                    """
                    interface Data exposes [data] imports []

                    Release : { version : Str, url : [Url Str], asset : [Url Str, NoAssetUrl] }
                    Repo : {
                        name : Str,
                        owner : Str,
                        description : Str,
                        homepage : [Url Str, NoHomepage],
                        github : [Url Str],
                        updatedAt : U64,
                        releases : List Release
                    }
                    data : {repos:List Repo,updatedAt:Str}
                    data =
                    """
                ).rstrip()
                + render_roc(data.to_roc())
            )


if __name__ == "__main__":
    main()
