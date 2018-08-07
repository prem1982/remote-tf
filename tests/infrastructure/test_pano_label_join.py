import unittest
import uuid

import mock
from bnr_robot_cloud_common.codegen.image.ttypes import PanoUploadEvent, PanoEventEnvelope

from bnr_robot_cloud_common.codegen.common.ttypes import AnalyticsHeader

from cloud_oos_detection.infrastructure.label_services import PanoLabelJoin
from cloud_oos_detection.infrastructure.service_bus_infrastructure import StatefulAzurePanoClient


class TestPanoLabelJoin(unittest.TestCase):
    def setUp(self):
        self.inter_bus = mock.MagicMock(StatefulAzurePanoClient)
        self.intra_bus = mock.MagicMock(StatefulAzurePanoClient)
        self.join = PanoLabelJoin(self.inter_bus, self.intra_bus)
        self.header = AnalyticsHeader(customer_id=str(uuid.uuid4()),
                                      store_id=str(uuid.uuid4()),
                                      aisle_id=str(uuid.uuid4()))

        self.event = PanoUploadEvent(url="foo", header=self.header, container_name=str(uuid.uuid4()))
        self.env = PanoEventEnvelope(pano_upload=self.event)

    def test_join_publishes_when_ready(self):
        self.inter_bus.listen.return_value = self.env
        self.join.streaming_join()
        self.intra_bus.publish.assert_called()

    def test_join_acks_when_ready(self):
        self.inter_bus.listen.return_value = self.env
        self.join.streaming_join()
        self.inter_bus.acknowledge.assert_called()

    def test_joins_and_forwards(self):
        self.inter_bus.listen.return_value = self.env
        self.join.streaming_join()
        actual_env = self.intra_bus.publish.call_args[0][0]
        self.assertEqual(actual_env.pano_upload.container_name, self.env.pano_upload.container_name)
        self.assertEqual(actual_env.correlation_id, self.env.correlation_id)
        self.assertEqual(actual_env.pano_upload.url, self.env.pano_upload.url)
        self.assertEqual(actual_env.pano_upload.header, self.env.pano_upload.header)
