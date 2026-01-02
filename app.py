from flask import Flask,request,jsonify,session,send_from_directory
from flask_cors import CORS
import threading
import secrets

app=Flask(__name__,static_folder="static")
app.secret_key=secrets.token_hex(16)
CORS(app,supports_credentials=True)

USERS={
    "admin":{"password":"admin123","role":"admin"},
    "student1":{"password":"student123","role":"student"},
    "student2":{"password":"student123","role":"student"},
    "student3":{"password":"student123","role":"student"}
}

shared_data={
    "meals":[],
    "ratings":{},
    "student_votes":{}
}

lock=threading.Lock()

@app.route("/")
def index():
    return send_from_directory("static","index.html")

@app.route("/api/login",methods=["POST"])
def login():
    data=request.json
    username=data.get("username")
    password=data.get("password")
    if username in USERS and USERS[username]["password"]==password:
        session["username"]=username
        session["role"]=USERS[username]["role"]
        return jsonify({"success":True,"role":session["role"]})
    return jsonify({"success":False,"message":"Invalid credentials"}),401

@app.route("/api/logout",methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success":True})

@app.route("/api/check-session",methods=["GET"])
def check_session():
    if "username" in session:
        return jsonify({"authenticated":True,"role":session["role"]})
    return jsonify({"authenticated":False}),401

@app.route("/api/meals",methods=["GET"])
def get_meals():
    if "username" not in session:
        return jsonify({"error":"Unauthorized"}),401
    with lock:
        return jsonify({
            "meals":list(shared_data["meals"]),
            "ratings":dict(shared_data["ratings"])
        })

@app.route("/api/meals",methods=["POST"])
def create_meals():
    if "username" not in session or session["role"]!="admin":
        return jsonify({"error":"Unauthorized"}),401

    data=request.json
    meals=data.get("meals",[])

    with lock:
        shared_data["meals"]=meals[:]
        shared_data["ratings"].clear()
        shared_data["student_votes"].clear()

        for meal in meals:
            shared_data["ratings"][meal]={
                "good":0,
                "average":0,
                "poor":0
            }

    return jsonify({"success":True})

@app.route("/api/rate",methods=["POST"])
def rate_meal():
    if "username" not in session or session["role"]!="student":
        return jsonify({"error":"Unauthorized"}),401

    data=request.json
    meal=data.get("meal")
    rating=data.get("rating")
    user=session["username"]

    if rating not in ["good","average","poor"]:
        return jsonify({"error":"Invalid rating"}),400

    with lock:
        if meal not in shared_data["ratings"]:
            return jsonify({"error":"Meal not found"}),404

        if user not in shared_data["student_votes"]:
            shared_data["student_votes"][user]={}

        if shared_data["student_votes"][user].get(meal):
            return jsonify({"error":"Already rated"}),403

        shared_data["ratings"][meal][rating]+=1
        shared_data["student_votes"][user][meal]=True

    return jsonify({"success":True})

@app.route("/api/ratings/live",methods=["GET"])
def live_ratings():
    if "username" not in session:
        return jsonify({"error":"Unauthorized"}),401
    with lock:
        return jsonify({"ratings":dict(shared_data["ratings"])})

if __name__=="__main__":
    app.run(debug=True,port=5000,threaded=True,use_reloader=False)
