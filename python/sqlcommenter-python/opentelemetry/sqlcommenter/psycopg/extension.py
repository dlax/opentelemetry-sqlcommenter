#!/usr/bin/python
#
# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

import psycopg
from psycopg import pq
from opentelemetry.sqlcommenter import generate_sql_comment
from opentelemetry.sqlcommenter.flask import get_flask_info
from opentelemetry.sqlcommenter.opencensus import get_opencensus_values
from opentelemetry.sqlcommenter.opentelemetry import get_opentelemetry_values

logger = logging.getLogger(__name__)


# This integration extends psycopg2.extensions.cursor
# by implementing a custom execute method.
#
# By default, it doesn't enable adding trace_id and span_id
# to SQL comments due to their ephemeral nature. You can opt-in
# by instead setting with_opencensus=True
def CommenterCursorFactory(
        with_framework=True, with_controller=True, with_route=True,
        with_opencensus=False, with_opentelemetry=False, with_db_driver=False,
        with_dbapi_threadsafety=False, with_dbapi_level=False,
        with_libpq_version=False, with_driver_paramstyle=False):

    attributes = {
        'framework': with_framework,
        'controller': with_controller,
        'route': with_route,
        'db_driver': with_db_driver,
        'dbapi_threadsafety': with_dbapi_threadsafety,
        'dbapi_level': with_dbapi_level,
        'libpq_version': with_libpq_version,
        'driver_paramstyle': with_driver_paramstyle,
    }

    libpq_version = pq.version()

    class CommenterCursor(psycopg.Cursor):

        def _convert_query(self, query, params=None):
            data = dict(
                # Psycopg2/framework information
                db_driver='psycopg:%s' % psycopg.__version__,
                dbapi_threadsafety=psycopg.threadsafety,
                dbapi_level=psycopg.apilevel,
                libpq_version=libpq_version,
                driver_paramstyle=psycopg.paramstyle,
            )

            # Because psycopg2 is a plain database connectivity module,
            # folks using it in a web framework such as flask will
            # use it in unison with flask but initialize the parts disjointly,
            # unlike Django which uses ORMs directly as part of the framework.
            data.update(get_flask_info())

            # Filter down to just the requested attributes.
            data = {k: v for k, v in data.items() if attributes.get(k)}

            if with_opencensus and with_opentelemetry:
                logger.warning(
                    "with_opencensus and with_opentelemetry were enabled. "
                    "Only use one to avoid unexpected behavior"
                )
            if with_opencensus:
                data.update(get_opencensus_values())
            if with_opentelemetry:
                data.update(get_opentelemetry_values())

            query += generate_sql_comment(**data)

            return super()._convert_query(query, params)

    return CommenterCursor
