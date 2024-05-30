import inspect
from io import BytesIO, StringIO
import mimetypes
import logging
import os
import json
import time
from typing import Any, Dict, List, Type, TypeVar

import arrow
from pydantic import BaseModel

from config import config
from file_systems import FileSystem, LocalFileSystem, WeedFileSystem
import models
from utils import gen_random

from file_systems.weed import ListPathExceptionWeed
from file_systems.local import ListPathExceptionLocal


T = TypeVar("T", bound=BaseModel)
sep = config.PATH_SEPERATOR


class NotFound(Exception):
    pass


class NotWritten(Exception):
    pass


class ListPathException(Exception):
    pass


class LoadOjbectException(Exception):
    pass


class EntryLock:
    def __init__(self, path: str, fs: FileSystem, timeout: int = 1):
        # timeout in seconds
        self.path = path + ".lock"
        self.timeout = timeout
        self.fs = fs

    def __enter__(self):
        # see if we need to cleanup hung lock
        info = self.fs.info(self.path)
        while info:
            modified = info.get("Last-Modified", None)
            if not modified:
                self.fs.rm(self.path)
                break
            else:
                if (
                    arrow.utcnow()
                    - arrow.get(modified, "ddd, DD MMM YYYY HH:mm:ss ZZZ")
                ).seconds > self.timeout:
                    self.fs.rm(self.path)
                    break
            time.sleep(1)

        self.fs.put(self.path, obj=StringIO(""), ttl="1m")
        # ^^ min ttl is 1m so create with ttl to guarentee removal
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fs.exists(self.path):
            self.fs.rm(self.path)


class DataManager:
    def __init__(self, file_system: FileSystem, base_folder: str):
        self.fs = file_system
        self.base_folder = base_folder
        self.fs.mkdir(self.base_folder)

    def _get_full_path(self, path: str) -> str:
        base_folder = self.base_folder
        if not path.startswith(base_folder):
            return sep.join([base_folder, path])
        return path

    def save(self, obj: T) -> bool:
        parent_path = self._get_full_path(obj.get_parent_path())
        if not self.exists(path=parent_path):
            self.mkdir(path=parent_path)
        self.fs.put(
            path=self._get_full_path(obj.get_relative_path()),
            obj=json.dumps(obj.dict(), indent=4, default=str),
            ttl=obj.get_ttl(),
        )
        return True

    def put(self, path: str, obj: Any, ttl: str = "", with_lock: bool = False) -> bool:
        # puts any object into fs
        if with_lock:
            with EntryLock(path, self.fs) as lock:
                self.fs.put(path=self._get_full_path(path), obj=obj, ttl=ttl)
        else:
            self.fs.put(path=self._get_full_path(path), obj=obj, ttl=ttl)
        return True

    def ls(self, path: str) -> List[str]:
        full_path = self._get_full_path(path)
        try:
            return self.fs.ls(path=full_path)
        except ListPathExceptionLocal as exp:
            raise ListPathException(exp)
        except ListPathExceptionWeed as exp:
            raise ListPathException(exp)

    def loaddir(self, path: str, model_type: Type[T] = None) -> List[Any]:
        res = []
        for entry in [sep.join([path, x]) for x in self.ls(path)]:
            res.append(self.load(sep.join([entry, "data.json"]), model_type=model_type))
        return res

    def get(self, path: str) -> Any:  # file like object
        _path = self._get_full_path(path)
        return self.fs.get(_path)

    def load(self, path: str, model_type: Type[T] = None) -> T:
        # loads the data as an object
        try:
            data = json.load(self.fs.get(self._get_full_path(path)))
        except Exception as exp:
            raise LoadOjbectException(f"Could not load data at {path} (exp: {exp})")
        res = None
        if not model_type:
            for klass in [
                obj
                for name, obj in inspect.getmembers(models)
                if inspect.isclass(obj)
                and name not in ["Base0", "BaseModel", "CategoryBase"]
            ]:
                try:
                    res = klass(**data)
                    break
                except Exception as exp:
                    # load didn't work, try next model
                    pass
        else:
            try:
                res = model_type(**data)
            except Exception as exp:
                raise LoadOjbectException(exp)
        # update created and modified to reflect original data
        for k in ["created", "modified"]:
            if data.get(k, None):
                setattr(res, k, data.get(k))
        return res

    def rm(self, path: str, recursive: bool = False) -> bool:
        _path = self._get_full_path(path)
        res = self.fs.rm(_path, recursive=recursive)
        return True

    def mv(self, src_path: str, dst_path: str) -> bool:
        _src_path = self._get_full_path(src_path)

        _dst_path = self._get_full_path(dst_path)
        dirname = sep.join(_dst_path.split(sep)[0:-1])
        self.fs.mkdir(dirname)
        return self.fs.mv(src_path=_src_path, dst_path=_dst_path)

    def get_dir_key_value(self, path: str) -> Dict[str, str]:
        _path = self._get_full_path(path)
        res = dict()
        for key in self.fs.ls(_path):
            for val in self.fs.ls(sep.join([_path, key])):
                res[key] = val
        return res

    def mkdir(self, path) -> bool:
        _path = self._get_full_path(path)
        res = self.fs.mkdir(_path)
        return True

    def exists(self, path) -> bool:
        _path = self._get_full_path(path)
        try:
            res = self.fs.exists(_path)
            return True if res else False
        except Exception as exp:
            # path does not exist
            pass
        return False


def get_data_manager(file_system_type: str = "") -> DataManager:
    _file_system_type = (
        file_system_type if file_system_type else config.FILE_SYSTEM_TYPE
    )
    _file_system_type = _file_system_type.lower()
    file_system = None
    base_folder = None

    extra_info = ""
    if _file_system_type == "localfs":
        base_folder = config.LOCAL_BASE_FOLDER
        file_system = LocalFileSystem()
    elif _file_system_type == "weedfs":
        base_folder = config.WEEDFS_BASE_FOLDER
        file_system = WeedFileSystem(url_base=config.WEEDFS_FILER_URL)
        extra_info = f"at Weedfs url of {config.WEEDFS_FILER_URL} "
    else:
        raise ValueError(f"Unknown file system type {_file_system_type}")

    return DataManager(file_system, base_folder)


if __name__ == "__main__":
    d = get_data_manager()
    base_folder = "/data"
    for entry in [
        "/".join([base_folder, x])
        for x in d.fs.ls(base_folder)
        if x not in ["admin", "LatLonIndex", "User", "EmailUserIndex"]
    ]:
        print(entry, d.fs.vacuum(entry))
