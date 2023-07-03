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

from unittest import TestCase

import psycopg
from opentelemetry.sqlcommenter import url_quote
from opentelemetry.sqlcommenter.psycopg.extension import CommenterCursorFactory

from ..compat import mock
from ..opencensus_mock import mock_opencensus_tracer
from ..opentelemetry_mock import mock_opentelemetry_context


class PsycopgTestCase(TestCase):

    def assertSQL(self, sql, **kwargs):
        conn = mock.create_autospec(psycopg.Connection, cursor_factory=CommenterCursorFactory(**kwargs))
        self.assertEqual(conn.execute('SELECT 1;'), 'worked')


class Tests(PsycopgTestCase):

    def test_no_args(self):
        self.assertSQL('SELECT 1;')

    def test_db_driver(self):
        self.assertSQL(
            "SELECT 1; /*db_driver='psycopg%%3A{}'*/".format(url_quote(psycopg.__version__)),
            with_db_driver=True,
        )

    def test_dbapi_threadsafety(self):
        self.assertSQL(
            "SELECT 1; /*dbapi_threadsafety={}*/".format(psycopg.threadsafety),
            with_dbapi_threadsafety=True,
        )

    def test_driver_paramstyle(self):
        self.assertSQL(
            "SELECT 1; /*driver_paramstyle='{}'*/".format(psycopg.paramstyle),
            with_driver_paramstyle=True,
        )

    def test_dbapi_level(self):
        self.assertSQL(
            "SELECT 1; /*dbapi_level='{}'*/".format(url_quote(psycopg.apilevel)),
            with_dbapi_level=True,
        )

    def test_libpq_version(self):
        self.assertSQL(
            "SELECT 1; /*libpq_version={}*/".format(url_quote(psycopg.__libpq_version__)),
            with_libpq_version=True,
        )

    def test_opencensus(self):
        with mock_opencensus_tracer():
            self.assertSQL(
                "SELECT 1; /*traceparent='00-trace%%20id-span%%20id-00',"
                "tracestate='congo%%3Dt61rcWkgMzE%%2Crojo%%3D00f067aa0ba902b7'*/",
                with_opencensus=True,
            )

    def test_opentelemetry(self):
        with mock_opentelemetry_context():
            self.assertSQL(
                "SELECT 1; /*traceparent='00-000000000000000000000000deadbeef-000000000000beef-00',"
                "tracestate='some_key%%3Dsome_value'*/",
                with_opentelemetry=True,
            )

    def test_both_opentelemetry_and_opencensus_warn(self):
        with mock.patch(
            "opentelemetry.sqlcommenter.psycopg.extension.logger"
        ) as logger_mock, mock_opencensus_tracer(), mock_opentelemetry_context():
            self.assertSQL(
                "SELECT 1; /*traceparent='00-000000000000000000000000deadbeef-000000000000beef-00',"
                "tracestate='some_key%%3Dsome_value'*/",
                with_opentelemetry=True,
                with_opencensus=True,
            )
            self.assertEqual(len(logger_mock.warning.mock_calls), 1)


class FlaskTests(PsycopgTestCase):
    flask_info = {
        'framework': 'flask',
        'controller': 'c',
        'route': '/',
    }

    @mock.patch('opentelemetry.sqlcommenter.psycopg.extension.get_flask_info', return_value=flask_info)
    def test_all_data(self, get_info):
        self.assertSQL(
            "SELECT 1; /*controller='c',framework='flask',route='/'*/",
        )

    @mock.patch('opentelemetry.sqlcommenter.psycopg.extension.get_flask_info', return_value=flask_info)
    def test_framework_disabled(self, get_info):
        self.assertSQL(
            "SELECT 1; /*controller='c',route='/'*/",
            with_framework=False,
        )

    @mock.patch('opentelemetry.sqlcommenter.psycopg.extension.get_flask_info', return_value=flask_info)
    def test_controller_disabled(self, get_info):
        self.assertSQL(
            "SELECT 1; /*framework='flask',route='/'*/",
            with_controller=False,
        )

    @mock.patch('opentelemetry.sqlcommenter.psycopg.extension.get_flask_info', return_value=flask_info)
    def test_route_disabled(self, get_info):
        self.assertSQL(
            "SELECT 1; /*controller='c',framework='flask'*/",
            with_route=False,
        )
