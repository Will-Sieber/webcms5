from flask import *
from server import app
from webcms5db import Course, User
from forumdb import Forum

from urllib.parse import urlparse

import subprocess
import requests
import os
import bleach
import re
import xml.etree.ElementTree as ET

@app.route("/")
def index():
	if session.get("sid") is None:
		return redirect("/login");

	user = User.get_user(session.get("sid"))

	return render_template("index.html", user=user)

@app.route("/login", methods=["GET", "POST"])
def login():
	if request.method == "POST":
		if User.check_creds(request.form.get("sid"), request.form.get("password")):
			session["sid"] = request.form.get("sid")
			return redirect("/")
		else:
			return render_template("login.html", error="Invalid credentials")

	return render_template("login.html")

@app.route("/logout")
def logout():
	session.pop("sid")
	return redirect("/login")

@app.route("/courses", methods=["GET", "POST"])
def courses():
	if session.get("sid") is None:
		return redirect("/login");

	user = User.get_user(session.get("sid"))
	courses = ""

	search = request.form.get("search", "")
	if search != "":
		courses = Course.get_query(search)

	return render_template("courses.html", search=search, courses=courses, user=user)

@app.route("/profile/<sid>")
def profile(sid):
	if session.get("sid") is None:
		return redirect("/login");

	user = User.get_user(session.get("sid"))

	prof = User.get_user(sid)
	if prof is None:
		abort(404)

	return render_template_string(render_template("profile.html", user=user, 
			name=prof[1], image=prof[2], bio=prof[3], edit=user[0]==prof[0]))

@app.route("/profile/<sid>/edit", methods=["GET", "POST"])
def edit_profile(sid):
	if session.get("sid") is None:
		return redirect("/login");

	user = User.get_user(session.get("sid"))

	if sid != user[0]:
		abort(403)
	
	if request.method == "POST":
		url = request.form.get("url", "").strip()
		if url:
			parsed_url = urlparse(url)
			if parsed_url.scheme not in ['http', 'https']:
				return render_template("edit_profile.html", user=user, error="Invalid URL")

			filename = os.path.basename(parsed_url.path)
			filepath = os.path.join("uploads", "profiles", "images", filename)

			try:
				res = requests.get(url, allow_redirects=True)
				res.raise_for_status()
			except requests.exceptions.RequestException as e:
				return render_template("edit_profile.html", user=user, error=e)

			try:
				with open(filepath, "wb") as f:
					f.write(res.content)
			except OSError as e:
				return render_template("edit_profile.html", user=user, error="Failed to save file")

			User.update_image(sid, filename)

		bio = request.form.get("bio", "").strip()
		if bio:
			bio = re.sub(r'<\s*\/?\s*(script|img|svg)\s*\/?\s*>', '', bio)
			User.update_bio(sid, bio)

		user = User.get_user(sid)
		return render_template("edit_profile.html", user=user, update=True)

	return render_template("edit_profile.html", user=user)

@app.route("/outline")
def outline():
	if session.get("sid") is None:
		return redirect("/login");

	user = User.get_user(session.get("sid"))

	return render_template("outline.html", user=user)

@app.route("/exam-info")
def exam_info():
	if session.get("sid") is None:
		return redirect("/login");

	user = User.get_user(session.get("sid"))

	return render_template("exam-info.html", user=user)

@app.route("/previous-exam", methods=["GET", "POST"])
def handle_previous_exam():
	if session.get("sid") is None:
		return redirect("/login")

	user = User.get_user(session.get("sid"))
	if user[0] == "admin":
		if request.method == "GET":
			return render_template("previous-exam.html", user=user)
		elif request.method == "POST":
			if 'file' not in request.files:
				return redirect(request.url)

			file = request.files['file']
			if file.filename == '':
				return redirect(request.url)

			if file and file.filename.endswith('.xml'):
				filename = os.path.join("uploads", file.filename)
				file.save(filename)
				exam_data = parse_exam_xml(filename)
				res = "Uploaded file: " + file.filename
			else:
				res = "Failed to upload file: " + file.filename

			return render_template("previous-exam.html", exam_data=exam_data, res=res, user=user)
	else:
		abort(403)

def parse_exam_xml(filename):
    try:
        tree = ET.parse(filename)
        root = tree.getroot()

        data = []
        for element in root.findall('.//*'):
            element_data = {
                'tag': element.tag,
                'text': element.text.strip() if element.text else '',
                'attributes': element.attrib,
                'children': [child.tag for child in element.findall('*')]
            }
            data.append(element_data)

        return data

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return None

@app.route("/forum",  methods=["GET", "POST"])
def forum():
	if session.get("sid") is None:
		return redirect('/login')
	
	user = User.get_user(session.get("sid"))  

	if request.method == "POST":
		message = request.form.get("message")
		message = sanitise_input(message)
		Forum.add_thread(request.form.get('title'), user[1], message)
	
	threads = Forum.get_all_threads()
	return render_template('forum.html', user=user, threads=threads)

@app.route("/forum/<int:thread_id>",  methods=["GET", "POST", "DELETE"])
def forum_thread(thread_id):
	if session.get("sid") is None:
		return redirect('/login')
	user = User.get_user(session.get("sid"))

	if request.method == "DELETE":
		Forum.delete_thread(thread_id)
		threads = Forum.get_all_threads()

	messages = []
	thread_title = ""
	
	if request.method == "POST":
		message = request.form.get('message')
		message = sanitise_input(message)
		Forum.add_message(thread_id, user[1], message)
	
	threads = Forum.get_all_threads()
	if thread_id in [thread[0] for thread in threads]:
		messages = Forum.get_messages(thread_id)
		thread_title = Forum.get_thread_title(thread_id)[1]
		
	return render_template('forum.html', user=user, threads=threads, messages=messages, thread_title=thread_title, thread_id=thread_id)

@app.route("/forum/new-thread")
def new_thread():
	if session.get("sid") is None:
		return redirect('/login')

	return render_template('new-thread.html')

@app.route("/timetable")
def timetable():
	if session.get("sid") is None:
		return redirect('/login')
	
	user = User.get_user(session.get("sid"))

	return render_template('timetable.html', user=user)

@app.route("/getimage")
def getimage():
	print(os.getcwd())
	return send_file(os.getcwd() + "/uploads/profiles/images/" +
			request.args.get("image"))
	#return send_file(os.path.join(os.getcwd() + "/", "uploads/profiles/images/", 
	#		request.args.get("image")))

@app.route("/assignments", methods=["GET", "POST"])
def assignments():
	if session.get("sid") is None:
		return redirect("/login");

	user = User.get_user(session.get("sid"))

	if request.method == "POST":
		assign = request.form.get("assignment", "")
		try:
			output = subprocess.check_output(["bash", "-c", "./checksubmission.sh " + assign]).decode()
		except subprocess.CalledProcessError as e:
			output = f"Error: {e}"
		except Exception as e:
			output = f"Unexpected error: {e}"

		return render_template("assignments.html", user=user, assignment=assign, output=output)

	return render_template("assignments.html", user=user, assignment="assignment1")
	
def sanitise_input(input):
	allowed_tags = ['a', 'b', 'i', 'u', 'p', 'br', 'div', 'span', 'img']
	allowed_attrs = {
		'*': ['style'],
		'a': ['href', 'title'],
		'div': ['class'],
		'span': ['class'],
		'img': ['srcset']
	}
	sanitised_input = bleach.clean(input, tags=allowed_tags, attributes=allowed_attrs, strip=True)
	return sanitised_input