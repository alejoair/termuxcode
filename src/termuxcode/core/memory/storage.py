"""Persistencia genérica en disco (uso interno).

Proporciona métodos para guardar y cargar datos en formato JSON o CSV.
"""
import csv
import json
import os
from typing import Any


class Storage:
    """Clase base para persistencia genérica en disco (uso interno).

    Proporciona métodos genéricos para guardar y cargar datos en
    formato JSON o CSV.
    """

    def __init__(self, base_path: str):
        """Inicializa el storage con un directorio base.

        Args:
            base_path: Directorio base para guardar archivos.
        """
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def save(self, file_name: str, data: Any, format: str = "json") -> None:
        """Guarda datos a disco.

        Args:
            file_name: Nombre del archivo a guardar.
            data: Datos a guardar.
            format: Formato del archivo ("json" o "csv").
        """
        path = os.path.join(self.base_path, file_name)

        if format == "json":
            self._write_json(path, data)
        elif format == "csv":
            self._write_csv(path, data)
        else:
            raise ValueError(f"Formato no soportado: {format}")

    def load(self, file_name: str, format: str = "json") -> Any:
        """Carga datos desde disco.

        Args:
            file_name: Nombre del archivo a cargar.
            format: Formato del archivo ("json" o "csv").

        Returns:
            Datos cargados o None si el archivo no existe.
        """
        path = os.path.join(self.base_path, file_name)

        if not os.path.exists(path):
            return None

        if format == "json":
            return self._read_json(path)
        elif format == "csv":
            return self._read_csv(path)
        else:
            raise ValueError(f"Formato no soportado: {format}")

    def delete(self, file_name: str) -> bool:
        """Elimina un archivo del storage.

        Args:
            file_name: Nombre del archivo a eliminar.

        Returns:
            True si se eliminó, False si no existía.
        """
        path = os.path.join(self.base_path, file_name)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def exists(self, file_name: str) -> bool:
        """Verifica si existe un archivo.

        Args:
            file_name: Nombre del archivo a verificar.

        Returns:
            True si el archivo existe.
        """
        path = os.path.join(self.base_path, file_name)
        return os.path.exists(path)

    # Helpers privados

    def _write_json(self, path: str, data: Any) -> None:
        """Escribe datos en formato JSON."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _read_json(self, path: str) -> Any:
        """Lee datos en formato JSON."""
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_csv(self, path: str, rows: list[list[Any]]) -> None:
        """Escribe datos en formato CSV."""
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)

    def _read_csv(self, path: str) -> list[list[str]]:
        """Lee datos en formato CSV."""
        with open(path, "r", encoding="utf-8") as f:
            return list(csv.reader(f))