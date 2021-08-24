from datetime import datetime
from typing import Sequence, Union, List, Optional, Tuple, Dict, Callable, Any

import pytz
from feast import RepoConfig, FeatureTable, FeatureView, Entity
from feast.infra.key_encoding_utils import serialize_entity_key
from feast.infra.online_stores.online_store import OnlineStore
from feast.protos.feast.types.EntityKey_pb2 import EntityKey as EntityKeyProto
from feast.protos.feast.types.Value_pb2 import Value as ValueProto


import mysql.connector
from feast.repo_config import FeastConfigBaseModel
from mysql.connector.abstracts import MySQLConnectionAbstract
from pydantic import StrictStr
from pydantic.typing import Literal


class MySQLOnlineStoreConfig(FeastConfigBaseModel):
    """
    Configuration for the MySQL online store.
    NOTE: The class *must* end with the `OnlineStoreConfig` suffix.
    """
    type: Literal["mysql",
                  "feast_custom_online_store.mysql.MySQLOnlineStore"] \
        = "feast_custom_online_store.mysql.MySQLOnlineStore"

    host: Optional[StrictStr] = None
    user: Optional[StrictStr] = None
    password: Optional[StrictStr] = None
    database: Optional[StrictStr] = None


class MySQLOnlineStore(OnlineStore):
    """
    An online store implementation that uses MySQL.
    NOTE: The class *must* end with the `OnlineStore` suffix.
    """

    _conn: MySQLConnectionAbstract = None

    def _get_conn(self, config: RepoConfig):

        online_store_config = config.online_store
        assert isinstance(online_store_config, MySQLOnlineStoreConfig)

        if not self._conn:
            self._conn = mysql.connector.connect(
                host=online_store_config.host or "127.0.0.1",
                user=online_store_config.user or "root",
                password=online_store_config.password,
                database=online_store_config.database or "feast",
                autocommit=True
            )
        return self._conn

    def online_write_batch(
            self,
            config: RepoConfig,
            table: Union[FeatureTable, FeatureView],
            data: List[
                Tuple[EntityKeyProto, Dict[str, ValueProto], datetime, Optional[datetime]]
            ],
            progress: Optional[Callable[[int], Any]],
    ) -> None:

        conn = self._get_conn(config)
        cur = conn.cursor(buffered=True)

        project = config.project

        for entity_key, values, timestamp, created_ts in data:
            entity_key_bin = serialize_entity_key(entity_key).hex()
            timestamp = _to_naive_utc(timestamp)
            if created_ts is not None:
                created_ts = _to_naive_utc(created_ts)

            for feature_name, val in values.items():
                self.write_to_table(created_ts, cur, entity_key_bin, feature_name, project, table, timestamp, val)
            self._conn.commit()
            if progress:
                progress(1)

    @staticmethod
    def write_to_table(created_ts, cur, entity_key_bin, feature_name, project, table, timestamp, val):
        cur.execute(
            f"""
                        UPDATE {_table_id(project, table)}
                        SET value = %s, event_ts = %s, created_ts = %s
                        WHERE (entity_key = %s AND feature_name = %s)
                    """,
            (
                # SET
                val.SerializeToString(),
                timestamp,
                created_ts,
                # WHERE
                entity_key_bin,
                feature_name,
            ),
        )
        cur.execute(
            f"""INSERT INTO {_table_id(project, table)}
                        (entity_key, feature_name, value, event_ts, created_ts)
                        VALUES (%s, %s, %s, %s, %s)""",
            (
                entity_key_bin,
                feature_name,
                val.SerializeToString(),
                timestamp,
                created_ts,
            ),
        )

    def online_read(
            self,
            config: RepoConfig,
            table: Union[FeatureTable, FeatureView],
            entity_keys: List[EntityKeyProto],
            requested_features: Optional[List[str]] = None,
    ) -> List[Tuple[Optional[datetime], Optional[Dict[str, ValueProto]]]]:
        conn = self._get_conn(config)
        cur = conn.cursor(buffered=True)

        result: List[Tuple[Optional[datetime], Optional[Dict[str, ValueProto]]]] = []

        project = config.project
        for entity_key in entity_keys:
            entity_key_bin = serialize_entity_key(entity_key).hex()

            cur.execute(
                f"SELECT feature_name, value, event_ts FROM {_table_id(project, table)} WHERE entity_key = %s",
                (entity_key_bin,),
            )

            res = {}
            res_ts = None
            for feature_name, val_bin, ts in cur.fetchall():
                val = ValueProto()
                val.ParseFromString(val_bin)
                res[feature_name] = val
                res_ts = ts

            if not res:
                result.append((None, None))
            else:
                result.append((res_ts, res))
        return result

    def update(
            self,
            config: RepoConfig,
            tables_to_delete: Sequence[Union[FeatureTable, FeatureView]],
            tables_to_keep: Sequence[Union[FeatureTable, FeatureView]],
            entities_to_delete: Sequence[Entity],
            entities_to_keep: Sequence[Entity],
            partial: bool,
    ):
        conn = self._get_conn(config)
        cur = conn.cursor(buffered=True)

        project = config.project

        # We don't create any special state for the entites in this implementation.
        for table in tables_to_keep:
            cur.execute(
                f"CREATE TABLE IF NOT EXISTS {_table_id(project, table)} (entity_key VARCHAR(512), feature_name VARCHAR(256), value BLOB, event_ts timestamp, created_ts timestamp,  PRIMARY KEY(entity_key, feature_name))"
            )
            cur.execute(
                f"ALTER TABLE {_table_id(project, table)} ADD INDEX {_table_id(project, table)}_ek (entity_key);"
            )

        for table in tables_to_delete:
            cur.execute(
                f"DROP INDEX {_table_id(project, table)}_ek ON {_table_id(project, table)};"
            )
            cur.execute(f"DROP TABLE IF EXISTS {_table_id(project, table)}")

    def teardown(
            self,
            config: RepoConfig,
            tables: Sequence[Union[FeatureTable, FeatureView]],
            entities: Sequence[Entity],
    ):
        conn = self._get_conn(config)
        cur = conn.cursor(buffered=True)
        project = config.project

        for table in tables:
            cur.execute(
                f"DROP INDEX {_table_id(project, table)}_ek ON {_table_id(project, table)};"
            )
            cur.execute(f"DROP TABLE IF EXISTS {_table_id(project, table)}")


def _table_id(project: str, table: Union[FeatureTable, FeatureView]) -> str:
    return f"{project}_{table.name}"


def _to_naive_utc(ts: datetime):
    if ts.tzinfo is None:
        return ts
    else:
        return ts.astimezone(pytz.utc).replace(tzinfo=None)
