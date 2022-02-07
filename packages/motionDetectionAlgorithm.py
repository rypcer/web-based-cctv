import datetime, time 
import cv2

def drawTimeStamp(frame,timestamp):
    cv2.putText(frame, timestamp.strftime("%A %d %B %Y %I:%M:%S%p"), (10, 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

def drawMotionBox(contour,frame):
    (x, y, w, h) = cv2.boundingRect(contour)
    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 1)

def extractContours(contours, area_size=700):
    # Extracts the bigger white motion detected areas 
    out_cntrs =[]
    for contour in contours:
        if cv2.contourArea(contour) < area_size:        
            continue
        else:
            out_cntrs.append(contour)
    return out_cntrs

        
def detectMotionInFrame(prev_frame, cur_frame, thresholdVal = 20):
    # 1. Calculate Absolute Difference between Foreground & Background
    # 2. Convert Result To GrayScale
    # 3. Blur Frame
    # 4. Remove small blurred blobs from Frame with Dilations
    diff = cv2.absdiff(prev_frame, cur_frame)
    #cv2.imshow("feed", diff)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    #cv2.imshow("feed", gray)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    thresh = cv2.threshold(blur, thresholdVal, 255, cv2.THRESH_BINARY)[1]
    #cv2.imshow("feed", thresh)
    dilated = cv2.dilate(thresh, None, iterations=3)
    contours = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0]
    contours = extractContours(contours)
    if(len(contours)==0):
        return None
    return contours

def gen_video_name(name, timestamp):
    return name+'_'+timestamp.strftime("%d-%m-%Y_%H-%M-%S")

