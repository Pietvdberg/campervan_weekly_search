import base64
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from search_history import empty_state
from state_store import pull, push


class StateStoreTests(unittest.TestCase):
    def test_initialization_and_isolated_branch_creation(self):
        calls = []
        def request(repo,path,method="GET",data=None):
            calls.append((path,method,data))
            if method == "GET":
                raise HTTPError("https://api.github.com",404,"missing",{},None)
            return {"sha":"created"}
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(pull("owner/repo",folder,request)["initialized"])
            self.assertEqual(push("owner/repo",folder,request)["branch"], "search-state")
        refs = [data for path,method,data in calls if method=="POST" and path=="git/refs"]
        self.assertEqual(refs[0]["ref"], "refs/heads/search-state")

    def test_permission_error_and_corrupt_existing_state_do_not_reset(self):
        def denied(*args):
            raise HTTPError("https://api.github.com",403,"denied",{},None)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(HTTPError):
                pull("owner/repo",folder,denied)
            self.assertFalse((Path(folder)/"search_state.json").exists())
            def corrupt(repo,path,*args):
                if path.startswith("git/ref/"): return {"object":{"sha":"old"}}
                if path.startswith("git/commits/"): return {"tree":{"sha":"tree"}}
                if path.startswith("git/trees/"): return {"tree":[{"path":"search_state.json","type":"blob","sha":"blob"}]}
                return {"content":base64.b64encode(b'{}').decode()}
            with self.assertRaises(ValueError):
                pull("owner/repo",folder,corrupt)

    def test_concurrent_writer_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,"search_state.json").write_text(json.dumps(empty_state()))
            Path(folder,"base.json").write_text(json.dumps({"head":"old"}))
            with self.assertRaisesRegex(ValueError,"advanced"):
                push("owner/repo",folder,lambda *args:{"object":{"sha":"new"}})
