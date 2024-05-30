# wrap calls to seaweedfs
from io import BytesIO, StringIO
import json
import logging
import mimetypes
import os
from typing import Any, Dict, List
from urllib.parse import quote, urlencode, urljoin, urlsplit, urlunparse
import requests


class ListPathException(Exception):
    pass


class MoveException(Exception):
    pass


class WeedFS:
    def __init__(self, url_base: str):
        self.url_base = url_base
        parts = urlsplit(self.url_base)

        self.scheme = parts.scheme
        self.hostname = parts.hostname
        if parts.port:
            self.hostname += f":{parts.port}"

        self.headers = {"accept": "application/json"}

        self.text_file_types = ["text", "application/json"]  # 'startswith' match

    def _is_text_file_type(self, content_type: str) -> bool:
        return (
            True
            if [x for x in self.text_file_types if content_type.startswith(x)]
            else False
        )

    def get(self, path: str) -> Any:  # file like object
        url = urljoin(self.url_base, quote(path))
        rsp = None
        try:
            rsp = requests.get(url)
        except Exception as exp:
            raise Exception(f"Error GETing {url}. (exp: {exp}")
        if not rsp.ok:
            raise Exception(
                f"Error GETing {url}. (exp: response not ok - {rsp.ok} / {rsp.status_code}"
            )
        if self._is_text_file_type(rsp.headers.get("Content-Type", "")):
            return StringIO(rsp.content.decode())
        return BytesIO(rsp.content)

    def is_dir(self, path: str) -> bool:
        url = urljoin(self.url_base, quote(path))
        entries = []
        try:
            rsp = requests.get(url, headers=self.headers)
            if not rsp.ok:
                return False
            # only files have etag in header
            if "Etag" in rsp.headers:
                return False
        except Exception as exp:
            return False
        return True

    def put(self, path: str, data: Any, **kwargs) -> bool:
        query_string = urlencode(kwargs)
        url = urlunparse(
            (self.scheme, self.hostname, quote(path), "", query_string, "")
        )

        fp = None
        if hasattr(data, "read") and hasattr(data, "write"):
            fp = data
        else:
            if self._is_text_file_type(path):
                fp = StringIO(data)
            else:
                fp = BytesIO(data.encode("UTF-8"))

        fp.seek(0)

        try:
            rsp = requests.post(url, files={"file": fp})
            if rsp.ok:
                return True
            else:
                raise Exception(f"{rsp.status_code} POST {url}")
        except Exception as exp:
            raise Exception(f"Error POSTing url. (exp: {exp})")
        return False

    def delete(self, path: str) -> bool:
        url = urljoin(self.url_base, quote(path))
        try:
            rsp = requests.delete(url)
            if not rsp.ok:
                raise Exception(f"{rsp.status_code} DELETE {url}")
            return True
        except Exception as exp:
            raise Exception(f"Error deleting file: {path} (exp: {exp})")

    def ls(self, path: str, only_filenames=True) -> List[str]:
        _path = path if path.endswith("/") else (path + "/")
        url = urljoin(self.url_base, quote(_path))

        headers = {"Accept": "application/json"}
        data = []
        try:
            rsp = requests.get(url, headers=headers)
            if not rsp.ok:
                raise Exception(f"{rsp.status_code} GET {url}")
            data = rsp.json()
        except Exception as exp:
            raise ListPathException(f"Error listing path (exp: {exp})")
        entries = data.get("Entries", [])

        # sort by create date, ascending
        if entries:
            entries = sorted(entries, key=lambda x: x.get("Crtime"))

        if entries and only_filenames:
            return [os.path.basename(x.get("FullPath", "")) for x in entries]

        return data.get("Entries", [])

    def head(self, path: str) -> Dict[str, str]:
        url = urljoin(self.url_base, quote(path))
        headers = {"Accept": "application/json"}

        try:
            rsp = requests.head(url, headers=headers)
            if rsp.status_code == 404:
                return {}
            if not rsp.ok:
                raise Exception(f"{rsp.status_code} HEAD {url}")
            return rsp.headers
        except Exception as exp:
            raise Exception(f"Error 'heading' {path} (exp: {exp})")
        return {}

    def mkdir(self, directory: str, exists_ok: bool = True) -> bool:
        if exists_ok:
            try:
                res = self.head(directory)
                if res:
                    return True  # if the directory already exists, return true
            except Exception as exp:
                # print(f"Could not head {directory} (exp: {exp})")
                pass
        try:
            return self.put(data=StringIO(" "), path=f"{directory}/.info")
        except Exception as exp:
            raise Exception(f"Could not mkdir {directory} (exp: {exp})")

    def mv(self, src_path: str, dst_path: str) -> bool:
        # > curl -X POST 'http://localhost:8888/path/to/dst_file?mv.from=/path/to/src_file'
        url = urljoin(self.url_base, quote(dst_path)) + "?mv.from=" + quote(src_path)
        try:
            rsp = requests.post(url)
            return True
        except Exception as exp:
            raise MoveException(f"Could not move {src_path} to {dst_path} (exp:{exp})")
