# MET = how many times harder than sitting still each activity is.
# Calories (MET), BMR and the built-in exercise library.
# Used by: db.py, menus.py, onboarding.py, seed.py, server.py
MET = {"Gym": 5.0, "Yoga": 2.5, "Pilates": 3.0, "Cardio": 7.0}


# kcal = MET x weight (kg) x hours
# Used by: menus.ask_calories, seed.main, server.choose_html, server.aside_html,
# server.save_from_form.
def estimate_kcal(activity, weight, minutes):
    hours = minutes / 60
    return round(MET[activity] * weight * hours)


# Mifflin-St Jeor: calories the body burns per day at rest.
# "none" (not specified) uses the average of the male (+5) and female (-161) versions.
# Used by: menus.menu_profile, onboarding.step_body.
def bmr(profile):
    base = 10 * profile["weight"] + 6.25 * profile["height"] - 5 * profile["age"]
    if profile["gender"] == "male":
        return base + 5
    if profile["gender"] == "female":
        return base - 161
    return base + (5 - 161) / 2


# Built-in exercises: activity -> focus -> list of (group, exercise names).
# The groups only help people find an exercise in a long list; the rules only care
# about activity -> focus -> names (see default_library below).
EXERCISE_GROUPS = {
    "Gym": {
        "Upper Body": [
            ("Chest", ["Bench Press", "Incline Bench Press", "Dumbbell Press", "Push Up",
                       "Chest Fly", "Cable Crossover", "Dips"]),
            ("Back", ["Pull Up", "Chin Up", "Lat Pulldown", "Barbell Row", "Seated Cable Row",
                      "Dumbbell Row", "Face Pull"]),
            ("Shoulders", ["Shoulder Press", "Arnold Press", "Lateral Raise", "Front Raise",
                           "Rear Delt Fly", "Upright Row"]),
            ("Arms", ["Bicep Curl", "Hammer Curl", "Preacher Curl", "Tricep Pushdown",
                      "Skull Crusher", "Overhead Tricep Extension"]),
        ],
        "Lower Body": [
            ("Quads", ["Squat", "Front Squat", "Goblet Squat", "Leg Press", "Lunge",
                       "Bulgarian Split Squat", "Leg Extension"]),
            ("Hamstrings and glutes", ["Deadlift", "Romanian Deadlift", "Hip Thrust", "Leg Curl",
                                       "Glute Bridge", "Good Morning"]),
            ("Calves", ["Calf Raise", "Seated Calf Raise"]),
        ],
        "Full Body": [
            ("Power", ["Clean and Press", "Power Clean", "Thruster", "Kettlebell Swing", "Snatch"]),
            ("Conditioning", ["Burpee", "Battle Ropes", "Sled Push", "Farmer's Carry", "Wall Ball",
                              "Turkish Get Up"]),
        ],
    },
    "Yoga": {
        "Flexibility": [
            ("Standing", ["Downward Dog", "Forward Fold", "Triangle Pose", "Wide-Legged Forward Fold"]),
            ("Floor", ["Pigeon Pose", "Seated Forward Bend", "Butterfly Pose", "Lizard Pose"]),
            ("Backbends", ["Cobra Pose", "Upward Dog", "Camel Pose", "Bridge Pose"]),
        ],
        "Balance": [
            ("Standing", ["Tree Pose", "Warrior III", "Half Moon", "Eagle Pose", "Dancer Pose"]),
            ("Arm balances", ["Crow Pose", "Side Plank", "Firefly Pose"]),
        ],
        "Relax": [
            ("Restorative", ["Child's Pose", "Corpse Pose", "Legs Up the Wall", "Reclined Butterfly",
                             "Happy Baby"]),
            ("Gentle", ["Cat-Cow", "Supine Twist", "Sphinx Pose"]),
        ],
    },
    "Pilates": {
        "Core": [
            ("Abs", ["The Hundred", "Roll Up", "Criss Cross", "Double Leg Stretch", "Toe Taps"]),
            ("Stability", ["Plank", "Side Plank", "Dead Bug", "Leg Pull Front"]),
        ],
        "Mat": [
            ("Classical", ["Single Leg Stretch", "Swan", "Saw", "Teaser", "Rolling Like a Ball",
                           "Open Leg Rocker", "Corkscrew"]),
            ("Hips and legs", ["Leg Circles", "Clam", "Side Leg Lift"]),
        ],
        "Posture": [
            ("Spine", ["Spine Stretch", "Spine Twist", "Cat Stretch"]),
            ("Back and hips", ["Swimming", "Shoulder Bridge", "Side Kick", "Swan Dive"]),
        ],
    },
    "Cardio": {
        "Run": [("", ["Easy Run", "Tempo Run", "Interval Run", "Long Run", "Hill Repeats",
                      "Sprints", "Treadmill Run", "Trail Run"])],
        "Cycle": [("", ["Road Ride", "Indoor Bike", "Hill Climb", "Spin Class", "Mountain Bike",
                        "Commute Ride"])],
        "HIIT": [("", ["Jumping Jacks", "Mountain Climbers", "High Knees", "Jump Squat",
                       "Box Jump", "Jump Rope", "Skater Jumps", "Tuck Jumps", "Plank Jacks"])],
    },
}


# activity -> focus -> list of exercise names (the groups flattened).
# A function (not a constant) so every call returns a fresh copy we can add to.
# Used by: db.init_db.
def default_library():
    library = {}
    for activity in EXERCISE_GROUPS:
        library[activity] = {}
        for focus in EXERCISE_GROUPS[activity]:
            names = []
            for group, group_names in EXERCISE_GROUPS[activity][focus]:
                for name in group_names:
                    names.append(name)
            library[activity][focus] = names
    return library


# The exercises in library[activity][focus] sorted into their groups, as a list of
# (group, names). Exercises a person added themselves go into "Your own" at the end.
# Used by: menus.pick_exercises, server.exercise_picker.
def grouped_exercises(library, activity, focus):
    available = library[activity][focus]
    groups = []
    placed = []
    if activity in EXERCISE_GROUPS and focus in EXERCISE_GROUPS[activity]:
        for group, group_names in EXERCISE_GROUPS[activity][focus]:
            names = []
            for name in group_names:
                if name in available:
                    names.append(name)
                    placed.append(name)
            if len(names) > 0:
                groups.append((group, names))
    own = []
    for name in available:
        if name not in placed:
            own.append(name)
    if len(own) > 0:
        groups.append(("Your own", own))
    return groups
