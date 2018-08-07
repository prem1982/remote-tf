import os

from azure.storage.blob import BlockBlobService
from azure.servicebus import ServiceBusService
import numpy as np
from prometheus_client import Counter
from bnr_robot_cloud_common.codegen.image.ttypes import PanoUploadEvent
from bnr_robot_cloud_common.codegen.detection.ttypes import \
    OutRecommendationEvent

from cloud_oos_detection.infrastructure.service_bus_infrastructure import \
    StatefulAzurePanoClient, StatefulOutsRecommendationClient
from cloud_oos_detection.app_logging import logger

PANO_INGEST_COUNTER = Counter("pano_processing_total", "The number of panos the service is processing", ['direction'])


class AzurePanoBytesResponse(object):
    def __init__(self, byte_array, pano_upload_event):
        self.byte_array = byte_array
        self.pano_upload_event = pano_upload_event


class AbstractPanoProvider(object):
    def provide(self):
        raise NotImplementedError("Abstract Class")

    def acknowledge(self):
        raise NotImplementedError("Abstract Class")


class AbstractMessageSubscriber(object):
    def listen(self):
        raise NotImplementedError("Abstract Class")

    def acknowledge(self):
        raise NotImplementedError("Abstract Class")


class AzurePanoBytesService(object):
    def __init__(self, account_name, sas_token):
        self.account_name = account_name
        self.sas_token = sas_token
        self._block_blob_service = BlockBlobService(self.account_name,
                                                    self.sas_token)

    @staticmethod
    def build_from_environment():
        account_name = os.environ['CLOUD_DETECTION_PANO_STORAGE_ACCOUNT_NAME']
        sas_token = os.environ['CLOUD_DETECTION_PANO_STORAGE_ACCOUNT_SAS_KEY']

        return AzurePanoBytesService(account_name, sas_token)

    def download(self, pano_upload_event):
        assert (isinstance(pano_upload_event, PanoUploadEvent))
        return AzurePanoBytesResponse(
                self._block_blob_service.get_blob_to_bytes(
                    pano_upload_event.container_name,
                    pano_upload_event.url),
                self.pano_upload_event.pano_upload)


class AzurePanoProvider(AbstractPanoProvider):
    @staticmethod
    def build_from_environment():
        namespace_name = os.environ['CLOUD_OOS_DETECTION_SERVICE_NAMESPACE']
        sas_token = os.environ['CLOUD_OOS_DETECTION_PANO_SUBSCRIPTION_KEY']
        topic_name = os.environ['CLOUD_OOS_DETECTION_PANO_TOPIC_NAME']
        subscription_name = os.environ['CLOUD_OOS_DETECTION_PANO_SUBSCRIPTION_NAME']

        bus = ServiceBusService(service_namespace=namespace_name, account_key=sas_token)
        subscriber = StatefulAzurePanoClient(bus, topic_name, subscription_name)
        pano_service = AzurePanoBytesService.build_from_environment()
        return AzurePanoProvider(subscriber, pano_service)

    def __init__(self, subscriber, pano_service):
        self._subscriber = subscriber
        self.pano_service = pano_service
        self._pano_event_envelope = None

    def provide(self):
        if self._pano_event_envelope is not None:
            logger.error("Requested to provide pano while pano is outstanding")
        return self._workflow()

    def acknowledge(self):
        if self._pano_event_envelope is None:
            logger.warn("Attempt to acknowledge non existent message")
        else:
            self._pano_event_envelope.delete()
            PANO_INGEST_COUNTER.labels(direction='outbound').inc()

    def _workflow(self):
        self._pano_event_envelope = self._subscriber.listen()
        if self._pano_event_envelope is not None:

            if self._pano_event_envelope.pano_upload is not None:
                PANO_INGEST_COUNTER.labels(direction='inbound').inc()
                try:

                    logger.info(
                        "Ingested PanoEventEnvelope with correlation id {cid}".format(
                            cid=self._pano_event_envelope.correlation_id))
                    return self.pano_service.download(self._pano_event_envelope.pano_upload)
                except EOFError, ef:
                    logger.error("Poison message received: %s", ef)
                    self._subscriber.acknowledge()

            else:
                logger.warn("Irrelevant envelope with correlation id {cid}".format(
                    cid=self._pano_event_envelope.correlation_id))
                self._subscriber.acknowledge()

        return None


class FileBasedPanoWorkflow(AbstractPanoProvider):
    def __init__(self, directory):
        self.directory = directory

    def provide(self, callback):
        return self._workflow(callback)

    def _workflow(self, callback):
        panos = os.listdir(self.directory)
        for pano in panos:
            full_path = os.path.join(self.directory, pano)
            with open(full_path, 'r') as fd:
                byte_array = np.fromfile(fd, dtype='uint8')
                #                 callback(byte_array)
                # TODO callback function to handle the deliver of pano
                return byte_array, PanoUploadEvent(url="foo", container_name='container')


class CoordinateStorageService(object):
    def store(self, coordinates):
        raise NotImplementedError("Abstract Class")


class AzureCoordinateStorageService(CoordinateStorageService):
    @staticmethod
    def build_from_environment():
        namespace_name = os.environ['CLOUD_OOS_DETECTION_SERVICE_NAMESPACE']
        sas_token = os.environ['CLOUD_DETECTION_RESULTS_TOPIC_KEY']
        topic_name = os.environ['CLOUD_DETECTION_RESULTS_TOPIC_NAME']
        bus = ServiceBusService(service_namespace=namespace_name, account_key=sas_token)
        client = StatefulOutsRecommendationClient(bus, topic_name)
        return AzureCoordinateStorageService(client)

    def __init__(self, client):
        self._client = client

    def store(self, coordinates):
        assert isinstance(coordinates, OutRecommendationEvent)
        self._client.publish(coordinates)
