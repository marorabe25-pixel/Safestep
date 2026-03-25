# 🦶 SafeStep — Full-Stack Health Tech Platform
### Python FastAPI Backend + Standalone HTML Frontend

Premium diabetic foot monitoring platform with real-time sensor data, patient/doctor accounts,
automated email alerts, and preorder management.

---

## 📁 Project Structure

```
safestep-py/
├── main.py                        ← FastAPI app entry point
├── requirements.txt               ← Python dependencies
├── .env.example                   ← Copy to .env and configure
│
├── app/
│   ├── config.py                  ← Pydantic settings (reads .env)
│   ├── database.py                ← Async SQLAlchemy + SQLite setup
│   │
│   ├── models/
│   │   └── models.py              ← All ORM models (6 tables)
│   │
│   ├── middleware/
│   │   └── auth.py                ← JWT helpers + FastAPI dependency
│   │
│   ├── routes/
│   │   ├── auth.py                ← Register, login, /me
│   │   ├── sensors.py             ← Sensor readings + patient panel
│   │   ├── alerts.py              ← Alert list + resolve
│   │   └── orders.py              ← Preorders + demo requests
│   │
│   └── services/
│       ├── alert_service.py       ← Threshold engine + alert creation
│       └── email_service.py       ← HTML email templates via SMTP
│
├── public/
│   └── index.html                 ← Full website (served by FastAPI)
│
└── db/
    └── safestep.db                ← Auto-created SQLite database
```

---

## 🚀 Quick Start (3 steps)

### 1. Create virtual environment & install dependencies
```bash
cd safestep-py

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env — at minimum set a strong SECRET_KEY
# Email is optional: leave MAIL_USERNAME blank to log emails to console
```

### 3. Run the server
```bash
# Development (auto-reload on file changes)
uvicorn main:app --reload --port 8000

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Open the website
```
http://localhost:8000
```

The FastAPI backend serves the frontend HTML automatically. ✅

**Interactive API docs (Swagger UI):**
```
http://localhost:8000/api/docs
```

---

## 🗄️ Database

SQLite with async SQLAlchemy. Tables are auto-created on first startup.

| Table | Description |
|---|---|
| `users` | All users — patients, doctors, admins |
| `doctor_profiles` | Specialty, hospital, verification status |
| `patient_profiles` | Diabetes type, linked doctor, device pairing |
| `sensor_readings` | All insole sensor data + AI risk scores |
| `alerts` | Auto-generated + manual alerts with email status |
| `preorders` | Customer preorders |
| `demo_requests` | Clinical demo requests |

To use **PostgreSQL** in production, swap the `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql+asyncpg://user:password@localhost/safestep
pip install asyncpg
```

---

## 📡 API Reference

All API routes are prefixed with `/api`. Interactive docs at `/api/docs`.

---

### 🔐 Authentication

#### `POST /api/auth/register`
Register a new patient or doctor.
```json
{
  "email": "patient@example.com",
  "password": "securepass123",
  "name": "John Smith",
  "role": "patient",
  "diabetes_type": "type2"
}
```
Doctor registration:
```json
{
  "email": "dr.smith@hospital.org",
  "password": "securepass123",
  "name": "Dr. Jane Smith",
  "role": "doctor",
  "specialty": "Endocrinology",
  "hospital": "City Medical Center"
}
```
**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiJ9...",
  "user": { "id": "uuid", "email": "...", "name": "...", "role": "patient" }
}
```

#### `POST /api/auth/login`
```json
{ "email": "patient@example.com", "password": "securepass123" }
```
Returns same `{ token, user }` shape.

#### `GET /api/auth/me`
Requires: `Authorization: Bearer <token>`
Returns current user + role-specific profile.

---

### 📡 Sensor Data

#### `POST /api/sensors/reading`
**Auth:** Patient JWT

Post a live reading from the SafeStep insole device.
```json
{
  "device_id": "device-uuid-001",
  "foot_side": "left",
  "temp_heel": 33.2,
  "temp_arch": 33.8,
  "temp_ball": 34.1,
  "temp_toes": 34.5,
  "press_heel": 72.0,
  "press_arch": 45.0,
  "press_ball": 88.0,
  "press_toes": 55.0,
  "step_count": 1250,
  "battery_pct": 87
}
```
**Response:**
```json
{ "id": "reading-uuid", "risk_score": 42.5, "alerts_created": 1 }
```

**Auto-generated alerts when:**
| Condition | Severity | Email sent |
|---|---|---|
| `temp_max ≥ 35.0°C` | High | ✅ Patient |
| `temp_max ≥ 36.0°C` | Critical | ✅ Patient + Doctor |
| `press_max ≥ 85%` | Medium | ❌ |
| `press_max ≥ 95%` | Critical | ✅ Patient + Doctor |
| `risk_score ≥ 70` | Critical | ✅ Patient + Doctor |

#### `GET /api/sensors/latest`
**Auth:** Patient JWT — Returns most recent reading.

#### `GET /api/sensors/history?hours=24`
**Auth:** Patient or Doctor JWT
- Patients see their own data
- Doctors pass `?patient_id=<uuid>` to view a specific patient

#### `GET /api/sensors/patients`
**Auth:** Doctor JWT — Returns all assigned patients with latest readings, sorted by risk score.

---

### 🔔 Alerts

#### `GET /api/alerts`
**Auth:** JWT (Patient or Doctor)
- Patients see their own alerts
- Doctors see all alerts for their patients

Query params:
- `?unresolved=true` — only open alerts
- `?limit=50` — max results (default 50, max 200)

#### `PATCH /api/alerts/{alert_id}/resolve`
**Auth:** JWT — Mark an alert as resolved.

---

### 📦 Orders

#### `POST /api/orders/preorder`
Public endpoint — no auth required.
```json
{
  "name": "John Smith",
  "email": "john@example.com",
  "phone": "+1 555 0000",
  "plan": "patient",
  "quantity": 1,
  "city": "New York",
  "country": "US",
  "notes": "Optional notes"
}
```
Plans: `patient` ($299) · `clinical` ($799/yr) · `enterprise` (custom)

**Response:**
```json
{
  "id": "uuid",
  "order_ref": "A1B2C3D4",
  "message": "Preorder confirmed! Check your email for details.",
  "amount": "$299.00",
  "status": "pending"
}
```

#### `POST /api/orders/demo`
Public endpoint — request a clinical demo.
```json
{
  "name": "Dr. Jane Smith",
  "email": "jane@hospital.org",
  "organization": "City Hospital",
  "role": "Endocrinologist",
  "message": "Interested in a pilot for 50 patients"
}
```

#### `GET /api/orders`
**Auth:** Admin JWT only — list all preorders.

---

### 📊 Public Stats

#### `GET /api/stats`
No auth required. Returns live platform stats for the homepage counter.
```json
{
  "total_readings": 14821,
  "total_alerts": 342,
  "total_patients": 89,
  "total_preorders": 156,
  "amputations_prevented": 8288
}
```

---

## 📧 Email Configuration

Uses **fastapi-mail** with Jinja2 HTML templates.

**Gmail setup:**
1. Enable 2FA on your Google account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate an app password for "Mail"
4. Add to `.env`:
```
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=xxxx xxxx xxxx xxxx   # the 16-char app password
MAIL_FROM=alerts@safestep.health
```

**Without email config**, all emails are logged to console — perfect for development.

---

## 🔐 Security

| Feature | Implementation |
|---|---|
| Password hashing | bcrypt (passlib, 12 rounds) |
| Authentication | JWT (python-jose, HS256, 7-day expiry) |
| CORS | Configurable origins via `ALLOWED_ORIGINS` |
| Rate limiting | slowapi per-IP limiting |
| Role isolation | `require_role()` FastAPI dependency |
| Device verification | Device ID linked to patient profile |

---

## 🧪 Testing the API (curl examples)

```bash
BASE=http://localhost:8000/api

# 1. Register a patient
curl -X POST $BASE/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"pat@test.com","password":"test1234","name":"Test Patient","role":"patient","diabetes_type":"type2"}'

# 2. Login → grab token
TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"pat@test.com","password":"test1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# 3. Post a CRITICAL reading (temp_max=36.5, press_max=97)
curl -X POST $BASE/sensors/reading \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"dev-001","temp_heel":36.5,"temp_ball":36.2,"press_heel":97,"press_ball":95}'

# 4. Check alerts — should have critical alerts
curl $BASE/alerts \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 5. Submit a preorder (no auth needed)
curl -X POST $BASE/orders/preorder \
  -H "Content-Type: application/json" \
  -d '{"name":"John Smith","email":"john@example.com","plan":"patient","city":"New York"}'
```

---

## 🌐 Deployment

### Render / Railway (easiest)
1. Push to GitHub
2. Connect repo → set env vars → deploy
3. Change `DATABASE_URL` to PostgreSQL for production

### Docker
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

```bash
docker build -t safestep .
docker run -p 8000:8000 --env-file .env safestep
```

### VPS (nginx + systemd)
```ini
# /etc/systemd/system/safestep.service
[Unit]
Description=SafeStep FastAPI
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/srv/safestep
EnvironmentFile=/srv/safestep/.env
ExecStart=/srv/safestep/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

```nginx
# nginx reverse proxy
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📄 License
MIT — Build the future of healthcare.
