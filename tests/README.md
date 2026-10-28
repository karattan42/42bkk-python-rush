# Tests

โฟลเดอร์นี้ไม่ใช่ส่วนของแอป และไม่ต้องส่งตอน turn-in ทุก test ใช้ database ชั่วคราว ไม่แตะ `gym.db` จริง

| โฟลเดอร์ | ทดสอบอะไร | ต้องติดตั้งอะไร |
| --- | --- | --- |
| `unit/` | rules, stats, fitness, inputs, db, accounts, ฟอร์มและ HTML ของเว็บ | ไม่ต้อง (standard library) |
| `cli/` | รัน `main.py` จริงแล้วพิมพ์ input เหมือนคน: onboarding, rest day, ท่าผิดกลุ่ม, ซ้ำ, ลบ, plan | ไม่ต้อง |
| `cli/test_terminal_login.py` | โหมด SSH (`STREAKR_LOGIN=1`): สมัคร, login, แยกข้อมูลแต่ละคน, ล็อกหลังรหัสผิด, ชื่อที่มีตัวควบคุม | ไม่ต้อง |
| `web/` | ยิง HTTP จริงเข้า `server.py`: login, แยกข้อมูลแต่ละคน, CSRF, header ความปลอดภัย, theme | ไม่ต้อง |
| `e2e/` | เปิด Chrome จริงด้วย Playwright: สมัคร → ตั้ง profile → log → rest day → theme → 2 คน → มือถือ | `pytest`, `playwright` |

## รัน

จาก root ของโปรเจกต์

```bash
# unit + cli + web (รันบนเครื่อง 42 ได้เลย ไม่ต้องติดตั้งอะไร)
python3 -m unittest discover -s tests -t .

# ทุกอย่างรวม browser test
python3 -m venv tests/.venv
tests/.venv/bin/pip install -r tests/requirements.txt
tests/.venv/bin/pytest tests
```

- browser test ใช้ Chrome ที่ติดตั้งในเครื่อง ถ้าไม่มี Chrome ให้รัน `tests/.venv/bin/playwright install chromium` แล้วใช้ `PLAYWRIGHT_CHANNEL=chromium tests/.venv/bin/pytest tests`
- browser test จะ fail ถ้ามี error ใน console ของ browser (เช่น Content-Security-Policy บล็อกอะไร)
- รันไฟล์เดียว: `python3 -m unittest tests.unit.test_rules` หรือ `tests/.venv/bin/pytest tests/e2e -k theme`
