import unittest
import uuid

import mock
from redis import StrictRedis
from redis.exceptions import TimeoutError, ConnectionError

from cloud_oos_detection.infrastructure.label_services import RedisLabelDetectionStorage, RedisLabelLookupService


class TestRedisLabelLookupService(unittest.TestCase):
    def setUp(self):
        self.r = mock.MagicMock(StrictRedis)
        self.storage = RedisLabelDetectionStorage(self.r, ttl=10, retry_period=1)
        self.lookup = RedisLabelLookupService(self.storage)
        self.customer_id = str(uuid.uuid4())
        self.run_id = str(uuid.uuid4())
        self.store_id = str(uuid.uuid4())
        self.aisle_id = str(uuid.uuid4())

    def test_handles_timeout_exception(self):
        self.r.lrange.side_effect = TimeoutError()
        results = self.lookup.request_labels(self.customer_id, self.store_id, self.run_id, self.aisle_id)
        self.assertEqual(len(results), 0)

    def test_handles_connection_exception(self):
        self.r.lrange.side_effect = ConnectionError()
        results = self.lookup.request_labels(self.customer_id, self.store_id, self.run_id, self.aisle_id)
        self.assertEqual(len(results), 0)

    def test_handles_authentication_exception(self):
        self.r.lrange.side_effect = ConnectionError()
        results = self.lookup.request_labels(self.customer_id, self.store_id, self.run_id, self.aisle_id)
        self.assertEqual(len(results), 0)
