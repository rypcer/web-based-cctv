from flask import Flask, render_template, Response,request, redirect,url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
import datetime 
import cv2
import sys
from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField
from wtforms.validators import DataRequired
import os # to delete files

# ====================== Variables ==================

# Create Flask app & Database
app = Flask(__name__,static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recordings.db'
app.config["SQLAlchemy_TRACK_MODIFICATIONS"] = False
app.config['SECRET_KEY'] = "LetsGood"
db = SQLAlchemy(app)



# for ip camera use - rtsp://username:password@ip_address:554/user=username_password='password'_channel=channel_number_stream=0.sdp' 
# for local webcam use cv2.VideoCapture(0)
camera = cv2.VideoCapture('static/vid.mp4')
video_format = 'mp4'
current_video = "data:,";
current_video_id = -1;
initi = False;


class RecordForm(FlaskForm):
	name = StringField(validators=[DataRequired()])
	submit = SubmitField("Submit")


# ====================== Classes ==================

class Record(db.Model):
	id = db.Column(db.Integer,primary_key = True)
	video_name = db.Column(db.String(200),nullable=False)

	def __init__(self, name, count ):
		x = datetime.datetime.now()
		self.video_name = name+str(count)+'_'+str(x.date())+'_'+x.strftime("%H")+'.'+x.strftime("%M")+'.'+x.strftime("%S")


# ===================== Functions ====================


def gen_frames(): 
	while True:
		success, frame = camera.read()  # read the camera frame
		if not success:
			break
		else:
			ret, buffer = cv2.imencode('.jpg', frame)
			frame = buffer.tobytes()
			yield (b'--frame\r\n'
				b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result

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
			count = Record.query.count() 
			new_record = Record("Video",count)
			db.session.add(new_record)
		db.session.commit()
		initi = False

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



if __name__ == "__main__":
	db.create_all()
	app.run(debug=True)