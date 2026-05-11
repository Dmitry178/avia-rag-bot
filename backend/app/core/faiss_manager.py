"""FAISS vector index build and persistence."""

import asyncio
import faiss
import numpy as np

from pathlib import Path


class FaissManager:
    """
    Build and persist FAISS IndexFlatIP (L2-normalized inner-product search).
    """

    @staticmethod
    def _build_index(vectors: list[list[float]]) -> faiss.IndexFlatIP:
        """
        Build an in-memory FAISS index with L2-normalized vectors.
        """

        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[0] == 0:
            raise ValueError("Cannot build FAISS index from empty embeddings")

        faiss.normalize_L2(matrix)
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        
        return index

    @staticmethod
    def _write_index(index: faiss.IndexFlatIP, path: Path) -> None:
        """
        Atomically write FAISS index to disk.
        """

        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        faiss.write_index(index, str(temp_path))
        temp_path.replace(path)

    def build_and_save(self, vectors: list[list[float]], path: Path) -> None:
        """
        Build FAISS IndexFlatIP and persist to the given path.
        """

        index = self._build_index(vectors)
        self._write_index(index, path)

    async def save_async(self, vectors: list[list[float]], path: Path) -> None:
        """
        Run FAISS index build/write in a worker thread.
        """

        await asyncio.to_thread(self.build_and_save, vectors, path)

    @staticmethod
    def reconstruct_vectors(path: Path) -> list[list[float]]:
        """
        Load a persisted index and reconstruct all stored vectors.
        """

        if not path.is_file():
            return []

        index = faiss.read_index(str(path))
        if index.ntotal == 0:
            return []

        return [index.reconstruct(row).tolist() for row in range(index.ntotal)]

    async def reconstruct_vectors_async(self, path: Path) -> list[list[float]]:
        """
        Run FAISS vector reconstruction in a worker thread.
        """

        return await asyncio.to_thread(self.reconstruct_vectors, path)


faiss_manager = FaissManager()
