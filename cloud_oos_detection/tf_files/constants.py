TRAINED_MODEL_ENV = 'dev'


class TFCONST:
    __conf = {
        'OOS_STRIDE_INFO': {'w_stride': 512, 'height': 1024, 'h_stride': 512,
                            'width': 1024},
        'PROD_STRIDE_INFO': {'width': 640, 'height': 640, 'w_stride': 400,
                             'h_stride': 400},
        'OOS_HEIGHT': 1024,
        'OOS_WIDTH': 1024,
        'PROD_HEIGHT': 640,
        'PROD_WIDTH': 640,
        'OOS_HYPES_FILE': 'oos_hypes.json',
        'PROD_HYPES_FILE': 'product_hypes.json',
        'OOS_PB_FILE': 'oos_frozen_graph.pb',
        'PROD_PB_FILE': 'product_frozen_graph.pb',
        'OOS_ARGS': {'min_conf': 0.2, 'tau': 0.25, 'min_area': 5000,
                     'iou_threshold': .5},
        'DEBUG': True
        }

    @staticmethod
    def config(name):
        return TFCONST.__conf[name]
