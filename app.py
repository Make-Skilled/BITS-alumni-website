from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId  
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from flask_socketio import SocketIO, emit, join_room

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
chats = db["chats"]
chat_messages = db["chat_messages"]

ADMIN_CREDENTIALS = {
    "cse_admin@bitsalumni.com": {
        "password": "cse_admin123",
        "department": "CSE",
        "name": "CSE Administrator"
    },
    "ece_admin@bitsalumni.com": {
        "password": "ece_admin123",
        "department": "ECE",
        "name": "ECE Administrator"
    },
    "eee_admin@bitsalumni.com": {
        "password": "eee_admin123",
        "department": "EEE",
        "name": "EEE Administrator"
    },
    "civil_admin@bitsalumni.com": {
        "password": "civil_admin123",
        "department": "CIVIL",
        "name": "Civil Administrator"
    },
    "mech_admin@bitsalumni.com": {
        "password": "mech_admin123",
        "department": "MECH",
        "name": "Mechanical Administrator"
    }
}

# Initialize SocketIO
socketio = SocketIO(app)

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
        
        if email in ADMIN_CREDENTIALS and password == ADMIN_CREDENTIALS[email]["password"]:
            session["admin_logged_in"] = True
            session["admin_department"] = ADMIN_CREDENTIALS[email]["department"]
            session["admin_name"] = ADMIN_CREDENTIALS[email]["name"]
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
        news=all_news,
        admin_name=session.get("admin_name"),
        admin_department=session.get("admin_department")
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

@app.route("/view-attendees/<event_id>")
def view_attendees(event_id):
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    event = events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return "Event not found", 404

    attendees = event.get("participants", [])  # List of emails

    return render_template("view_attendees.html", event=event, attendees=attendees)



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


@app.route("/pending-registrations")
def pending_registrations():
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))
    
    # Find all users with status=False (pending approval)
    pending_users = users.find({"status": False})
    return render_template("pending_registrations.html", users=pending_users)

@app.route("/approve-user/<user_id>")
def approve_user(user_id):
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))
    
    users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"status": True}}
    )
    return redirect(url_for("pending_registrations"))

@app.route("/reject-user/<user_id>")
def reject_user(user_id):
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))
    
    users.delete_one({"_id": ObjectId(user_id)})
    return redirect(url_for("pending_registrations"))


@app.route("/signupdata", methods=["GET", "POST"])
def signup_data():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        roll_number = request.form.get("roll_number")
        password = request.form.get("password")
        
        if users.find_one({"email": email}):
            return "Email already exists", 400
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        users.insert_one({
            "name": name,
            "email": email,
            "roll_number": roll_number,
            "password": hashed_password,
            "created_at": datetime.utcnow(),
            "status": False  # Added status field
        })
        
        return render_template("registration_pending.html")
    return render_template("signup.html")

@app.route("/logindata", methods=["GET", "POST"])
def login_data():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        user = users.find_one({"email": email})
        if user and check_password_hash(user["password"], password):
            if not user.get("status", False):
                return "Your account is pending approval", 401
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
    all_events = events.find()
    
    event_list = []
    for event in all_events:
        event_list.append({
            "_id": str(event["_id"]),  # Convert ObjectId to string
            "title": event["title"],
            "date": event["date"],
            "description": event["description"]
        })

    return render_template("events_page.html", events=event_list)


@app.route("/api/join-event/<event_id>", methods=["POST"])
def join_event(event_id):
    print(f"Received request to join event: {event_id}")  # Debugging
    if "user_id" not in session:
        return jsonify({"message": "User not logged in"}), 401

    user_email = session.get("email")
    event = events.find_one({"_id": ObjectId(event_id)})
    
    if not event:
        return jsonify({"message": "Event not found"}), 404

    if user_email in event.get("participants", []):
        return jsonify({"message": "User already joined this event"}), 400

    events.update_one(
        {"_id": ObjectId(event_id)},
        {"$push": {"participants": user_email}}
    )

    return jsonify({"message": "Successfully joined event!"})



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

    current_user_id = ObjectId(session["user_id"])
    
    # Find all users except the current user
    # Fix: Use either all inclusion or all exclusion in projection
    all_users = users.find(
        {"_id": {"$ne": current_user_id}},
        {
            "_id": 1,  # Include _id
            "name": 1,
            "email": 1,
            "department": 1,
            "graduation_year": 1,
            "occupation": 1,
            "organisation": 1,
            "mobile": 1
        }
    )
    
    return render_template("alumni_network.html", users=all_users)


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("email", None)
    session.pop("admin_logged_in", None)
    
    return redirect(url_for("landing"))


@app.route("/chat/<receiver_id>")
def chat(receiver_id):
    if "user_id" not in session:
        return redirect(url_for("loginpage"))
    
    try:
        current_user_id = session["user_id"]
        receiver = users.find_one({"_id": ObjectId(receiver_id)})
        
        if not receiver:
            return "User not found", 404
        
        # Mark all messages from this sender as read
        chat_messages.update_many(
            {
                "sender_id": receiver_id,
                "receiver_id": current_user_id,
                "read": False
            },
            {"$set": {"read": True}}
        )
        
        # Emit event to update unread count
        socketio.emit('messages_read', {}, room=current_user_id)
        
        # Get chat history
        chat_history = chat_messages.find({
            "$or": [
                {"sender_id": current_user_id, "receiver_id": receiver_id},
                {"sender_id": receiver_id, "receiver_id": current_user_id}
            ]
        }).sort("timestamp", 1)
        
        return render_template(
            "chat.html",
            receiver=receiver,
            current_user_id=current_user_id,
            chat_history=chat_history
        )
    except Exception as e:
        print(f"Chat error: {str(e)}")
        return "Error loading chat", 500

@app.route("/chats")
def chats():
    if "user_id" not in session:
        return redirect(url_for("loginpage"))
    
    current_user_id = session["user_id"]
    
    # Get all unique conversations for the current user
    pipeline = [
        {
            "$match": {
                "$or": [
                    {"sender_id": current_user_id},
                    {"receiver_id": current_user_id}
                ]
            }
        },
        {
            "$sort": {"timestamp": -1}
        },
        {
            "$group": {
                "_id": {
                    "$cond": [
                        {"$eq": ["$sender_id", current_user_id]},
                        "$receiver_id",
                        "$sender_id"
                    ]
                },
                "last_message": {"$first": "$content"},
                "timestamp": {"$first": "$timestamp"},
                "unread_count": {
                    "$sum": {
                        "$cond": [
                            {
                                "$and": [
                                    {"$eq": ["$receiver_id", current_user_id]},
                                    {"$eq": ["$read", False]}
                                ]
                            },
                            1,
                            0
                        ]
                    }
                }
            }
        }
    ]
    
    chat_list = []
    for chat in chat_messages.aggregate(pipeline):
        other_user_id = chat["_id"]
        other_user = users.find_one({"_id": ObjectId(other_user_id)})
        if other_user:
            chat_list.append({
                "user": other_user,
                "last_message": chat["last_message"],
                "timestamp": chat["timestamp"],
                "unread_count": chat["unread_count"]
            })
    
    return render_template(
        "chats.html",
        chats=chat_list,
        current_user_id=current_user_id
    )

@app.route("/get-unread-count")
def get_unread_count():
    if "user_id" not in session:
        return jsonify({"count": 0})
    
    current_user_id = session["user_id"]
    unread_count = chat_messages.count_documents({
        "receiver_id": current_user_id,
        "read": False
    })
    
    return jsonify({"count": unread_count})

@app.route("/get-chat-list")
def get_chat_list():
    if "user_id" not in session:
        return jsonify({"chats": []})
    
    current_user_id = session["user_id"]
    
    pipeline = [
        {
            "$match": {
                "$or": [
                    {"sender_id": current_user_id},
                    {"receiver_id": current_user_id}
                ]
            }
        },
        {
            "$sort": {"timestamp": -1}
        },
        {
            "$group": {
                "_id": {
                    "$cond": [
                        {"$eq": ["$sender_id", current_user_id]},
                        "$receiver_id",
                        "$sender_id"
                    ]
                },
                "unread_count": {
                    "$sum": {
                        "$cond": [
                            {
                                "$and": [
                                    {"$eq": ["$receiver_id", current_user_id]},
                                    {"$eq": ["$read", False]}
                                ]
                            },
                            1,
                            0
                        ]
                    }
                }
            }
        }
    ]
    
    chat_list = []
    for chat in chat_messages.aggregate(pipeline):
        chat_list.append({
            "user_id": str(chat["_id"]),
            "unread_count": chat["unread_count"]
        })
    
    return jsonify({"chats": chat_list})

# WebSocket event handlers
@socketio.on('join')
def on_join(data):
    user_id = data['user_id']
    join_room(user_id)

@socketio.on('message')
def handle_message(data):
    if "user_id" not in session:
        return
    
    try:
        sender_id = session["user_id"]
        receiver_id = data['receiver_id']
        content = data['content']
        timestamp = datetime.utcnow()
        
        # Save message to database with read status
        message = {
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "content": content,
            "timestamp": timestamp,
            "read": False  # Add read status
        }
        chat_messages.insert_one(message)
        
        # Emit to both sender and receiver
        message_data = {
            "sender_id": sender_id,
            "content": content,
            "timestamp": timestamp.strftime('%H:%M')
        }
        
        emit('message', message_data, room=sender_id)
        emit('message', message_data, room=receiver_id)
        emit('new_message', {}, room=receiver_id)  # Notify receiver about new message
    except Exception as e:
        print(f"Message handling error: {str(e)}")

if __name__ == '__main__':
    socketio.run(app, debug=True)
