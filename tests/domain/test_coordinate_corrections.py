import unittest
import copy

from cloud_oos_detection.tasks.coordinate_correction import \
    CoordinateCorrection
from tests.files import constants
from bnr_robot_cloud_common.codegen.image.ttypes import PanoUploadEvent


class TestCoordinateCorrections(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.coordinates = copy.deepcopy(constants.COORDINATES_FOR_CORRECTION)
        self.pano_upload_event = PanoUploadEvent(url="foo",
                                                 container_name='container')

    def test_coordinates_are_corrected_with_resize_factor_1(self):
        coordinates = CoordinateCorrection(self.coordinates,
                                                self.pano_upload_event).run()
        self.assertEqual(constants.RESIZE_FACTOR_1_COORDINATES,
                         coordinates[0].to_dict())

    def test_coordinates_are_corrected_with_resize_factor_2(self):
        coordinates = CoordinateCorrection(self.coordinates,
                                                self.pano_upload_event,
                                                resize_factor=(2., 2.)).run()
        self.assertEqual(constants.RESIZE_FACTOR_2_COORDINATES,
                         coordinates[0].to_dict())

    def test_check_if_all_coordinates_are_processed(self):
        coordinates = CoordinateCorrection(self.coordinates,
                                                self.pano_upload_event).run()
        self.assertEqual(1, len(coordinates))
