# Fills gym.db with 4 weeks of demo data. Run: python3 seed.py
# The schedule follows every business rule, and it ends yesterday, so at the defense:
#   - the streak is 5 days and still alive (today is not logged yet)
#   - logging Gym / Upper Body today triggers the rest-day warning
# Uses: db.py, fitness.py, inputs.py
# Used by: nobody imports it; run it with python3 seed.py
import datetime
import os

import db
import fitness
import inputs

PROFILE = {"name": "Demo", "gender": "male", "age": 24, "height": 175, "weight": 70,
           "weekly_goal": 4, "activities": ["Gym", "Yoga", "Cardio"]}

CUSTOM_EXERCISES = [("Gym", "Upper Body", "Dumbbell Fly")]

# (days ago, activity, focus, exercises, minutes)
SCHEDULE = [
    (27, "Gym", "Upper Body", ["Bench Press", "Pull Up", "Shoulder Press"], 60),
    (26, "Cardio", "Run", ["Easy Run"], 30),
    (25, "Gym", "Lower Body", ["Squat", "Deadlift", "Lunge"], 55),
    (23, "Yoga", "Flexibility", ["Downward Dog", "Forward Fold"], 40),
    (22, "Gym", "Full Body", ["Burpee", "Kettlebell Swing"], 45),
    (20, "Gym", "Upper Body", ["Bench Press", "Barbell Row", "Bicep Curl"], 60),
    (19, "Cardio", "HIIT", ["Jumping Jacks", "Mountain Climbers", "High Knees"], 25),
    (18, "Yoga", "Relax", ["Child's Pose", "Corpse Pose"], 30),
    (16, "Gym", "Lower Body", ["Squat", "Leg Press", "Calf Raise"], 50),
    (13, "Cardio", "Cycle", ["Road Ride"], 70),
    (12, "Gym", "Upper Body", ["Bench Press", "Pull Up", "Dumbbell Fly"], 65),
    (11, "Yoga", "Balance", ["Tree Pose", "Warrior III"], 35),
    (5, "Gym", "Lower Body", ["Squat", "Deadlift"], 55),
    (4, "Cardio", "Run", ["Tempo Run"], 35),
    (3, "Yoga", "Flexibility", ["Pigeon Pose", "Cobra Pose", "Downward Dog"], 40),
    (2, "Gym", "Full Body", ["Thruster", "Burpee"], 45),
    (1, "Gym", "Upper Body", ["Bench Press", "Shoulder Press", "Dumbbell Fly"], 60),
    (1, "Yoga", "Relax", ["Cat-Cow", "Legs Up the Wall"], 20),
]

PLANS = [
    {"name": "Push day", "activity": "Gym", "focus": "Upper Body",
     "exercises": ["Bench Press", "Shoulder Press", "Dumbbell Fly"]},
    {"name": "Leg day", "activity": "Gym", "focus": "Lower Body",
     "exercises": ["Squat", "Lunge", "Leg Press", "Calf Raise"]},
    {"name": "Morning stretch", "activity": "Yoga", "focus": "Flexibility",
     "exercises": ["Downward Dog", "Cobra Pose"]},
]


# Delete gym.db (after asking) and fill a new one with demo data.
# Used by: python3 seed.py (the if __name__ block).
def main():
    if os.path.exists(db.DB_FILE):
        if not inputs.ask_yes_no("gym.db already exists. Delete it and load demo data?"):
            print("Nothing changed.")
            return
        os.remove(db.DB_FILE)

    db.init_db()
    db.save_profile(PROFILE)
    for activity, focus, name in CUSTOM_EXERCISES:
        db.save_exercise(activity, focus, name, 1)

    today = datetime.date.today()
    for days_ago, activity, focus, exercises, minutes in SCHEDULE:
        date = today - datetime.timedelta(days=days_ago)
        log = {"date": date.isoformat(), "activity": activity, "focus": focus,
               "exercises": exercises, "duration": minutes,
               "calories": fitness.estimate_kcal(activity, PROFILE["weight"], minutes)}
        db.save_log(log)

    for plan in PLANS:
        db.save_plan(plan)

    print(f"Loaded {len(SCHEDULE)} workouts and {len(PLANS)} plans for {PROFILE['name']}.")
    print("Now run: python3 main.py")


if __name__ == "__main__":
    main()
