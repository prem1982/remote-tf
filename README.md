# cloud-oos-detection

Repository that represents services necessary for out of stock detection.

There are 6 tasks involved in this workflow.

1. Chunk the images.
2. Run detection - Images through tensorflow
3. Nominal suppression
4. Apply co-ordinates correction.
5. Filter and merge boxes.
6. Post processing - run product segmentation and send coordinates to HITL


To run the service go to app folder - python service.py

The service.py module assembles all the components and kick starts the service.


