# wraps calls to local file system
import mimetypes
import os
import shutil
from typing import Any, List

from file_systems import FileSystem


class NotFoundLocal(Exception):
    pass


class ListPathExceptionLocal(Exception):
    pass


class LocalFileSystem(FileSystem):
    def _is_text_file_type(self, path: str) -> bool:
        mime_type, _ = mimetypes.guess_type(path)
        mime_type = mime_type or "text/text"
        text_file_types = ["text", "application/json"]  # 'startswith' match
        return (
            True if [x for x in text_file_types if mime_type.startswith(x)] else False
        )

    def get(self, path: str) -> Any:  # file like object
        """gets what ever is at path (if anthing)"""
        try:
            return open(path)
        except:
            raise NotFoundLocal(f"Nothing found at {path}")

    def put(self, path: str, obj: Any, ttl: str = "") -> bool:
        # ttl is ignored, but kept here for compatibility
        write_attr = "wb"
        if self._is_text_file_type(path):
            write_attr = "w"

        with open(path, write_attr) as f:
            if hasattr(obj, "read") and hasattr(obj, "write"):
                f.write(obj.read())
            else:
                if write_attr == "wb":
                    f.write(obj.encode("UTF-8"))
                else:
                    f.write(obj)
        return True

    def rm(self, path: str, recursive: bool = False) -> bool:
        if os.path.exists(path):
            shutil.rmtree(path)

        return True

    def exists(self, path: str) -> bool:
        return os.path.exists(path)

    def mkdir(self, path: str) -> bool:
        os.makedirs(path, exist_ok=True)
        return True

    def ls(self, path: str) -> List[str]:
        try:
            return os.listdir(path)
        except Exception as exp:
            raise ListPathExceptionLocal(exp)

    def path_join(self, *args) -> str:
        return os.path.join(*args)
