"""Read/persist search state on an isolated GitHub branch with optimistic locking."""
import argparse
import base64
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from search_history import empty_state, validate

BRANCH = "search-state"


def api(repo, path, method="GET", data=None):
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise ValueError("GH_TOKEN is required for state storage")
    request = Request("https://api.github.com/repos/" + repo + "/" + path,
                      data=json.dumps(data).encode() if data is not None else None, method=method,
                      headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json", "Content-Type": "application/json"})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def pull(repo, directory, request=api, branch=BRANCH):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        ref = request(repo, "git/ref/heads/" + branch)
    except HTTPError as exc:
        if exc.code != 404:
            raise
        state, head = empty_state(), None
    else:
        head = ref["object"]["sha"]
        # Missing/corrupt state on an existing branch must fail, never reset it.
        commit = request(repo, "git/commits/" + head)
        tree = request(repo, "git/trees/" + commit["tree"]["sha"])
        files = [entry for entry in tree["tree"] if entry.get("path") == "search_state.json" and entry.get("type") == "blob"]
        if len(files) != 1 or tree.get("truncated"):
            raise ValueError("Existing state branch lacks its unique state blob")
        blob = request(repo, "git/blobs/" + files[0]["sha"])
        state = validate(json.loads(base64.b64decode(blob["content"], validate=False)))
    (directory / "search_state.json").write_text(json.dumps(state, indent=2) + "\n")
    (directory / "base.json").write_text(json.dumps({"head": head}) + "\n")
    return {"initialized": head is None, "head": head}


def push(repo, directory, request=api, branch=BRANCH):
    directory = Path(directory)
    state = validate(json.loads((directory / "search_state.json").read_text()))
    head = json.loads((directory / "base.json").read_text())["head"]
    try:
        current = request(repo, "git/ref/heads/" + branch)["object"]["sha"]
    except HTTPError as exc:
        if exc.code != 404:
            raise
        current = None
    if current != head:
        raise ValueError("Search state advanced since this run; refusing to overwrite it")
    tree = request(repo, "git/trees", "POST", {"tree": [{"path": "search_state.json", "mode": "100644", "type": "blob", "content": json.dumps(state, indent=2) + "\n"}]})
    commit = request(repo, "git/commits", "POST", {"message": "Record bounded camper search history", "tree": tree["sha"], "parents": [head] if head else []})
    if head:
        request(repo, "git/refs/heads/" + branch, "PATCH", {"sha": commit["sha"], "force": False})
    else:
        request(repo, "git/refs", "POST", {"ref": "refs/heads/" + branch, "sha": commit["sha"]})
    return {"branch": branch, "sha": commit["sha"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("pull", "push"))
    p.add_argument("--repo", required=True)
    p.add_argument("--directory", default=".search-state")
    p.add_argument("--branch", default=BRANCH)
    args = p.parse_args()
    print(json.dumps((pull if args.action == "pull" else push)(args.repo, args.directory, branch=args.branch)))


if __name__ == "__main__":
    main()
