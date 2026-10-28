# Streakr — Rush00 Design Doc

> **For Claude Code:** This is the design spec for a 42 Bangkok Discovery Piscine Rush00 project.
> Build in the phase order at the bottom. Hard constraints:
> - Python **standard library only** (no pip packages: no `rich`, `textual`, `PyQt`).
> - Main menu must use `input()` / `print()` and run in a terminal.
> - Turn-in files: `*.py`, `README.md`, `auteur` only (no separate `.html` / `.css`).
> - Keep code plain and readable: functions, no classes, no clever one-liners — both teammates must explain every line at the defense.
> - All data processing (sum, count, sort, search, streak) must be written in Python loops. SQL is only `SELECT *`, `INSERT`, `UPDATE`, `DELETE`.

## Overview

Streakr คือแอปบันทึกการออกกำลังกายแบบ TUI ที่รันใน terminal ด้วย Python standard library ล้วน รองรับ Gym, Yoga, Pilates และ Cardio และต้องผ่าน requirement ของ Rush00 ครบทั้ง 8 ข้อก่อนเพิ่มฟีเจอร์อื่น

**ปัญหาที่แก้:** ลืมบันทึกการเล่น, ไม่รู้ว่าวันนี้จะเล่นท่าไหน, และไม่เห็นภาพรวมความสม่ำเสมอของตัวเอง

**ข้อจำกัดจากโจทย์**

- ใช้ได้แค่ built-in และ standard library ดังนั้นไม่มี `rich`, `textual` หรือ `PyQt`
- เมนูหลักต้องใช้ `input()` และ `print()` ส่วน GUI หรือ web เป็นแค่ส่วนเสริม
- ไฟล์ที่ส่งได้คือ `*.py`, `README.md` และ `auteur` เท่านั้น
- ทั้งสองคนในทีมต้องอธิบายโค้ดได้ทุกบรรทัด

## Features & menus

รันครั้งแรกจะเข้าหน้า onboarding ก่อน จากนั้นทุกครั้งจะเข้าเมนูหลักที่มี 5 เมนู + Exit

### Onboarding (เฉพาะครั้งแรก เมื่อยังไม่มี profile ใน DB)

| Step | ถาม | ใช้ทำอะไร |
| --- | --- | --- |
| 1 | ชื่อ | ทักทายใน header |
| 2 | เพศ (ชาย / หญิง / ไม่ระบุ) | สูตร BMR ต่างกันระหว่างชายกับหญิง ถ้าไม่ระบุจะใช้ค่าเฉลี่ยของสองสูตร |
| 3 | อายุ, ส่วนสูง (cm), น้ำหนัก (kg) | น้ำหนักใช้คำนวณ kcal และทั้งสามค่าใช้คำนวณ BMR |
| 4 | กิจกรรมที่เล่น (เลือกได้หลายข้อ) | เมนูแสดงเฉพาะกิจกรรมที่เลือก |
| 5 | เป้าหมายกี่วันต่อสัปดาห์ | progress bar ในหน้า stats |

ทุก step มี progress bar กดย้อนกลับได้ด้วย `b` และ mascot จะตอบรับหลังกรอกแต่ละข้อ

### เมนูหลัก

1. **Log workout:** เลือก activity → focus → ท่า แล้วกรอก duration ระบบประเมิน kcal ให้ และผู้ใช้แก้ค่าเองได้
2. **My plans:** สร้าง plan เอง, สุ่ม plan, แก้ plan (เพิ่ม / ลบ / สลับท่า), และ start plan ซึ่งพอเล่นเสร็จจะส่งต่อไป log ทันที
3. **History & stats:** รายการทั้งหมดเรียงตามวันที่, ผลรวมเวลาและ kcal, จำนวนครั้งต่อ activity, ท่าที่เล่นบ่อยที่สุด, streak และ progress เทียบกับเป้าหมายรายสัปดาห์
4. **Search / edit / delete:** ค้นด้วย id, วันที่ หรือ activity แล้วเลือกแก้หรือลบ (มีถามยืนยันก่อนลบ)
5. **Profile & library:** แก้ profile และเพิ่มท่าของตัวเองเข้า library
0. **Exit:** บันทึกข้อมูลแล้วออก

### Activity library

| Activity | Focus | MET |
| --- | --- | --- |
| Gym | Upper Body / Lower Body / Full Body | 5.0 |
| Yoga | Flexibility / Balance / Relax | 2.5 |
| Pilates | Core / Mat / Posture | 3.0 |
| Cardio | Run / Cycle / HIIT | 7.0 |

### TUI

- ใช้ ANSI escape codes ทำสี และใช้ box-drawing characters ทำกรอบ ทั้งหมดผ่าน `print()`
- header แสดงชื่อผู้ใช้, streak และ mascot ตลอด
- mascot เปลี่ยนอารมณ์ตาม state: ดีใจเมื่อ log สำเร็จ, เบ่งกล้ามเมื่อ streak ยาว, ง่วงเมื่อไม่ได้เล่นหลายวัน และตกใจเมื่อกรอกผิด
- animation สั้นๆ ไม่เกิน 1 วินาที

```
  (•̀ᴗ•́)و    log สำเร็จ
  ᕦ(ò_óˇ)ᕤ   streak ยาว / ทำสถิติใหม่
  (￣o￣) zzZ  ไม่ได้เล่นมาหลายวัน
  (°ロ°) !    กรอกข้อมูลผิด
```

## Business rules & validation

มี business rule 4 ข้อ (โจทย์ขอขั้นต่ำ 3) โดยทุกข้อเปลี่ยนผลลัพธ์ของการกระทำ

| # | Rule | เมื่อผิดเงื่อนไข | เหตุผลที่ใช้อธิบาย |
| --- | --- | --- | --- |
| 1 | Rest-day: เล่นกลุ่มเดิมสองวันติดกัน | **เตือนแล้วถามยืนยัน** ถ้าตอบ n จะยกเลิก | กล้ามเนื้อต้องพักฟื้น rule นี้ใช้กับ Gym และ Cardio HIIT เท่านั้น ส่วน Yoga / Pilates เล่นทุกวันได้ |
| 2 | No duplicate: วัน + activity + focus เดิมมีอยู่แล้ว | ปฏิเสธ และบอกให้ไปแก้รายการเดิมแทน | กันข้อมูลซ้ำทำให้สถิติเพี้ยน |
| 3 | Exercise must match: ท่าต้องอยู่ใน focus ที่เลือก | ปฏิเสธท่านั้น แล้วให้เลือกใหม่ | กันพิมพ์ผิดหรือเลือกผิดกลุ่ม |
| 4 | Plan ห้ามมีท่าซ้ำ และต้องมี 1–10 ท่า | ปฏิเสธ | plan ต้องใช้งานได้จริง |

### Validation (ข้อ 7)

ฟังก์ชันใน `inputs.py` ทุกตัววน `while True` จนกว่าจะได้ค่าที่ถูก โปรแกรมจึงไม่มีทาง crash จาก input

| Input | เงื่อนไข |
| --- | --- |
| เมนู | ต้องอยู่ในตัวเลือกที่มี |
| ตัวเลข | แปลงด้วย `try/except ValueError` |
| duration | 1–300 นาที |
| kcal | 0–3000 |
| อายุ / ส่วนสูง / น้ำหนัก | 10–100 ปี / 100–250 cm / 30–250 kg |
| วันที่ | รูปแบบ `YYYY-MM-DD` ผ่าน `datetime.strptime` และห้ามอยู่ในอนาคต (Enter ว่าง = วันนี้) |
| id ที่ค้นหา | ถ้าไม่พบจะได้ `None` แล้วแสดงข้อความ ไม่ crash |
| ลบรายการ | ต้องตอบ y ยืนยันก่อน |

## Data model

SQLite เป็นที่เก็บถาวร แต่ระหว่างที่โปรแกรมรัน ข้อมูลทั้งหมดอยู่ใน `list` ของ `dict` และทุกการคำนวณทำด้วย Python

### In memory

```python
profile = {"name": "Demo", "gender": "male", "age": 24,
           "height": 175, "weight": 70, "weekly_goal": 4,
           "activities": ["Gym", "Yoga"]}

library = {                     # dict -> dict -> list
    "Gym":  {"Upper Body": ["Bench Press", "Pull Up"], ...},
    "Yoga": {"Flexibility": ["Downward Dog", ...], ...},
}

logs = [                        # list of dict
    {"id": 1, "date": "2026-10-28", "activity": "Gym",
     "focus": "Upper Body", "exercises": ["Bench Press", "Pull Up"],
     "duration": 60, "calories": 350},
]

plans = [                       # list of dict
    {"id": 1, "name": "Push day", "activity": "Gym",
     "focus": "Upper Body", "exercises": ["Bench Press", "Shoulder Press"]},
]
```

### SQLite schema (`gym.db`)

```sql
CREATE TABLE profile   (id INTEGER PRIMARY KEY, name TEXT, gender TEXT, age INTEGER,
                        height INTEGER, weight INTEGER, weekly_goal INTEGER, activities TEXT);
CREATE TABLE exercises (id INTEGER PRIMARY KEY AUTOINCREMENT, activity TEXT, focus TEXT,
                        name TEXT, is_custom INTEGER);
CREATE TABLE plans     (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, activity TEXT,
                        focus TEXT, exercises TEXT);
CREATE TABLE logs      (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, activity TEXT, focus TEXT,
                        exercises TEXT, duration INTEGER, calories INTEGER);
```

### การตัดสินใจที่ต้องอธิบายได้

- **list ของท่าเก็บเป็น JSON text** (`json.dumps` / `json.loads`) แทนการทำ join table เพราะอธิบายง่ายกว่ามาก
- **วันที่เก็บเป็น string `YYYY-MM-DD`** เพราะ sort แบบตัวอักษรแล้วได้ลำดับเวลาถูกต้อง ส่วนตอนเช็คอนาคตหรือวันติดกันค่อยแปลงเป็น `datetime`
- **SQL ใช้แค่ `SELECT *`, `INSERT`, `UPDATE`, `DELETE`** ห้ามใช้ `SUM`, `COUNT`, `ORDER BY` และห้ามใช้ `WHERE` ใน `SELECT` เพื่อให้ข้อ 4 และข้อ 6 เป็นงานของ Python ล้วน (`UPDATE` / `DELETE` ใช้ `WHERE id = ?` ได้ ไม่งั้นจะโดนทุกแถว)
- **id ไม่นำกลับมาใช้ซ้ำ** เพราะใช้ `AUTOINCREMENT` (ถ้าเป็น `INTEGER PRIMARY KEY` เฉยๆ SQLite อาจเอา id ของแถวล่าสุดที่ถูกลบกลับมาใช้)
- **การคำนวณ kcal:** `kcal = MET × น้ำหนัก (kg) × ชั่วโมง`
- **BMR (Mifflin-St Jeor):** `10w + 6.25h − 5a + 5` สำหรับชาย และ `− 161` สำหรับหญิง

## File structure & functions

แบ่งเป็น 10 ไฟล์ แต่ละไฟล์มีหน้าที่เดียว พอถูกถามว่า "X อยู่ตรงไหน" ก็ชี้ไฟล์ได้ทันที

```
rush/
├── main.py        # entry: เช็ค profile → onboarding หรือเข้าเมนูหลัก
├── onboarding.py  # 5 steps ตั้งค่าครั้งแรก
├── menus.py       # log / history / manage / profile
├── plans.py       # My Plans
├── inputs.py      # ถาม input แบบวนจนกว่าจะถูก
├── rules.py       # business rules
├── stats.py       # algorithm ประมวลผลข้อมูล
├── fitness.py     # MET, kcal, BMR
├── db.py          # sqlite ↔ list of dict
├── ui.py          # สี, กรอบ, mascot, progress bar
├── seed.py        # ใส่ข้อมูลตัวอย่าง 4 สัปดาห์ลง gym.db สำหรับเดโม
├── server.py      # (เสริม) web view: dashboard + ฟอร์ม log ที่ใช้ rules เดียวกัน
├── README.md
└── auteur
```

| ไฟล์ | ฟังก์ชัน | Return |
| --- | --- | --- |
| `inputs.py` | `ask_int(prompt, lo, hi)` | int ที่อยู่ในช่วง |
| | `ask_date(prompt)` | string วันที่ที่ไม่อยู่ในอนาคต |
| | `ask_choice(prompt, options)` | ตัวเลือกจาก list |
| | `ask_multi(prompt, options)` | list ของตัวเลือกที่เลือก (ไม่ซ้ำ) |
| | `ask_yes_no(prompt)` | bool |
| `rules.py` | `is_duplicate(logs, date, activity, focus)` | bool |
| | `needs_rest(logs, date, activity, focus)` | bool (เช็ค activity ก่อนว่าใช้ rule ไหม) |
| | `valid_exercises(library, activity, focus, names)` | `(ok, bad_names)` |
| | `valid_plan(exercises)` | `(ok, message)` |
| `stats.py` | `total_of(logs, key)` | ผลรวม duration หรือ calories |
| | `count_by(logs, key)` | dict เช่น `{"Gym": 7, "Yoga": 3}` |
| | `most_frequent_exercise(logs)` | `(name, count)` หรือ `None` |
| | `current_streak(logs)` | int |
| | `days_this_week(logs)` | int |
| | `sort_logs(logs, key, reverse)` | list ใหม่ที่เรียงแล้ว (เขียน sort เอง) |
| | `search_logs(logs, field, value)` | list ที่ตรงเงื่อนไข |
| | `find_by_id(items, item_id)` | dict หรือ `None` |
| | `random_workout(library, activity, focus, n)` | list ท่าที่สุ่ม (`random.sample`) |
| `fitness.py` | `estimate_kcal(activity, weight, minutes)` | int |
| | `bmr(profile)` | float |
| `db.py` | `init_db()`, `load_all()`, `save_log(log)`, `update_log(log)`, `delete_log(id)`, … | |
| `ui.py` | `color(text, c)`, `box(title, lines)`, `mascot(mood)`, `progress(cur, total)`, `clear()` | string / print |
| `menus.py` | `menu_log(state, preset=None)`, `menu_history(state)`, `menu_manage(state)`, `menu_profile(state)` | |
| `plans.py` | `menu_plans(state)`, `create_plan(state)`, `random_plan(state)`, `edit_plan(state, plan)`, `start_plan(state, plan)` | |
| `onboarding.py` | `run_onboarding()` | profile dict |

`state` คือ dict ที่รวมทุกอย่างไว้ (`{"profile":…, "library":…, "logs":…, "plans":…}`) ส่งตัวเดียวเข้าทุกเมนู ไม่ต้องใช้ global

`preset` คือ dict ของ plan ที่ start แล้ว ส่งเข้า `menu_log` เพื่อกรอก activity, focus และท่าให้อัตโนมัติ

## Program flow

```
Open app (load gym.db)
        │
  Profile exists? ──no──► Onboarding (5 steps, first run only)
        │ yes                     │
        ▼                         │
   ┌─────────┐ ◄──────────────────┘
   │Main menu│ ──0──► Exit (save and quit)
   └────┬────┘
        ├── 1 Log            (rules, save)
        ├── 2 My plans       (create, random, edit, start) ──start plan──► 1 Log (preset)
        ├── 3 Stats          (history, streak)
        ├── 4 Search         (edit, delete)
        └── 5 Profile        (edit, library)
```

ทุกเมนูทำงานเสร็จแล้วจะกลับมาที่เมนูหลัก และ save ลง DB ทุกครั้งที่ข้อมูลเปลี่ยน ส่วน Start plan ใน My plans จะส่ง preset ต่อไปให้ Log

## Defense cheat sheet

| ข้อ | อยู่ตรงไหน | เดโมยังไง |
| --- | --- | --- |
| 1 Menu | `main.py` while loop + 5 เมนู | เปิดโปรแกรมแล้ววนเมนูให้ดู |
| 2 List / Dict | `state`, `library` (dict ซ้อน dict ซ้อน list), `logs`, `plans` (list of dict) | log, แก้ และลบให้เห็นว่าข้อมูลเปลี่ยน |
| 3 Rules | `rules.py` 4 ฟังก์ชัน | log Gym Upper สองวันติด, log ซ้ำวันเดิม, ใส่ท่าผิดกลุ่ม |
| 4 Loops | `while` ใน `main` และ `inputs`, `for` ใน `stats` ทั้งไฟล์ | อธิบายลูปใน `current_streak` |
| 5 Functions | ทุกไฟล์ มี parameter และ return | ชี้ `total_of(logs, key)` ที่ return ค่า |
| 6 Processing | `stats.py`: streak, count, sum, sort, search, most frequent | เปิดหน้า stats |
| 7 Validation | `inputs.py`, `find_by_id` คืน `None` | พิมพ์ `abc`, `-5`, `99`, วันพรุ่งนี้, id ที่ไม่มี |
| 8 Workflow | onboarding → plan → start → log → stats → edit → delete | เดโม flow เต็มตั้งแต่ต้นจนจบ |

### คำถามที่ evaluator น่าจะถาม

- ทำไม rest-day rule ไม่ใช้กับ Yoga?
- ถ้าลบ log แล้ว id จะซ้ำไหม?
- ทำไมไม่ใช้ `SUM()` ใน SQL?
- `current_streak` ทำงานยังไงถ้าวันนี้ยังไม่ได้เล่น?
- ถ้าไม่ระบุเพศ BMR คำนวณยังไง?

## Build phases & risks

ทำ Phase 1 ให้ผ่าน 8 ข้อก่อนเสมอ ถ้าเวลาไม่พอ หยุดหลัง Phase 3 ก็ส่งได้แล้ว

- [x] **Phase 1 Core:** `inputs`, `rules`, `stats`, `menus` ใช้แค่ Gym และเก็บใน memory → ผ่าน 8 ข้อ
- [x] **Phase 2:** multi-activity + `db.py` SQLite
- [x] **Phase 3:** onboarding + `fitness.py` (kcal อัตโนมัติ, BMR)
- [x] **Phase 4:** My Plans
- [x] **Phase 5:** ความสวย: สี, mascot, animation
- [x] **Phase 6 (ถ้ามีเวลา):** `server.py` ใช้ `http.server` + web UI โดยฝัง HTML เป็น string ไว้ในไฟล์ `.py`
- [ ] เขียน README + auteur
- [ ] ทดสอบ input ผิดทุกจุดบนเครื่อง 42

### Risks

| Risk | ทางแก้ |
| --- | --- |
| เพื่อนอธิบายโค้ดไม่ได้ แล้วทีมตก | ทำคู่มืออธิบายรายไฟล์ + ซ้อมถามตอบกันก่อน defense |
| scope ใหญ่เกิน ทำไม่ทัน | ทำตามลำดับ phase และไม่ข้าม |
| ANSI ไม่แสดงผลในบาง terminal | มี `NO_COLOR` fallback |
| ไฟล์ HTML แยกไม่อยู่ในรายชื่อไฟล์ที่ส่งได้ | ฝัง HTML ใน `.py` หรือถามพี่ Tarm ก่อน |
