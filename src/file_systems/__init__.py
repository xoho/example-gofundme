from typing import Any


class FileSystem:
    def get(self, path: str) -> Any:
        raise NotImplementedError()

    def put(self, path: str, obj: Any, ttl: str = "") -> bool:
        raise NotImplementedError()

    def rm(self, path: str) -> bool:
        raise NotImplementedError()

    def exists(self, path: str) -> bool:
        raise NotImplementedError()

    def mkdir(self, path: str) -> bool:
        raise NotImplementedError()

    def ls(self, path: str) -> bool:
        raise NotImplementedError()

    def path_join(self, *args) -> str:
        raise NotImplementedError()


from file_systems.local import LocalFileSystem
from file_systems.weed import WeedFileSystem
