from app import app, db, SensorData, Prediction, Alert
import pandas as pd
from datetime import datetime

csv_file = "rwl_tel_hr_maharashtra_sw_010_2021_2025.csv"
# Read only first 50 rows
df = pd.read_csv(csv_file, nrows=50)

with app.app_context():
    for index, row in df.iterrows():
        try:
            timestamp = datetime.strptime(row['Data Acquisition Time'], "%d-%m-%Y %H:%M")
        except:
            timestamp = datetime.now()

        # Save sensor data
        new_data = SensorData(
            rainfall=0.0,
            river_level=row['River Water Level Telemetry Hourly (meter)'],
            soil_moisture=0.0,
            timestamp=timestamp
        )
        db.session.add(new_data)

        # Generate dummy prediction
        river_level = row['River Water Level Telemetry Hourly (meter)']
        if river_level >= 7:
            risk = "High"
            probability = 0.9
        elif river_level >= 4:
            risk = "Medium"
            probability = 0.6
        else:
            risk = "Low"
            probability = 0.3

        prediction = Prediction(
            flood_risk=risk,
            probability=probability,
            timestamp=timestamp
        )
        db.session.add(prediction)

        # Create alert if risk is Medium or High
        if risk in ["Medium", "High"]:
            alert = Alert(
                message=f"Flood Risk Alert: {risk} at {row['Station']}",
                risk_level=risk,
                timestamp=timestamp
            )
            db.session.add(alert)

        print(f"Row {index} processed")

    db.session.commit()
    print("Inserted sensor, prediction, and alert data for 50 rows successfully")