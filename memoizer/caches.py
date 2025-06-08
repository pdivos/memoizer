from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import List, Union
from memoizer.core import NodeId, CallId, Metadata, datetime_to_str, is_windows
from io import BytesIO
import pickle

class AbstractCache(ABC):
    @abstractmethod
    def write(self, node_id: NodeId, result: object, metadata: Metadata) -> None:
        pass

    @abstractmethod
    def read_result(self, node_id: NodeId) -> object:
        pass

    @abstractmethod
    def read_metadata(self, node_id: NodeId) -> Metadata:
        pass

    @abstractmethod
    def contains(self, node_id: NodeId) -> bool:
        pass

    @abstractmethod
    def remove(self, node_id: NodeId) -> None:
        pass

    @abstractmethod
    def list_node_ids(self) -> List[NodeId]:
        pass

    @abstractmethod
    def list_node_ids_by_call_id(self, call_id: CallId) -> List[NodeId]:
        pass

    @abstractmethod
    def get_latest_node_id_by_call_id(self, call_id: CallId) -> Union[NodeId, None]:
        pass

class NoOpCache(AbstractCache):
    def write(self, node_id: NodeId, result: object, metadata: Metadata) -> None:
        pass

    def read_result(self, node_id: NodeId) -> object:
        pass

    def read_metadata(self, node_id: NodeId) -> Metadata:
        pass

    def contains(self, node_id: NodeId) -> bool:
        return False

    def remove(self, node_id: NodeId) -> None:
        pass

    def list_node_ids(self) -> List[NodeId]:
        return []

    def list_node_ids_by_call_id(self, call_id: CallId) -> List[NodeId]:
        return []

    def get_latest_node_id_by_call_id(self, call_id: CallId) -> Union[NodeId, None]:
        return []

class InMemoryCache(AbstractCache):
    def __init__(self, capacity_bytes = None) -> None:
        self.cache = OrderedDict()
        self.capacity_bytes = capacity_bytes or float("inf")
        self.curren_size_bytes = 0

    def write(self, node_id: NodeId, result: object, metadata: Metadata) -> None:
        value = (result, metadata)
        key = InMemoryCache._key(node_id)
        size = len(_serialize(value))
        if size >= self.capacity_bytes: return
        self.cache[key] = (value, size)
        self.cache.move_to_end(key)
        self.curren_size_bytes += size
        while self.curren_size_bytes > self.capacity_bytes:
            key = next(iter(self.cache))
            self._remove(key)

    def read_result(self, node_id: NodeId) -> object:
        return self._read(node_id)[0]

    def read_metadata(self, node_id: NodeId) -> Metadata:
        return self._read(node_id)[0]
    
    def _read(self, node_id: NodeId):
        key = InMemoryCache._key(node_id)
        self.cache.move_to_end(key)
        return self.cache[key][0]

    def contains(self, node_id: NodeId) -> bool:
        return InMemoryCache._key(node_id) in self.cache

    def remove(self, node_id: NodeId) -> None:
        key = InMemoryCache._key(node_id)
        self._remove(key)

    def _remove(self, key) -> None:
        size = self.cache[key][1]
        self.curren_size_bytes -= size
        del self.cache[key]

    def list_node_ids(self) -> List[NodeId]:
        return list(set([NodeId(_id) for _id in self.cache.keys()]))

    def list_node_ids_by_call_id(self, call_id: CallId) -> List[NodeId]:
        raise NotImplementedError()

    def get_latest_node_id_by_call_id(self, call_id: CallId) -> Union[NodeId, None]:
        raise NotImplementedError()
    
    @staticmethod
    def _key(node_id: NodeId):
        assert type(node_id) is NodeId
        return node_id.id

from os import makedirs, remove, listdir
from os.path import isfile, join

def list_files(path):
    "lists files in a folder"
    onlyfiles = [join(path, f) for f in listdir(path) if isfile(join(path, f))]
    return onlyfiles

def read_file(fullpath, text=False):
    with open(fullpath, 'r' + ('b' if not text else '')) as myfile:
        return myfile.read()

def write_file(fullpath, contents):
    with open(fullpath, 'wb') as f:
        f.write(contents)

def exists_file(path):
    return isfile(path)

def remove_file(path):
    return remove(path)

def makedir(path):
    makedirs(path, exist_ok=True)

class FileCache(AbstractCache):
    _RESULT_EXT = '.res.pickle'
    _METADATA_EXT = '.metadata.pickle'

    def __init__(self, path, inmemory_cache_capacity_bytes = 0) -> None:
        assert path.endswith('/') or (is_windows and path.endswith('\\'))
        self.inmemorycache = InMemoryCache(inmemory_cache_capacity_bytes)
        self.path = path

    def write(self, node_id: NodeId, result: object, metadata: Metadata) -> None:
        _, asof = node_id.to_call_id_and_asof()
        makedir(self._folder(asof))
        write_file(self._fname(node_id, FileCache._RESULT_EXT), _serialize(result))
        write_file(self._fname(node_id, FileCache._METADATA_EXT), _serialize(metadata))
        self.inmemorycache.write(node_id, result, metadata)

    def read_result(self, node_id: NodeId) -> object:
        if self.inmemorycache.contains(node_id):
            return self.inmemorycache.read_result(node_id)
        return _deserialize(read_file(self._fname(node_id, FileCache._RESULT_EXT)))

    def read_metadata(self, node_id: NodeId) -> Metadata:
        if self.inmemorycache.contains(node_id):
            return self.inmemorycache.read_result(node_id)
        return _deserialize(read_file(self._fname(node_id, FileCache._METADATA_EXT)))
    
    def contains(self, node_id: NodeId) -> bool:
        return self.inmemorycache.contains(node_id) or exists_file(self._fname(node_id, FileCache._RESULT_EXT))

    def remove(self, node_id: NodeId) -> None:
        # TODO would be nice clean up empty folder
        remove_file(self._fname(node_id, FileCache._RESULT_EXT))
        remove_file(self._fname(node_id, FileCache._METADATA_EXT))
        if self.inmemorycache.contains(node_id):
            self.inmemorycache.remove(node_id)

    def list_node_ids(self) -> List[NodeId]:
        raise NotImplementedError()

    def list_node_ids_by_call_id(self, call_id: CallId) -> List[NodeId]:
        raise NotImplementedError()

    def get_latest_node_id_by_call_id(self, call_id: CallId) -> Union[NodeId, None]:
        raise NotImplementedError()
    
    def _folder(self, asof):
        asof_folder = datetime_to_str(asof).replace(":","-")
        return f"{self.path}{asof_folder}/"
    
    def _fname(self, node_id: NodeId, extension: str):
        assert type(node_id) is NodeId
        call_id, asof = node_id.to_call_id_and_asof()
        folder = self._folder(asof)
        return folder + call_id.to_fname() + extension
    
    @staticmethod
    def _key(node_id: NodeId):
        assert type(node_id) is NodeId
        return node_id.id

def _serialize(obj: object) -> bytes:
    buffer = BytesIO()
    pickle.dump(obj, buffer)
    return buffer.getvalue()

def _deserialize(buffer: bytes) -> object:
    buf = BytesIO(buffer)
    r = pickle.load(buf)
    buf.close()
    return r