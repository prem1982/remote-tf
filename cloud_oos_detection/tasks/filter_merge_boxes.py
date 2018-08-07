import sys
from cloud_oos_detection.app_utils.utils import log_decorator
from cloud_oos_detection.app_utils.exception import WorkflowException
from prometheus_client import Counter
from cloud_oos_detection.tf_files.constants import TFCONST

FILTER_COUNTER = Counter("filter_merge_total", "Box flow in and out", ["kind"])


class FilterMergeBoxes(object):
    def merge_boxes(self, pano_rects, iou_threshold=0.5, score_threshold=0.2):
        raise NotImplementedError("Abstract Class")


class FilterMergeBoxesImpl():

    def __init__(self, rects=None, pano_upload_event=None,):
        self.rects = rects
        self.pano_upload_event = pano_upload_event

    @log_decorator
    def run(self):
        ''' This method filters and merge the boxes '''
        try:
            final_indices = {}
            final_rects = sorted(self.rects,
                                 key=lambda r: r.width*r.height,
                                 reverse=True)
            for i in range(len(final_rects)):

                if i in final_indices:
                    curr_root = final_indices[i]
                else:
                    curr_root = i
                rect = final_rects[curr_root]

                for j in range(i+1, len(final_rects)):
                    if j in final_indices:
                        other = final_rects[final_indices[j]]
                    else:
                        other = final_rects[j]

                    cov = other.cov(rect)
                    if cov > TFCONST.config('OOS_ARGS')['iou_threshold']:
                        final_indices[j] = curr_root
            final_rects = list(set([final_rects[i] if i not in final_indices
                                    else final_rects[final_indices[i]]
                                    for i in range(len(final_rects))]))
        except Exception as e:
            raise WorkflowException(
                                'Filter Merge Boxes Exception in ' +
                                'line {0} for container {1} and url {2}'.
                                format(sys.exc_info()[2].tb_lineno,
                                       self.pano_upload_event.container_name,
                                       self.pano_upload_event.url), e)
        return final_rects
