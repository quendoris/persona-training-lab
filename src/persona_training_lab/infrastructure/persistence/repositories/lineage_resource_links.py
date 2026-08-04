from __future__ import annotations

import sqlite3
from threading import RLock

from persona_training_lab.application.runtime.operations import ResourceClaim


class SQLiteLineageResourceLinksRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = RLock()

    def replace_links(
        self,
        node_id: str,
        claims: tuple[ResourceClaim, ...],
    ) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "DELETE FROM lineage_resource_links WHERE node_id = ?",
                (node_id,),
            )
            self._connection.executemany(
                """
                INSERT INTO lineage_resource_links (
                    node_id, resource_kind, resource_id, access_mode
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    (
                        node_id,
                        claim.resource_kind,
                        claim.resource_id,
                        claim.access_mode,
                    )
                    for claim in claims
                ),
            )

    def list_links(self, node_id: str) -> tuple[ResourceClaim, ...]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT resource_kind, resource_id, access_mode
                FROM lineage_resource_links
                WHERE node_id = ?
                ORDER BY resource_kind, resource_id
                """,
                (node_id,),
            ).fetchall()
        return tuple(
            ResourceClaim(
                resource_kind=str(row["resource_kind"]),
                resource_id=str(row["resource_id"]),
                access_mode=str(row["access_mode"]),
            )
            for row in rows
        )

    def delete_links(self, node_ids: tuple[str, ...]) -> int:
        if not node_ids:
            return 0
        placeholders = ",".join("?" for _ in node_ids)
        with self._lock, self._connection:
            cursor = self._connection.execute(
                f"DELETE FROM lineage_resource_links "
                f"WHERE node_id IN ({placeholders})",
                node_ids,
            )
        return cursor.rowcount
