# Social Media Listener

A social media monitoring tool that tracks brand mentions, keywords, and conversations across **Bluesky** (with architecture ready for Threads and future platforms).

## Features

- **Keyword Monitoring** - Track any keyword, hashtag, or @mention across social platforms
- **Real-time Collection** - Automated polling with configurable intervals
- **Sentiment Analysis** - Portuguese NLP with LeIA sentiment analyzer
- **Named Entity Recognition** - Extract people, organizations, and locations using spaCy
- **Analytics Dashboard** - Visualize trends, sentiment breakdown, and engagement metrics
- **Multi-listener Support** - Monitor multiple keywords/brands simultaneously

## Screenshots

### Dashboard
- Overview stats (total posts, listeners, entities)
- Sentiment breakdown pie chart
- Posts timeline with sentiment stacking
- Engagement statistics

### Listeners Management
- Create/edit/delete monitoring rules
- Toggle active status
- Manual collection trigger
- New content indicators

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SOCIAL LISTENER                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────┐              ┌─────────────────────────────┐  │
│   │  MANAGEMENT API     │              │     COLLECTOR SERVICE       │  │
│   │  (FastAPI)          │◄────────────►│     (Python)                │  │
│   │  Port 8000          │   Database   │     Port 8001               │  │
│   │                     │              │                             │  │
│   │  • Web Dashboard    │              │  • Bluesky Collector        │  │
│   │  • REST API         │              │  • NLP Pipeline             │  │
│   │  • Swagger Docs     │              │  • Scheduled Polling        │  │
│   └─────────────────────┘              └─────────────────────────────┘  │
│              │                                       │                  │
│              └───────────────┬───────────────────────┘                  │
│                              ▼                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    DATABASE (PostgreSQL)                        │   │
│   │   listeners  │  posts  │  entities  │  post_entities            │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| Web Framework | FastAPI |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 (async) |
| Frontend | Jinja2 + HTMX + Bootstrap 5 |
| Charts | Plotly.js |
| Sentiment Analysis | LeIA (Portuguese) |
| NER | spaCy (pt_core_news_sm) |
| Containers | Docker + Docker Compose |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) Bluesky account for authenticated requests

### 1. Clone and Configure

```bash
git clone https://github.com/yourusername/social-listener.git
cd social-listener

# Copy environment template
cp .env.example .env

# Edit .env with your settings (optional for basic usage)
```

### 2. Start Services

```bash
# Start all containers
docker compose up -d

# View logs
docker compose logs -f
```

### 3. Access the Application

- **Dashboard**: http://localhost:8000/
- **API Documentation**: http://localhost:8000/docs
- **Collector Status**: http://localhost:8001/status

### 4. Create Your First Listener

Via the web interface:
1. Go to http://localhost:8000/listeners
2. Click "New Listener"
3. Enter a name, select platform (Bluesky), rule type, and value
4. Click "Create Listener"

Or via API:
```bash
curl -X POST http://localhost:8000/api/listeners \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Brand Monitor",
    "platform": "bluesky",
    "rule_type": "keyword",
    "rule_value": "your-brand"
  }'
```

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/sociallistener

# Bluesky (optional - for authenticated requests)
BLUESKY_HANDLE=your-handle.bsky.social
BLUESKY_APP_PASSWORD=your-app-password

# Collector Settings
BLUESKY_POLL_INTERVAL=120  # seconds

# NLP Settings
ENABLE_NLP=true
```

## API Endpoints

### Listeners
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/listeners` | List all listeners |
| POST | `/api/listeners` | Create new listener |
| GET | `/api/listeners/{id}` | Get listener details |
| PUT | `/api/listeners/{id}` | Update listener |
| DELETE | `/api/listeners/{id}` | Delete listener |
| POST | `/api/listeners/{id}/toggle` | Toggle active status |
| POST | `/api/listeners/{id}/collect` | Trigger manual collection |

### Posts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/posts` | List posts (paginated) |
| GET | `/api/posts/{id}` | Get post details |
| GET | `/api/listeners/{id}/posts` | Posts for specific listener |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/overview` | Dashboard statistics |
| GET | `/api/analytics/sentiment` | Sentiment breakdown |
| GET | `/api/analytics/timeline` | Posts over time |
| GET | `/api/analytics/engagement` | Engagement metrics |

### Entities
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/entities` | List extracted entities |
| GET | `/api/entities/top` | Top entities by occurrence |
| GET | `/api/entities/types` | Entity type distribution |

## Development

### Project Structure

```
social-listener/
├── docker-compose.yml
├── .env.example
├── README.md
├── PLAN.md
│
├── api/                        # Management API
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── models/             # SQLAlchemy models
│       ├── schemas/            # Pydantic schemas
│       ├── routes/             # API endpoints
│       ├── templates/          # Jinja2 templates
│       └── static/             # CSS, JS assets
│
├── collector/                  # Data Collection Service
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── collectors/         # Platform collectors
│       ├── nlp/                # NLP processors
│       └── scheduler.py
│
└── scripts/
    └── init.sql               # Database initialization
```

### Useful Commands

```bash
# Rebuild after code changes
docker compose up -d --build

# View specific service logs
docker compose logs -f api
docker compose logs -f collector

# Access database
docker compose exec db psql -U postgres sociallistener

# Stop all services
docker compose down

# Full reset (removes data)
docker compose down -v
```

## Roadmap

- [x] Bluesky collector with keyword/hashtag/mention search
- [x] NLP pipeline (sentiment + NER) for Portuguese
- [x] Web dashboard with analytics
- [x] Listener management UI
- [ ] Threads platform integration
- [ ] Export functionality (CSV/JSON)
- [ ] Multi-user authentication
- [ ] Email/Slack notifications

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read the [PLAN.md](PLAN.md) for architecture details and development guidelines.
