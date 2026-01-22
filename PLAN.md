# Social Media Listener - Project Plan

> **Project Codename:** social-listener  
> **Version:** 0.1.0 (MVP)  
> **Last Updated:** January 2026  
> **Author:** Chris 

---

## 1. Project Vision

### 1.1 What We're Building

A social media monitoring tool that tracks brand mentions, keywords, and conversations across **Threads** and **Bluesky** (with architecture ready for future platforms).

### 1.2 Marketing Pitch (For Reference)

> **See when your brand gets name-dropped**  
> Users don't always tag you. With keyword and mention monitoring, you can catch every brand reference, even if it's subtle or indirect.
>
> **Monitor your brand's voice and how it lands**  
> Keep tabs on your own Threads activity, from what you post to how people react—you'll always know how your content performs.
>
> **Analyze your brand's impact**  
> Once you've collected the data, export it to unlock metrics like total posts, top authors, common hashtags, keyword usage, and sentiment breakdown.

### 1.3 Core Principles

1. **Simplicity first** - Start minimal, evolve incrementally
2. **No server-side JavaScript** - Python all the way
3. **Unified behavior** - Both platforms work the same way (polling model)
4. **Container-ready** - Docker from day one for easy deployment
5. **Future-proof** - Architecture supports multi-user and more platforms

### 1.4 Development Order

1. **Bluesky first** - No OAuth bureaucracy, faster iteration
2. **End-to-end before expansion** - Complete flow working before adding Threads
3. **NLP before Threads** - Sentiment & NER integrated with Bluesky first

---

## 2. Platform API Analysis

### 2.1 Threads (Meta Official API)

| Feature | Status | Notes |
|---------|--------|-------|
| Keyword Search | Available | 500 queries per 7-day rolling window (~70/day) |
| Mentions Retrieval | Available | Public posts that mention authenticated account |
| Webhooks | Partial | Only for reply events, not general mentions |
| Analytics | Available | Views, likes, replies, reposts, shares, clicks |
| Rate Limits | Strict | 250 posts/day, 1000 replies/day for publishing |
| Auth Required | Yes | Meta Business account + OAuth + App Review |

**API Endpoints We'll Use:**
- `GET /threads_search` - Search public posts by keyword
- `GET /{user-id}/threads` - Get user's own posts
- `GET /{user-id}/replies` - Get replies to user's posts
- `GET /{media-id}/insights` - Get engagement metrics

**Key Limitations:**
- Must complete Meta App Review process
- Business account verification required
- Search queries are precious (budget them wisely)

### 2.2 Bluesky (AT Protocol)

| Feature | Status | Notes |
|---------|--------|-------|
| Firehose | Available | Real-time stream of ALL posts (~1000+ events/sec) |
| Jetstream | Available | Simplified JSON stream (easier than raw firehose) |
| Search API | Available | `app.bsky.feed.searchPosts` endpoint |
| Auth for Reading | Not Required | Can read public data anonymously |
| Rate Limits | Generous | Especially for reading operations |

**API Endpoints We'll Use:**
- `app.bsky.feed.searchPosts` - Search posts by keyword
- `app.bsky.actor.getProfile` - Get user profile info
- `app.bsky.feed.getPostThread` - Get post with replies

**Key Advantages:**
- No authentication needed for public data
- No strict rate limits for reading
- Can poll more frequently than Threads

### 2.3 Unified Polling Strategy

Even though Bluesky offers real-time firehose, we'll use **polling for both platforms** to maintain:
- Consistent behavior and code structure
- Simpler mental model
- Easier debugging and monitoring
- Same data freshness guarantees

| Platform | Poll Frequency | Rationale |
|----------|---------------|-----------|
| Threads | Every 15 minutes | Preserve API quota (70 searches/day = ~4/hour) |
| Bluesky | Every 2-5 minutes | No strict limits, can be more aggressive |

---

## 3. Architecture

### 3.1 High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SOCIAL LISTENER                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────┐              ┌─────────────────────────────┐  │
│   │  MANAGEMENT API     │              │     COLLECTOR SERVICE       │  │
│   │  (FastAPI Container)│◄────────────►│     (Python Container)      │  │
│   │                     │   Database   │                             │  │
│   │  • Swagger at /docs │              │  ┌───────────────────────┐  │  │
│   │  • CRUD listeners   │              │  │  Bluesky Collector    │  │  │
│   │  • View posts       │              │  │  (Poll every 2 min)   │  │  │
│   │  • Analytics/Export │              │  └───────────────────────┘  │  │
│   │  • Health checks    │              │                             │  │
│   │                     │              │  ┌───────────────────────┐  │  │
│   └──────────┬──────────┘              │  │  Threads Collector    │  │  │
│              │                         │  │  (Poll every 15 min)  │  │  │
│              │                         │  │  [Phase 4]            │  │  │
│              │                         │  └───────────────────────┘  │  │
│              │                         │                             │  │
│              │                         │  ┌───────────────────────┐  │  │
│              │                         │  │  NLP Processor        │  │  │
│              │                         │  │ • Sentiment (TextBlob)│  │  │
│              │                         │  │ • NER (spaCy)         │  │  │
│              │                         │  │  [Phase 2]            │  │  │
│              │                         │  └───────────────────────┘  │  │
│              │                         │                             │  │
│              │                         └─────────────┬───────────────┘  │
│              │                                       │                  │
│              ▼                                       ▼                  │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    DATABASE (PostgreSQL Container)              │   │
│   │                                                                 │   │
│   │   listeners    posts    entities    post_entities               │   │
│   │                                                                 │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Container Architecture

```yaml
# docker-compose.yml structure
services:
  db:          # PostgreSQL 15
  api:         # FastAPI Management Interface (port 8000)
  collector:   # Polling + NLP Processing
```

### 3.3 Component Responsibilities

| Component | Container | Responsibilities |
|-----------|-----------|------------------|
| **Database** | `db` | Store all data, fast inserts, indexed queries |
| **Management API** | `api` | REST API, Swagger docs, serve simple UI |
| **Collector** | `collector` | Poll APIs, run NLP, store posts |

---

## 4. Data Model

### 4.1 Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌──────────────┐       ┌─────────────┐
│  listeners  │──1:N──│    posts    │──M:N──│ post_entities│──N:1──│  entities   │
└─────────────┘       └─────────────┘       └──────────────┘       └─────────────┘
```

### 4.2 Core Tables

```sql
-- Monitoring rules created by users
CREATE TABLE listeners (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    platform        VARCHAR(50) NOT NULL,  -- 'threads' | 'bluesky' | 'all'
    rule_type       VARCHAR(50) NOT NULL,  -- 'keyword' | 'mention' | 'hashtag'
    rule_value      VARCHAR(500) NOT NULL, -- The actual keyword/handle to monitor
    is_active       BOOLEAN DEFAULT true,
    has_new_content BOOLEAN DEFAULT false, -- Flag for "new content available"
    poll_frequency  INTEGER DEFAULT 300,   -- Seconds between polls
    last_polled_at  TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Collected posts from social platforms
CREATE TABLE posts (
    id                  SERIAL PRIMARY KEY,
    listener_id         INTEGER REFERENCES listeners(id) ON DELETE CASCADE,
    platform            VARCHAR(50) NOT NULL,      -- 'threads' | 'bluesky'
    platform_post_id    VARCHAR(255) NOT NULL,     -- Original post ID from platform
    author_handle       VARCHAR(255),
    author_display_name VARCHAR(255),
    author_avatar_url   TEXT,
    content             TEXT,
    post_url            TEXT,
    
    -- Engagement metrics (explicit columns, not JSON)
    likes_count         INTEGER DEFAULT 0,
    replies_count       INTEGER DEFAULT 0,
    reposts_count       INTEGER DEFAULT 0,
    quotes_count        INTEGER DEFAULT 0,
    views_count         INTEGER DEFAULT 0,
    shares_count        INTEGER DEFAULT 0,
    clicks_count        INTEGER DEFAULT 0,
    
    -- NLP Analysis results
    sentiment_score     FLOAT,                     -- -1.0 to 1.0
    sentiment_label     VARCHAR(50),               -- 'positive' | 'negative' | 'neutral'
    
    post_created_at     TIMESTAMP,                 -- When post was made on platform
    collected_at        TIMESTAMP DEFAULT NOW(),   -- When we collected it
    
    UNIQUE(platform, platform_post_id)             -- Prevent duplicates
);

-- Named entities (deduplicated, reusable across posts)
-- Example: "Apple" as ORG appears once, linked to many posts
CREATE TABLE entities (
    id              SERIAL PRIMARY KEY,
    entity_type     VARCHAR(100) NOT NULL,  -- 'PERSON' | 'ORG' | 'PRODUCT' | 'LOCATION' | etc.
    entity_text     VARCHAR(500) NOT NULL,  -- Normalized text (e.g., "Apple Inc." -> "apple")
    display_text    VARCHAR(500) NOT NULL,  -- Original text as found
    created_at      TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(entity_type, entity_text)        -- One entity per type+text combination
);

-- Junction table: M:N relationship between posts and entities
CREATE TABLE post_entities (
    id          SERIAL PRIMARY KEY,
    post_id     INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    entity_id   INTEGER REFERENCES entities(id) ON DELETE CASCADE,
    confidence  FLOAT,                      -- NER confidence score
    start_pos   INTEGER,                    -- Position in post content
    end_pos     INTEGER,
    created_at  TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(post_id, entity_id, start_pos)   -- Same entity can appear multiple times in a post
);

-- Indexes for common queries
CREATE INDEX idx_posts_listener ON posts(listener_id);
CREATE INDEX idx_posts_platform ON posts(platform);
CREATE INDEX idx_posts_collected_at ON posts(collected_at DESC);
CREATE INDEX idx_posts_sentiment ON posts(sentiment_label);
CREATE INDEX idx_posts_author ON posts(author_handle);
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_text ON entities(entity_text);
CREATE INDEX idx_post_entities_post ON post_entities(post_id);
CREATE INDEX idx_post_entities_entity ON post_entities(entity_id);
```

### 4.3 Credentials Strategy

**Decision:** All credentials in `.env` file, NOT in database.

| Credential | Storage | Rationale |
|------------|---------|-----------|
| Bluesky handle/password | `.env` | Static, rarely changes |
| Threads App ID/Secret | `.env` | Static, should never be in DB |
| Threads OAuth tokens | `.env` or `credentials.json` | Dynamic but can be file-based |

**For MVP:** Everything in `.env`. When Threads OAuth is added, we'll evaluate if a `credentials.json` file is needed for token refresh persistence.

**Why not database for credentials?**
- Separation of concerns (config vs data)
- Easier secrets management in production (K8s secrets, Docker secrets)
- No risk of credential exposure through API bugs
- Simpler backup/restore (don't need to worry about sensitive data in dumps)

---

## 5. Technology Stack

### 5.1 Core Technologies

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Language** | Python 3.11+ | Your preference, excellent ML libraries |
| **Web Framework** | FastAPI | Async, auto Swagger docs, Pydantic validation |
| **ORM** | SQLAlchemy 2.0 | Powerful, async support, good PostgreSQL support |
| **Database** | PostgreSQL | Fast inserts, scales well, proper column types |
| **Task Scheduling** | APScheduler | Built-in, no external dependencies |
| **HTTP Client** | httpx | Modern, async-capable, clean API |
| **Containers** | Docker + Compose | Easy deployment, consistent environments |
| **Validation** | Pydantic v2 | Typed schemas, auto-serialization |

### 5.2 FastAPI Features We'll Use

```python
# Auto-generated Swagger docs at /docs
# Auto-generated ReDoc at /redoc
# Typed request/response models with Pydantic

from pydantic import BaseModel
from datetime import datetime

class ListenerCreate(BaseModel):
    name: str
    platform: Literal["threads", "bluesky", "all"]
    rule_type: Literal["keyword", "mention", "hashtag"]
    rule_value: str

class ListenerResponse(BaseModel):
    id: int
    name: str
    platform: str
    rule_type: str
    rule_value: str
    is_active: bool
    has_new_content: bool
    created_at: datetime
    
    class Config:
        from_attributes = True  # For SQLAlchemy model conversion
```

### 5.3 NLP Libraries

**MVP (Lighter alternatives for faster iteration):**

| Task | Library | Model | Notes |
|------|---------|-------|-------|
| **Sentiment** | TextBlob | Built-in | Fast, good enough for MVP |
| **NER** | spaCy | `en_core_web_sm` | Small model, quick loading |

**Production (after MVP works):**

| Task | Library | Model | Notes |
|------|---------|-------|-------|
| **Sentiment** | transformers | `cardiffnlp/twitter-roberta-base-sentiment-latest` | Better accuracy for social media |
| **NER** | spaCy | `en_core_web_lg` or transformer-based | More entity types |

### 5.4 NLP Model Loading Strategy

**Problem:** NLP models are heavy (100MB-1GB). Loading them per-request would be disastrous.

**Solution:** FastAPI's lifespan context manager - load ONCE at startup, inject via dependencies.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends

# Global state holder
class NLPModels:
    sentiment_analyzer = None
    ner_model = None

nlp_models = NLPModels()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models at startup, cleanup at shutdown."""
    print("Loading NLP models...")
    
    # Load sentiment analyzer (TextBlob is instant, transformers take ~5-10s)
    from textblob import TextBlob
    nlp_models.sentiment_analyzer = TextBlob  # Class reference, not instance
    
    # Load spaCy NER model
    import spacy
    nlp_models.ner_model = spacy.load("en_core_web_sm")
    
    print("NLP models loaded!")
    yield
    
    # Cleanup (if needed)
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

# Dependency injection for routes
def get_sentiment_analyzer():
    return nlp_models.sentiment_analyzer

def get_ner_model():
    return nlp_models.ner_model

# Usage in routes
@app.post("/api/posts/{post_id}/analyze")
async def analyze_post(
    post_id: int,
    sentiment: TextBlob = Depends(get_sentiment_analyzer),
    ner = Depends(get_ner_model)
):
    # Models are already loaded, instant access
    pass
```

**Benefits over Singletons:**
- Explicit lifecycle management
- Proper async support
- Testable (can mock dependencies)
- FastAPI-idiomatic

### 5.5 Platform SDKs

| Platform | Library | Notes |
|----------|---------|-------|
| **Threads** | `httpx` (direct API) | No official Python SDK |
| **Bluesky** | `atproto` | Official AT Protocol SDK |

---

## 6. API Endpoints (Management Interface)

> All endpoints auto-documented via Swagger UI at `/docs`

### 6.1 Listeners

```
GET    /api/listeners              # List all listeners
POST   /api/listeners              # Create new listener
GET    /api/listeners/{id}         # Get listener details
PUT    /api/listeners/{id}         # Update listener
DELETE /api/listeners/{id}         # Delete listener
POST   /api/listeners/{id}/toggle  # Toggle active status
POST   /api/listeners/{id}/ack     # Acknowledge new content (clear flag)
```

### 6.2 Posts

```
GET    /api/posts                       # List posts (paginated, filterable)
GET    /api/posts/{id}                  # Get post details with entities
GET    /api/listeners/{id}/posts        # Get posts for specific listener
DELETE /api/posts/{id}                  # Delete specific post
POST   /api/posts/{id}/analyze          # Re-run NLP analysis on a post
```

### 6.3 Entities

```
GET    /api/entities                    # List all unique entities
GET    /api/entities/{id}               # Get entity with related posts
GET    /api/entities/top                # Top entities by occurrence
```

### 6.4 Analytics

```
GET    /api/analytics/overview          # Dashboard stats
GET    /api/analytics/sentiment         # Sentiment breakdown
GET    /api/analytics/entities          # Top entities by type
GET    /api/analytics/authors           # Top authors
GET    /api/analytics/timeline          # Posts over time
GET    /api/export                      # Export data as CSV/JSON
```

### 6.5 System

```
GET    /api/health                      # Health check
GET    /api/platforms/status            # Platform connection status
```

### 6.6 Response Models (Pydantic)

```python
# All responses are typed and validated

class PostResponse(BaseModel):
    id: int
    platform: str
    platform_post_id: str
    author_handle: str | None
    author_display_name: str | None
    content: str | None
    post_url: str | None
    likes_count: int
    replies_count: int
    reposts_count: int
    sentiment_score: float | None
    sentiment_label: str | None
    post_created_at: datetime | None
    collected_at: datetime
    entities: list[EntityBrief] = []

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
```

---

## 7. Development Phases

### Phase 1: Foundation (MVP) - COMPLETE

**Goal:** Basic working system with one platform

**Deliverables:**
- [x] Project structure and Docker setup
- [x] Database schema (auto-created via SQLAlchemy)
- [x] Bluesky collector (authenticated, keyword/hashtag/mention search)
- [x] Basic FastAPI API (CRUD for listeners, posts)
- [x] Simple capture storage with deduplication
- [ ] Basic HTML interface (deferred to Phase 4)

**Timeline:** 1 session (done)

### Phase 2: Threads Integration

**Goal:** Add Threads platform support

**Deliverables:**
- [ ] Threads API client
- [ ] OAuth flow for Threads authentication
- [ ] Unified collector interface (both platforms)
- [ ] Platform credential management

**Timeline:** 1-2 sessions

### Phase 3: NLP Pipeline - COMPLETE

**Goal:** Add sentiment analysis and entity extraction

**Deliverables:**
- [x] Sentiment analysis integration (LeIA - Portuguese)
- [x] NER pipeline (spaCy pt_core_news_sm)
- [x] Entity storage and querying (with deduplication)
- [x] Inline processing during collection
- [x] NLP error tracking (failsafe, non-blocking)

**Timeline:** 1 session (done)

### Phase 4: Analytics & UI - MOSTLY COMPLETE

**Goal:** Rich analytics and improved interface

**Deliverables:**
- [x] Analytics endpoints (overview, sentiment, timeline, authors, engagement)
- [x] Dashboard with Plotly charts (sentiment pie, timeline bar chart)
- [x] Listener management UI (create, edit, delete, toggle, collect)
- [x] Posts browser with filters and pagination
- [x] Entities explorer with type/listener filters
- [x] Dashboard listener filter (multi-select)
- [x] "New content" flag system
- [ ] Export functionality (CSV/JSON)

**Timeline:** 1-2 sessions

### Phase 5: Production Readiness

**Goal:** Ready for real deployment

**Deliverables:**
- [ ] Multi-user authentication
- [ ] Rate limiting and quotas
- [ ] Logging and monitoring
- [ ] Error handling and retries
- [ ] Documentation

**Timeline:** 1-2 sessions

---

## 8. Project Structure

```
social-listener/
├── docker-compose.yml
├── .env.example
├── README.md
├── PLAN.md                          # This file
│
├── api/                             # Management Interface (FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                     # Database migrations
│   │   ├── versions/
│   │   └── env.py
│   ├── alembic.ini
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app + lifespan
│   │   ├── config.py                # Settings from .env
│   │   ├── database.py              # SQLAlchemy async setup
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── listener.py
│   │   │   ├── post.py
│   │   │   └── entity.py
│   │   ├── schemas/                 # Pydantic schemas (typed!)
│   │   │   ├── __init__.py
│   │   │   ├── listener.py
│   │   │   ├── post.py
│   │   │   ├── entity.py
│   │   │   └── analytics.py
│   │   ├── routes/                  # API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── listeners.py
│   │   │   ├── posts.py
│   │   │   ├── entities.py
│   │   │   └── analytics.py
│   │   ├── services/                # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── listener_service.py
│   │   │   └── post_service.py
│   │   └── templates/               # Jinja2 templates (simple UI)
│   │       ├── base.html
│   │       ├── dashboard.html
│   │       ├── listeners.html
│   │       └── posts.html
│   └── run.py
│
├── collector/                       # Data Collection Service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # Entry point + scheduler
│   │   ├── config.py
│   │   ├── database.py              # Shared DB connection
│   │   ├── collectors/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Abstract collector interface
│   │   │   ├── bluesky.py           # Bluesky implementation
│   │   │   └── threads.py           # Threads implementation (Phase 4)
│   │   ├── nlp/
│   │   │   ├── __init__.py
│   │   │   ├── processor.py         # Main NLP orchestrator
│   │   │   ├── sentiment.py         # Sentiment analysis
│   │   │   └── ner.py               # Named Entity Recognition
│   │   └── scheduler.py             # APScheduler setup
│   └── run.py
│
└── scripts/
    ├── init_db.py                   # Initialize database
    ├── seed_data.py                 # Sample data for testing
    └── test_bluesky.py              # Quick API test script
```

---

## 9. Configuration

### 9.1 Environment Variables

```bash
# .env file
# Copy from .env.example and fill in your values

# ===================
# DATABASE
# ===================
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/sociallistener

# ===================
# BLUESKY (optional - only needed for authenticated actions)
# ===================
# For MVP, we only read public data, so these are optional
BLUESKY_HANDLE=
BLUESKY_APP_PASSWORD=

# ===================
# THREADS (Phase 4 - leave empty for now)
# ===================
THREADS_APP_ID=
THREADS_APP_SECRET=
THREADS_ACCESS_TOKEN=
THREADS_REDIRECT_URI=http://localhost:8000/auth/threads/callback

# ===================
# COLLECTOR SETTINGS
# ===================
# Poll intervals in seconds
THREADS_POLL_INTERVAL=900      # 15 minutes (preserve API quota)
BLUESKY_POLL_INTERVAL=120      # 2 minutes (no strict limits)

# ===================
# NLP SETTINGS
# ===================
# Models loaded at startup
SENTIMENT_MODEL=textblob                    # MVP: textblob | PROD: cardiffnlp/twitter-roberta-base-sentiment-latest
NER_MODEL=en_core_web_sm                    # MVP: en_core_web_sm | PROD: en_core_web_lg
ENABLE_NLP=true                             # Set to false to skip NLP processing

# ===================
# API SETTINGS
# ===================
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
SECRET_KEY=change-me-in-production

# ===================
# LOGGING
# ===================
LOG_LEVEL=INFO                              # DEBUG | INFO | WARNING | ERROR
```

### 9.2 Configuration Validation (Pydantic Settings)

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str
    
    # Bluesky
    bluesky_handle: str = ""
    bluesky_app_password: str = ""
    
    # Threads (Phase 4)
    threads_app_id: str = ""
    threads_app_secret: str = ""
    threads_access_token: str = ""
    
    # Collector
    threads_poll_interval: int = 900
    bluesky_poll_interval: int = 120
    
    # NLP
    sentiment_model: str = "textblob"
    ner_model: str = "en_core_web_sm"
    enable_nlp: bool = True
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    secret_key: str = "change-me"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

---

## 10. Future Roadmap

### 10.1 Planned Features (Post-MVP)

| Feature | Priority | Phase |
|---------|----------|-------|
| Multi-user authentication | High | Phase 5 |
| Email/Slack notifications | Medium | Phase 6 |
| Competitor tracking | Medium | Phase 6 |
| Historical data import | Low | Phase 7 |
| AI-powered insights (LLM summaries) | Low | Phase 7 |
| Mobile app | Low | Phase 8 |

### 10.1.1 TODO - Small Improvements

- [x] **Bluesky pagination**: Implemented cursor-based pagination
  - Initial scrape: up to 500 posts with pagination
  - Regular scrapes: 100 posts (API max, single request)
  - Tracked via `initial_scrape_completed` field on Listener
- [ ] **Reprocess endpoint**: Add `POST /posts/reprocess` to re-run NLP on existing posts
- [x] **Listener update endpoint**: Add `PUT /listeners/{id}` to update listener settings
- [x] **Manual collection trigger**: Add `POST /listeners/{id}/collect` to trigger collection from UI
- [ ] **Language detection + multi-language NLP**: Detect post language and use appropriate models
  - Use `langdetect` or `lingua` for language detection
  - Load multiple spaCy models (en, pt, es, etc.)
  - Route to correct model based on detected language
  - Store detected language in posts table
- [ ] **Filter noisy NER entities**: Clean up false positives from spaCy
  - Skip @handles being detected as LOC
  - Filter out currency symbols (R$)
  - Skip common words misclassified as ORG/LOC
  - Add minimum entity length filter
  - Consider entity type whitelist per context
- [ ] **Export functionality**: Add CSV/JSON export for posts and analytics

### 10.2 Platform Expansion

| Platform | Difficulty | Notes |
|----------|------------|-------|
| **Mastodon** | Easy | ActivityPub, similar to Bluesky |
| **X/Twitter** | Hard | API access expensive, limited |
| **LinkedIn** | Medium | Limited API, business focus |
| **Reddit** | Medium | Good API, different content type |

### 10.3 Scaling Considerations

When volume grows:

1. **Database:** 
   - Add connection pooling (pgbouncer)
   - Consider TimescaleDB for time-series optimization
   - Partitioning by date for posts table

2. **Collector:** 
   - Split into separate containers per platform
   - Add Redis/RabbitMQ for job queue
   - Horizontal scaling for high-volume listeners

3. **API:**
   - Add Redis for response caching
   - Rate limiting per user/IP
   - Read replicas for analytics queries

4. **Search:** 
   - Add Elasticsearch/Meilisearch for full-text search
   - Semantic search with embeddings (future)

---

## 11. Quick Reference

### 11.1 Key Commands

```bash
# Start development environment
docker-compose up -d

# Start with rebuild (after code changes)
docker-compose up -d --build

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f collector
docker-compose logs -f api

# Stop everything
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v

# Run database migrations
docker-compose exec api alembic upgrade head

# Create new migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Access database directly
docker-compose exec db psql -U postgres sociallistener

# Access API container shell
docker-compose exec api bash
```

### 11.2 API Quick Test

```bash
# Health check
curl http://localhost:8000/api/health

# Swagger docs (open in browser)
open http://localhost:8000/docs

# Create a listener
curl -X POST http://localhost:8000/api/listeners \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Brand Monitor",
    "platform": "bluesky",
    "rule_type": "keyword",
    "rule_value": "myproduct"
  }'

# List all listeners
curl http://localhost:8000/api/listeners

# List posts for a listener
curl "http://localhost:8000/api/listeners/1/posts?limit=10"

# List all posts (paginated)
curl "http://localhost:8000/api/posts?page=1&page_size=20"

# Get analytics overview
curl http://localhost:8000/api/analytics/overview
```

### 11.3 Useful Links

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Bluesky API Docs](https://docs.bsky.app/)
- [AT Protocol Python SDK](https://atproto.blue/)
- [Threads API Docs](https://developers.facebook.com/docs/threads) (Phase 4)
- [Meta App Dashboard](https://developers.facebook.com/apps/) (Phase 4)
- [spaCy Models](https://spacy.io/models)
- [TextBlob Docs](https://textblob.readthedocs.io/)

---

## 12. Session Notes

> Use this section to track progress across sessions

### Session 1 - January 2026 (Planning)
- [x] Initial planning completed
- [x] Architecture decisions made
- [x] Tech stack finalized (FastAPI, PostgreSQL, SQLAlchemy 2.0)
- [x] Data model designed (posts, entities M:N relationship)
- [x] Development phases defined

### Session 2 - January 22, 2026 (Collector Service)
- [x] Project structure created (`collector/`, `api/`, `scripts/`)
- [x] Docker Compose setup (PostgreSQL + Collector containers)
- [x] Database models implemented (Listener, Post, Entity, PostEntity)
- [x] Collector service with FastAPI endpoints:
  - `GET /health` - Health check
  - `GET /status` - Scheduler status
  - `POST /collect/bluesky` - Manual collection trigger
  - `POST /collect/bluesky/test` - Test Bluesky connection
  - `GET /listeners` - List listeners
  - `POST /listeners` - Create listener
  - `GET /listeners/{id}` - Get listener
  - `DELETE /listeners/{id}` - Delete listener
  - `GET /posts` - List collected posts
  - `GET /posts/{id}` - Get specific post
- [x] Bluesky collector implemented with:
  - Keyword search
  - Hashtag search (prepends #)
  - Mention search (@handle)
  - Post deduplication (upsert on conflict)
  - Engagement metrics update on re-collection
- [x] APScheduler integration for automatic polling
- [x] Fixed timezone-aware datetime handling for PostgreSQL
- [x] Tested end-to-end: 62+ posts collected successfully
- [x] NLP Pipeline integration (sentiment + NER)
- [x] Portuguese NLP models:
  - Sentiment: LeIA (Portuguese VADER adaptation, lexicon-based)
  - NER: spaCy `pt_core_news_sm`
- [x] NLP error handling (failsafe, logs to `nlp_error` column)
- [x] Entity deduplication with M:N linking
- [x] Management API (`api/` container) with Swagger UI:
  - Listeners CRUD + toggle/acknowledge
  - Posts with pagination and filtering
  - Entities with top occurrences
  - Analytics: overview, sentiment, timeline, authors, engagement
- [x] Database init script (`scripts/init.sql`)
- **Active listeners:** Lula Oficial, Netflix Brasil
- **Stats:** 100 posts, 187 entities, sentiment analysis working

### Session 3 - January 22, 2026 (Frontend UI)
- [x] Jinja2 + HTMX + Bootstrap 5 frontend setup
- [x] Plotly.js chart integration
- [x] Dashboard page with:
  - Stats cards (posts, listeners, entities, posts today)
  - Sentiment breakdown pie chart
  - Posts timeline bar chart (stacked by sentiment)
  - Engagement stats section
  - Multi-select listener filter
- [x] Listeners management page with:
  - Table view with status badges
  - Create/Edit/Delete functionality
  - Toggle active status
  - Manual "Collect Now" trigger
  - New content indicators
- [x] Posts browser with:
  - Pagination
  - Filter by listener, sentiment, search
  - Post cards with author, content, sentiment badge
- [x] Entities explorer with:
  - Entity type distribution pie chart
  - Top entities table
  - Filter by listener and entity type
- [x] Fixed timeline API (reuse date_col expression for GROUP BY)
- [x] Fixed Portuguese NER labels (PER, ORG, LOC, MISC)
- [x] API proxy for collector service (trigger collection from UI)
- [x] Multi-listener filter support in analytics endpoints

### Session 4 - January 22, 2026 (Refinements)
- [x] Dashboard date range filter (7, 14, 30, 60, 90, 180 days + All time)
- [x] Date filter applies to ALL dashboard components (overview, sentiment, timeline, engagement)
- [x] Fixed "Posts Today" to use post_created_at instead of collected_at
- [x] Posts page pagination with page numbers and navigation
- [x] Fixed posts page filters (sentiment_label, page_size params)
- [x] Bluesky pagination for initial scrape:
  - First scrape: up to 500 posts with cursor pagination
  - Subsequent scrapes: 100 posts (API max, no pagination)
  - Added `initial_scrape_completed` field to Listener model
- [x] Fixed timeline chart x-axis clipping (use Date objects instead of strings)
- [x] Timeline now properly handles "All time" with type: 'date' axis
- **Stats:** 1002 posts, 1540 entities, 2 active listeners

### Session 5 - [Date]
- [ ] Export functionality (CSV/JSON)
- [ ] Threads platform integration
- [ ] ...

---

## 13. Key Decisions Log

| Decision | Choice | Rationale | Date |
|----------|--------|-----------|------|
| Web framework | FastAPI | Async, auto Swagger, typed | Jan 2026 |
| Database | PostgreSQL | Reliable, good for structured data | Jan 2026 |
| Credentials storage | `.env` only | Security, separation of concerns | Jan 2026 |
| Engagement columns | Explicit columns | No JSON blobs, easier queries | Jan 2026 |
| Entity relationship | M:N | Same entity in multiple posts | Jan 2026 |
| Dev order | Bluesky first | No OAuth bureaucracy | Jan 2026 |
| NLP loading | FastAPI lifespan | Load once at startup | Jan 2026 |
| NLP MVP models | LeIA + spaCy pt | Portuguese support, lighter models | Jan 2026 |
| Frontend stack | Jinja2 + HTMX + Bootstrap 5 | Server-rendered, no JS framework | Jan 2026 |
| Charts | Plotly.js | Interactive, easy to use, no build step | Jan 2026 |

---

*This document is the single source of truth for the Social Listener project. Update it as decisions are made and features are completed.*
