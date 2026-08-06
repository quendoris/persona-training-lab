from __future__ import annotations

import sqlite3
from collections.abc import Mapping

from persona_training_lab.application.runtime.operations import ResourceClaim
from persona_training_lab.infrastructure.persistence.sqlite.locking import (
    connection_lock,
)


class SQLiteLineageResourceLinksRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = connection_lock(connection)

    def replace_links(
        self,
        node_id: str,
        claims: tuple[ResourceClaim, ...],
    ) -> None:
        with self._lock, self._connection:
            self._replace_links_locked(node_id, claims)

    def reconcile_projection_links(
        self,
        claims_by_node: Mapping[str, tuple[ResourceClaim, ...]],
        stale_node_ids: tuple[str, ...],
    ) -> None:
        """Replace one complete projection link-set in a single transaction."""

        current_ids = set(claims_by_node)
        stale = tuple(
            node_id
            for node_id in dict.fromkeys(stale_node_ids)
            if node_id and node_id not in current_ids
        )
        with self._lock, self._connection:
            for node_id in sorted(current_ids):
                self._replace_links_locked(
                    node_id,
                    claims_by_node[node_id],
                )
            if stale:
                placeholders = ",".join("?" for _ in stale)
                self._connection.execute(
                    "DELETE FROM lineage_resource_links "
                    f"WHERE node_id IN ({placeholders})",
                    stale,
                )

    def list_node_ids(self) -> tuple[str, ...]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT DISTINCT node_id
                FROM lineage_resource_links
                ORDER BY node_id
                """
            ).fetchall()
        return tuple(str(row["node_id"]) for row in rows)

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
                "DELETE FROM lineage_resource_links "
                f"WHERE node_id IN ({placeholders})",
                node_ids,
            )
        return cursor.rowcount

    def _replace_links_locked(
        self,
        node_id: str,
        claims: tuple[ResourceClaim, ...],
    ) -> None:
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
