import os
import sys
from sys import exc_info
import signal

from prometheus_client import Counter
import tensorflow as tf
from azure.common import AzureException

from cloud_oos_detection.app_logging import logger, logInfo
from tasks.chunk_images import ChunkImages
from tasks.tf_inference import TfCall
from tasks.oos_post_process import PostProcessing
from tasks.coordinate_correction import CoordinateCorrection
from tasks.filter_merge_boxes import FilterMergeBoxesImpl
from bnr_robot_cloud_common.codegen.detection.ttypes import DetectedOut, OutRecommendationEvent, DetectionEventEnvelope
from cloud_oos_detection.infrastructure.pano_service import AzurePanoProvider,\
                FileBasedPanoWorkflow, AzureCoordinateStorageService
from cloud_oos_detection.infrastructure.label_services import RedisLabelLookupService
from cloud_oos_detection.app_utils.exception import WorkflowException
from cloud_oos_detection.tf_files.constants import TFCONST as TF
from cloud_oos_detection.tf_files.constants import TRAINED_MODEL_ENV


TF_FAILURE_COUNT = Counter("pano_process_failure", "failure counter")
TF_SUCCESS_COUNT = Counter("pano_process_success", "success counter")
os.environ['CUDA_VISIBLE_DEVICES'] = '0'


class WorkFlow(object):
    def __init__(self, oos_graph, chunk_image, tf_call_service,
                 apply_coordinate_correction, filter_merge_boxes,
                 label_service, coordinate_storage, post_processing,
                 provider):
        self.chunk_image = chunk_image
        self.tf_call_service = tf_call_service
        self.tf_call_service.graph = oos_graph
        self.apply_coordinate_correction = apply_coordinate_correction
        self.filter_merge_boxes = filter_merge_boxes
        self.label_service = label_service
        self.coordinate_storage = coordinate_storage
        self.post_processing = post_processing
        self.provider = provider

    def run(self):
        try:
            # get pano byte_array and pano upload event
            self.azure_pano_byte_response = self.provider.provide(return_panos)
            if self.azure_pano_byte_response is not None:
                # chunk the images
                self.chunk_image.byte_array = \
                    self.azure_pano_byte_response.byte_array
                self.pano_upload_event =  \
                    self.azure_pano_byte_response.pano_upload_event

                self.chunk_image.pano_upload_event = self.pano_upload_event
                self.positions, self.tf_call_service.img = self.chunk_image.run()

                # tensorflow service call
                self.tf_call_service.pano_upload_event = self.pano_upload_event
                self.coordinates = self.tf_call_service.run(
                                    stride_info=TF.config('OOS_STRIDE_INFO'),
                                    height=TF.config('OOS_HEIGHT'),
                                    width=TF.config('OOS_WIDTH'),
                                    positions=self.positions)

                # appy coordinate correction
                self.apply_coordinate_correction.positions_rect_dict = \
                    self.coordinates
                self.apply_coordinate_correction.pano_upload_event = \
                    self.pano_upload_event
                self.coordinates = self.apply_coordinate_correction.run()

                # filter merge boxes
                self.filter_merge_boxes.rects = self.coordinates
                self.filter_merge_boxes.pano_upload_event = \
                    self.pano_upload_event
                print 'filter_merge_boxes_rect = ', self.filter_merge_boxes.rects
                self.oos_coordinates = self.filter_merge_boxes.run()

                # get label coordinates
                self.label_coordinates = self.label_service.request_labels(
                    self.pano_upload_event.header.customer_id,
                    self.pano_upload_event.header.store_id,
                    self.pano_upload_event.header.run_id,
                    self.pano_upload_event.header.aisle_id)

                # post processing

                self.post_processing.oos_coords = self.oos_coordinates
                self.post_processing.label_coords = self.label_coordinates
                self.post_processing.pano_upload_event = self.pano_upload_event
                self.coordinates = self.post_processing.run()
                # send coordinates to HITL
                out_rec_event = OutRecommendationEvent(
                    header=self.azure_pano_byte_response.pano_upload_event.header,
                    url=self.azure_pano_byte_response.pano_upload_event.url,
                    container_name=self.azure_pano_byte_response.pano_upload_event.container_name,
                    detected_outs=self.coordinates['detection_boxes']
                    )

                self.coordinate_storage.store(out_rec_event)

                # acknowledge pano has been processed
                self.provider.acknowledge()

                TF_SUCCESS_COUNT.inc()
                return self.coordinates
        except AzureException, ae:
            # TODO more specific errors for transient exceptions
            TF_FAILURE_COUNT.inc()
            logger.error("Azure Exception ", exc_info=True)
        except tf.OpError, oe:
            TF_FAILURE_COUNT.inc()
            logger.error("Tensorflow Exception", exc_info=True)
        except WorkflowException, we:
            TF_FAILURE_COUNT.inc()
            logger.error("Workflow Exception {0}".format(we), exc_info=True)
        except Exception, e:
            TF_FAILURE_COUNT.inc()
            logger.info("pano not processed", exc_info=True)

        return None


def return_panos(byte_array):
    # TODO need to write a iterator to deliver a pano
    return byte_array


def load_graph(trained_model_env):
    ''' This method loads the graph '''
    dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'tf_files', '{env}/')
    dir_path = dir_path.format(env=trained_model_env.lower())
    pb_graphs = [dir_path + TF.config('OOS_PB_FILE')]
    # ,dir_path + TF.config('PROD_PB_FILE') ]
    graphs = []
    for each in pb_graphs:
        if os.path.isfile(each):
            with tf.gfile.GFile(each, "rb") as f:
                graph_def = tf.GraphDef()
                graph_def.ParseFromString(f.read())
            with tf.Graph().as_default() as graph:
                tf.import_graph_def(
                    graph_def,
                    input_map=None,
                    return_elements=None,
                    name=""
                )
            graphs.append(graph)
        else:
            sys.exit("OOS Model - pb file not available in the directory..Please check!!")
    oos_graph = graphs[0]
    return oos_graph


class SigTermHandler:
    terminate_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.terminate_now = True


class Service(object):
    @staticmethod
    def build_from_environment(local=False,
                               local_dir_path=None,
                               chunk_image=None,
                               tf_call_service=None,
                               apply_coordiante_correction=None,
                               filter_merge_boxes=None,
                               label_service=None,
                               coordinate_storage=None,
                               trained_model_env=None):
        # TODO depends on your model version strategy
        model_version = os.environ['CLOUD_OOS_DETECTION_MODEL_VERSION']
        if local:
            pano_provider = FileBasedPanoWorkflow(local_dir_path)
            return Service(trained_model_env,
                           pano_provider,
                           chunk_image,
                           tf_call_service,
                           apply_coordinate_correction,
                           filter_merge_boxes,
                           label_service,
                           coordinate_storage,
                           post_processing)
        else:
            pano_provider = AzurePanoProvider.build_from_environment()
            return Service(trained_model_env,
                           pano_provider,
                           chunk_image,
                           tf_call_service,
                           apply_coordinate_correction,
                           filter_merge_boxes,
                           label_service,
                           coordinate_storage,
                           post_processing)

    def __init__(self, trained_model_env, pano_provider, chunk_image,
                 tf_call_service, apply_coordinate_correction,
                 filter_merge_boxes, label_service, coordinate_storage,
                 post_processing):
        self._trained_model_env = trained_model_env
        self.pano_provider = pano_provider
        self.chunk_image = chunk_image
        self.coordinate_storage = coordinate_storage
        self.tf_call_service = tf_call_service
        self.apply_coordinate_correction = apply_coordinate_correction
        self.filter_merge_boxes = filter_merge_boxes
        self.label_service = label_service
        self.post_processing = post_processing
        self.load_graph()
        self.termination_handler = SigTermHandler()

    def load_graph(self):

        self.oos_graph = load_graph(self._trained_model_env)

    def main(self):
        w = WorkFlow(self.oos_graph,
                             self.chunk_image,
                             self.tf_call_service,
                             self.apply_coordinate_correction,
                             self.filter_merge_boxes,
                             self.label_service,
                             self.coordinate_storage,
                             self.post_processing,
                             self.pano_provider)

        while True:
                w.run()


if __name__ == "__main__":
    tf_call_service = TfCall()
    apply_coordinate_correction = CoordinateCorrection()
    filter_merge_boxes = FilterMergeBoxesImpl()
    label_service = RedisLabelLookupService.build_from_environment()
    coordinate_storage = AzureCoordinateStorageService().build_from_environment()
    chunk_image = ChunkImages()
    post_processing = PostProcessing()
    service = Service.build_from_environment(
                     chunk_image=chunk_image,
                     tf_call_service=tf_call_service,
                     apply_coordiante_correction=apply_coordinate_correction,
                     filter_merge_boxes=filter_merge_boxes,
                     label_service=label_service,
                     coordinate_storage=coordinate_storage,
                     trained_model_env=TRAINED_MODEL_ENV
                                            )
    service.main()
