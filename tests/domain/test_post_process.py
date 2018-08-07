import unittest
from bnr_robot_cloud_common.codegen.image.ttypes import PanoUploadEvent
from bnr_robot_cloud_common.codegen.label.ttypes import LabelDetected
from bnr_robot_cloud_common.codegen.common.ttypes import AnalyticsHeader
from bnr_robot_cloud_common.codegen.common.ttypes import Location
from cloud_oos_detection.tasks.oos_post_process import PostProcessing
from cloud_oos_detection.tasks.utils.rect import RectXY


class TestPostProcessing(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        label_coordinates = [
                           {u'x2': 888.0, u'y1': 1250.5, u'x1': 830.0, u'score': 0.7487457990646362, u'y2': 1281.5}
                          ,{u'x2': 1006.5, u'y1': 1250.0, u'x1': 949.5, u'score': 0.766859233379364, u'y2': 1282.0}
                          ,{u'x2': 764.0, u'y1': 1247.0, u'x1': 696.0, u'score': 0.6605881452560425, u'y2': 1281.0}
                          ,{u'x2': 1311.0, u'y1': 1251.0, u'x1': 1243.0, u'score': 0.7006424069404602, u'y2': 1283.0}
                          ,{u'x2': 1403.5, u'y1': 1248.0, u'x1': 1344.5, u'score': 0.4193185865879059, u'y2': 1282.0}
                          ,{u'x2': 1792.0, u'y1': 1252.0, u'x1': 1740.0, u'score': 0.7496013045310974, u'y2': 1282.0}
                          ,{u'x2': 2026.0, u'y1': 1252.5, u'x1': 1964.0, u'score': 0.4746813178062439, u'y2': 1283.5}
                          ,{u'x2': 1065.0, u'y1': 1556.0, u'x1': 1003.0, u'score': 0.8263323903083801, u'y2': 1584.0}
                          ,{u'x2': 1080.5, u'y1': 1864.5, u'x1': 1015.5, u'score': 0.7881831526756287, u'y2': 1895.5}
                          ,{u'x2': 930.0, u'y1': 1559.5, u'x1': 876.0, u'score': 0.642421543598175, u'y2': 1586.5}
                          ,{u'x2': 763.0, u'y1': 1560.5, u'x1': 701.0, u'score': 0.5948898792266846, u'y2': 1589.5}
                          ,{u'x2': 763.5, u'y1': 1865.5, u'x1': 698.5, u'score': 0.4365368187427521, u'y2': 1896.5}
                          ,{u'x2': 1303.5, u'y1': 1864.0, u'x1': 1238.5, u'score': 0.8164230585098267, u'y2': 1898.0}
                          ,{u'x2': 1516.0, u'y1': 1861.5, u'x1': 1452.0, u'score': 0.8087289333343506, u'y2': 1896.5}
                          ,{u'x2': 1155.0, u'y1': 1558.5, u'x1': 1099.0, u'score': 0.7831433415412903, u'y2': 1587.5}
                          ,{u'x2': 1307.0, u'y1': 1558.0, u'x1': 1249.0, u'score': 0.7730177044868469, u'y2': 1586.0}
                          ,{u'x2': 1598.5, u'y1': 1559.5, u'x1': 1539.5, u'score': 0.7512322664260864, u'y2': 1588.5}
                          ,{u'x2': 1402.0, u'y1': 1866.0, u'x1': 1338.0, u'score': 0.773095428943634, u'y2': 1898.0}
                          ,{u'x2': 1359.5, u'y1': 1560.5, u'x1': 1302.5, u'score': 0.5328022241592407, u'y2': 1589.5}
                          ,{u'x2': 1983.5, u'y1': 1562.0, u'x1': 1922.5, u'score': 0.8385599255561829, u'y2': 1592.0}
                          ,{u'x2': 1661.0, u'y1': 1861.5, u'x1': 1595.0, u'score': 0.8351650238037109, u'y2': 1894.5}
                          ,{u'x2': 1812.5, u'y1': 1557.5, u'x1': 1753.5, u'score': 0.7382558584213257, u'y2': 1586.5}
                          ,{u'x2': 1839.0, u'y1': 1858.5, u'x1': 1773.0, u'score': 0.7210707664489746, u'y2': 1891.5}
                          ]
        header = AnalyticsHeader(customer_id='CUST-1', store_id='STORE-1',
                                      aisle_id='ASILE-1', generated_at=None,
                                      unique_id=None, robot_id='ROBOT-1',
                                      run_id='1', context=None,)

        self.label_json = [LabelDetected(header=header,
                           location=Location(x1=each['x1'],
                                             y1=each['y1'],
                                             x2=each['x2'],
                                             y2=each['y2']))
                           for each in label_coordinates]

        self.label_json_empty = []
        self.oos_rect_coordinates = [
                        [742.5, 1321.5, 1273.5, 1622.5, 0.40706422925],
                        [1639.0, 1053.0, 1953.0, 1345.0, 0.563274502754],
                        ]

        self.oos_json = [RectXY(
                         [each[0], each[1], each[2], each[3]],
                         is_wh=False, score=each[4])
                         for each in self.oos_rect_coordinates]
        self.pano_upload_event = PanoUploadEvent(url="foo",
                                                 container_name='container')

    def test_no_of_label_oos_rects_processed(self):
        p = PostProcessing(self.oos_json, self.label_json,
                           pano_upload_event=self.pano_upload_event)
        self.assertEqual(len(p.run()['oos_coordinates']), 2)
        self.assertEqual(len(p.run()['label_coordinates']), 6)

    def test_instance_of_outputs_processed(self):
        p = PostProcessing(self.oos_json, self.label_json,
                           pano_upload_event=self.pano_upload_event)
        self.assertIsInstance(p.run(), dict)

    def test_outputs_processed(self):
        p = PostProcessing(self.oos_json, self.label_json,
                           pano_upload_event=self.pano_upload_event)
        self.result = [{'y2': 1622, 'x2': 1273, 'score': 0.40706422925, 'y1': 1321, 'x1': 742, 'class': 1},
                       {'y2': 1345, 'x2': 1953, 'score': 0.563274502754, 'y1': 1053, 'x1': 1639, 'class': 1}]
        self.assertEqual(p.run()['oos_coordinates'], self.result)

    def test_outputs_if_labels_are_empty(self):
        p = PostProcessing(self.oos_json, self.label_json_empty,
                           pano_upload_event=self.pano_upload_event)
        self.assertEqual(len(p.run()['oos_coordinates']), len(self.oos_rect_coordinates))
