# txsftp
# Copyright (c) 2011 Phil Christensen
#
#
# See LICENSE for details

"""
Provide access to the database via psycopg3 AsyncConnectionPool.
"""

import asyncio
import re

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from twisted.internet import defer


def connect(db_url):
    """
    Get a connection pool for a given db_url.

    @param db_url: A URL of the form C{psycopg://user:password@host/dbname}
    @type db_url: str

    @return: A L{TxPool} instance.
    """
    return TxPool(db_url)


def _url_to_conninfo(db_url):
    """
    Convert a psycopg[2]://... URL to a postgresql://... URI for psycopg3.
    """
    return re.sub(r'^psycopg2?://', 'postgresql://', db_url)


class TxPool:
    """
    Async PostgreSQL connection pool backed by psycopg3 C{AsyncConnectionPool}.

    All public methods return Deferreds, compatible with Twisted's asyncio reactor.
    Query results are returned as lists of dicts (column name → value).
    """

    def __init__(self, db_url):
        if not re.match(r'^psycopg2?://', db_url):
            raise RuntimeError("Only psycopg is supported for DB connections at this time.")
        conninfo = _url_to_conninfo(db_url)
        self._pool = AsyncConnectionPool(
            conninfo,
            kwargs={"autocommit": True, "row_factory": dict_row},
            open=False,
        )
        # Open synchronously while the asyncio loop exists but isn't running yet.
        # asyncioreactor.install() sets up the loop before makeService() runs,
        # so run_until_complete() can drive the open() coroutine to completion
        # before the reactor starts and before any connections are accepted.
        asyncio.get_event_loop().run_until_complete(self._pool.open())

    def _as_deferred(self, coro):
        """
        Schedule a coroutine as a proper asyncio Task and return a Deferred.

        psycopg3's async I/O uses asyncio.timeout() internally, which requires
        the coroutine to run inside an asyncio Task (asyncio.current_task() must
        be non-None). defer.ensureDeferred drives coroutines as Twisted callbacks
        without creating a Task, so we must use create_task + Deferred.fromFuture
        instead.
        """
        task = asyncio.get_running_loop().create_task(coro)
        return defer.Deferred.fromFuture(task)

    def runQuery(self, query, args=None):
        """
        Execute a SELECT query and return a Deferred that fires with a list of dicts.
        """
        return self._as_deferred(self._run_query(query, args))

    async def _run_query(self, query, args=None):
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                return await cur.fetchall()

    def runOperation(self, query, args=None):
        """
        Execute an INSERT/UPDATE/DELETE and return a Deferred that fires with None.
        """
        return self._as_deferred(self._run_operation(query, args))

    async def _run_operation(self, query, args=None):
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)

    def runInteraction(self, interaction, *args, **kwargs):
        """
        Run a callable with an C{AsyncConnection} from the pool.

        Returns a Deferred that fires with the callable's return value.
        The callable must be a coroutine function (async def).
        """
        return self._as_deferred(self._run_interaction(interaction, *args, **kwargs))

    async def _run_interaction(self, interaction, *args, **kwargs):
        async with self._pool.connection() as conn:
            return await interaction(conn, *args, **kwargs)
