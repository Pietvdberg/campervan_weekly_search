"""Upload validated RSS snapshot to a single GitHub repository file.

Requires GH_RSS_TOKEN with Contents: read/write scoped to this repository.
Does NOT trigger workflow_dispatch or send mail. Keep token out of repo/logs.
"""
import base64
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import quote

from autowereld_snapshot import read_snapshot_records

REPO="Pietvdberg/campervan_weekly_search"
DEST="data/autowereld_rss_snapshot.json"
API=f"https://api.github.com/repos/{REPO}/contents/{DEST}"

def request(method,url,token,payload=None):
    raw=None if payload is None else json.dumps(payload).encode("utf-8")
    req=Request(url,data=raw,method=method,headers={
        "Accept":"application/vnd.github+json",
        "Authorization":"Bearer "+token,
        "X-GitHub-Api-Version":"2022-11-28",
        "User-Agent":"CamperVanResearch-RSS-Handoff/1.0",
        **({"Content-Type":"application/json"} if raw is not None else {}),
    })
    with urlopen(req,timeout=20) as res:
        return json.load(res)

def upload(path):
    token=os.environ.get("GH_RSS_TOKEN","")
    if not token:raise RuntimeError("GH_RSS_TOKEN not set: only local collection performed")
    records,status=read_snapshot_records(path)
    if status!="fresh_index_only" or not records:
        raise RuntimeError("No fresh validated RSS snapshot: "+status)
    data=Path(path).read_bytes()
    url=API+"?ref=main"
    try:
        previous=request("GET",url,token)
        sha=previous["sha"]
    except HTTPError as exc:
        if exc.code!=404:raise
        sha=None
    payload={"message":"data: refresh public AutoWereld RSS index (unverified)",
             "branch":"main","content":base64.b64encode(data).decode("ascii")}
    if sha:payload["sha"]=sha
    request("PUT",API,token,payload)
    print("Uploaded validated RSS index:",len(records),"unverified leads; no workflow dispatched")

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("path",nargs="?",default="data/autowereld_rss_snapshot.json")
    upload(p.parse_args().path)
