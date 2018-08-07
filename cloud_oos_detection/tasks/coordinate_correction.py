import sys
from prometheus_client import Counter
from cloud_oos_detection.app_utils.utils import log_decorator
from cloud_oos_detection.app_logging import logDebug
from cloud_oos_detection.app_utils.exception import WorkflowException

COORDINATES_CORRECTED_TOTAL = Counter("coordinates_correction_total",
                                      "total coordinates corrected")


class CoordinateCorrection(object):

    def __init__(self, positions_rect_dict=None, pano_upload_event=None,
                 resize_factor=(1., 1.)):
        self.positions_rect_dict = positions_rect_dict
        self.resize_factor = resize_factor
        self.pano_upload_event = pano_upload_event

    @log_decorator
    def run(self):
        try:
            all_rects = []
            for position, rects in self.positions_rect_dict.items():
                i, j = position
                for rect in rects:
                    rect.transform(self.resize_factor, j, i)
                    all_rects.append(rect)

                logDebug("rects after coordinate correction {0} ".format(all_rects))

        except Exception as e:
            raise WorkflowException(
                                'Coordinate Correction Exception in ' +
                                'line {0} for container {1} and url {2}'.
                                format(sys.exc_info()[2].tb_lineno,
                                       self.pano_upload_event.container_name,
                                       self.pano_upload_event.url), e)

        return all_rects
