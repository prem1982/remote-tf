import sys
from cloud_oos_detection.app_utils.utils import reformat_oos_coords_to_x_y_axis, \
    reformat_label_coords_to_x_y_axis, format_coords_output
from utils.rect_utils import read_boxes, filter_boxes_by_size, \
    filter_boxes_by_shelves, filter_oos_by_labels
from utils.shelf_estimator import extract_shelves
from cloud_oos_detection.app_utils.utils import log_decorator
from cloud_oos_detection.app_logging import logInfo, logDebug
from cloud_oos_detection.app_utils.exception import WorkflowException


class PostProcessing(object):

    def __init__(self, oos_json=None, label_json=None, min_conf=.1,
                 pano_upload_event=None):
        self.min_conf = min_conf
        self.pano_upload_event = pano_upload_event
        self.oos_coords = oos_json
        self.label_coords = label_json

    @log_decorator
    def run(self):
        try:
            oos_coords_input = reformat_oos_coords_to_x_y_axis(self.oos_coords)
            label_coords_input = reformat_label_coords_to_x_y_axis(self.label_coords)

            logDebug('oos coordinates before pre processing = {0} {1}'.format(
                     oos_coords_input, self._add_container_n_url_name()))

            logDebug('label coordinates before pre processing = {0} {1}'.format(
                     label_coords_input, self._add_container_n_url_name()))

            oos_rects = read_boxes(oos_coords_input)

            label_rects = read_boxes(label_coords_input)

            oos_rects = [r for r in oos_rects if r.score > self.min_conf]

            oos_rects = filter_boxes_by_size(oos_rects, min_w=150, min_h=80,
                                             max_asp_ratio=12)

            label_rects = filter_boxes_by_size(label_rects, min_w=40, min_h=20)

            if len(label_rects) == 0:
                return {'oos_coordinates': format_coords_output(oos_rects),
                        'label_coordinates': None,
                        'detection_boxes': filter_oos_by_labels(oos_rects, label_rects)}

            shelf_rects = read_boxes(extract_shelves(label_rects))

            logInfo('no of oos before processing with shelves {0} {1}'.format(
                    len(oos_rects), self._add_container_n_url_name()))

            oos_rects, removed_rects = filter_boxes_by_shelves(oos_rects,
                                                               shelf_rects)

            logInfo('no of oos within shelf = {0} {1}'.format(len(oos_rects),
                    self._add_container_n_url_name()))

            logInfo('no of labels = {0} {1}'.format(len(label_rects),
                    self._add_container_n_url_name()))

            # add labels that is part of oos regions.
            detection_boxes = filter_oos_by_labels(oos_rects, label_rects)

            logInfo('no of labels within oos region = {0} {1} '.format(len(label_rects),
                    self._add_container_n_url_name()))

            # This can removed - Added for debugging.
            oos_coordinates = format_coords_output(detection_boxes.oos_coordinates)
            label_coordinates = format_coords_output(detection_boxes.label_coordinates)

            logDebug('final shelf coordinates = {0} {1}'.format(shelf_rects,self._add_container_n_url_name()))

            logDebug('final oos coordinates = {0} {1}'.format(oos_coordinates, self._add_container_n_url_name()))

            logDebug('final label coordinates = {0} {1} '.format(label_coordinates, self._add_container_n_url_name()))

        except Exception as e:
            raise WorkflowException(
                                'Post Process Exception in ' +
                                'line {0} for container {1} and url {2}'.
                                format(sys.exc_info()[2].tb_lineno,
                                       self.pano_upload_event.container_name,
                                       self.pano_upload_event.url), e)

        return {'detection_boxes': detection_boxes,
                'oos_coordinates': oos_coordinates,
                'label_coordinates': label_coordinates
                }

    def _add_container_n_url_name(self):
        return 'for container  = ' + self.pano_upload_event.container_name + \
            ' and url  = ' + self.pano_upload_event.url + ' '
