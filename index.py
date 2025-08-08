import os
import bcrypt
import logging
import datetime
from datetime import date
from bson import ObjectId, errors as bson_errors
from werkzeug.utils import secure_filename
from flask import Flask, request, session, redirect, url_for, render_template, flash
from pymongo import MongoClient
from functools import wraps
from flask import abort
from flask import current_app

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash("Login required", "warning")
            return redirect(url_for('home'))
        try:
            user_obj_id = ObjectId(user_id)
        except bson_errors.InvalidId:
            abort(403)
        user = users_col.find_one({"_id": user_obj_id})
        if not user or user.get("role") != "admin":
            abort(403)  # Forbidden access if not admin
        return f(*args, **kwargs)
    return decorated_function

# Logging setup
logging.basicConfig(level=logging.INFO)

# Flask app setup
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_secret_key")

# MongoDB setup
mongo = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = mongo["mydatabase"]
users_col = db["users"]
proj_col = db["projects"]

# File upload setup
UPLOAD_FOLDER = os.path.join(os.getcwd(), "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 2 MB
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}

def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

# Helper functions
def days_since(d):
    if isinstance(d, str):
        d = datetime.datetime.fromisoformat(d).date()
    elif isinstance(d, datetime.datetime):
        d = d.date()
    return (datetime.date.today() - d).days

def time_left_for_next_day_bangla():
    now = datetime.datetime.now()
    next_day = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    remaining = next_day - now
    total_seconds = int(remaining.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return f"{hours:02} ঘণ্টা {minutes:02} মিনিট {seconds:02} সেকেন্ড"

def feed_level(weight, animal):
    if animal == "goat":
        if weight < 15: return 1
        elif weight < 18: return 2
        elif weight < 21: return 3
        elif weight < 23: return 4
        return 5
    else:  # cow
        if weight < 150: return 1
        elif weight < 280: return 2
        return 3

def Grass(weight, animal):
    if animal == "goat":
        return 2.5
    else:
        if weight < 150:
            return 5
        elif weight < 250:
            return 7.5
        if weight < 400:
            return 12.5
        elif weight < 500:
            return 17.5
        return 17.5

def build_schedule(day, weight, animal):
    day=day # need work
    if animal == "cow":
        return [
            {
                "phase": "সকাল",
                "tasks": [
                    {"description": "গোয়াল ঘর পরিষ্কার করুন, চারি পরিষ্কার করুন, গরুর পা হাঁটু পর্যন্ত ধুয়ে দিন", "time_range": "সকাল ৬ঃ০০ - ৭ঃ০০"},
                    {"description": f"সবুজ ঘাস খাওয়ান ({Grass(weight, animal)} কেজি)", "time_range": "সকাল ৭ঃ০০ - ৮ঃ০০"},
                    {"description": f"দানাদার খাদ্য {feed_level(weight, animal)} কেজি + চিটাগুড় মিশ্রিত পানি খাওয়ান (৫ গ্রাম / ৫ লিটার)", "time_range": "সকাল ৮ঃ০০ - ৯ঃ০০"},
                    {"description": "খড় খাওয়ান (চিটাগুড় মিশ্রিত পানি খড়ের উপর ছিটিয়ে দিন)", "time_range": "সকাল ৯ঃ০০ - ১০ঃ০০"},
                    {"description": "প্রয়োজন অনুযায়ী সবুজ ঘাস প্রদান করুন", "time_range": "সকাল ১০ঃ০০ - ১১ঃ০০"},
                ]
            },
            {
                "phase": "দুপুর",
                "tasks": [
                    {"description": "পানি দিয়ে চারি ধুয়ে দিন, গোয়াল ঘর পরিষ্কার করুন", "time_range": "সকাল ১১ঃ০০ - ১২ঃ০০"},
                    {"description": "গরুকে গোসল করিয়ে দিন (গরমে প্রতিদিন, শীতে ২ দিনে একবার)", "time_range": "দুপুর ১২ঃ০০ - ১ঃ০০"},
                    {"description": "চারিতে পরিষ্কার পানি দিন এবং গরুকে বিশ্রাম নিতে দিন", "time_range": "দুপুর ১ঃ০০ - ৩ঃ০০"},
                ]
            },
            {
                "phase": "বিকাল",
                "tasks": [
                    {"description": f"সবুজ ঘাস খাওয়ান ({Grass(weight, animal)} কেজি)", "time_range": "বিকাল ৩ঃ০০ - ৪ঃ০০"},
                    {"description": f"দানাদার খাদ্য খাওয়ান {feed_level(weight, animal)} কেজি", "time_range": "বিকাল ৪ঃ০০ - ৫ঃ০০"},
                    {"description": "খড় খাওয়ান (চিটাগুড় মিশ্রিত পানি খড়ের উপর ছিটিয়ে দিন)", "time_range": "বিকাল ৫ঃ০০ - ৬ঃ০০"},
                    {"description": "প্রয়োজন অনুযায়ী সবুজ ঘাস প্রদান করুন", "time_range": "বিকাল ৬ঃ০০ - সন্ধ্যা ৬ঃ৪৫"},
                ]
            },
            {
                "phase": "সন্ধ্যা",
                "tasks": [
                    {"description": "গোয়াল ঘর পরিষ্কার করুন, রাতের জন্য কয়েল জ্বালিয়ে দিন, চারি পরিষ্কার করে পানি দিন", "time_range": "সন্ধ্যা ৭ঃ০০ - ৮ঃ০০"}
                ]
            }
        ]

    elif animal == "goat":
        return [
            {
                "phase": "সকাল",
                "tasks": [
                    {"description": "ছাগলের ঘর পরিষ্কার করুন, চারি পরিষ্কার করুন, ছাগলের পা হাঁটু পর্যন্ত ধুয়ে দিন", "time_range": "সকাল ৬ঃ০০ - ৭ঃ০০"},
                    {"description": f"সবুজ ঘাস খাওয়ান {Grass(weight, animal)} কেজি", "time_range": "সকাল ৭ঃ০০ - ৮ঃ০০"},
                    {"description": f"দানাদার খাদ্য {feed_level(weight, animal)} গ্রাম(একটি বাটিতে পরিমাপ করে দিন) + চিটাগুড় মিশ্রিত পানি (৫ গ্রাম / ৫ লিটার)", "time_range": "সকাল ৮ঃ০০ - ৯ঃ০০"},
                    {"description": "খড় খাওয়ান (চিটাগুড় মিশ্রিত পানি খড়ের উপর ছিটিয়ে দিন)", "time_range": "সকাল ৯ঃ০০ - ১০ঃ০০"},
                    {"description": "প্রয়োজন অনুযায়ী সবুজ ঘাস প্রদান করুন", "time_range": "সকাল ১০ঃ০০ - ১১ঃ০০"},
                    {"description": "পানি দিয়ে চারি ধুয়ে দিন, ছাগলের ঘর পরিষ্কার করুন", "time_range": "সকাল ১১ঃ০০ - ১২ঃ০০"},
                ]
            },
            {
                "phase": "দুপুর",
                "tasks": [
                    {"description": "চারিতে পরিষ্কার পানি দিন এবং ছাগলকে বিশ্রাম নিতে দিন", "time_range": "দুপুর ১ঃ০০ - ৩ঃ০০"},
                    {"description": f"সবুজ ঘাস খাওয়ান ({Grass(weight, animal)} কেজি", "time_range": "দুপুর ৩ঃ০০ - ৪ঃ০০"},
                    {"description": f"দানাদার খাদ্য {feed_level(weight, animal)} গ্রাম", "time_range": "বিকাল ৪ঃ০০ - ৫ঃ০০"},
                    {"description": "খড় খাওয়ান (চিটাগুড় মিশ্রিত পানি খড়ের উপর ছিটিয়ে দিন)", "time_range": "বিকাল ৫ঃ০০ - ৬ঃ০০"},
                    {"description": "প্রয়োজন অনুযায়ী সবুজ ঘাস দিন", "time_range": "বিকাল ৬ঃ০০ - সন্ধ্যা ৬ঃ৪৫"},
                ]
            },
            {
                "phase": "বিকাল",
                "tasks": [
                    {"description": "ছাগলের ঘর পরিষ্কার করুন, রাতের জন্য কয়েল জ্বালিয়ে দিন, চারি পরিষ্কার করে পানি দিন", "time_range": "সন্ধ্যা ৭ঃ০০ - ৮ঃ০০"},
                ]
            }
        ]

    else:
        return [
            {
                "phase": "default",
                "tasks": [
                    {"description": f"{animal} এর জন্য সাধারণ কাজ", "time_range": "–"}
                ]
            }
        ]

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form.get('email')
    password = request.form.get('password')
    name = request.form.get('name')
    role = "user"  # Default role, can be changed manually in DB for admin
    if users_col.find_one({'email': email}):
        flash("User already exists", "warning")
        return redirect(url_for('home'))
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    inserted = users_col.insert_one({'email': email, 'password': pw_hash, 'name': name, 'role': role})
    session['email'] = email
    session['user_id'] = str(inserted.inserted_id)
    flash("Signup successful!", "success")
    return redirect(url_for('projects'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    user = users_col.find_one({'email': email})
    if user and bcrypt.checkpw(password.encode(), user['password']):
        session['email'] = email
        session['user_id'] = str(user['_id'])
        flash("Login successful!", "success")
        if user.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('projects'))
    flash("Invalid credentials", "danger")
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out!", "info")
    return redirect(url_for('home'))

@app.route('/profile')
def profile():
    email = session.get('email')
    user = users_col.find_one({'email': email})
    return render_template('profile.html', user=user)

@app.route("/projects")
def projects():
    projs = list(proj_col.find({"owner": session["user_id"]}))
    days_map = {str(p["_id"]): days_since(p["purchase_date"]) for p in projs}
    return render_template("projects.html", projects=projs, days=days_map)

@app.route("/projects/new", methods=["GET", "POST"])
def new_project():
    if request.method == "POST":
        doc = {
            "today": date.today().isoformat(),
            "owner": session["user_id"],
            "name": request.form["name"].strip(),
            "type": request.form["type"],
            "purchase_date": request.form["purchase_date"],
            "weight": float(request.form["weight"]),
            "feed_level": feed_level(float(request.form["weight"]), request.form["type"]),
            "target": 24 if request.form["type"] == "goat" else float(request.form["weight"])+120,
            "check_period": 30 if request.form["type"] == "cow" else 1,
            "task_done": {},
            "task_photo": {},
        }
        proj_col.insert_one(doc)
        flash("Project created!", "success")
        return redirect(url_for("projects"))
    return render_template("new_project.html")

@app.route("/projects/<pid>/dashboard")
def dashboard(pid):
    try:
        proj_id = ObjectId(pid)
    except bson_errors.InvalidId:
        flash("Invalid project ID", "danger")
        return redirect(url_for("projects"))

    proj = proj_col.find_one({"_id": proj_id, "owner": session["user_id"]})
    if not proj:
        flash("Not found!", "danger")
        return redirect(url_for("projects"))

    days = days_since(proj["purchase_date"])
    today = date.today().isoformat()
    now = time_left_for_next_day_bangla()
    period = proj["check_period"]
    show_weight = (days % period == 0 and days != 0) or proj["type"] == "goat"
    days_left = (period - (days % period)) % period

    # Feed level update check
    if days % period == 0 and days != 0 and proj.get("last_check") != days:
        new_level = feed_level(proj["weight"] + (30 if proj["type"] == "cow" else 0), proj["type"])
        proj_col.update_one(
            {"_id": proj["_id"]},
            {"$set": {"feed_level": new_level, "last_check": days}}
        )
        proj = proj_col.find_one({"_id": proj["_id"]})  # Refresh after update

    # --- Daily task_done & task_photo reset logic ---
    # Store last_reset_date in project doc to track when last reset happened
    last_reset_date = proj.get("task_done_reset_date")

    if last_reset_date != today:
        # Reset for new day: clear today's entries and update reset date
        proj_col.update_one(
            {"_id": proj["_id"]},
            {
                "$set": {
                    "task_done": {today: {}},
                    "task_photo": {today: {}},
                    "task_done_reset_date": today
                }
            }
        )
        proj = proj_col.find_one({"_id": proj["_id"]})  # Refresh after reset

    # Ensure keys exist in case no reset triggered (show today's data)
    task_done = proj.get("task_done", {})
    task_photo = proj.get("task_photo", {})
    if today not in task_done:
        task_done[today] = {}
    if today not in task_photo:
        task_photo[today] = {}

    # Inject data to template
    proj["task_done"] = task_done
    proj["task_photo"] = task_photo
    proj["task_done_date"] = today

    schedule = build_schedule(today, proj["weight"], proj["type"])

    return render_template(
        "dashboard.html",
        project=proj,
        schedule=schedule,
        days=days,
        show_weight_input=show_weight,
        days_left=days_left,
        today=today,
        now=now
    )
    
    
    
@app.route("/projects/<pid>/weight", methods=["POST"])
def update_weight(pid):
    try:
        proj_id = ObjectId(pid)
    except bson_errors.InvalidId:
        flash("Invalid project ID", "danger")
        return redirect(url_for("projects"))

    weight = float(request.form["weight"])
    proj = proj_col.find_one({"_id": proj_id, "owner": session["user_id"]})
    if proj:
        proj_col.update_one({"_id": proj_id}, {"$set": {"weight": weight}})
        level = feed_level(weight, proj["type"])
        proj_col.update_one({"_id": proj_id}, {"$set": {"feed_level": level}})
        flash("Weight updated!", "success")
    return redirect(url_for("dashboard", pid=pid))

@app.route("/projects/<pid>/tasks/save", methods=["POST"])
def save_tasks(pid):
    try:
        proj_id = ObjectId(pid)
    except bson_errors.InvalidId:
        flash("Invalid project ID", "danger")
        return redirect(url_for("projects"))

    proj = proj_col.find_one({"_id": proj_id, "owner": session["user_id"]})
    if proj:
        done_indices = request.form.getlist("done")
        done_dict = {str(i): False for i in range(len(build_schedule(days_since(proj["purchase_date"]), proj["weight"], proj["type"])))}
        for idx in done_indices:
            done_dict[idx] = True
        proj_col.update_one({"_id": proj["_id"]}, {"$set": {"task_done": done_dict}})
        flash("Tasks saved!", "success")
    return redirect(url_for("dashboard", pid=pid))

@app.route("/projects/<pid>/photos/upload", methods=["POST"])
def upload_photos(pid):
    try:
        proj_id = ObjectId(pid)
    except bson_errors.InvalidId:
        flash("Invalid project ID", "danger")
        return redirect(url_for("projects"))

    proj = proj_col.find_one({"_id": proj_id, "owner": session["user_id"]})
    task_idx = request.form.get("task_idx")
    files = request.files.getlist("photos")
    if proj and task_idx:
        task_photos = proj.get("task_photo", {}).get(task_idx, [])
        if isinstance(task_photos, str):
            task_photos = [task_photos]
        saved = []
        for file in files:
            if file and allowed(file.filename):
                filename = f"{ObjectId()}_{secure_filename(file.filename)}"
                saved.append(filename)
        task_photos.extend(saved)

        # Update photos
        proj_col.update_one({"_id": proj["_id"]}, {"$set": {f"task_photo.{task_idx}": task_photos}})

        # Mark task as done if any photo uploaded
        if saved:
            task_done = proj.get("task_done", {})
            task_done[task_idx] = True
            proj_col.update_one({"_id": proj["_id"]}, {"$set": {"task_done": task_done}})

        flash(f"Uploaded {len(saved)} photo(s)! Task marked as done.", "success")
    return redirect(url_for("dashboard", pid=pid))

@app.route('/some_form')
def some_form():
    return render_template('new_project.html', today=date.today().isoformat())




# admin======================================================================


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    search_query = request.args.get('search', '').strip().lower()
    users = {str(u['_id']): u for u in users_col.find()}

    if not search_query:
        projects = list(proj_col.find())
    else:
        projects = []
        for proj in proj_col.find():
            owner = users.get(proj.get('owner'))
            owner_name = owner.get('name', '').lower() if owner else ''
            if (search_query in proj.get('name', '').lower() or
                search_query in proj.get('type', '').lower() or
                search_query in owner_name):
                projects.append(proj)

    for proj in projects:
        owner_id = proj.get("owner")
        owner = users.get(owner_id)
        proj["owner_name"] = owner.get("name") if owner else "Unknown"
        proj["owner_email"] = owner.get("email") if owner else "Unknown"

    return render_template('admin_dashboard.html', projects=projects, users=users, search=search_query)

@app.route('/admin/projects/<pid>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_project(pid):
    try:
        proj_id = ObjectId(pid)
    except bson_errors.InvalidId:
        flash("Invalid project ID", "danger")
        return redirect(url_for('admin_dashboard'))

    proj = proj_col.find_one({"_id": proj_id})
    if not proj:
        flash("Project not found", "danger")
        return redirect(url_for('admin_dashboard'))

    if request.method == "POST":
        name = request.form.get("name", proj.get("name")).strip()
        animal_type = request.form.get("type", proj.get("type"))
        purchase_date = request.form.get("purchase_date", proj.get("purchase_date"))
        weight_str = request.form.get("weight", str(proj.get("weight")))
        try:
            weight = float(weight_str)
        except ValueError:
            flash("Weight must be a valid number", "danger")
            return render_template("admin_edit_project.html", project=proj)

        feed_lvl = feed_level(weight, animal_type)

        # Update base project fields
        proj_col.update_one({"_id": proj_id}, {"$set": {
            "name": name,
            "type": animal_type,
            "purchase_date": purchase_date,
            "weight": weight,
            "feed_level": feed_lvl,
        }})

        # Update task_done and remove images if unchecked
        task_done = proj.get("task_done", {})
        task_photo = proj.get("task_photo", {})

        for task_index in task_done.keys():
            field_name = f"task_done_{task_index}"
            done_value = field_name in request.form
            task_done[task_index] = done_value

            if not done_value:
                # Delete all images for this task from disk
                photos_to_remove = task_photo.get(task_index, [])
                for filename in photos_to_remove:
                    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except Exception as e:
                            logging.error(f"Error deleting image {filename}: {e}")
                # Remove photos for this task in DB
                if task_index in task_photo:
                    del task_photo[task_index]

        # Update DB with cleaned task_done and task_photo
        proj_col.update_one({"_id": proj_id}, {"$set": {"task_done": task_done, "task_photo": task_photo}})

        # Handle photo deletions requested explicitly (checkboxes named delete_photo_<task_index>)
        changed = False
        for task_index, photos in task_photo.items():
            if not photos:
                continue
            delete_keys = request.form.getlist(f"delete_photo_{task_index}")
            if delete_keys:
                new_photos = [p for p in photos if p not in delete_keys]
                if len(new_photos) != len(photos):
                    for filename in delete_keys:
                        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                        if os.path.exists(path):
                            try:
                                os.remove(path)
                            except Exception as e:
                                logging.error(f"Failed to delete file {filename}: {e}")
                    task_photo[task_index] = new_photos
                    changed = True
        if changed:
            proj_col.update_one({"_id": proj_id}, {"$set": {"task_photo": task_photo}})

        # Handle new photo uploads per task (input names like photo_<task_index>)
        for key in request.files:
            if not key.startswith("photo_"):
                continue
            task_index = key.split("_", 1)[1]
            files = request.files.getlist(key)
            if not files:
                continue
            current_photos = task_photo.get(task_index, [])
            for file in files:
                if file and allowed(file.filename):
                    filename = f"{ObjectId()}_{secure_filename(file.filename)}"
                    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    file.save(filepath)
                    current_photos.append(filename)
            task_photo[task_index] = current_photos
        # Save updated photos list after uploads
        proj_col.update_one({"_id": proj_id}, {"$set": {"task_photo": task_photo}})

        flash("Project updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template("admin_edit_project.html", project=proj)

@app.route('/admin/projects/<pid>/delete', methods=['POST'])
@admin_required
def admin_delete_project(pid):
    try:
        proj_id = ObjectId(pid)
    except bson_errors.InvalidId:
        flash("Invalid project ID", "danger")
        return redirect(url_for('admin_dashboard'))

    result = proj_col.delete_one({"_id": proj_id})
    if result.deleted_count:
        flash("Project deleted successfully!", "success")
    else:
        flash("Project not found or already deleted", "warning")
    return redirect(url_for('admin_dashboard'))


@app.route("/time-left")
def time_left():
    return time_left_for_next_day_bangla()

if __name__ == '__main__':
    app.run(debug=True)
