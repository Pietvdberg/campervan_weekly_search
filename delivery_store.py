"""One durable outbox per audience, isolated from discovery observations."""
import base64
from copy import deepcopy
import json
from urllib.error import HTTPError

from search_history import validate as validate_history
from state_store import api

MAX_BYTES = 4 * 1024 * 1024


def empty_state():
    from search_history import empty_state as history
    return {"schema_version": 1, "history": history(), "pending": None, "delivered": []}


def validate(state):
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise ValueError("Invalid delivery state; refusing to reset it")
    validate_history(state.get("history"))
    if not isinstance(state.get("delivered"), list):
        raise ValueError("Invalid delivery confirmations")
    for row in state["delivered"]:
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) for k in ("period", "message_id")):
            raise ValueError("Invalid delivery confirmation")
    pending = state.get("pending")
    if pending is not None:
        if not isinstance(pending, dict) or not all(isinstance(pending.get(k), str) and pending[k] for k in
                ("period", "date", "text", "html", "sender", "mode")):
            raise ValueError("Invalid frozen report")
        validate_history(pending.get("history"))
        if pending["mode"] not in ("production", "development") or not isinstance(pending.get("recipients"), list) or not pending["recipients"]:
            raise ValueError("Invalid frozen report audience")
        mail = pending.get("mail_state")
        if mail is not None and (not isinstance(mail, dict) or not isinstance(mail.get("message_id"), str)
                or mail.get("status") not in ("submitting", "smtp_accepted", "sent_confirmed", "recipients_refused")):
            raise ValueError("Invalid mail submission state")
    return state


class Store:
    def __init__(self, repo, mode, request=api):
        if mode not in ("production", "development"):
            raise ValueError("Invalid delivery audience")
        self.repo, self.mode, self.request = repo, mode, request
        self.branch = "delivery-" + mode
        self.head = None
        try:
            self.head = request(repo, "git/ref/heads/" + self.branch)["object"]["sha"]
        except HTTPError as exc:
            if exc.code != 404:
                raise
            self.state = empty_state()
            return
        commit = request(repo, "git/commits/" + self.head)
        tree = request(repo, "git/trees/" + commit["tree"]["sha"])
        files = [entry for entry in tree["tree"] if entry.get("path") == "delivery_state.json" and entry.get("type") == "blob"]
        if tree.get("truncated") or len(files) != 1:
            raise ValueError("Existing delivery branch lacks its unique state blob")
        blob = request(repo, "git/blobs/" + files[0]["sha"])
        if blob.get("size", 0) > MAX_BYTES:
            raise ValueError("Delivery state exceeds size limit")
        raw = base64.b64decode(blob["content"])
        if len(raw) > MAX_BYTES:
            raise ValueError("Delivery state exceeds size limit")
        self.state = validate(json.loads(raw))

    def save(self, state):
        """A failed checkpoint must abort sending. Never force-update another writer."""
        validate(state)
        content = json.dumps(state, ensure_ascii=False) + "\n"
        if len(content.encode()) > MAX_BYTES:
            raise ValueError("Delivery state exceeds size limit")
        try:
            current = self.request(self.repo, "git/ref/heads/" + self.branch)["object"]["sha"]
        except HTTPError as exc:
            if exc.code != 404:
                raise
            current = None
        if current != self.head:
            raise ValueError("Delivery state advanced; refusing concurrent submission")
        tree = self.request(self.repo, "git/trees", "POST", {"tree": [
            {"path": "delivery_state.json", "mode": "100644", "type": "blob", "content": content}]})
        commit = self.request(self.repo, "git/commits", "POST", {
            "message": "Checkpoint " + self.mode + " report delivery", "tree": tree["sha"],
            "parents": [self.head] if self.head else []})
        if self.head:
            self.request(self.repo, "git/refs/heads/" + self.branch, "PATCH", {"sha": commit["sha"], "force": False})
        else:
            self.request(self.repo, "git/refs", "POST", {"ref": "refs/heads/" + self.branch, "sha": commit["sha"]})
        self.head, self.state = commit["sha"], deepcopy(state)
