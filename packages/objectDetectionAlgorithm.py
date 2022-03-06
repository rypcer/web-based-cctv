import numpy as np
import cv2

with open("packages/mobileNetSSDClasses.txt", 'r') as f:
    CLASSES = [line.strip() for line in f.readlines()]
COLORS = np.random.uniform(0, 255, size=(len(CLASSES), 3)) # len(classes)*3; 3 means rgb values
net = cv2.dnn.readNetFromCaffe("packages/MobileNetSSD_deploy.prototxt.txt",
 "packages/MobileNetSSD_deploy.caffemodel")
min_conf_threshold = 0.3
blob_res = (400, 400)

def object_detection(previous_frame,current_frame,classesToLookFor):

    detected = 0
    frame_height = current_frame.shape[0]
    frame_width = current_frame.shape[1]

    # Generate Blob - is an array with: nchw(batch, channels,height, width)
    blob = cv2.dnn.blobFromImage(cv2.resize(current_frame,blob_res ),
        0.005719, blob_res, 200)
    net.setInput(blob)
    detections = net.forward()

    # detections has a shape that consists of (1,1,numberOfDetections,7)
    # When access a detection detection[0,0,noOfDetection,Whichparameter]
    # Whichparameter = [Image number, Binary (0 or 1), confidence score (0 to 1), StartX, StartY, EndX, EndY]
    for i in range(detections.shape[2]): 

        # get the probability for the current detection
        confidence = detections[0, 0, i, 2] 

        # If detection exceeds minimum threshold
        if confidence > min_conf_threshold:
            # Get class index of current detection
            # Then get it's (x,y,w,h) * frame(x,y,w,h) 
            # We scale it so it fit's with current frame dimensions
            classIndex = int(detections[0, 0, i, 1])
            box = detections[0, 0, i, 3:7] * np.array([frame_width , 
                frame_height, frame_width , frame_height])
            (x, y, w, h) = box.astype("int")

            # Draw Detection Rectangle
            if(classIndex in classesToLookFor):
                label = CLASSES[classIndex]
                cv2.putText(previous_frame, label, (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[classIndex], 2)
                cv2.rectangle(previous_frame, (x, y), 
                    (w, h), COLORS[classIndex], 2)
                detected = 1

    if(detected): return True
    else: return False
