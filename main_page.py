from flask import Flask, render_template, Response,request, redirect,url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
import datetime, time 
import cv2
import sys
import os # to delete files

# ====================== Variables ==================

# Create Flask app & Database
app = Flask(__name__,static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recordings.db'
app.config["SQLAlchemy_TRACK_MODIFICATIONS"] = False
app.config['SECRET_KEY'] = "LetsGood"
db = SQLAlchemy(app)



# Recorded Output Video 
output_resolution = (1280,720)
output_fps = 30
video_format = 'mp4'
fourcc = cv2.VideoWriter_fourcc(*"H264") #.MP4, .AVI = 'XVID' 
is_grayscale = False
recording = False
output_created = False

# Camera Settings
# for ip camera use - rtsp://username:password@ip_address:554/user=username_password='password'_channel=channel_number_stream=0.sdp' 
# for local webcam use cv2.VideoCapture(0)
camera = cv2.VideoCapture('static/vid.mp4')
live_stream_res = (852,480)
camera_name = "MainCamera"
previous_frame = camera.read()[1]
current_frame = camera.read()[1]

# Other settings
current_video = "data:,"
current_video_id = -1
initi = False

rec_stopped_time = None;

time_after_record_ended = 5
timer_started = False
rec_started = False
out = None
output_done = False
# ====================== Classes ==================

class Record(db.Model):
	id = db.Column(db.Integer,primary_key = True)
	video_name = db.Column(db.String(200),nullable=False)

	def __init__(self, name):
		self.video_name = name


# ===================== Functions ====================

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

def generateOutputVideo(database, camera_name, timestamp):
	global output_created, out
	if not output_created:
		out = cv2.VideoWriter(f"static/{gen_video_name(camera_name,timestamp)}.{video_format}", fourcc, output_fps, output_resolution,0)
		output_created = True
		# Add to Database
		new_record = Record(gen_video_name(camera_name,timestamp))
		database.session.add(new_record)
		database.session.commit()
    # Write resized frame to outputVideo
	out_frame = current_frame.copy()

	drawTimeStamp(out_frame,timestamp)
	if is_grayscale:
		out_frame = cv2.cvtColor(out_frame, cv2.COLOR_BGR2GRAY)
	out_frame = cv2.resize(out_frame, output_resolution)
	#print(out_frame.shape,file=sys.stderr)
	out.write(out_frame)

def motion_detection():
	global current_frame, previous_frame, recording, timer_started, rec_stopped_time
	
	previous_frame = current_frame
	camera_working, current_frame = camera.read()
	if not camera_working:
		out.release()
		return False 
				
	timestamp = datetime.datetime.now()
	drawTimeStamp(current_frame, timestamp)

	contours = detectMotionInFrame(previous_frame, current_frame)
	if contours is not None:
		if recording:
			timer_started = False
		else:
			recording = True
		for contour in contours:
			drawMotionBox(contour, previous_frame)
	elif recording:
		if timer_started:
			if time.time() - rec_stopped_time >= time_after_record_ended:
				recording = False
				output_created = True
				out.release()
				print("STOP",file=sys.stderr)
				
		else:
			timer_started = True
			rec_stopped_time = time.time()
	
	if recording: 
		generateOutputVideo(db,camera_name, timestamp)
	return True
@app.route('/gen')
def gen_frames(): 
	global output_done
	while True:

		#camera_working,frame = camera.read()
		if not motion_detection():
			print("WHy",file=sys.stderr)
			output_done = True
			return redirect("/")

			
		# Convert Frame to jpg format and send it
		buffer = cv2.imencode('.jpg', previous_frame)[1]
		img_frame = buffer.tobytes()
		yield (b'--frame\r\n'
			b'Content-Type: image/jpeg\r\n\r\n' + img_frame + b'\r\n')  # concat frame one by one and show result

# Generating the thumbnail is slow needs improving
def gen_thumbnail(video_name): 
	video = cv2.VideoCapture(f'static/{video_name}.mp4')
	if video.isOpened():
		video.set(2,0.5); # Set Frame to middle
		success, frame = video.retrieve()  # read the camera frame
		video.release()
		frame = cv2.resize(frame, (52,30))
		ret, buffer = cv2.imencode('.jpg', frame)
		frame = buffer.tobytes()
		yield (b'--frame\r\n'
			b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result
	else:
		video.release()
		yield(b'--frame\r\n')




# ===================== Routes ====================


# Without methods in paramters, buttons cannot send data to index
@app.route('/', methods=["POST","GET"])
def index():
	global current_video, initi
	
	#if "open" in request.form:
		
	if initi:
		for i in range(5):
			#count = Record.query.count() 
			new_record = Record(gen_video_name(camera_name,timestamp))
			db.session.add(new_record)
		db.session.commit()
		initi = False


	# Get all new records
	records = Record.query.order_by(Record.id.desc()).all()
	#print("Test: ",current_video, file=sys.stderr)
	return render_template('index.html',video_name = current_video, 
		current_video_id=current_video_id, video_format = video_format,records = records)


@app.route('/download/<video_name>,<video_format>')
def download_video (video_name,video_format):
    #For windows you need to use drive name [ex: F:/Example.pdf]
    path = f"static/{video_name}.{video_format}"
    return send_file(path, as_attachment=True)


@app.route('/delete_video/<video_id>')
def delete_video(video_id):
	global current_video
	# Delete Video from Server
	if os.path.isfile(f'static/{current_video}.{video_format}'):
		os.remove(f'static/{current_video}.{video_format}')
	# Delete From Database
	video_record = Record.query.get_or_404(video_id)
	db.session.delete(video_record)
	db.session.commit()
	current_video = "data:,"
	return redirect("/")

@app.route('/rename_video/<video_id>',methods=['POST'])
def rename_video(video_id):
	global current_video
	if request.method == "POST":
		new_name = request.form["new_video_name"];
		is_name_available = db.session.query(Record.id).filter_by(video_name=new_name).first() is not None
		if is_name_available: flash(f" ERROR: '{new_name}' already exists!"); return redirect('/')
		# Rename Video from Server
		if os.path.isfile(f'static/{current_video}.{video_format}'):
			os.rename(f'static/{current_video}.{video_format}',f'static/{new_name}.{video_format}')
		# Rename From Database
		video_record = Record.query.get_or_404(video_id)
		video_record.video_name = new_name
		db.session.commit()
		current_video = new_name
	return redirect('/')


# Get videoname from button link
@app.route('/play_video/<video_name>,<video_id>')
def play_video(video_name,video_id):
	global current_video, current_video_id
	current_video = video_name
	current_video_id = video_id
	return redirect("/")

@app.route('/get_thumbnail/<video_name>')
def get_thumbnail(video_name):
	return Response(gen_thumbnail(video_name), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/liveStream')
def liveStream():
	return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


# ===================== Main ====================

if __name__ == "__main__":
	db.create_all()
	app.run(debug=True)