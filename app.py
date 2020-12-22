# import the necessary packages
import numpy as np
import argparse
import time
import cv2
import os
from flask import Flask, request, Response, jsonify
import jsonpickle
import base64
import io as StringIO
import base64
from io import BytesIO
import io
import json
from PIL import Image
# import matplotlib.pyplot as plt

# construct the argument parse and parse the arguments

confthres = 0.3
nmsthres = 0.1
yolo_path = './'

def get_labels(labels_path):
    # load the COCO class labels our YOLO model was trained on
    #labelsPath = os.path.sep.join([yolo_path, "yolo_v3/coco.names"])
    lpath=os.path.sep.join([yolo_path, labels_path])
    LABELS = open(lpath).read().strip().split("\n")
    return LABELS

def get_colors(LABELS):
    # initialize a list of colors to represent each possible class label
    np.random.seed(42)
    COLORS = np.random.randint(0, 255, size=(len(LABELS), 3),dtype="uint8")
    return COLORS

def get_weights(weights_path):
    # derive the paths to the YOLO weights and model configuration
    weightsPath = os.path.sep.join([yolo_path, weights_path])
    return weightsPath

def get_config(config_path):
    configPath = os.path.sep.join([yolo_path, config_path])
    return configPath

def load_model(configpath,weightspath):
    # load our YOLO object detector trained on COCO dataset (80 classes)
    print("[INFO] loading YOLO from disk...")
    net = cv2.dnn.readNetFromDarknet(configpath, weightspath)
    return net


# def image_to_byte_array(image:Image):
#     imgByteArr = io.BytesIO()
#     image.save(imgByteArr, format='PNG')
#     imgByteArr = base64.encodebytes(imgByteArr.getvalue()).decode('ascii')
#     return imgByteArr

def image_to_byte_array(image:Image):
    imgByteArr = io.BytesIO()
    image.save(imgByteArr, format='PNG')
    imgByteArr = imgByteArr.getvalue()
    return imgByteArr

def get_response_image(image_path):
    pil_img = Image.open(image_path, mode='r') # reads the PIL image
    byte_arr = io.BytesIO()
    pil_img.save(byte_arr, format='PNG') # convert the PIL image to byte array
    encoded_img = base64.encodebytes(byte_arr.getvalue()).decode('ascii') # encode as base64
    return encoded_img


def get_predection(image,net,LABELS,COLORS):
    (H, W) = image.shape[:2]

    # determine only the *output* layer names that we need from YOLO
    ln = net.getLayerNames()
    ln = [ln[i[0] - 1] for i in net.getUnconnectedOutLayers()]

    # construct a blob from the input image and then perform a forward
    # pass of the YOLO object detector, giving us our bounding boxes and
    # associated probabilities
    blob = cv2.dnn.blobFromImage(image, 1 / 255.0, (416, 416),
                                 swapRB=True, crop=False)
    net.setInput(blob)
    start = time.time()
    layerOutputs = net.forward(ln)
    # print("layerOutputs {}".format(layerOutputs))
    end = time.time()

    # show timing information on YOLO
    print("[INFO] YOLO took {:.6f} seconds".format(end - start))

    # initialize our lists of detected bounding boxes, confidences, and
    # class IDs, respectively
    boxes = []
    confidences = []
    classIDs = []

    # loop over each of the layer outputs
    for output in layerOutputs:
        # loop over each of the detections
        for detection in output:
            # extract the class ID and confidence (i.e., probability) of
            # the current object detection
            # print("D E T E c T  I O  N {}".format(detection))
            scores = detection[5:]
            # print(scores)
            classID = np.argmax(scores)
            # print("classID {}".format(classID))
            confidence = scores[classID]
            # print("CLASS IDSS = > {}".format(classID))
            # filter out weak predictions by ensuring the detected
            # probability is greater than the minimum probability
            if confidence > confthres:
                # scale the bounding box coordinates back relative to the
                # size of the image, keeping in mind that YOLO actually
                # returns the center (x, y)-coordinates of the bounding
                # box followed by the boxes' width and height
                box = detection[0:4] * np.array([W, H, W, H])
                (centerX, centerY, width, height) = box.astype("int")

                # use the center (x, y)-coordinates to derive the top and
                # and left corner of the bounding box
                x = int(centerX - (width / 2))
                y = int(centerY - (height / 2))
                # print(" X = {}, Y = {}".format(x, y))
                # update our list of bounding box coordinates, confidences,
                # and class IDs
                boxes.append([x, y, int(width), int(height)])
                confidences.append(float(confidence))
                classIDs.append(classID)

    # apply non-maxima suppression to suppress weak, overlapping bounding
    # boxes
    idxs = cv2.dnn.NMSBoxes(boxes, confidences, confthres,
                            nmsthres)

    # print("IDXS {}".format(idxs))
    # ensure at least one detection exists
    if len(idxs) > 0:
        # loop over the indexes we are keeping
        for i in idxs.flatten():
            # extract the bounding box coordinates
            (x, y) = (boxes[i][0], boxes[i][1])
            (w, h) = (boxes[i][2], boxes[i][3])

            # draw a bounding box rectangle and label on the image
            color = [int(c) for c in COLORS[classIDs[i]]]
            cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
            text = "{}: {:.4f}".format(LABELS[classIDs[i]], confidences[i])
            # print(boxes)
            # print("CLASS IDS {}".format(classIDs))
            cv2.putText(image, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX,0.5, color, 2)
    return image


labelsPath="yolo_v3/obj.names"
cfgpath="yolo_v3/yolov3-tiny.cfg"
wpath="yolo_v3/yolov3-tiny_17000.weights"
Lables=get_labels(labelsPath)
# print(Lables)
CFG=get_config(cfgpath)
Weights=get_weights(wpath)
nets=load_model(CFG,Weights)
Colors=get_colors(Lables)
# Initialize the Flask application
app = Flask(__name__)

# route http posts to this method
@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({"message": "Smart City Reviews - Server Active"})

@app.route('/api/test', methods=['POST'])
def main():
    # load our input image and grab its spatial dimensions
    #image = cv2.imread("./test1.jpg")
    img = request.json["image"]
    img = Image.open(io.BytesIO(base64.b64decode(img)))
    npimg=np.array(img)
    image=npimg.copy()
    image=cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
    res=get_predection(image,nets,Lables,Colors)
    image=cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
    # show the output image
    # plt.imshow(res, cmap = 'gray', interpolation = 'bicubic')
    # plt.xticks([]), plt.yticks([])  # to hide tick values on X and Y axis
    # plt.show()
    np_img=Image.fromarray(image)
    np_img.save("TEST.png")
    encoded_img = get_response_image("TEST.png")
    response =  { 'Status' : 'Success', 'message': 'Class Detected to be shown here.' , 'image': encoded_img}
    return jsonify(response)
    # return Response(response=img_encoded, status=200,mimetype="image/jpeg")

    # start flask app
if __name__ == '__main__':
    app.run(debug=True)