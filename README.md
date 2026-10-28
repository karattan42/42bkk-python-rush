# Streakr

แอปบันทึกการออกกำลังกายใน terminal เขียนด้วย Python standard library ล้วน รองรับ Gym, Yoga, Pilates และ Cardio
ช่วยให้จำได้ว่าเล่นอะไรไปแล้ว, มี plan ให้เล่นตาม และเห็น streak กับความสม่ำเสมอของตัวเอง

Rush00 — 42 Bangkok Discovery Piscine

## วิธีรัน

ต้องใช้ Python 3.8 ขึ้นไป ไม่ต้องติดตั้ง package เพิ่ม

```bash
python3 main.py      # แอปหลัก (ครั้งแรกจะเข้าหน้าตั้งค่า 5 ขั้นตอน)
python3 seed.py      # (ไม่บังคับ) ใส่ข้อมูลตัวอย่าง 4 สัปดาห์สำหรับเดโม
python3 server.py    # (ไม่บังคับ) web view ที่ http://localhost:8042
```

- ข้อมูลเก็บใน `gym.db` (SQLite) ข้างไฟล์โค้ด สร้างให้อัตโนมัติตอนรันครั้งแรก
- ถ้า terminal แสดงสีเพี้ยน ให้รัน `NO_COLOR=1 python3 main.py`
- `seed.py` จะถามก่อนลบ `gym.db` เดิม วันที่ในข้อมูลตัวอย่างคิดจากวันนี้ ข้อมูลจึงจบที่เมื่อวาน และ streak ยังนับต่อได้

## เมนู

| # | เมนู | ทำอะไรได้ |
| --- | --- | --- |
| 1 | Log workout | เลือก activity → focus → ท่า แล้วใส่เวลา ระบบประเมิน kcal ให้ (กด Enter เพื่อใช้ค่านั้น) |
| 2 | My plans | สร้าง, สุ่ม, แก้ (เพิ่ม / ลบ / สลับท่า / เปลี่ยนชื่อ), ลบ และ start plan ซึ่งจะพาไปหน้า log พร้อมกรอกให้ |
| 3 | History & stats | ประวัติเรียงตามวันที่, เวลาและ kcal รวม, streak ปัจจุบันและดีที่สุด, เป้าหมายรายสัปดาห์, จำนวนครั้งต่อ activity และท่าที่เล่นบ่อยที่สุด |
| 4 | Search / edit / delete | ค้นด้วย ID, วันที่ หรือ activity แล้วแก้หรือลบ (ถามยืนยันก่อนลบ) |
| 5 | Profile & library | แก้ข้อมูลส่วนตัว, เลือก activity ที่เล่น, ดู BMR และเพิ่มท่าของตัวเอง |
| 0 | Exit | ออก (ข้อมูลถูก save ทุกครั้งที่มีการเปลี่ยนแปลงอยู่แล้ว) |

## Business rules

| # | Rule | ผลลัพธ์ |
| --- | --- | --- |
| 1 | Rest day: Gym หรือ Cardio HIIT กลุ่มเดิมวันติดกัน | เตือนแล้วถามยืนยัน ตอบ n = ยกเลิก (Yoga / Pilates เล่นทุกวันได้) |
| 2 | ห้าม log วัน + activity + focus ซ้ำ | ปฏิเสธ และบอกให้ไปแก้รายการเดิม |
| 3 | ท่าต้องอยู่ใน focus ที่เลือก | ปฏิเสธท่านั้น แล้วให้เลือกใหม่ |
| 4 | Plan ต้องมี 1–10 ท่าและห้ามซ้ำ | ปฏิเสธ |

## Input validation

ทุก input วนถามจนกว่าจะได้ค่าที่ถูก โปรแกรมไม่ crash จากการพิมพ์ผิด (Ctrl-C / Ctrl-D ก็ออกได้ปกติ)

| Input | เงื่อนไข |
| --- | --- |
| เมนู / ตัวเลือก | ต้องเป็นตัวเลขในช่วงที่มี |
| duration | 1–300 นาที |
| kcal | 0–3000 |
| อายุ / ส่วนสูง / น้ำหนัก | 10–100 ปี / 100–250 cm / 30–250 kg |
| วันที่ | `YYYY-MM-DD` และห้ามอยู่ในอนาคต (Enter ว่าง = วันนี้) |
| ID ที่ไม่มีอยู่ | แสดงข้อความว่าไม่พบ |

## โครงสร้างไฟล์

| ไฟล์ | หน้าที่ |
| --- | --- |
| `main.py` | จุดเริ่มต้น: โหลดข้อมูล, onboarding ถ้ายังไม่มี profile, วนเมนูหลัก |
| `onboarding.py` | ตั้งค่าครั้งแรก 5 ขั้นตอน (พิมพ์ `b` เพื่อย้อนกลับ) |
| `menus.py` | เมนู log / history / search / profile |
| `plans.py` | เมนู My plans |
| `inputs.py` | ฟังก์ชันถาม input แบบวนจนกว่าจะถูก |
| `rules.py` | business rules ทั้ง 4 ข้อ |
| `stats.py` | ประมวลผลข้อมูล: sum, count, sort (insertion sort), search, streak |
| `fitness.py` | MET, kcal, BMR และท่าตั้งต้น |
| `db.py` | อ่าน / เขียน SQLite ↔ list of dict |
| `ui.py` | สี, กรอบ, mascot, progress bar, animation |
| `seed.py` | ข้อมูลตัวอย่างสำหรับเดโม |
| `server.py` | web view (ส่วนเสริม) ใช้ rules และ stats ชุดเดียวกับแอปหลัก |
| `accounts.py` | สมัคร / login / session ของ web view และ terminal (hash รหัสผ่านด้วย PBKDF2) |
| `login.py` | หน้า Log in / Create account ใน terminal (เปิดเมื่อ `STREAKR_LOGIN=1` เช่นตอนเข้าผ่าน SSH) |
| `Dockerfile`, `Dockerfile.ssh`, `docker-compose.yml`, `deploy/ssh/` | สำหรับ deploy (ไม่ใช่ไฟล์ที่ต้องส่ง) |

## สูตรที่ใช้

- **kcal** = MET × น้ำหนัก (kg) × ชั่วโมง โดย MET: Gym 5.0, Yoga 2.5, Pilates 3.0, Cardio 7.0
- **BMR** (Mifflin-St Jeor) = 10 × น้ำหนัก + 6.25 × ส่วนสูง − 5 × อายุ, +5 สำหรับชาย, −161 สำหรับหญิง, ถ้าไม่ระบุใช้ค่าเฉลี่ยของสองสูตร

## หมายเหตุการออกแบบ

- ระหว่างรัน ข้อมูลอยู่ใน list / dict ส่วน SQLite ใช้เก็บถาวรเท่านั้น ใช้แค่ `SELECT *`, `INSERT`, `UPDATE`, `DELETE` ส่วนการรวม, นับ, เรียง และค้นหาทำด้วย loop ใน Python
- ID ใช้ `AUTOINCREMENT` จึงไม่ถูกนำกลับมาใช้ซ้ำหลังลบ
- รายการท่าเก็บเป็น JSON text ในคอลัมน์เดียว แทนการทำตารางแยก

## Web view: บัญชีผู้ใช้

- แต่ละคนสมัครด้วย username + password แล้วตั้งค่า profile ครั้งแรก จากนั้นเห็นเฉพาะข้อมูลของตัวเอง
- ทุกแถวใน `logs`, `plans` และท่าที่เพิ่มเองมี `user_id` แอปใน terminal ใช้บัญชี `local` (id 1) เสมอ ซึ่ง login จากเว็บไม่ได้
- `gym.db` เก่าที่ยังไม่มี `user_id` จะถูกเพิ่มคอลัมน์ให้อัตโนมัติ และข้อมูลเดิมเป็นของบัญชี `local`
- ปุ่ม Auto / Light / Dark ด้านบนเลือกธีม และจำไว้ใน cookie

### ความปลอดภัย

| เรื่อง | ทำยังไง |
| --- | --- |
| XSS | ข้อความทุกอย่างผ่าน `html.escape()` และ header `Content-Security-Policy` สั่งให้ browser ไม่รัน JavaScript เลย |
| SQL injection | ทุก query ใช้ `?` placeholder |
| รหัสผ่าน | เก็บเป็น PBKDF2-SHA256 200,000 รอบ + salt สุ่มต่อคน เทียบด้วย `hmac.compare_digest` |
| Session | token สุ่มจาก `secrets` อยู่ใน cookie `HttpOnly; SameSite=Lax` (และ `Secure` เมื่ออยู่หลัง HTTPS) ใน DB เก็บแค่ SHA-256 ของ token, หมดอายุ 30 วัน, log out แล้วใช้ไม่ได้ |
| เดารหัสผ่าน | ผิด 5 ครั้งล็อก 5 นาที, ข้อความเดียวกันทั้ง "ไม่มี user" และ "รหัสผิด" |
| CSRF | form POST ต้องมี `Origin` เป็นเว็บเราเท่านั้น, log out เป็น POST |
| Host header / DNS rebinding | รับเฉพาะ host ใน `ALLOWED_HOSTS` |
| request ใหญ่ / แปลก | body เกิน 10 KB ตอบ 413, ตัวอักษรเสียไม่ทำให้ crash |

## ใช้ผ่าน SSH (terminal ของแต่ละคน)

คนอื่นใช้แอปใน terminal ของตัวเองได้ด้วย `ssh streakr@your-server -p 2222` แล้วจะเจอหน้า Log in / Create account ทันที บัญชีเดียวกับเว็บ ข้อมูลที่ log ผ่าน SSH ขึ้นบนเว็บด้วย

- ลองในเครื่อง: `STREAKR_LOGIN=1 python3 main.py` (รัน `python3 main.py` ธรรมดา = บัญชี `local` เหมือนเดิม)
- SSH user `streakr` ไม่มีรหัสผ่าน เพราะ login จริงอยู่ในแอป และ `ForceCommand` บังคับให้รันได้แค่แอปนี้ ออกจากแอปเมื่อไหร่ connection ปิดทันที ไม่มี shell
- ปิด port forwarding, agent forwarding, X11, tunnel และไม่มี sftp, ลองได้ 3 ครั้งต่อ connection, ตัด connection ที่ค้างเกิน 10 นาที
- รหัสผิด 3 ครั้งใน 1 ครั้งที่เข้า แอปปิดเอง, ผิดรวม 5 ครั้งบัญชีล็อก 5 นาที (เก็บใน database จึงต่อใหม่ก็ไม่หาย)
- ชื่อที่พิมพ์มีตัวอักษรควบคุม (เช่น escape code ของ terminal) ไม่ได้

## Deploy บน Dokploy

**แบบเว็บ + SSH (แนะนำ)**: ใน Dokploy สร้าง **Docker Compose** app จาก repo นี้ (`docker-compose.yml`) แล้ว
- ใส่โดเมนให้ service `web` port `8042` เปิด HTTPS และตั้ง `ALLOWED_HOSTS=โดเมนของคุณ`
- เปิด port `2222` บน firewall ของ server ให้คนเข้า SSH ได้
- ทั้งสอง service ใช้ volume `streakr-data` ร่วมกัน (บัญชีและข้อมูลชุดเดียวกัน)

**แบบเว็บอย่างเดียว:**

1. push โปรเจกต์ขึ้น GitHub (หรือ Git ที่ Dokploy ต่อได้)
2. ใน Dokploy สร้าง Application → เลือก repo → Build Type: **Dockerfile**
3. Environment: `ALLOWED_HOSTS=ชื่อโดเมนของคุณ` เช่น `streakr.example.com` (ถ้ามีหลายชื่อคั่นด้วย `,`)
4. Volumes: mount volume ไปที่ `/data` (ไม่งั้นบัญชีและข้อมูลหายทุกครั้งที่ deploy ใหม่)
5. Domains: ใส่โดเมน, container port `8042`, เปิด HTTPS
6. Deploy แล้วเปิดโดเมน จะเจอหน้า Log in / Create account

ถ้าเปิดเว็บแล้วได้ `400 Unknown host` แปลว่า `ALLOWED_HOSTS` ไม่ตรงกับโดเมนที่ใช้เปิด

**อย่ารัน `seed.py` บน server จริง** เพราะมันลบ `gym.db` ทั้งไฟล์ รวมบัญชีของทุกคน
