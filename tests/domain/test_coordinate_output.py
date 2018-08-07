import unittest
import os
import numpy as np
from nose.plugins.attrib import attr

from cloud_oos_detection import service
from cloud_oos_detection.tasks.chunk_images import ChunkImages
from cloud_oos_detection.tasks.tf_inference import TfCall
from cloud_oos_detection.tf_files.constants import TRAINED_MODEL_ENV
from bnr_robot_cloud_common.codegen.image.ttypes import PanoUploadEvent
from cloud_oos_detection.tf_files.constants import TFCONST as TF
from tests.files import constants

TEST_IMAGE = os.path.join(os.path.dirname(os.path.dirname(
    __file__)), "files", "panos", 'A.6_shelfview_pano.jpg')

os.environ['CUDA_VISIBLE_DEVICES'] = '0'


@attr(kind='GPU')
class TestCoordinateOutputs(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        with open(TEST_IMAGE, 'r') as fd:
            self.byte_array = np.fromfile(fd, dtype='uint8')
        self.pano_upload_event = PanoUploadEvent(url="foo",
                                                 container_name='container')
        self.oos_graph = service.load_graph(TRAINED_MODEL_ENV)
        self.chunk_positions, self.img = ChunkImages(
                                            self.byte_array,
                                            self.pano_upload_event).run()
        self.response = {'(512, 9728)': [{'score': 0.2135249674320221,
                                          'x1': 233.5,
                                          'x2': 1190.5,
                                          'y1': -7.5,
                                          'y2': 363.5},
                                         {'score': 0.25605374574661255,
                                          'x1': 657.5,
                                          'x2': 1026.5,
                                          'y1': 885.5,
                                          'y2': 1020.5}]}
        self.tf_call = TfCall(graph=self.oos_graph,
                              img=self.img,
                              pano_upload_event=self.pano_upload_event,
                              hypes_file=TF.config('OOS_HYPES_FILE'))
        self.coordinates = self.tf_call.run(
                          stride_info=TF.config('OOS_STRIDE_INFO'),
                          height=TF.config('OOS_HEIGHT'),
                          width=TF.config('OOS_WIDTH'),
                          positions=self.chunk_positions)

    def test_calls_to_tensorflow_gpu_enabled(self):
        formatted_output = {}
        for k, v in self.coordinates.items():
            formatted_coordinates = []
            for each in v:
                coord = each.to_dict()
                del coord['score']
                del coord['confidence']
                formatted_coordinates.append(coord)
            formatted_output[k] = formatted_coordinates
        self.assertEqual(len(formatted_output), len(constants.TF_COORDINATES))
        self.assertEqual(formatted_output, constants.TF_COORDINATES)

    def test_check_results_not_empty(self):
        self.assertNotEqual(len(self.coordinates), 0)
