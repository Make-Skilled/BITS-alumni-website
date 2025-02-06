from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId  
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "1234567890"

client = MongoClient("mongodb://127.0.0.1:27017/")
db = client["bits-alumni"]
users = db["users"]
events = db["events"]
gallery = db["gallery"]
jobs = db["jobs"]
news = db["news"]
fundraising = db["fundraising"]
donations = db["donations"]

ADMIN_EMAIL = "admin@bitsalumni.com"
ADMIN_PASSWORD = "admin123"

@app.route("/")
def landing():
    if "user_id" in session:
        user_id = session["user_id"]
        user = users.find_one({"_id": ObjectId(user_id)})
        return render_template("home.html", user=user)
    return render_template("landing.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/loginpage")
def loginpage():
    return render_template("login.html")


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return "Invalid credentials", 401
    return render_template("admin_login.html")


@app.route("/admin-dashboard")
def admin_dashboard():
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    all_events = events.find()
    all_gallery = gallery.find()
    all_funds = fundraising.find()
    all_news = news.find()

    return render_template(
        "admin_dashboard.html", 
        events=all_events, 
        gallery=all_gallery, 
        funds=all_funds, 
        news=all_news
    )

@app.route("/add-event", methods=["GET", "POST"])
def add_event():
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        event_title = request.form.get("event_title")
        event_date = request.form.get("event_date")
        event_description = request.form.get("event_description")
        
        events.insert_one({
            "title": event_title,
            "date": event_date,
            "description": event_description,
            "created_at": datetime.utcnow(),
            "participants": []
        })
        return redirect(url_for("admin_dashboard"))

    return render_template("add_event.html")


@app.route("/add-gallery-image", methods=["GET", "POST"])
def add_gallery_image():
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        file = request.files["image"]
        if file:
            filename = file.filename
            file.save(os.path.join("static/uploads", filename))
            

            gallery.insert_one({
                "image": filename,
                "uploaded_at": datetime.utcnow()
            })
            return redirect(url_for("admin_dashboard"))

    return render_template("add_gallery_image.html")

@app.route("/user-profiles")
def user_profiles():
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))
    
    all_users = users.find()
    return render_template("user_profiles.html", users=all_users)


@app.route("/view-user/<user_id>")
def view_user(user_id):
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))
    
    user = users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return "User not found", 404

    return render_template("view_user_details.html", user=user)




@app.route("/signupdata", methods=["GET", "POST"])
def signup_data():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        roll_number = request.form.get("roll_number")
        password = request.form.get("password")
        
        if users.find_one({"email": email}):
            return "Email already exists", 400
        
        hashed_password = generate_password_hash(password)
        users.insert_one({
            "name": name,
            "email": email,
            "roll_number": roll_number,
            "password": hashed_password,
            "created_at": datetime.utcnow()
        })
        
        return redirect(url_for("loginpage"))
    return render_template("signup.html")

@app.route("/logindata", methods=["GET", "POST"])
def login_data():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        user = users.find_one({"email": email})
        if user and check_password_hash(user["password"], password):
            session["user_id"] = str(user["_id"])
            session["email"] = user["email"]
            return redirect(url_for("landing"))
        else:
            return "Invalid email or password", 401
    return render_template("login.html")


@app.route("/update-profile", methods=["GET", "POST"])
def update_profile():
    if "user_id" not in session:
        return redirect(url_for("loginpage"))

    user_id = session["user_id"]
    user = users.find_one({"_id": ObjectId(user_id)})

    if request.method == "POST":
        updated_data = {
            "name": request.form.get("name"),
            "roll_number": request.form.get("roll_number"),
            "department": request.form.get("department"),
            "graduation_year": request.form.get("graduation_year"),
            "gender": request.form.get("gender"),
            "occupation": request.form.get("occupation"),
            "organisation":request.form.get("organisation"),
            "mobile": request.form.get("mobile"),
            "user_type": request.form.get("user_type")
        }
        users.update_one({"_id": ObjectId(user_id)}, {"$set": updated_data})
        return redirect(url_for("landing"))

    return render_template("update_profile.html", user=user)

@app.route("/events")
def events_page():
    # Fetch all events from MongoDB
    all_events = events.find()
    
    # Convert MongoDB cursor to a list of events
    event_list = []
    for event in all_events:
        event_list.append({
            "title": event["title"],
            "date": event["date"],
            "description": event["description"]
        })

    # Render the events page with event data
    return render_template("events_page.html", events=event_list)


@app.route("/gallery")
def gallery_page():
    # Fetch all images from the MongoDB gallery collection
    all_images = gallery.find()

    # Convert MongoDB cursor to a list of image filenames
    image_list = [img["image"] for img in all_images]

    # Render the gallery page with image data
    return render_template("gallery_page.html", images=image_list)


@app.route("/job-referrals")
def job_referrals():
    all_jobs = jobs.find()
    return render_template("job_referrals.html", jobs=all_jobs)

@app.route("/add-job-referral", methods=["GET", "POST"])
def add_job_referral():
    if "user_id" not in session:
        return redirect(url_for("loginpage"))
    
    user_id = session["user_id"]
    user = users.find_one({"_id": ObjectId(user_id)})
    
    if request.method == "POST":
        job_title = request.form.get("job_title")
        company = request.form.get("company")
        location = request.form.get("location")
        description = request.form.get("description")
        contact_email = request.form.get("contact_email")
        
        jobs.insert_one({
            "job_title": job_title,
            "company": company,
            "location": location,
            "description": description,
            "contact_email": contact_email,
            "uploaded_by": user["name"],
            "created_at": datetime.utcnow()
        })
        return redirect(url_for("job_referrals"))
    
    return render_template("add_job_referral.html")


@app.route("/add-news", methods=["GET", "POST"])
def add_news():
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))
    return render_template("add_news.html")


@app.route("/submit-news", methods=["POST"])
def submit_news():
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    news_data = {
        "title": request.form.get("title"),
        "description": request.form.get("description"),
        "date": request.form.get("date"),
        "created_at": datetime.utcnow()
    }

    news.insert_one(news_data)
    return redirect(url_for("admin_dashboard"))


@app.route("/news")
def view_news():
    all_news = news.find()
    news_list = []
    for item in all_news:
        news_list.append({
            "title": item["title"],
            "description": item["description"],
            "date": item["date"]
        })
    return render_template("news.html", news_list=news_list)

@app.route("/fundraising")
def fundraisingpage():
    return render_template("fundraising.html")

@app.route("/add-fund", methods=["GET", "POST"])
def add_fund():
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        fund_name = request.form.get("fund_name")
        fund_description = request.form.get("fund_description")

        fundraising.insert_one({
            "name": fund_name,
            "description": fund_description,
            "money_collected": 0,  # Initialize at 0
            "created_at": datetime.utcnow()
        })

        return redirect(url_for("admin_dashboard"))

    return render_template("add_fund.html")

@app.route("/get-funds", methods=["GET"])
def get_funds():
    try:
        funds = fundraising.find()
        fund_list = []
        for fund in funds:
            fund_list.append({
                "_id": str(fund["_id"]),
                "name": fund.get("name", "No Name"),
                "description": fund.get("description", "No Description"),
                "money_collected": fund.get("money_collected", 0)
            })
        return jsonify(fund_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/donate", methods=["POST"])
def donate():
    if "user_id" not in session:
        return jsonify({"message": "User not logged in"}), 401

    fund_id = request.form.get("fund_id")
    amount = int(request.form.get("amount"))

    fund = fundraising.find_one({"_id": ObjectId(fund_id)})
    if not fund:
        return jsonify({"message": "Fund not found"}), 404

    # Update the money collected in the fundraising collection
    new_total = fund["money_collected"] + amount
    fundraising.update_one({"_id": ObjectId(fund_id)}, {"$set": {"money_collected": new_total}})

    # Store donation details in the donations collection
    donation_data = {
        "fund_id": fund_id,
        "donor_id": session["user_id"],
        "donor_email": session["email"],
        "amount": amount,
        "timestamp": datetime.utcnow()
    }
    donations.insert_one(donation_data)

    return jsonify({"message": f"Successfully donated ${amount}!", "new_total": new_total})

@app.route("/get-user-details/<user_name>")
def get_user_details(user_name):
    user = users.find_one({"name": user_name}, {"_id": 0, "password": 0})  # Exclude sensitive data
    if user:
        return jsonify(user)
    return jsonify({"error": "User not found"}), 404


@app.route("/alumni-network")
def alumni_network():
    if "user_id" not in session:
        return redirect(url_for("loginpage"))

    all_users = users.find({}, {"_id": 0,"password":0})
    return render_template("alumni_network.html", users=all_users)


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("email", None)
    session.pop("admin_logged_in", None)
    
    return redirect(url_for("landing"))


if __name__ == "__main__":
    app.run(port=3000, debug=True)
