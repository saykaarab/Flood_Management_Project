from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import datetime
import joblib

# -------------------------------
# LOAD MODEL
# -------------------------------
model = joblib.load("models/flood_model_final.pkl")
threshold = joblib.load("models/decision_threshold.pkl")

# -------------------------------
# CREATE APP
# -------------------------------
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:990099@localhost:5432/flood_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------------------
# DATABASE TABLES
# -------------------------------

class SensorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rainfall = db.Column(db.Float)
    river_level = db.Column(db.Float)
    soil_moisture = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now)


class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flood_risk = db.Column(db.String(20))
    probability = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now)


class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(200))
    risk_level = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    location = db.Column(db.String(100))


# -------------------------------
# HOME ROUTE
# -------------------------------
@app.route('/')
def home():
    return "Flood Management Backend Running"


# -------------------------------
# SENSOR + PREDICTION
# -------------------------------
@app.route('/sensor', methods=['POST'])
def add_sensor_data():

    data = request.get_json()

    rainfall = data['rainfall']
    river_level = data['river_level']
    soil_moisture = data['soil_moisture']

    # Save sensor data
    new_data = SensorData(
        rainfall=rainfall,
        river_level=river_level,
        soil_moisture=soil_moisture
    )
    db.session.add(new_data)
    db.session.commit()

    # -------------------------------
    # FEATURE ENGINEERING (CORRECT)
    # -------------------------------
    last_data = SensorData.query.order_by(SensorData.timestamp.desc()).limit(6).all()
    last_data = list(reversed(last_data))  # oldest → newest

    levels = [d.river_level for d in last_data]
    levels.append(river_level)
    
    # rate_of_rise = last - previous
    rate_of_rise = levels[-1] - levels[-2] if len(levels) >= 2 else 0
    
    # level_change_3h = last - 3 steps ago
    level_change_3h = levels[-1] - levels[-4] if len(levels) >= 4 else 0
    
    # rolling_avg_6h = average of last 6 levels
    rolling_avg_6h = sum(levels[-6:]) / min(6, len(levels)) if levels else river_level
    
    features = {
        "water_level": river_level,
        "rate_of_rise": rate_of_rise,
        "level_change_3h": level_change_3h,
        "rolling_avg_6h": rolling_avg_6h
    }
    
    # convert to 2D list for model
    df = [[features["water_level"], features["rate_of_rise"],
           features["level_change_3h"], features["rolling_avg_6h"]]]
    
    prob = model.predict_proba(df)[0][1]
    pred_label = int(prob >= threshold)

    risk = "High" if pred_label == 1 else "Low"

    # Save prediction
    pred_entry = Prediction(
        flood_risk=risk,
        probability=float(prob)
    )
    db.session.add(pred_entry)

    # Create alert if high risk
    if risk == "High":
        alert = Alert(
            message=f"Flood Risk Alert: {risk} at sensor {new_data.id}",
            risk_level=risk
        )
        db.session.add(alert)

    db.session.commit()

    return jsonify({
        "message": "Sensor data stored",
        "flood_risk": risk,
        "probability": float(prob)
    })


# -------------------------------
# GET LAST 5 PREDICTIONS
# -------------------------------
@app.route('/predictions', methods=['GET'])
def get_predictions():

    preds = Prediction.query.order_by(Prediction.timestamp.desc()).limit(5).all()

    result = []
    for p in preds:
        result.append({
            "risk": p.flood_risk,
            "probability": p.probability,
            "time": p.timestamp
        })

    return jsonify(result)


# -------------------------------
# DASHBOARD
# -------------------------------
@app.route('/dashboard')
def dashboard():
    preds = Prediction.query.order_by(Prediction.timestamp.desc()).limit(5).all()
    return render_template("dashboard.html", predictions=preds)


# -------------------------------
# EVACUATION
# -------------------------------
safe_shelters = [
    {"name": "Thane Relief Shelter", "lat": 19.2183, "lon": 72.9781},
    {"name": "Community Hall Shelter", "lat": 19.2050, "lon": 72.9900}
]

@app.route("/evacuation")
def evacuation():

    flood_location = {"lat": 19.2100, "lon": 72.9800}
    shelter = safe_shelters[0]

    return {
        "flood_lat": flood_location["lat"],
        "flood_lon": flood_location["lon"],
        "shelter_lat": shelter["lat"],
        "shelter_lon": shelter["lon"],
        "shelter_name": shelter["name"]
    }


@app.route("/map")
def evacuation_map():
    return render_template("map.html")


# -------------------------------
# REGISTER
# -------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        location = request.form['location']

        user = User(name=name, phone=phone, location=location)

        db.session.add(user)
        db.session.commit()

        return "User Registered Successfully!"

    return render_template('register.html')


# -------------------------------
# LOGIN
# -------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        phone = request.form['phone']

        user = User.query.filter_by(phone=phone).first()

        if user:
            return f"Welcome {user.name}"
        else:
            return "User not found"

    return render_template('login.html')


# -------------------------------
# RUN SERVER
# -------------------------------
if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(debug=True)
