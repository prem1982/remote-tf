import os
from threading import Thread
import time

from azure.common import AzureException
from azure.servicebus import ServiceBusService

from prometheus_client import Summary, Counter

from bnr_robot_cloud_common.codegen.image.ttypes import PanoEventEnvelope

from bnr_robot_cloud_common.codegen.label.ttypes import LabelDetectedBatch, LabelDetected
import redis

from redis.exceptions import RedisError, ConnectionError, TimeoutError, AuthenticationError

from cloud_oos_detection.app_logging import logger
from cloud_oos_detection.infrastructure import binary_deserialize, binary_serialize
from cloud_oos_detection.infrastructure.service_bus_infrastructure import StatefulLabelEventEnvelopeClient

LABEL_RPC_SUMMARY = Summary("label_rpc_duration_seconds", "Box flow in and out", ["status"])
LABEL_RPC_COUNTER = Counter("label_rpc_count_total", "Status Counter", ["direction", "status"])


class PanoLabelJoin(object):
    def __init__(self, inter_service_bus, intra_service_bus):
        self.inter_service_bus = inter_service_bus
        self.intra_service_bus = intra_service_bus

    def streaming_join(self):
        pano_event_envelope = self.inter_service_bus.listen()
        assert (isinstance(pano_event_envelope, PanoEventEnvelope))

        self.intra_service_bus.publish(pano_event_envelope)
        self.inter_service_bus.acknowledge()


class RedisLabelDetectionStorage(object):
    @staticmethod
    def build_from_environment():
        redis_endpoint = os.environ['CLOUD_OOS_DETECTION_REDIS_ENDPOINT']
        redis_password = os.environ['CLOUD_OOS_DETECTION_REDIS_PASSWORD']

        r = redis.StrictRedis(host=redis_endpoint,
                              port=6379,
                              db=0,
                              password=redis_password,
                              ssl=True)

        return RedisLabelDetectionStorage(r)

    def __init__(self, r,
                 ttl=60 * 60 * 12,
                 max_retries=3,
                 retry_period=5):
        self._ttl = ttl
        self._r = r
        self._pending_batch = []
        self._current_key = None
        self._max_retries = max_retries
        self._retry_period = retry_period

    def _build_key(self, store_id, unique_id, aisle_id):
        return store_id + unique_id + aisle_id

    def _flush(self):

        if len(self._pending_batch) > 0:
            pipe = self._r.pipeline()
            pipe.lpush(self._current_key, *self._pending_batch)
            pipe.expire(self._current_key, self._ttl)
            pipe.execute()
            logger.info("Stored LabelBatch for Key: {k}".format(k=self._current_key))
            self._pending_batch = []

    def push(self, label_detected_batch):

        def internal():
            assert isinstance(label_detected_batch, LabelDetectedBatch)

            self._current_key = None
            for label in label_detected_batch.label_detected_batch:
                try:

                    header = label.header
                    key = self._build_key(header.store_id, header.unique_id, header.aisle_id)
                    if self._current_key is None or self._current_key == key:
                        self._current_key = key
                        serialized_label = binary_serialize(label)
                        self._pending_batch.append(serialized_label)
                    else:
                        self._flush()
                        self._current_key = key
                except EOFError, er:
                    logger.warn("Poison LabelDetection received. Message will be ignored ")

            self._flush()

        return self._retry(internal)

    def getall(self, store_id, unique_id, aisle_id):

        def internal():
            key = self._build_key(store_id, unique_id, aisle_id)
            return [binary_deserialize(r, LabelDetected) for r in self._r.lrange(key, 0, -1)]

        return self._retry(internal)

    def _retry(self, f):

        count = 0
        while True:
            try:

                return f()
            except AuthenticationError, ae:
                logger.error("Unrecoverable Authentication Exception")
                raise ae
            except (ConnectionError, TimeoutError), re:
                count += 1
                if count < self._max_retries:
                    logger.warn("Transient Error Received %s ", re)
                    time.sleep(self._retry_period)
                else:
                    logger.error("Unrecoverable Network Error %s", re)
                    raise re


class LabelEventEnvelopeStorage(object):
    @staticmethod
    def build_from_environment():
        namespace_name = os.environ['CLOUD_OOS_DETECTION_SERVICE_NAMESPACE']
        topic_name = os.environ['CLOUD_OOS_DETECTION_LABEL_TOPIC_NAME']
        subscription_name = os.environ['CLOUD_OOS_DETECTION_LABEL_SUBSCRIPTION_NAME']
        sas_token = os.environ['CLOUD_OOS_DETECTION_LABEL_SUBSCRIPTION_KEY']
        bus = ServiceBusService(service_namespace=namespace_name, account_key=sas_token)
        subscriber = StatefulLabelEventEnvelopeClient(bus, topic_name, subscription_name)

        redis_storage = RedisLabelDetectionStorage.build_from_environment()
        return LabelEventEnvelopeStorage(subscriber, redis_storage)

    def __init__(self, client, redis_storage):
        self._client = client
        self._redis_storage = redis_storage

    @staticmethod
    def run(service):
        consumer = Thread(target=service.consume_aisle_completion)
        consumer.setDaemon(True)
        consumer.start()

    def store(self, aisle_completion_event):
        raise NotImplementedError("Abstract Class")

    def consume_n(self, n=100):

        count = 0
        while count < n:
            envelope = self._client.listen()
            if envelope is not None:
                count += 1
                batch = envelope.label_detected_batch
                if batch is not None:
                    try:
                        self._redis_storage.push(batch)
                    except AzureException, aze:
                        logger.error("Unable to store AisleCompletionEventEntity %s", aze)
                    else:
                        logger.info("Stored LabelDetectedBatch")
                        self._client.acknowledge()
                        envelope = None
                else:
                    self._client.acknowledge()
            else:
                return

    def consume_aisle_completion(self):
        while True:
            self.consume_n()
            time.sleep(5)


class LabelLookupService(object):
    def request_labels(self, customer_id, store_id, mission_id, aisle_id, interpret_as_frame=False):
        raise NotImplementedError("Abstract Class")


class RedisLabelLookupService(LabelLookupService):
    @staticmethod
    def build_from_environment():

        r = RedisLabelDetectionStorage.build_from_environment()
        return RedisLabelLookupService(r)

    def __init__(self, r):
        self.r = r

    def request_labels(self, customer_id, store_id, mission_id, aisle_id, interpret_as_frame=False):

        try:
            response = self.r.getall(store_id, mission_id, aisle_id)
            return response
        except RedisError:
            return []
