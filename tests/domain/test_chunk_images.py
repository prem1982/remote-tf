import unittest
import os
import numpy as np

from nose.plugins.attrib import attr

from cloud_oos_detection.tasks.chunk_images import ChunkImages
from tests.files.constants import POSITIONS_RESULT
from bnr_robot_cloud_common.codegen.image.ttypes import PanoUploadEvent

TEST_IMAGE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "files",
                          "panos", 'A.6_shelfview_pano.jpg')


@attr(kind='CI')
class TestChunkImages(unittest.TestCase):
    def setUp(self):
        with open(TEST_IMAGE, 'r') as fd:
            self.byte_array = np.fromfile(fd, dtype='uint8')
        self.pano_upload_event = PanoUploadEvent(url="foo",
                                                 container_name='container')

    def test_give_any_output(self):
        chunk_positions, _ = ChunkImages(self.byte_array,
                                         self.pano_upload_event).run()
        self.assertEqual(len(chunk_positions), 170)

    def test_chunks_is_correct(self):
        chunk_positions, _ = ChunkImages(self.byte_array,
                                         self.pano_upload_event).run()
        self.assertEqual(chunk_positions, POSITIONS_RESULT)

    def test_image_is_not_none(self):
        _, image = ChunkImages(self.byte_array, self.pano_upload_event).run()
        self.assertIsNotNone(image)

    def test_positions_sample_input(self):
        chunk_positions, = ChunkImages().get_pano_positions()
