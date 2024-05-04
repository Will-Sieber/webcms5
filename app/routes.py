from flask import *
from server import app
from webcms5db import Course, User
from forumdb import Forum

from urllib.parse import urlparse

import subprocess
import requests
import os
import bleach

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
			filepath = "uploads/profiles/images/" + os.path.basename(urlparse(url).path)
			res = requests.get(url, allow_redirects=True)
			if res.status_code != 200:
				return render_template("edit_profile.html", user=user)

			with open(filepath, "wb") as f:
				f.write(res.content)

			User.update_image(sid, os.path.basename(filepath))

		User.update_bio(sid, request.form.get("bio", ""))
		user = User.get_user(sid)
		return render_template("edit_profile.html", user=user, update=True)

	return render_template("edit_profile.html", user=user)

@app.route("/outline")
def outline():
	if session.get("sid") is None:
		return redirect("/login");

	user = User.get_user(session.get("sid"))

	return render_template("outline.html", user=user)

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