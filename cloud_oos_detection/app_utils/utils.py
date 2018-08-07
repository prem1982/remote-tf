
from prometheus_client import REGISTRY
from functools import wraps
import cv2

from cloud_oos_detection.app_logging import log_process_start_n_end, \
    logInfo


def prometheus_metrics(pano_processsed_status=True):
    def real_decorator(f):
        @wraps(f)
        def wrapper(*args, **kw):
            if pano_processsed_status:
                before = REGISTRY.get_sample_value('pano_process_success')
            else:
                before = REGISTRY.get_sample_value('pano_process_failure')

            f(*args, **kw)

            if pano_processsed_status:
                after = REGISTRY.get_sample_value('pano_process_success')
            else:
                after = REGISTRY.get_sample_value('pano_process_failure')
            assert 1 == after - before
        return wrapper
    return real_decorator


def log_decorator(f):
    @wraps(f)
    def wrapper(self, *args, **kw):
        log_process_start_n_end(f, self.pano_upload_event.container_name,
                                self.pano_upload_event.url, 'S')
        result = f(self, *args, **kw)
        log_process_start_n_end(f, self.pano_upload_event.container_name,
                                self.pano_upload_event.url, 'E')
        return result
    return wrapper


def equal_dicts(x, y):
    keys_match = set(x.keys()) == set(y.keys())
    vals_match = all([x[k] == y[k] for k in x])

    return keys_match and vals_match


def store_intermediate_results(image_location, image):
    try:
        cv2.imwrite(image_location, image)
    except Exception as e:
        logInfo("Exception writing intermediate files", sys_exc=True)


def reformat_oos_coords_to_x_y_axis(oos_coords):
    return [{'x1': each.x1, 'y1': each.y1, 'x2': each.x2, 'y2': each.y2,
             'score': each.score} for each in oos_coords]


def reformat_label_coords_to_x_y_axis(label_coords):
    return [{'x1': each.location.x1, 'y1': each.location.y1, 'x2': each.location.x2,
             'y2': each.location.y2} for each in label_coords]


def format_coords_output(rects):
    return [{"x1": r.x1, "y1": r.y1, "x2": r.x2, "y2": r.y2,
            "class": 1, "score": r.score} for r in rects]
