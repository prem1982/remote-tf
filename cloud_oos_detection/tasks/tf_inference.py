import json
from os.path import dirname, abspath
import sys
import numpy as np
from datetime import datetime
from prometheus_client import Summary

from utils.rect import Rect
import tensorflow as tf
from cloud_oos_detection.tf_files.constants import TFCONST as TF
from cloud_oos_detection.app_logging import log_time_chunk
from cloud_oos_detection.app_logging import logInfo, logDebug
from cloud_oos_detection.app_utils.utils import log_decorator

from prometheus_client import REGISTRY
TF_CALL_SUMMARY = Summary("tf_call_seconds",
                          "Time spent inside of tensor flow")
REGISTRY.unregister(TF_CALL_SUMMARY)


class TfCall():
    """ this object call the tensorflow model and makes the inference """

    def __init__(self, graph=None, img=None, pano_upload_event=None,
                 show_suppressed=False, hypes_file='oos_hypes.json'):
        self.graph = graph
        self.img = img
        self.pano_upload_event = pano_upload_event
        self.show_suppressed = show_suppressed
        d = dirname(dirname(abspath(__file__)))
        d = d + '/tf_files/' + hypes_file
        self.hypes_config = json.load(open(d))

    @log_decorator
    def run(self, stride_info, height, width, positions):
        ''' This post takes a request from , chunks the image and passes the
        response from tensorflow call'''

        result = {}
        tf_call_no, counter = 0, 0
        sess = tf.Session(graph=self.graph, config=tf.ConfigProto(log_device_placement=False))
        x_in = self.graph.get_tensor_by_name("x_in:0")
        pred_boxes = self.graph.get_tensor_by_name("decoder/concat:0")
        pred_confs = self.graph.get_tensor_by_name("decoder/Reshape_4:0")

        for each in positions:
            y, x = each
            images = self.img[y:y + height, x:x + width, :]

            if images.shape[0] != stride_info['height'] or \
                    images.shape[1] != stride_info['width']:
                continue

            x_batch = images.astype('float32')
            feed_dict_testing = {x_in: x_batch}
            t1 = datetime.now()
            np_pred_confs, np_pred_boxes = sess.run([pred_confs, pred_boxes],
                                                    feed_dict=feed_dict_testing)
            t2 = datetime.now()
            delta = t2 - t1
            TF_CALL_SUMMARY.observe(delta.total_seconds())
            rects = self._assign_rects(
                                    self.hypes_config,
                                    np_pred_confs,
                                    np_pred_boxes,
                                    use_stitching=True,
                                    rnn_len=1,
                                    min_conf=TF.config('OOS_ARGS')['min_conf'],
                                    tau=TF.config('OOS_ARGS')['tau'],
                                    min_area=TF.config('OOS_ARGS')['min_area']
                                      )

            log_time_chunk(tf_call_no, delta)
            if len(rects) != 0:
                result[each] = rects
            if counter == 20:
                logInfo('''tf inference - no of chunks processed = {0} for container name = {1}
                        for url = {2} '''.format(str(tf_call_no), self.pano_upload_event.container_name, self.pano_upload_event.url)
                        )
                counter = 0

            tf_call_no += 1
            counter += 1
        sess.close()
        return result

    def _assign_rects(self, H, confidences, boxes, use_stitching=False,
                      rnn_len=1, min_conf=0.1, tau=0.25, min_area=100):
        boxes_r = np.reshape(boxes, (-1,
                                     H["grid_height"],
                                     H["grid_width"],
                                     rnn_len,
                                     4))
        confidences_r = np.reshape(confidences, (-1,
                                                 H["grid_height"],
                                                 H["grid_width"],
                                                 rnn_len,
                                                 H['num_classes']))
        cell_pix_size = H['region_size']
        all_rects = [[[] for _ in range(H["grid_width"])]
                     for _ in range(H["grid_height"])]
        for n in range(rnn_len):
            for y in range(H["grid_height"]):
                for x in range(H["grid_width"]):
                    bbox = boxes_r[0, y, x, n, :]
                    abs_cx = int(bbox[0]) + cell_pix_size/2 + cell_pix_size * x
                    abs_cy = int(bbox[1]) + cell_pix_size/2 + cell_pix_size * y
                    w = bbox[2]
                    h = bbox[3]
                    conf = np.max(confidences_r[0, y, x, n, 1:])
                    all_rects[y][x].append(Rect(abs_cx, abs_cy, w, h, conf))

        all_rects_r = [r for row in all_rects for cell in row for r in cell]
        if use_stitching:
            from utils.stitch_wrapper import stitch_rects
            acc_rects = stitch_rects(all_rects, tau)
        else:
            acc_rects = all_rects_r
        
        bounding_boxes = [r for r in acc_rects
                if r.score > min_conf and r.area > min_area]

        return bounding_boxes

    def read_message(self):
        pass

    def send_message(self):
        pass
