import unittest
import os
import mock
import numpy as np

from azure.servicebus import Message
from azure.servicebus import ServiceBusService

from bnr_robot_cloud_common.codegen.image.ttypes import PanoUploadEvent, \
    PanoEventEnvelope
from bnr_robot_cloud_common.codegen.common.ttypes import AnalyticsHeader
from cloud_oos_detection.service import load_graph, WorkFlow
from cloud_oos_detection.app_utils.utils import prometheus_metrics
from cloud_oos_detection.tasks.tf_inference import TfCall
from cloud_oos_detection.tasks.oos_post_process import PostProcessing
from cloud_oos_detection.tasks.chunk_images import ChunkImages
from cloud_oos_detection.tasks.coordinate_correction import \
    CoordinateCorrection
from cloud_oos_detection.tasks.filter_merge_boxes import FilterMergeBoxesImpl
from cloud_oos_detection.infrastructure.label_services import \
    RedisLabelLookupService
from cloud_oos_detection.infrastructure import binary_serialize, \
    binary_deserialize
from cloud_oos_detection.infrastructure.service_bus_infrastructure import \
            StatefulAzureServiceBusClient
from cloud_oos_detection.infrastructure.pano_service import \
    AzurePanoBytesResponse, AzurePanoProvider, \
    AzurePanoBytesService, AzureCoordinateStorageService
from tests.files import constants
from nose.plugins.attrib import attr


@attr(kind='GPU')
class TestWorkflowServiceGPU(unittest.TestCase):

    def setUp(self):
        self.bus = mock.MagicMock(ServiceBusService)
        self.subscriber = StatefulAzureServiceBusClient(
                                self.bus, "topic", "sub", "pano_upload_event")
        self.blob = mock.MagicMock(AzurePanoBytesService)
        self.provider = mock.MagicMock(AzurePanoProvider(self.subscriber,
                                                         self.blob))
        self.coordinate_storage = \
            mock.MagicMock(AzureCoordinateStorageService)

        self.chunk_image = ChunkImages()
        self.mock_chunk_image = mock.MagicMock(ChunkImages)

        self.tf_call_service = TfCall()
        self.mock_tf_call_service = mock.MagicMock(TfCall)

        self.apply_coordinate_correction = CoordinateCorrection()
        self.mock_apply_coordinate_correction = mock.MagicMock(
                                            CoordinateCorrection)

        self.filter_merge_boxes = FilterMergeBoxesImpl()
        self.mock_filter_merge_boxes = mock.MagicMock(FilterMergeBoxesImpl)

        self.mock_label_service = mock.MagicMock(RedisLabelLookupService)
        self.mock_coordinate_storage = mock.MagicMock(
                                        AzureCoordinateStorageService)
        self.post_processing = PostProcessing()
        self.mock_post_processing = mock.MagicMock(PostProcessing)

        self.header = AnalyticsHeader(customer_id='CUST-1', store_id='STORE-1',
                                      aisle_id='ASILE-1', generated_at=None,
                                      unique_id=None, robot_id='ROBOT-1',
                                      run_id='1', context=None,)
        self.event = PanoUploadEvent(url="foo", container_name='container',
                                     header=self.header)
        self.envelope = PanoEventEnvelope(self.event, "a-b-c")
        message = Message(body=binary_serialize(self.envelope))
        self.good_message = message
        TEST_IMAGE = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  'files', 'panos', 'A.16_shelfview_pano.jpg')

        with open(TEST_IMAGE, 'r') as fd:
            self.byte_array = np.fromfile(fd, dtype='uint8')

        self.pano_event_envelope = binary_deserialize(self.good_message.body,
                                                      PanoEventEnvelope)
        self.provider.provide.return_value = AzurePanoBytesResponse(
                                        self.byte_array,
                                        self.pano_event_envelope.pano_upload)
        self.graph = load_graph('dev')
        self.tf_call_service.graph = self.graph
        self.mock_tf_call_service.graph = self.graph

    @prometheus_metrics(pano_processsed_status=True)
    def test_successfull_processing_of_workflow(self):
        self.mock_label_service.request_labels.return_value = \
                constants.label_json
        self.workflow = WorkFlow(self.graph,
                                 self.chunk_image,
                                 self.tf_call_service,
                                 self.apply_coordinate_correction,
                                 self.filter_merge_boxes,
                                 self.mock_label_service,
                                 self.coordinate_storage,
                                 self.post_processing,
                                 self.provider)
        coordinates = self.workflow.run()
        self.workflow.provider.acknowledge.assert_called()
        self.assertEqual(len(coordinates['oos_coordinates']), 25)
        self.assertEqual(len(coordinates['label_coordinates']), 98)
