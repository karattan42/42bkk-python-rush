# First run in the terminal: 5 questions that make the profile.
# Uses: fitness.py, inputs.py, ui.py
# Used by: main.py, menus.py
import fitness
import inputs
import ui

STEPS = 5
GENDERS = {"Male": "male", "Female": "female", "Not specified": "none"}


# Step 1. Each step fills part of the profile and returns a reply (None = go back).
# Used by: run_onboarding.
def step_name(profile):
    name = inputs.ask_text("What should I call you? ")
    profile["name"] = name
    return f"Nice to meet you, {name}!"


# Step 2: gender, used only by the daily calorie formula.
# Used by: run_onboarding.
def step_gender(profile):
    label = inputs.ask_choice("Gender (used for your daily calorie estimate):",
                              list(GENDERS.keys()), True)
    if label is None:
        return None
    profile["gender"] = GENDERS[label]
    return "Got it."


# Step 3: age, height and weight.
# Used by: run_onboarding.
def step_body(profile):
    age = inputs.ask_int("Age (10-100): ", 10, 100, True)
    if age is None:
        return None
    height = inputs.ask_int("Height in cm (100-250): ", 100, 250, True)
    if height is None:
        return None
    weight = inputs.ask_int("Weight in kg (30-250): ", 30, 250, True)
    if weight is None:
        return None
    profile["age"] = age
    profile["height"] = height
    profile["weight"] = weight
    return f"Your body burns about {round(fitness.bmr(profile))} kcal a day at rest."


# Step 4: which activities this user does (shown in the menus later).
# Used by: run_onboarding.
def step_activities(profile):
    activities = inputs.ask_multi("Which activities do you do?",
                                  list(fitness.MET.keys()), True)
    if activities is None:
        return None
    profile["activities"] = activities
    return f"{', '.join(activities)}. Great mix!"


# Step 5: how many days a week to train.
# Used by: run_onboarding.
def step_goal(profile):
    goal = inputs.ask_int("How many days a week do you want to train? (1-7): ", 1, 7, True)
    if goal is None:
        return None
    profile["weekly_goal"] = goal
    return f"{goal} days a week. Let's build that streak!"


# Each step fills part of the profile and returns the mascot's reply,
# or None when the user typed b to go back one step.
# Used by: main.main.
def run_onboarding():
    profile = {"name": "", "gender": "none", "age": 0, "height": 0,
               "weight": 0, "weekly_goal": 1, "activities": []}
    steps = [step_name, step_gender, step_body, step_activities, step_goal]
    step = 0
    reply = None
    while step < STEPS:
        # The screen is cleared each step, so the last reply is shown under the progress bar.
        ui.header("Welcome", f"Step {step + 1} of {STEPS}")
        print("  " + ui.progress(step + 1, STEPS, 30) + ui.paint(f"  {step + 1}/{STEPS}", ui.MUTED))
        print()
        if reply is not None:
            ui.say("happy", reply)
            print()
        if step > 0:
            print("  " + ui.paint("(type b to go back)", ui.MUTED))
        reply = steps[step](profile)
        if reply is None:
            step = step - 1
        else:
            step = step + 1
    ui.success(reply)
    return profile
