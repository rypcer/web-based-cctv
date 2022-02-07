from flask import Flask, request, jsonify, after_this_request, render_template
import sys
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index2.html')

x = 0
@app.route('/hello', methods=['GET'])
def hello():
    global x
    @after_this_request
    def add_header(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    
    x+=1;    
    return jsonify(x)

if __name__ == '__main__':
    app.run(host='localhost', port=8989)