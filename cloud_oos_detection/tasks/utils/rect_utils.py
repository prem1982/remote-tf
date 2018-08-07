from rect import RectXY
from bnr_robot_cloud_common.codegen.detection.ttypes import DetectedOut
from bnr_robot_cloud_common.codegen.common.ttypes import Location


class DetectionBoxes(object):
    def __init__(self, detection_boxes, oos_coordinates, label_coordinates):
        self.detection_boxes = detection_boxes
        self.oos_coordinates = oos_coordinates
        self.label_coordinates = label_coordinates


def filter_boxes_by_size(boxes, min_w=20, min_h=20, max_asp_ratio=8):
    return [box for box in boxes if box.width/box.height < max_asp_ratio
            if box.width > min_w or box.height > min_h]


def read_boxes(img_rects, min_conf=.1, annot_format='tensorbox'):
    bboxes = []
    for d in img_rects:
        if "score" not in d:
            d["score"] = 1.0
        bboxes.append(RectXY([int(d["x1"]), int(d["y1"]),
                             int(d["x2"]), int(d["y2"])],
                             is_wh=False, score=d["score"]))
    return bboxes


def filter_boxes_by_shelves(bboxes, shelf_rects):
    new_boxes, filtered_boxes = [], []
    for bbox in bboxes:
        count = 0
        for shelf in shelf_rects:
            if shelf.cov(bbox) > 0:
                count += 1
        if count > 0:
            new_boxes.append(bbox)
        else:
            filtered_boxes.append(bbox)
    return new_boxes, filtered_boxes


def filter_oos_by_labels(oos_rects, label_rects):
    detected_outs, eligible_label_boxes = [], []
    oos_coordinates, label_coordinates = [], []
    for oos_box in oos_rects:
        for label in label_rects:
            if label.cov(oos_box) > 0:
                eligible_label_boxes.append(Location(x1=label.x1,
                                                     y1=label.y1,
                                                     x2=label.x2,
                                                     y2=label.y2))
                label_coordinates.append(label)
        detected_outs.append(DetectedOut(Location(x1=oos_box.x1,
                             y1=oos_box.y1,
                             x2=oos_box.x2,
                             y2=oos_box.y2),
                             eligible_label_boxes))
        eligible_label_boxes = []
        oos_coordinates.append(oos_box)

    return DetectionBoxes(detected_outs, oos_coordinates, label_coordinates)
