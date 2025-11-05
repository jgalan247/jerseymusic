# Deployment Options for Jersey Events

## Summary of Options

| Platform | Monthly Cost | Ease of Setup | Best For | Worker Support |
|----------|-------------|---------------|----------|----------------|
| Railway | $10-20 | ⭐⭐⭐⭐⭐ | Quick deployment | ✅ Native |
| Render | $7-15 | ⭐⭐⭐⭐⭐ | Cost-effective | ✅ Native |
| Heroku | $14-25 | ⭐⭐⭐⭐ | Enterprise-ready | ✅ Native |
| Docker (VPS) | $5-12 | ⭐⭐⭐ | Full control | ✅ Manual setup |
| Digital Ocean | $12-24 | ⭐⭐ | Custom setup | ✅ Supervisor/systemd |

## 🚀 Quick Deploy: Railway (Recommended)

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Add deployment configs"
git push origin main
```

### Step 2: Deploy on Railway
1. Go to https://railway.app
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repo
5. Railway will auto-detect Django and create:
   - Web service (runs `gunicorn`)
   - PostgreSQL database

### Step 3: Add Worker Service
1. In Railway dashboard, click "New Service"
2. Select "From existing repo"
3. Choose same repo
4. Set start command: `python manage.py qcluster`
5. Link to same database

### Step 4: Set Environment Variables
Add these in Railway settings:
```
SECRET_KEY=<generate-random-key>
DEBUG=False
DATABASE_URL=<auto-populated>
ALLOWED_HOSTS=*.railway.app,yourdomain.com

# SumUp
SUMUP_CLIENT_ID=<your-client-id>
SUMUP_CLIENT_SECRET=<your-secret>
SUMUP_MERCHANT_CODE=<your-merchant-code>

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<your-email>
EMAIL_HOST_PASSWORD=<app-password>
```

### Step 5: Run Migrations
In Railway terminal:
```bash
python manage.py migrate
python manage.py createsuperuser
```

### Step 6: Create Polling Schedule
```bash
python manage.py shell
```
```python
from django_q.models import Schedule
Schedule.objects.create(
    name='Payment Polling',
    func='payments.polling_service.polling_service.process_pending_payments',
    schedule_type='I',
    minutes=5,
    repeats=-1
)
```

**Done!** Your app is live with both web server and worker running.

---

## 🎨 Deploy: Render.com (Alternative)

### Using render.yaml (included)

1. Go to https://render.com
2. Click "New +" → "Blueprint"
3. Connect GitHub repo
4. Render reads `render.yaml` and creates:
   - Web service
   - Worker service
   - PostgreSQL database

5. Set environment variables in Render dashboard
6. Deploy!

---

## 🐳 Docker Deployment (Advanced)

### Local Testing

```bash
# Build and start all services
docker-compose up --build

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Create schedule
docker-compose exec web python manage.py shell
>>> from django_q.models import Schedule
>>> Schedule.objects.create(...)
```

### Deploy to Production (DigitalOcean, AWS, etc.)

1. **Install Docker on server:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

2. **Clone repo:**
```bash
git clone <your-repo>
cd jerseymusic
```

3. **Create .env file:**
```bash
cp .env.example .env
nano .env  # Configure production settings
```

4. **Start services:**
```bash
docker-compose up -d
```

5. **Setup SSL with Let's Encrypt:**
```bash
docker-compose exec nginx certbot --nginx -d yourdomain.com
```

---

## 🖥️ Traditional VPS Deployment

### Option: Digital Ocean + Supervisor

Your codebase already has configs for this!

**Files included:**
- `systemd_django_q.service` - Systemd service for worker
- Supervisor configs mentioned in docs

**Steps:**

1. **Provision VPS:**
   - Digital Ocean Droplet (2GB RAM minimum)
   - Ubuntu 22.04

2. **Install dependencies:**
```bash
sudo apt update
sudo apt install python3-pip python3-venv postgresql nginx supervisor
```

3. **Setup application:**
```bash
git clone <repo>
cd jerseymusic
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. **Configure PostgreSQL:**
```bash
sudo -u postgres psql
CREATE DATABASE jerseyevents;
CREATE USER jerseyevents WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE jerseyevents TO jerseyevents;
```

5. **Configure Supervisor** (for worker):
```bash
sudo nano /etc/supervisor/conf.d/jerseyevents-worker.conf
```
```ini
[program:jerseyevents-worker]
command=/home/user/jerseymusic/venv/bin/python manage.py qcluster
directory=/home/user/jerseymusic
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/jerseyevents-worker.log
```

6. **Configure Nginx:**
```bash
sudo nano /etc/nginx/sites-available/jerseyevents
```
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /home/user/jerseymusic/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

7. **Start services:**
```bash
# Web server (use systemd)
sudo systemctl start gunicorn

# Worker
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start jerseyevents-worker

# Nginx
sudo systemctl restart nginx
```

---

## 📊 Comparison Matrix

### Railway.app
**Pros:**
- ✅ Fastest deployment (5 minutes)
- ✅ Handles web + worker automatically
- ✅ Auto-scaling
- ✅ Built-in monitoring
- ✅ Easy rollbacks

**Cons:**
- ❌ More expensive at scale
- ❌ Less control

**Best for:** Quick launch, MVP, startups

---

### Render.com
**Pros:**
- ✅ Great free tier
- ✅ Native worker support
- ✅ Good documentation
- ✅ Auto-deploy from Git

**Cons:**
- ❌ Free tier has spindown delay

**Best for:** Budget-conscious, side projects

---

### Docker Compose
**Pros:**
- ✅ Portable (run anywhere)
- ✅ Full control
- ✅ Easy local development
- ✅ Cost-effective

**Cons:**
- ❌ Need Docker knowledge
- ❌ Manual server setup

**Best for:** Developers comfortable with Docker

---

### Traditional VPS
**Pros:**
- ✅ Maximum control
- ✅ Most cost-effective at scale
- ✅ Can optimize everything

**Cons:**
- ❌ Most DevOps work
- ❌ Security management
- ❌ No auto-scaling

**Best for:** Teams with DevOps resources

---

## 🎯 My Recommendation for Jersey Events

**Start with: Railway.app or Render.com**

**Why:**
1. Your app has 2 processes (web + worker) - they handle this natively
2. You don't need to manage servers
3. Fast time-to-market
4. Built-in monitoring and logging
5. Easy to scale later

**Migrate to:** Docker on VPS (when you need more control or have higher traffic)

---

## 📋 Deployment Checklist

Before deploying to ANY platform:

- [ ] Set `DEBUG=False` in production
- [ ] Generate secure `SECRET_KEY`
- [ ] Configure PostgreSQL (not SQLite)
- [ ] Set up email provider (Gmail/SendGrid)
- [ ] Configure SumUp OAuth credentials
- [ ] Set `ALLOWED_HOSTS` correctly
- [ ] Run `collectstatic`
- [ ] Run migrations
- [ ] Create superuser
- [ ] **Create Django-Q schedule for polling**
- [ ] Verify worker is running
- [ ] Test payment flow end-to-end
- [ ] Set up SSL certificate
- [ ] Configure domain DNS

---

## 🆘 Need Help?

**Railway:** https://docs.railway.app/
**Render:** https://render.com/docs
**Docker:** https://docs.docker.com/

**Questions?** Check the deployment guide in your repo or file an issue.
