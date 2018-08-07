from collections import Counter
import numpy as np
from rect_utils import read_boxes


def merge_intervals(shelf_intervals, new_intervals):
    merged_intervals = list(shelf_intervals)
    for new_interval in new_intervals:
        merged = False
        for s in range(len(shelf_intervals)):
            shelf_interval = shelf_intervals[s]
            if ((new_interval[0] > shelf_interval[0] and
                 new_interval[0] - 800 < shelf_interval[1]) or
               (shelf_interval[0] > new_interval[0] and
               shelf_interval[0] - 800 < new_interval[1])) and \
               abs(new_interval[2]-shelf_interval[2]) < 2:
                merged_intervals[s][0] = min(new_interval[0],
                                             shelf_interval[0])
                merged_intervals[s][1] = max(new_interval[1],
                                             shelf_interval[1])
                merged = True
                break
        if not merged:
            merged_intervals.append(new_interval)
    return merged_intervals


def extract_shelves(label_rects, prod_rects=None, factor=15):
    if label_rects is not None:
        if len(label_rects) > 0 and type(label_rects[0]) is dict:
            label_rects = read_boxes(label_rects)
    else:
        return []

    if prod_rects is not None:
        if len(prod_rects) > 0 and \
           type(prod_rects[0]) is dict:
            prod_rects = read_boxes(label_rects)
    else:
        prod_rects = []

    y_values = [l.y1 for l in label_rects]

    y_quantized = [int(round(y_v / factor)) for y_v in y_values]
    c = Counter(y_quantized)
    x1_hist = {y_q: [] for y_q in y_quantized if c[y_q] > 1}

    for label in label_rects:
        y_q = int(round(label.y1 / factor))
        if y_q in x1_hist:
            x1_hist[y_q].append([label.x1, label.y1])

    for prod in prod_rects:
        y_q = int(round(prod.y1 / factor))
        min_dists = []
        for y_delta in [y_q - 1, y_q, y_q + 1]:
            if y_delta in x1_hist:
                label_vals = np.array(x1_hist[y_delta])
                rel_x = [abs(prod.x - l[0]) for l in label_vals
                         if abs(l[1] - prod.y1) < 30]
                min_dists.append(min(rel_x + [10000]))
            else:
                min_dists.append(10000)
        if len(min_dists) == 0 or min(min_dists) > 1000:
            continue
        ind = y_q - 1 + np.argmin(min_dists)
        x1_hist[ind].append([prod.x, prod.y1])

    shelf_intervals = []

    for k, v in sorted(x1_hist.items(), key=lambda ki: ki[0]):
        if len(v) < 1:
            continue
        v.sort(key=lambda vi: vi[0])
        end_indexes = []
        start_index = 0
        h_shelf_intervals = []
        for i in range(1, len(v)):
            if v[i][0] - v[i - 1][0] > 1200:
                end_indexes.append([start_index, i - 1])
                start_index = i
        end_indexes.append([start_index, len(v) - 1])

        for e in end_indexes:
            h_shelf_intervals.append([v[e[0]][0], v[e[1]][0], k])

        # h_shelf_interval contains - [x1,x2,height]

        shelf_intervals = merge_intervals(shelf_intervals, h_shelf_intervals)

    final_shelf_intervals = []

    for shelf_interval in shelf_intervals:
        if shelf_interval[1] - shelf_interval[0] < 100:
            continue
        final_shelf_intervals.append([shelf_interval[0],
                                     shelf_interval[1] + 100,
                                     shelf_interval[2]])

    shelf_segments = [{"x1": int(f[0]),
                       "x2": int(f[1]),
                       "y1": int(f[2] * factor),
                       "y2": int(f[2] * factor + 50), "class": 1}
                      for f in final_shelf_intervals]
    return shelf_segments
