import unittest

import mock
from bnr_robot_cloud_common.codegen.image.ttypes import PanoEventEnvelope, PanoUploadEvent
from azure.servicebus import ServiceBusService
from azure.servicebus import Message

from cloud_oos_detection.infrastructure.pano_service import AzurePanoBytesService, AzurePanoProvider
from cloud_oos_detection.infrastructure import binary_serialize
from cloud_oos_detection.infrastructure.service_bus_infrastructure import StatefulAzurePanoClient


class TestAzurePanoProvider(unittest.TestCase):
    def setUp(self):
        self.bus = mock.MagicMock(ServiceBusService)
        self.subscriber = StatefulAzurePanoClient(self.bus, "topic", "sub")
        self.blob = mock.MagicMock(AzurePanoBytesService)
        self.provider = AzurePanoProvider(self.subscriber, self.blob)
        self.event = PanoUploadEvent(url="foo")
        self.envelope = PanoEventEnvelope(self.event, "a-b-c")
        message = Message(body=binary_serialize(self.envelope))
        self.good_message = message


    def test_calls_the_download_service_when_valid_event_received(self):

        self.bus.receive_subscription_message.return_value = self.good_message
        self.provider.provide()
        self.blob.download.assert_called_with(self.event)

    def test_does_not_call_the_download_service_when_invalid_event_received(self):

        message = Message(body="")
        self.bus.receive_subscription_message.return_value = message
        self.provider.provide()
        self.blob.download.assert_not_called()

    def test_does_acknowledge_when_invalid_event_received(self):

        message = Message(body="")
        self.bus.receive_subscription_message.return_value = message
        self.provider.provide()
        self.bus.delete_subscription_message.call_args(message)

    def test_does_acknowledge_when_irrelevant_event_received(self):

        self.envelope = PanoEventEnvelope(correlation_id= "a-b-c",pano_converted=None)
        message = Message(body=binary_serialize(self.envelope))
        self.bus.receive_subscription_message.return_value = message
        self.provider.provide()
        self.blob.download.assert_not_called()
        self.bus.delete_subscription_message.call_args(message)

    def test_does_progress_when_invalid_event_received_then_valid(self):

        message = Message(body="")
        self.bus.receive_subscription_message.return_value = message
        self.provider.provide()
        self.bus.delete_subscription_message.call_args(message)

        self.bus.receive_subscription_message.return_value = self.good_message
        self.provider.provide()
        self.blob.download.assert_called_with(self.event)

if __name__ == '__main__':
    unittest.main()        