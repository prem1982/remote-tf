import sys
import cv2

from cloud_oos_detection.app_utils.utils import log_decorator
from cloud_oos_detection.app_utils.exception import WorkflowException
from cloud_oos_detection.tf_files.constants import TFCONST
import itertools


class ChunkImages():

    def __init__(self, byte_array=None, pano_upload_event=None):
        self.maxDiff = None
        self.byte_array = byte_array
        self.pano_upload_event = pano_upload_event

    @log_decorator
    def run(self):
        try:
            img = cv2.imdecode(self.byte_array, cv2.IMREAD_UNCHANGED)
            start_x, start_y = 0, 0
            end_y, end_x, _ = img.shape
            positions = self.get_pano_positions(
                            start_x, start_y, end_y, end_x,
                            TFCONST.config('OOS_STRIDE_INFO')['height'],
                            TFCONST.config('OOS_STRIDE_INFO')['width'],
                            TFCONST.config('OOS_STRIDE_INFO')['h_stride'],
                            TFCONST.config('OOS_STRIDE_INFO')['w_stride'])
        except Exception as e:
            raise WorkflowException(
                                'Image Chunking Exception in ' +
                                'line {0} for container {1} and url {2}'.
                                format(sys.exc_info()[2].tb_lineno,
                                       self.pano_upload_event.container_name,
                                       self.pano_upload_event.url), e)
        return positions, img

    def get_pano_positions(self, start_y, start_x, end_y, end_x, chunk_height,
                            chunk_width, chunk_h_stride, chunk_w_stride):
        ''' This methos gets the positions in the pano '''
        i_s = [i for i in range(start_y, end_y, chunk_h_stride)
               if i+chunk_height <= end_y]
        if start_y + chunk_h_stride * (len(i_s)-1) != end_y - chunk_height:
            i_s.append(end_y - chunk_height)

        j_s = [j for j in range(start_x, end_x, chunk_w_stride)
               if j+chunk_width <= end_x]
        if start_x + chunk_w_stride * (len(j_s)-1) != end_x - chunk_width:
            j_s.append(end_x - chunk_width)

        all_pano_pos = list(itertools.product(i_s, j_s))
        return all_pano_pos
