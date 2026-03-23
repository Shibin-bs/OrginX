import hashlib
import json
import os
from typing import List

MERKLE_STATE_FILE = "originx_merkle.json"


class MerkleTree:
    def __init__(self):
        self.leaves: List[str] = []
        self._load()

    def _load(self):
        if os.path.exists(MERKLE_STATE_FILE):
            with open(MERKLE_STATE_FILE, "r") as f:
                data = json.load(f)
                self.leaves = data.get("leaves", [])

    def _save(self):
        with open(MERKLE_STATE_FILE, "w") as f:
            json.dump({"leaves": self.leaves}, f)

    def _hash(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    def add_leaf(self, data: str):
        self.leaves.append(self._hash(data))
        self._save()

    def get_root(self) -> str:
        if not self.leaves:
            return self._hash("empty")
        layer = list(self.leaves)
        while len(layer) > 1:
            if len(layer) % 2 == 1:
                layer.append(layer[-1])
            layer = [self._hash(layer[i] + layer[i + 1]) for i in range(0, len(layer), 2)]
        return layer[0]

    def get_proof(self, index: int) -> list:
        if index >= len(self.leaves):
            return []
        proof = []
        layer = list(self.leaves)
        while len(layer) > 1:
            if len(layer) % 2 == 1:
                layer.append(layer[-1])
            sibling = index ^ 1
            proof.append(layer[sibling])
            index //= 2
            layer = [self._hash(layer[i] + layer[i + 1]) for i in range(0, len(layer), 2)]
        return proof

    def verify_leaf(self, data: str, proof: list) -> bool:
        current = self._hash(data)
        for sibling in proof:
            if current < sibling:
                current = self._hash(current + sibling)
            else:
                current = self._hash(sibling + current)
        return current == self.get_root()


merkle_tree = MerkleTree()