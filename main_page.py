from flask import Flask, render_template, Response,request, redirect,url_for
from flask_sqlalchemy import SQLAlchemy
import datetime 
import cv2
import sys
from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField


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
	video_id = StringField()
	submit = SubmitField("Submit")


# ====================== Classes ==================

class Record(db.Model):
	id = db.Column(db.Integer,primary_key = True)
	video_name = db.Column(db.String(200),nullable=False)

	def __init__(self, name, count ):
		x = datetime.datetime.now()
		self.video_name = name+str(count)+'_'+str(x.date())+'_'+x.strftime("%H")+'.'+x.strftime("%M")+'.'+x.strftime("%S")

# ===================== Routes ====================


# Without methods in paramters, buttons cannot send data to index
@app.route('/', methods=["POST","GET"])
def index():
	global current_video, initi
	
	#if "open" in request.form:
		
	
	if initi:
		for i in range(4):
			count = Record.query.count() 
			new_record = Record("Video",count)
			db.session.add(new_record)
		db.session.commit()
		initi = False

	
	form = RecordForm()
	if form.validate_on_submit():
		print(form.video_id, file=sys.stderr)


	records = Record.query.order_by(Record.id.desc()).all()
	#print("Test: ",current_video, file=sys.stderr)
	return render_template('index.html',form = form,video_name = current_video, current_video_id=current_video_id, video_format = video_format,records = records )


@app.route('/delete_video/<video_id>')
def delete_video(video_id):
	global current_video
	video_record = Record.query.get_or_404(video_id)
	current_video = "data:,"
	db.session.delete(video_record)
	db.session.commit()
	return redirect("/")


# Get videoname from button link
@app.route('/play_video/<video_name>,<video_id>')
def play_video(video_name,video_id):
	global current_video, current_video_id
	current_video = video_name
	current_video_id = video_id
	return redirect("/")



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

@app.route('/get_thumbnail/<video_name>')
def get_thumbnail(video_name):
	return Response(gen_thumbnail(video_name), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/liveStream')
def liveStream():
	return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')



if __name__ == "__main__":
	db.create_all()
	app.run(debug=True)