# Importing is Case sensitive, * means everthing is imported from doc
# But function vars and classes can be imported seperately aswell by typing their name
from packages.motionDetectionAlgorithm import *
from packages.objectDetectionAlgorithm import *
from flask import (Flask, render_template, Response,request, 
redirect,url_for, flash, send_file, jsonify, after_this_request)
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import sys # Just used for print
import os # to delete files


# ====================== Variables ==================

# Create Flask app 
app = Flask(__name__,static_folder='static')

# DATABASE SETUP
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recordings.db'
app.config["SQLAlchemy_TRACK_MODIFICATIONS"] = False
app.config['SECRET_KEY'] = "LetsGood"
db = SQLAlchemy(app)

# EMAIL SETUP 
# Setup the MAIL_USERNAME_FLASK & MAIL_PASSWORD_FLASK in env vars
# If not setup then live stream will freeze after refresh 
# when a motion is done recording 
email = os.environ.get('MAIL_USERNAME_FLASK');
app.config['MAIL_SERVER'] = 'smtp.gmail.com' 
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = email
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD_FLASK')
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)


# Recorded Output Video 
output_resolution = (854,480)
output_fps = 30
video_format = 'mp4'
fourcc = cv2.VideoWriter_fourcc(*"H264") #.MP4, .AVI = 'XVID' 
is_grayscale = False
recording = False
output_created = False
initFrames = True

# Camera Settings
# for ip camera use - rtsp://username:password@ip_address:554/
# user=username_password='password'_channel=channel_number_stream=0.sdp' 
# Get Video Data from WebCam
#camera = cv2.VideoCapture(0) 

#camera = cv2.VideoCapture('static/testdata/vid.mp4')
live_stream_res = (854,480)
camera_name = "MainCamera"
previous_frame = None
current_frame = None

# Other settings
current_video = "data:,"
current_video_id = -1
rec_stopped_time = None;
time_after_record_ended = 5
timer_started = False
rec_started = False
out = None
output_done = False
send_refresh_status = False
notification_email = "" 
is_notified = True
detect_person = False
detect_car = False


# ====================== Classes ==================

class Record(db.Model):
	id = db.Column(db.Integer,primary_key = True)
	video_name = db.Column(db.String(200),nullable=False)

	def __init__(self, name):
		self.video_name = name

class UserConfig(db.Model):
	id = db.Column(db.Integer,primary_key = True)
	notification_email = db.Column(db.String(200),nullable=False)
	is_grayscale = db.Column(db.Boolean)
	is_notified = db.Column(db.Boolean)
	detect_person = db.Column(db.Boolean)
	detect_car = db.Column(db.Boolean)
	def __init__(self,email):
		self.notification_email = email 

# ===================== Functions ====================


def send_mail(image_data, receiver_email):
	msg = Message("Hello",
		sender=email,
		recipients=[f"<{receiver_email}>"])

	# Inline thats that the position of attachment should be inside the email, 
	# header is used to generate id so we can position where we want the img to be
	# Content-ID is MyImage
	msg.attach("s.jpeg",'image/jpeg',image_data,'inline',headers=[['Content-ID','<Myimage>'],])
	# cid: tells that is should use attachement and MyImage is the content ID
	msg.html = "<h2> Motion Detected </h2> <br> <img src='cid:Myimage' alt='image'/> " 
	mail.send(msg)

def generateOutputVideo(database, camera_name, timestamp):
	global output_created, out
	if output_created == False:
		out = cv2.VideoWriter(f"static/{gen_video_name(camera_name,timestamp)}.{video_format}", fourcc, output_fps, output_resolution,0)
		output_created = True
		# Add to Database
		new_record = Record(gen_video_name(camera_name,timestamp))
		database.session.add(new_record)
		database.session.commit()
		# Send the email
		buffer = cv2.imencode('.jpg', cv2.resize(current_frame.copy(),(854,480)))[1]
		img_frame = buffer.tobytes()
		if is_notified:
			with app.app_context():
				send_mail(img_frame, notification_email)

    # Write resized frame to outputVideo
	out_frame = current_frame.copy()

	drawTimeStamp(out_frame,timestamp)
	if is_grayscale:
		out_frame = cv2.cvtColor(out_frame, cv2.COLOR_BGR2GRAY)
	out_frame = cv2.resize(out_frame, output_resolution)
	out.write(out_frame)


def motion_detection():
	global current_frame, previous_frame, recording, timer_started, rec_stopped_time, send_refresh_status, output_created
	
	previous_frame = current_frame
	camera_working, current_frame = camera.read()
	#current_frame = cv2.resize(current_frame,live_stream_res)
	if not camera_working:
		out.release() # Very important Without release recorded footage wont be saved
		return False 
				
	timestamp = datetime.datetime.now()
	drawTimeStamp(current_frame, timestamp)
	# 7,15 are indices of classes array
	detected = False
	if detect_person and detect_car:
		detected = object_detection(previous_frame,current_frame,(7,15)) 
	elif detect_car:
		detected = object_detection(previous_frame,current_frame,(7,))
	elif detect_person:
		detected = object_detection(previous_frame,current_frame,(15,))
	else:
		contours = detectMotionInFrame(previous_frame, current_frame)
		detected = (0,1)[contours is not None]

	if detected:
		if recording:
			timer_started = False
		else:
			recording = True
			print("START",file=sys.stderr)
		if not detect_person or detect_car:
			for contour in contours:
				drawMotionBox(contour, previous_frame)

	elif recording:
		if timer_started:
			if time.time() - rec_stopped_time >= time_after_record_ended:
				recording = False
				output_created = False
				timer_started = False
				out.release() # Very important Without release recorded footage wont be saved
				print("STOP",file=sys.stderr)
				send_refresh_status = True
		else:
			timer_started = True
			rec_stopped_time = time.time()
	

	if recording: 
		generateOutputVideo(db,camera_name, timestamp)
	return True


def gen_frames(): 
	global output_done, previous_frame, current_frame, initFrames
	if initFrames:	
		previous_frame = camera.read(0)[1]
		current_frame = previous_frame
		initFrames = False
	print("WHILE TRUE***************************************************************************")
	while True:
		
		if not motion_detection():
			break
		# Convert Frame to jpg format and send it
		buffer = cv2.imencode('.jpg', previous_frame)[1]
		img_frame = buffer.tobytes()
		# yield returns value but doesnt exit the function so new frames can be received
		yield (b'--frame\r\n'
			b'Content-Type: image/jpeg\r\n\r\n' + img_frame + b'\r\n') # starts from

# Generating the thumbnail is slow needs improving
def gen_thumbnail(video_name): 
	video = cv2.VideoCapture(f'static/{video_name}.mp4')
	if video.isOpened():
		video.set(2,0.5); # Set Frame to middle
		frame = video.retrieve()[1]  # read the camera frame
		video.release()
		frame = cv2.resize(frame, (52,30))
		buffer = cv2.imencode('.jpg', frame)[1]
		frame = buffer.tobytes()
		yield (b'--frame\r\n'
			b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  
	else:
		video.release()
		yield(b'--frame\r\n')

def checkBoxValue(checkbox):
	return (0,1)[request.form.get(checkbox)=="on"] 


# ===================== Routes ====================

# Without methods in paramters, buttons cannot send data to index
@app.route('/', methods=["POST","GET"])
def index():
	global current_video, initi, send_refresh_status

	send_refresh_status = False
	
	# Get all new records
	records = Record.query.order_by(Record.id.desc()).all()
	#print("Test: ",current_video, file=sys.stderr)
	return render_template('index.html',video_name = current_video, 
		current_video_id=current_video_id, video_format = video_format,records = records,
		notification_email= notification_email, isGrayScale = is_grayscale, isNotified = is_notified,
		detect_person=detect_person, detect_car=detect_car)

@app.route('/download/<video_name>,<video_format>')
def download_video (video_name,video_format):
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


@app.route('/update_config/', methods=['POST'])
def update_config():
	global is_grayscale, notification_email, is_notified, detect_person, detect_car
	
	if request.method == "POST":
		notification_email = request.form["new_email"]
		is_grayscale = checkBoxValue("is_greyscale")
		is_notified = checkBoxValue("is_notified")
		detect_person = checkBoxValue("detect_person")
		detect_car = checkBoxValue("detect_car")
		# Update in Database
		UserCfg = UserConfig.query.get(1)
		UserCfg.notification_email = notification_email
		UserCfg.is_grayscale = is_grayscale
		UserCfg.is_notified = is_notified
		UserCfg.detect_person = detect_person
		UserCfg.detect_car = detect_car
		db.session.commit()
	return redirect('/')


# Get videoname from button link
@app.route('/play_video/<video_name>,<video_id>')
def play_video(video_name,video_id):
	global current_video, current_video_id
	current_video = video_name
	current_video_id = video_id
	return redirect("/")

# A better more safer way of playing video send from directory
@app.route('/playVid/<video_name>')
def vid(video_name):
	path = f"static/{video_name}.{video_format}"
	return send_file(path)


@app.route('/get_thumbnail/<video_name>')
def get_thumbnail(video_name):
	return Response(gen_thumbnail(video_name), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/liveStream')
def liveStream():
	return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/refresh_page', methods=['GET'])
def refresh_page():
    @after_this_request
    def add_header(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response  
    
    return jsonify(send_refresh_status) # Send recording Status to client
	
# ===================== Main ====================

if __name__ == "__main__":
	db.create_all() # Creates all tables for the DB classes
	if db.session.query(UserConfig.notification_email).count() == 0:
		userConfig = UserConfig("")
		db.session.add(userConfig)
		db.session.commit()
	# Initialize the Settings from DB
	UserCfg = UserConfig.query.get(1)
	notification_email = UserCfg.notification_email
	is_grayscale = UserCfg.is_grayscale
	detect_person = UserCfg.detect_person
	detect_car = UserCfg.detect_car
	is_notified = UserCfg.is_notified
	# Init First Frames
	#previous_frame = cv2.resize(camera.read(0)[1],live_stream_res)
	#current_frame = previous_frame
	#camera = cv2.VideoCapture(0) 
	#previous_frame = camera.read(0)[1]
	#current_frame = previous_frame
	app.run(debug=True)
