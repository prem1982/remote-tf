import unittest
import uuid

import mock


from redis import StrictRedis
from redis.client import StrictPipeline
from bnr_robot_cloud_common.codegen.common.ttypes import AnalyticsHeader

from bnr_robot_cloud_common.codegen.label.ttypes import *

from cloud_oos_detection.infrastructure.label_services import *
from cloud_oos_detection.infrastructure.service_bus_infrastructure import StatefulLabelEventEnvelopeClient


class TestLabelEventEnvelopeStorage(unittest.TestCase):
    def setUp(self):
        self.bus = mock.MagicMock(StatefulLabelEventEnvelopeClient)
        self.pipe = mock.MagicMock(StrictPipeline)
        self.r = mock.MagicMock(StrictRedis)
        self.label_storage = RedisLabelDetectionStorage(self.r)

        self.label_service = mock.MagicMock(LabelLookupService)
        self.customer_id = str(uuid.uuid4())
        self.run_id = str(uuid.uuid4())
        self.store_id = str(uuid.uuid4())
        self.aisle_id = str(uuid.uuid4())

        self.r.pipeline.return_value = self.pipe

        header = AnalyticsHeader(store_id=self.store_id,
                                 aisle_id=self.aisle_id,
                                 unique_id=self.run_id)

        label = LabelDetected(header=header)
        label_detected_batch = LabelDetectedBatch(label_detected_batch=[label])
        self.envelope = LabelEventEnvelope(label_detected_batch=label_detected_batch)

    def assert_pipelined_insert(self, n = 1):
        self.assertEqual(self.pipe.lpush.call_count, n)
        self.assertEqual(self.pipe.expire.call_count, n)
        self.assertEqual(self.pipe.execute.call_count, n)

    def test_does_not_store_when_none_received(self):
        self.bus.listen.return_value = None
        completion_service = LabelEventEnvelopeStorage(self.bus, self.label_storage)
        completion_service.consume_n()
        self.assertTrue(self.pipe.lpush.not_called)

    def test_does_store_when_event_received(self):
        self.bus.listen.return_value = self.envelope
        completion_service = LabelEventEnvelopeStorage(self.bus, self.label_storage)
        completion_service.consume_n(1)

        self.assert_pipelined_insert()

    def test_does_consume_multiple_events_when_available(self):
        self.bus.listen.return_value = self.envelope
        completion_service = LabelEventEnvelopeStorage(self.bus, self.label_storage)
        completion_service.consume_n(100)
        self.assert_pipelined_insert(100)

    def test_does_consume_multiple_events_when_available_exits_early(self):
        self.bus.listen.side_effect = [self.envelope, self.envelope,self.envelope,  None]
        completion_service = LabelEventEnvelopeStorage(self.bus, self.label_storage)
        completion_service.consume_n(3)
        self.assert_pipelined_insert(3)

    def test_does_acknowledge_when_event_received_and_stored(self):
        self.bus.listen.return_value = self.envelope
        completion_service = LabelEventEnvelopeStorage(self.bus, self.label_storage)
        completion_service.consume_n()
        self.bus.acknowledge.assert_called()

    def test_does_not_acknowledge_when_event_received_but_storing_fails(self):
        self.bus.listen.return_value = self.envelope
        completion_service = LabelEventEnvelopeStorage(self.bus, self.label_storage)
        self.pipe.lpush.side_effect = AzureException()
        completion_service.consume_n()
        self.bus.acknowledge.assert_not_called()