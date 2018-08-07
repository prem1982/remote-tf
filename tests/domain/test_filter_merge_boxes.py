import unittest
import os

from nose.plugins.attrib import attr

from cloud_oos_detection.tasks.filter_merge_boxes import FilterMergeBoxesImpl
from bnr_robot_cloud_common.codegen.image.ttypes import PanoUploadEvent
from cloud_oos_detection.tasks.utils.rect import Rect

TEST_IMAGE = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                          "files", "panos", 'a6_2048_2048_2_rects.jpg')


@attr(kind='CI')
class TestFilterMergeBoxesImpl(unittest.TestCase):
    def setUp(self):
        self.dict_1_rect_inside_other_rect = [Rect(1200, 1050, 400, 300, 0),
                                              Rect(1200, 1050, 300, 200, 0)]

        self.dict_2_rect_overlapping_less_than_50_percent = \
            [Rect(1200, 1050, 400, 300, 0),
             Rect(1200, 1175, 400, 250, 0)]

        self.dict_2_rect_overlapping_more_than_50_percent = \
            [Rect(1200, 1050, 400, 300, 0),
             Rect(1200, 1125, 400, 350, 0)]

        self.dict_3_rect_overlapping_2_more_than_50_pct = \
            [Rect(1200, 1050, 400, 300, 0),
             Rect(1200, 1125, 400, 350, 0),
             Rect(1250, 1500, 300, 200, 0)]

        self.pano_upload_event = PanoUploadEvent(url="foo",
                                                 container_name='container')

    def test_pano_with_one_rectangle_inside(self):
        rects = FilterMergeBoxesImpl(self.dict_1_rect_inside_other_rect,
                                     self.pano_upload_event).run()
        self.assertEqual(rects[0].to_dict(),
                         {'cx': 1200, 'x2': 1400.0, 'cy': 1050,
                          'y2': 1200.0, 'score': 0, 'width': 400,
                          'y1': 900.0, 'x1': 1000.0, 'confidence': 0,
                          'height': 300})

    def test_pano_overlapping_2_rects_less_than_50_percent(self):
        rects = FilterMergeBoxesImpl(
                self.dict_2_rect_overlapping_less_than_50_percent,
                self.pano_upload_event).run()
        self.assertEqual(rects[0].to_dict(),
                         {'cx': 1200, 'x2': 1400.0, 'cy': 1050,
                          'y2': 1200.0, 'score': 0, 'width': 400,
                          'y1': 900.0, 'x1': 1000.0, 'confidence': 0,
                          'height': 300})

    def test_pano_overlapping_2_rects_more_than_50_percent(self):
        rects = FilterMergeBoxesImpl(
                    self.dict_2_rect_overlapping_more_than_50_percent,
                    self.pano_upload_event).run()
        self.assertEqual(rects[0].to_dict(),
                         {'cx': 1200, 'x2': 1400.0, 'cy': 1125,
                          'y2': 1300.0, 'score': 0, 'width': 400,
                          'y1': 950.0, 'x1': 1000.0, 'confidence': 0,
                          'height': 350})

    def test_pano_overlapping_3_rects_2_more_than_50_percent(self):
        rects = FilterMergeBoxesImpl(
                    self.dict_3_rect_overlapping_2_more_than_50_pct,
                    self.pano_upload_event).run()
        self.assertEqual(len(rects), 2)
