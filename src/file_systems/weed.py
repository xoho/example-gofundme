# wraps calls to weedfs
from typing import Any, Dict, List

from file_systems import FileSystem
from file_systems.weedfs import WeedFS, ListPathException


class NotWrittenWeed(Exception):
    pass


class NotFoundWeed(Exception):
    pass


class ListPathExceptionWeed(Exception):
    pass


class WeedFileSystem(FileSystem):
    def __init__(self, url_base):
        self.wf = WeedFS(url_base=url_base)

    def get(self, path: str) -> Any:
        """gets what ever is at path (if anthing)"""
        res = {}
        try:
            return self.wf.get(path)
        except Exception as exp:
            raise NotFoundWeed(f"Nothing found at {path}")

    def put(self, path: str, obj: Any, ttl: str = "") -> bool:
        if path.endswith("/"):
            raise Exception(f"Cannot put a directory with path {path}")
        try:
            kwargs = dict(path=path, data=obj)
            if ttl:
                kwargs["ttl"] = ttl
            self.wf.put(**kwargs)
            return True
        except Exception as exp:
            raise NotWrittenWeed(f"Could not write data to {path} - (exp: {exp})")

    def rm(self, path: str, recursive: bool = False) -> bool:
        if recursive and self.wf.is_dir(path):
            for entry in [f"{path}/{x}" for x in self.wf.ls(path)]:
                if self.wf.is_dir(entry):
                    self.rm(path=entry, recursive=True)
                else:
                    self.rm(path=entry)

        self.wf.delete(path)
        return True

    def is_dir(self, path: str) -> bool:
        return self.wf.is_dir(path)

    def exists(self, path: str) -> bool:
        return True if self.wf.head(path) else False

    def mkdir(self, path: str) -> bool:
        return self.wf.mkdir(path)

    def ls(self, path: str) -> List[str]:
        try:
            return self.wf.ls(path)
        except ListPathException as exp:
            raise ListPathExceptionWeed(exp)

    def path_join(self, *args) -> str:
        return "/".join(args)

    def mv(self, src_path: str, dst_path: str) -> bool:
        return self.wf.mv(src_path=src_path, dst_path=dst_path)

    def info(self, path: str) -> Dict[str, Any]:
        return self.wf.head(path)

    def vacuum(self, path: str) -> bool:
        # removes folders reverse-recursively if
        # they have no folder or files in them
        # return true when the path no longer exists
        print("vacuum on", path)
        if not self.exists(path):
            print("vacuum path doesnt exist", path)
            return True
        if not self.is_dir(path):
            # file exists, abort the clean on this leaf
            print("vacuum - found a file, aborting", path)
            return False
        # we know it's dir so handle
        entries = self.ls(path) or []
        print("vacuum path", path, "entries", entries)
        if len(entries) == 0:
            print("vacuum - no entries for", path, "deleting")
            self.rm(path)
            return True
        res = []
        for entry in ["/".join([path, x]) for x in entries]:
            res.append(self.vacuum(entry))
        print("vacuum - sub folder results", res)
        if all(res):
            self.rm(path)
        return not self.exists(path)
