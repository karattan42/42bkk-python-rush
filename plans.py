import db
import inputs
import menus
import rules
import stats
import ui


def print_plans(plans):
    for i in range(len(plans)):
        plan = plans[i]
        what = ui.paint(plan["activity"] + " / " + plan["focus"], ui.activity_rgb(plan["activity"]))
        print(ui.option(i + 1, ui.paint(plan["name"], None, True) + " (" + what + ")"))
        print("       " + ui.paint(", ".join(plan["exercises"]), ui.MUTED))


# Returns the chosen plan, or None when there are no plans yet.
def choose_plan(state):
    plans = state["plans"]
    if len(plans) == 0:
        ui.error("No plans yet. Create one first.")
        return None
    print_plans(plans)
    number = inputs.ask_int("Which plan? ", 1, len(plans))
    return plans[number - 1]


def menu_plans(state):
    while True:
        ui.title("My plans")
        if len(state["plans"]) == 0:
            ui.say("happy", "No plans yet. Create one, or let me pick a random one.")
        else:
            print_plans(state["plans"])
        choice = inputs.ask_choice("Choose:", ["Create plan", "Random plan", "Edit plan",
                                               "Start plan", "Delete plan", "Back"])
        if choice == "Create plan":
            create_plan(state)
        elif choice == "Random plan":
            random_plan(state)
        elif choice == "Back":
            return
        else:
            plan = choose_plan(state)
            if plan is None:
                continue
            if choice == "Edit plan":
                edit_plan(state, plan)
            elif choice == "Start plan":
                start_plan(state, plan)
                return
            else:
                delete_plan(state, plan)


def save_new_plan(state, name, activity, focus, exercises):
    plan = {"name": name, "activity": activity, "focus": focus, "exercises": exercises}
    db.save_plan(plan, state["user_id"])
    state["plans"].append(plan)
    ui.success(f"Saved plan '{name}'.")


def create_plan(state):
    library = state["library"]
    name = inputs.ask_text("Plan name: ")
    activity = inputs.ask_choice("Activity:", state["profile"]["activities"])
    focus = inputs.ask_choice("Focus:", list(library[activity].keys()))
    exercises = menus.pick_exercises(library, activity, focus, True)
    save_new_plan(state, name, activity, focus, exercises)


def random_plan(state):
    library = state["library"]
    activity = inputs.ask_choice("Activity:", state["profile"]["activities"])
    focus = inputs.ask_choice("Focus:", list(library[activity].keys()))
    most = len(library[activity][focus])
    if most > 10:
        most = 10
    count = inputs.ask_int(f"How many exercises? (1-{most}): ", 1, most)
    while True:
        exercises = stats.random_workout(library, activity, focus, count)
        print()
        for line in ui.card(f"Random {activity} / {focus}", exercises, ui.activity_rgb(activity)):
            print("  " + line)
        choice = inputs.ask_choice("Like it?", ["Save as plan", "Start now", "Shuffle again",
                                                "Cancel"])
        if choice == "Save as plan":
            name = inputs.ask_text("Plan name: ")
            save_new_plan(state, name, activity, focus, exercises)
            return
        if choice == "Start now":
            plan = {"name": "Random workout", "activity": activity, "focus": focus,
                    "exercises": exercises}
            start_plan(state, plan)
            return
        if choice == "Cancel":
            return


# Exercises in the plan's focus that are not in the plan yet.
def unused_exercises(state, plan):
    unused = []
    for name in state["library"][plan["activity"]][plan["focus"]]:
        if name not in plan["exercises"]:
            unused.append(name)
    return unused


def edit_plan(state, plan):
    while True:
        print()
        for line in ui.card(plan["name"], plan["exercises"], ui.activity_rgb(plan["activity"])):
            print("  " + line)
        choice = inputs.ask_choice("Edit:", ["Add exercise", "Remove exercise",
                                             "Swap exercise", "Rename", "Back"])
        if choice == "Back":
            return
        new_exercises = list(plan["exercises"])
        if choice == "Rename":
            plan["name"] = inputs.ask_text("New name: ")
        elif choice == "Remove exercise":
            name = inputs.ask_choice("Remove which?", plan["exercises"])
            new_exercises.remove(name)
        else:
            unused = unused_exercises(state, plan)
            if len(unused) == 0:
                ui.error(f"Every {plan['focus']} exercise is already in this plan.")
                continue
            if choice == "Add exercise":
                new_exercises.append(inputs.ask_choice("Add which?", unused))
            else:
                old = inputs.ask_choice("Swap out which?", plan["exercises"])
                new = inputs.ask_choice(f"Swap {old} for?", unused)
                new_exercises[new_exercises.index(old)] = new
        ok, message = rules.valid_plan(new_exercises)
        if not ok:
            ui.error(message)
            continue
        plan["exercises"] = new_exercises
        db.update_plan(plan)
        ui.success("Plan updated.")


def start_plan(state, plan):
    ui.header("My plans", plan["name"])
    lines = []
    for name in plan["exercises"]:
        lines.append(ui.paint("○ ", ui.activity_rgb(plan["activity"])) + name)
    for line in ui.card(f"{plan['activity']} / {plan['focus']}", lines, ui.activity_rgb(plan["activity"])):
        print("  " + line)
    print()
    input(inputs.indent(ui.paint("Do these exercises, then press Enter to log the workout...", ui.MUTED)))
    menus.menu_log(state, plan)


def delete_plan(state, plan):
    if inputs.ask_yes_no(f"Delete plan '{plan['name']}'?"):
        db.delete_plan(plan["id"])
        state["plans"].remove(plan)
        ui.success("Deleted.")
    else:
        print("  " + ui.paint("Kept.", ui.MUTED))
