from flask import request, jsonify
from app import app, db, User

@app.route("/add_user", methods=["POST"])
def add_user():
    data = request.get_json()
    name = data.get("name")
    phone = data.get("phone")
    location = data.get("location")

    if not name or not phone or not location:
        return jsonify({"error": "Missing fields"}), 400

    # Check if user already exists (optional)
    existing_user = User.query.filter_by(phone=phone).first()
    if existing_user:
        return jsonify({"message": "User already exists", "id": existing_user.id})

    user = User(name=name, phone=phone, location=location)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User added successfully", "id": user.id})