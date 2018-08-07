from azure.common import AzureHttpError
from azure.servicebus import Message
from prometheus_client import Counter
from bnr_robot_cloud_common.codegen.image.ttypes import PanoEventEnvelope
from bnr_robot_cloud_common.codegen.label.ttypes import LabelEventEnvelope
from bnr_robot_cloud_common.codegen.detection.ttypes import \
    OutRecommendationEvent

from cloud_oos_detection.infrastructure import binary_deserialize, binary_serialize
from cloud_oos_detection.app_logging import logger

SB_IO_COUNTER = Counter("message_processing_total", "The number of message the service is ingesting",
                        ['direction', "kind"])


class StatefulAzureServiceBusClient(object):
    def __init__(self, bus, topic_name, subscription_name, kind):
        self._bus = bus
        self.topic_name = topic_name
        self.subscription = subscription_name
        self._kind = kind
        self._message = None

    def _deserialize(self):
        raise NotImplementedError("")

    def listen(self):
        self._message = self._bus.receive_subscription_message(self.topic_name, self.subscription)
        if self._message is not None and self._message.body is not None:
            SB_IO_COUNTER.labels(direction='inbound',
                                 kind=self._kind).inc()
            try:
                envelope = self._deserialize()
                logger.info(
                    "Ingested Envelope with correlation id {cid}".format(
                        cid=envelope.correlation_id))
                return envelope
            except EOFError, ef:
                logger.error("Poison message received: %s", ef)
                self._bus.delete_subscription_message(self._message)

            return None

    def acknowledge(self):
        if self._message is None:
            logger.warn("Attempt to acknowledge non existent message")
        else:
            self._bus.delete_subscription_message(self._message)
            SB_IO_COUNTER.labels(direction='outbound', kind=self._kind).inc()

    def publish(self, envelope):
        try:
            msg = Message(body=binary_serialize(envelope))
            self._bus.send_topic_message(self.topic_name, msg)
        except AzureHttpError, ef:
            logger.error('''Exception sending coordinates to HITL:
                %s for url %s and container %''', ef, envelope.url, envelope.container)
            raise


class StatefulAzurePanoClient(StatefulAzureServiceBusClient):
    def __init__(self, bus, topic_name, subscription_name):
        super(StatefulAzurePanoClient, self).__init__(bus, topic_name, subscription_name,
                                                      "pano_upload_event")

    def _deserialize(self):
        return binary_deserialize(self._message.body, PanoEventEnvelope)


class StatefulLabelEventEnvelopeClient(StatefulAzureServiceBusClient):
    def __init__(self, bus, topic_name, subscription_name):
        super(StatefulLabelEventEnvelopeClient, self).__init__(bus, topic_name, subscription_name,
                                                               "label_event_envelope")

    def _deserialize(self):
        return binary_deserialize(self._message.body, LabelEventEnvelope)


class StatefulOutsRecommendationClient(StatefulAzurePanoClient):
    def __init__(self, bus, topic_name):
        super(StatefulOutsRecommendationClient, self).__init__(bus, topic_name, None,
                                                               "outs_recommendation_event")

    def _deserialize(self):
        return binary_deserialize(self._message.body, OutRecommendationEvent)
