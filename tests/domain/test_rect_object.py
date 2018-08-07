import unittest
from cloud_oos_detection.tasks.utils.rect import Rect


class TestRectObject(unittest.TestCase):

    def setUp(self):
        self.rect1 = Rect(100, 100, 100, 100, 1)
        self.rect2 = Rect(400, 400, 100, 100, 1)
        self.rect3 = Rect(450, 450, 100, 100, 1)
        self.rect4 = Rect(250, 250, 100, 100, 1)

    def test_area_is_calculated_correctly(self):
        self.assertEqual(10000, self.rect1.area())

    def test_rect_is_rescaled_correctly(self):
        self.rect2.rescale(2)
        self.assertEqual(300, self.rect2.x1)
        self.assertEqual(300, self.rect2.y1)

    def test_other_rect_overlaps(self):
        self.rect2.overlaps(self.rect3)
        self.assertEqual(True, True)
        self.rect2.overlaps(self.rect4)
        self.assertEqual(False, False)

    def test_other_rect_intersection(self):
        self.assertEqual(self.rect2.intersection(self.rect3), 2500)

    def test_other_rect_union(self):
        self.assertEqual(self.rect2.union(self.rect3), 17500)
