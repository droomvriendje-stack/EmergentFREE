# Droomvriendjes - E-commerce Platform

Een complete e-commerce webshop voor slaapknuffels met nachtlampje en rustgevende geluiden.

## 🏗️ Architectuur

| Component | Platform | Status |
|-----------|----------|--------|
| Domain | TransIP → Cloudflare | ✅ |
| DNS + SSL | Cloudflare | ✅ |
| Frontend | Cloudflare Pages | ✅ |
| Backend | Railway.app | ✅ |
| Database | Supabase (PostgreSQL) | ✅ |
| Storage | Supabase Storage | ✅ |
| Payments | Mollie | ✅ |
| Email | Postmark | ✅ |

## 🚀 Lokale Ontwikkeling

### Vereisten
- Node.js 18+
- Python 3.11+
- Docker (optioneel)

### 1. Clone de repository
```bash
git clone https://github.com/droomvriendje-stack/DroomvriendjeGithubnieuwste.git
cd DroomvriendjeGithubnieuwste
```

### 2. Environment Variables

#### Backend (.env in root of /backend)
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_ANON_KEY=your-anon-key

# Mollie Payments
MOLLIE_API_KEY=live_xxxxx
MOLLIE_PROFILE_ID=pfl_xxxxx

# URLs
FRONTEND_URL=https://droomvriendjes.nl
API_URL=https://api.droomvriendjes.nl
CORS_ORIGINS=https://droomvriendjes.nl

# Email
POSTMARK_API_TOKEN=your-token
SMTP_FROM=info@droomvriendjes.nl

# Sendcloud Shipping
SENDCLOUD_PUBLIC_KEY=your-key
SENDCLOUD_SECRET_KEY=your-secret
```

#### Frontend (.env in /frontend)
```env
REACT_APP_BACKEND_URL=https://api.droomvriendjes.nl
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_ANON_KEY=your-anon-key
```

### 3. Backend starten
```bash
cd backend
pip install -r ../requirements.txt
uvicorn server:app --reload --port 8000
```

### 4. Frontend starten
```bash
cd frontend
yarn install
yarn start
```

### 5. Docker (optioneel)
```bash
docker-compose up
```

## 📁 Project Structuur

```
/
├── backend/
│   ├── server.py          # FastAPI main application
│   ├── routes/            # API endpoints
│   │   ├── products_supabase.py
│   │   ├── orders_supabase.py
│   │   ├── reviews_supabase.py
│   │   └── ...
│   ├── services/          # Business logic
│   └── utils/             # Helpers
├── frontend/
│   ├── src/
│   │   ├── pages/         # React pages
│   │   ├── components/    # Reusable components
│   │   ├── context/       # React context (cart, auth)
│   │   └── hooks/         # Custom hooks
│   └── public/
├── supabase/
│   └── migrations/        # Database schema
├── Dockerfile             # Railway backend
├── docker-compose.yml     # Local development
├── railway.toml           # Railway config
└── requirements.txt       # Python dependencies
```

## 🗄️ Database Schema

De database draait op Supabase (PostgreSQL). Zie `/supabase/migrations/` voor het volledige schema.

### Belangrijkste tabellen:
- `products` - Producten met afbeeldingen, SEO, prijzen
- `orders` - Bestellingen met items, status, betaling
- `customers` - Klantgegevens
- `reviews` - Productbeoordelingen
- `discount_codes` - Kortingscodes
- `email_logs` - Email tracking
- `email_campaigns` - Marketing campagnes

## 🌐 Deployment

### Railway (Backend)

1. **Connect GitHub**
   - Ga naar [railway.app](https://railway.app)
   - New Project → Deploy from GitHub repo

2. **Environment Variables**
   Voeg alle variables uit `/backend/.env` toe in Railway Settings → Variables

3. **Deploy**
   Railway detecteert automatisch de Dockerfile en deployt

4. **Custom Domain**
   Settings → Domains → Add `api.droomvriendjes.nl`

### Cloudflare Pages (Frontend)

1. **Connect GitHub**
   - Ga naar Cloudflare Dashboard → Pages
   - Create Project → Connect to Git

2. **Build Settings**
   ```
   Framework: Create React App
   Build command: yarn build
   Output directory: build
   Root directory: frontend
   ```

3. **Environment Variables**
   ```
   REACT_APP_BACKEND_URL=https://api.droomvriendjes.nl
   REACT_APP_SUPABASE_URL=https://your-project.supabase.co
   REACT_APP_SUPABASE_ANON_KEY=your-key
   ```

4. **Custom Domain**
   Add `droomvriendjes.nl` en `www.droomvriendjes.nl`

### Cloudflare DNS

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| CNAME | @ | Cloudflare Pages URL | ✅ Proxied |
| CNAME | www | Cloudflare Pages URL | ✅ Proxied |
| CNAME | api | Railway URL | ❌ DNS only |

## 🔧 Wijzigingen Maken

### Via GitHub/Cursor
1. Open de repo in [Cursor.sh](https://cursor.sh) of VS Code
2. Maak je wijzigingen
3. Commit en push naar `main`
4. Railway en Cloudflare Pages deployen automatisch

### Via Emergent (niet meer nodig)
Dit project is nu volledig zelfstandig en draait zonder Emergent.

## 📧 Email Marketing

### Campagnes verzenden
1. Ga naar Admin → Email Marketing
2. Upload CSV met contacten
3. Selecteer template
4. Klik "Verstuur"

### Tracking
Open/click tracking is ingebouwd. Bekijk statistieken in Admin → Email Logs.

## 💳 Betalingen

Betalingen worden verwerkt via Mollie. Webhook URL:
```
https://api.droomvriendjes.nl/api/webhook/mollie
```

## 🔑 Kortingscodes

Actieve codes:
- `WELKOM10` - 10% korting voor nieuwe klanten
- `EENMALIG2026` - 10% korting (geldig tot 31-12-2026)

## 📱 WhatsApp Support

WhatsApp knop is alleen zichtbaar op `/contact` pagina.
Nummer: +31 6 84588815

GTM Container: GTM-W9PZRP4B

## 🔍 SEO Keywords

De website is geoptimaliseerd voor:
- slaapknuffel met sterrenprojectie
- slaapknuffel white noise kinderen
- knuffel die helpt met slapen
- slaapknuffel nachtlampje kind
- slaapknuffel cadeau baby shower
- slaapknuffel volwassenen
- kind bang in het donker knuffel

## 🐛 Troubleshooting

### Backend niet bereikbaar
```bash
curl https://api.droomvriendjes.nl/health
```

### CORS errors
Check CORS_ORIGINS in Railway env vars (exact match, geen trailing slash)

### Database problemen
Check Supabase dashboard → Logs

### Frontend build faalt
```bash
cd frontend && yarn build
```

## 📞 Support

- Email: info@droomvriendjes.nl
- WhatsApp: +31 6 84588815

---

*Laatste update: Juli 2025*
*Gemigreerd van Emergent.sh naar zelfstandige hosting*
