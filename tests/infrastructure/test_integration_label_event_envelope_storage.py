import unittest
import uuid

from nose.plugins.attrib import attr
import mock
from redis import StrictRedis

from bnr_robot_cloud_common.codegen.common.ttypes import AnalyticsHeader

from bnr_robot_cloud_common.codegen.label.ttypes import *

from cloud_oos_detection.infrastructure.label_services import *
from cloud_oos_detection.infrastructure.service_bus_infrastructure import StatefulLabelEventEnvelopeClient


@attr(kind='CI')
class TestIntegrationLabelEventEnvelopeStorage(unittest.TestCase):
    def setUp(self):
        self.bus = mock.MagicMock(StatefulLabelEventEnvelopeClient)
        self.r = StrictRedis()
        self.label_storage = RedisLabelDetectionStorage(self.r)

        self.label_service = mock.MagicMock(LabelLookupService)
        self.customer_id = str(uuid.uuid4())
        self.run_id = str(uuid.uuid4())
        self.store_id = str(uuid.uuid4())
        self.aisle_id = str(uuid.uuid4())

        header = AnalyticsHeader(store_id=self.store_id,
                                 aisle_id=self.aisle_id,
                                 unique_id=self.run_id)

        label = LabelDetected(header=header)
        label_detected_batch = LabelDetectedBatch(label_detected_batch=[label])
        self.envelope = LabelEventEnvelope(label_detected_batch=label_detected_batch)
        self.header = header

    def assert_pipelined_insert(self, n=1):
        self.assertEqual(self.pipe.lpush.call_count, n)
        self.assertEqual(self.pipe.expire.call_count, n)
        self.assertEqual(self.pipe.execute.call_count, n)

    def test_does_not_store_when_none_received(self):
        self.bus.listen.return_value = None
        completion_service = LabelEventEnvelopeStorage(self.bus, self.label_storage)
        completion_service.consume_n()
        results = self.label_storage.getall(self.header.store_id, self.header.unique_id, self.aisle_id)
        self.assertEqual(len(results), 0)

    def test_does_store_when_event_received(self):
        self.bus.listen.return_value = self.envelope
        completion_service = LabelEventEnvelopeStorage(self.bus, self.label_storage)
        completion_service.consume_n(1)
        results = self.label_storage.getall(self.header.store_id, self.header.unique_id, self.aisle_id)
        self.assertEqual(len(results), 1)

    def test_does_consume_multiple_events_when_available(self):
        self.bus.listen.return_value = self.envelope
        completion_service = LabelEventEnvelopeStorage(self.bus, self.label_storage)
        completion_service.consume_n(100)
        results = self.label_storage.getall(self.header.store_id, self.header.unique_id, self.aisle_id)
        self.assertEqual(len(results), 100)

    def test_does_return_correct_event_types(self):
        self.bus.listen.return_value = self.envelope
        completion_service = LabelEventEnvelopeStorage(self.bus, self.label_storage)
        completion_service.consume_n(100)
        results = self.label_storage.getall(self.header.store_id, self.header.unique_id, self.aisle_id)
        for result in results:
            assert(isinstance(result,LabelDetected))
