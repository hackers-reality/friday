---
name: code_gen
description: Use this skill when generating code in ANY programming language — write complete, production-quality code, not snippets
---

# Advanced Code Generation Skill

## Overview

FRIDAY generates production-quality code in ANY programming language. Code is complete, tested, documented, and follows best practices. There is NO line limit — FRIDAY writes as many lines as needed (single files can be 20k+ lines).

**IMPORTANT: Before generating code, the agent MUST read this skill file and follow its instructions. Read any other relevant skill files (e.g., svg, chart, docx) if the code involves those domains.**

**ABSOLUTE RULE: The Plan→Build two-phase workflow is MANDATORY for any code generation task. Never skip Phase 1 (Plan). Never generate code without first presenting a plan.**

## Triggers

- "write code", "create a script", "build an app", "implement"
- "program", "function", "class", "module", "library"
- "API", "CLI", "GUI", "web app", "microservice"
- "refactor", "rewrite", "convert to [language]"
- "generate [language] code", "port to [language]"
- ANY coding-related request in ANY language

---

## Phase 1: Plan (MANDATORY — NEVER SKIP)

Before writing a single line of code, FRIDAY MUST complete this planning phase thoroughly. Present the plan to the user and get explicit approval before proceeding.

### Step 1: Requirements Analysis

1. Parse the user's request and identify all explicit requirements
2. Ask clarifying questions about any ambiguity — do not assume
3. Identify implicit requirements the user may not have stated
4. Determine the scope: is this a utility, module, application, or system?
5. List all functional requirements (what the code must do)
6. List all non-functional requirements (performance, security, scalability)
7. Identify constraints: platform, budget (time), dependencies, team size

### Step 2: Technology Selection

Choose the optimal language, framework, and libraries based on:

```
CRITERIA                   WEIGHT (1-5)
Task suitability           5
Team expertise             4
Ecosystem maturity         4
Performance needs          3
Deployment environment     3
Long-term maintainability  4
Security considerations    4
```

For each selection, justify why each choice was made over alternatives.

### Step 3: Architecture Design

1. Define the system architecture pattern (see Architecture Patterns section)
2. Design the module/component breakdown
3. Define interfaces between components (APIs, events, messages)
4. Design the data model (entities, relationships, storage)
5. Plan the data flow (how data moves through the system)
6. Identify cross-cutting concerns: auth, logging, error handling, monitoring
7. Create a folder/file structure diagram

Output format:
```
## Architecture Plan

### Pattern
[Selected pattern and justification]

### Components
- `src/auth/` — Authentication module
- `src/api/` — REST API handlers
- `src/db/` — Database access layer

### Data Flow
[ASCII diagram or description of request→response flow]

### File Structure
project/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ...
├── tests/
├── docs/
└── README.md
```

### Step 4: Risk Assessment

1. Identify technical risks (e.g., "library X has no Windows support")
2. Identify security risks (e.g., "handling PII data requires encryption")
3. Identify scalability risks (e.g., "this approach doesn't handle 10k+ QPS")
4. Plan mitigations for each risk

### Step 5: Get Approval

Present the plan to the user and wait for explicit approval. Include:

- Summary of what will be built
- Key technology choices
- File/module structure
- Estimated lines of code per file
- Risks and mitigations

**Do NOT proceed to Phase 2 without user approval on complex tasks.**

---

## Phase 2: Build (Execution)

Once the plan is approved, execute with these rules:

### Step 1: Project Scaffolding

1. Create the directory structure matching the plan
2. Initialize language-specific project files:
   - `package.json` for JS/TS
   - `Cargo.toml` for Rust
   - `go.mod` for Go
   - `requirements.txt` / `pyproject.toml` for Python
   - `pom.xml` / `build.gradle` for Java
3. Set up version control (.gitignore appropriate for language)
4. Create configuration files (.env.example, config.yaml, etc.)
5. Create Dockerfile if containerization is needed

### Step 2: Write Implementation Files

Each file MUST follow this template:

```
1. Module header comment (purpose, author, date)
2. All imports (standard lib, third-party, local)
3. Constants and configuration
4. Type definitions / models / interfaces
5. Core implementation classes and functions
6. Error types and handlers
7. Entry point (if applicable)
8. Only export what's needed (public API surface)
```

### Step 3: Error Handling (MANDATORY)

Every I/O operation, network call, database query, file read/write, type conversion, and external API call MUST have error handling. Patterns by language are in the Error Handling section below.

### Step 4: Logging (MANDATORY)

Every significant event must be logged:
- `INFO` — normal operations (request started, completed)
- `WARNING` — unexpected but handled situations
- `ERROR` — failures that don't crash the application
- `DEBUG` — detailed information for troubleshooting

### Step 5: Testing

1. Write unit tests for every public function/class
2. Write integration tests for data flow paths
3. Include at least 3 edge case tests per function
4. Verify tests pass before declaring completion

### Step 6: Documentation

1. README.md with: purpose, setup, usage, API reference, examples
2. Inline docstrings for all public API
3. Comment complex logic (the "why", not the "what")

### Step 7: Verification Checklist

Before declaring the code complete, verify ALL of these:
1. Code compiles/parses without errors
2. Linter passes (ruff, eslint, golint, clippy)
3. Type checker passes (mypy, tsc, gotype)
4. All tests pass
5. Tested with at least one sample input
6. Error handling paths work (test with invalid input)
7. No hardcoded secrets, keys, or credentials
8. Documentation is accurate and complete
9. Code follows project conventions

---

## Architecture Patterns — Deep Reference

### Model-View-Controller (MVC)

Best for: Web applications with clear separation of concerns

```
User → Controller (validates, routes)
     → Model (business logic, data)
     → View (presentation, template)
     → Response
```

Implementation notes by language:
- **Python (Django)**: Models in `models.py`, Views in `views.py`, Templates in `templates/`
- **Python (Flask)**: Blueprints as controllers, Jinja2 templates
- **JavaScript (Express)**: Routes as controllers, EJS/Pug as views
- **TypeScript (NestJS)**: Decorators @Controller, @Get, @Post
- **Java (Spring)**: @RestController, @Service, @Repository
- **C# (ASP.NET)**: Controllers folder, Views folder, Models folder
- **Ruby on Rails**: Convention over configuration — MVC is built-in
- **Go (Gin)**: Handler functions, service layer, model structs

### Microservices Architecture

Best for: Large-scale, independently deployable components

Key principles:
1. Single responsibility per service
2. Decentralized data management (each service owns its DB)
3. Communication via APIs (REST/gRPC) or async events (message queue)
4. Independent deployment and scaling
5. Resilience: circuit breakers, retries, fallbacks
6. Observability: centralized logging, distributed tracing, metrics

Implementation:
```
service/
├── user-service/
│   ├── src/
│   ├── Dockerfile
│   └── k8s/deployment.yaml
├── order-service/
│   ├── src/
│   ├── Dockerfile
│   └── k8s/deployment.yaml
├── api-gateway/
├── shared/
│   └── proto/  (gRPC protobuf definitions)
└── docker-compose.yml
```

Common patterns:
- **API Gateway**: Single entry point that routes to services
- **Service Discovery**: Consul, etcd, Kubernetes DNS
- **Circuit Breaker**: Fail fast, degrade gracefully
- **Saga Pattern**: Distributed transactions via compensating actions
- **CQRS**: Separate read and write models
- **Event Sourcing**: Store state changes as event log

### Event-Driven Architecture

Best for: Real-time processing, loosely coupled systems

Components:
1. **Event Producers**: Generate events (user actions, system events)
2. **Event Bus/Broker**: RabbitMQ, Kafka, AWS SQS/SNS, Redis Pub/Sub
3. **Event Consumers**: Process events asynchronously

Patterns:
- **Pub/Sub**: Publishers don't know subscribers
- **Event Sourcing**: State is derived from event log
- **Stream Processing**: Kafka Streams, Apache Flink
- **Dead Letter Queue**: Failed events stored for later analysis

Implementation considerations:
- Event schema versioning (protobuf, Avro, JSON Schema)
- Exactly-once vs at-least-once delivery semantics
- Event ordering guarantees
- Backpressure handling
- Idempotent consumers

### Serverless Architecture

Best for: Event-driven workloads, variable traffic, reduced ops

Key concepts:
- **FaaS**: AWS Lambda, Azure Functions, Google Cloud Functions
- **BaaS**: Auth0, Firebase, Supabase
- Cold starts: minimize by keeping dependencies small
- Stateless functions: no local state between invocations
- Time limits: functions typically max out at 15 minutes (Lambda)

Implementation:
```python
# AWS Lambda handler
def handler(event: dict, context: Any) -> dict:
    try:
        body = json.loads(event.get('body', '{}'))
        result = process(body)
        return {
            'statusCode': 200,
            'body': json.dumps(result),
            'headers': {'Content-Type': 'application/json'}
        }
    except ValueError as e:
        return {'statusCode': 400, 'body': json.dumps({'error': str(e)})}
    except Exception as e:
        logger.exception("Unhandled error")
        return {'statusCode': 500, 'body': 'Internal error'}
```

### Monolithic Architecture

Best for: Small teams, simple applications, rapid prototyping

Structure:
```
app/
├── src/
│   ├── controllers/   (HTTP request handling)
│   ├── services/      (business logic)
│   ├── repositories/  (data access)
│   ├── models/        (data models)
│   ├── middleware/     (auth, logging, error handling)
│   └── utils/         (shared utilities)
├── config/            (application config)
├── database/          (migrations, seeds)
├── tests/
└── public/            (static assets)
```

Advantages: Simpler deployment, easier debugging, no network overhead
Disadvantages: Scaling requires entire app, technology lock-in

### Hexagonal Architecture (Ports & Adapters)

Best for: Domain-driven design, testable business logic

Core principle: Business logic is at the center, independent of external concerns (databases, APIs, UI).

```
[Driving Adapters] → [Ports] → [Domain Core] → [Ports] → [Driven Adapters]
   (Web, CLI,     )   (inbound )               (outbound)   (DB, API,  )
   (Test         )                              (           ) (Filesystem)
```

Layers:
1. **Domain**: Entities, value objects, domain services — NO external dependencies
2. **Application**: Use cases, ports (interfaces), application services
3. **Infrastructure**: Adapters (database repos, HTTP clients, message queues)
4. **Presentation**: Controllers, CLI handlers, API endpoints

```python
# Domain layer — pure business logic
class Order:
    def __init__(self, items: list[LineItem]):
        self.items = items

    def total(self) -> Decimal:
        return sum(item.price for item in self.items)

# Port (interface)
class OrderRepository(ABC):
    @abstractmethod
    def save(self, order: Order) -> None: ...

    @abstractmethod
    def find_by_id(self, order_id: str) -> Order | None: ...

# Infrastructure adapter
class PostgresOrderRepository(OrderRepository):
    def __init__(self, conn: Connection):
        self.conn = conn

    def save(self, order: Order) -> None:
        self.conn.execute("INSERT INTO orders ...")
```

---

## Design Patterns — Implementation by Language

### Singleton Pattern

Ensures a class has only one instance.

**Python:**
```python
class DatabaseConnection:
    _instance: "DatabaseConnection | None" = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "DatabaseConnection":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, connection_string: str):
        if not hasattr(self, '_initialized'):
            self.conn = create_engine(connection_string)
            self._initialized = True
```

**Go:**
```go
var (
    instance *Database
    once     sync.Once
)

func GetDatabase() *Database {
    once.Do(func() {
        instance = &Database{conn: connect()}
    })
    return instance
}
```

**TypeScript:**
```typescript
class DatabaseService {
    private static instance: DatabaseService;
    private constructor(private connectionString: string) {}

    static getInstance(connectionString: string): DatabaseService {
        if (!DatabaseService.instance) {
            DatabaseService.instance = new DatabaseService(connectionString);
        }
        return DatabaseService.instance;
    }
}
```

**Rust:**
```rust
use std::sync::OnceLock;

static DB: OnceLock<Database> = OnceLock::new();

fn get_database() -> &'static Database {
    DB.get_or_init(|| Database::new("connection_string"))
}
```

### Factory Pattern

Creates objects without specifying exact class.

**Python:**
```python
class PaymentProcessorFactory:
    processors: dict[str, type[PaymentProcessor]] = {
        'stripe': StripeProcessor,
        'paypal': PayPalProcessor,
        'square': SquareProcessor,
    }

    @classmethod
    def create(cls, provider: str, config: dict) -> PaymentProcessor:
        processor_class = cls.processors.get(provider)
        if not processor_class:
            raise ValueError(f"Unsupported payment provider: {provider}")
        return processor_class(config)
```

**Java:**
```java
public interface Database {
    void connect();
    void query(String sql);
}

public class DatabaseFactory {
    public static Database create(String type, String url) {
        return switch (type) {
            case "postgres" -> new PostgresDatabase(url);
            case "mysql" -> new MySQLDatabase(url);
            case "sqlite" -> new SQLiteDatabase(url);
            default -> throw new IllegalArgumentException("Unknown DB type: " + type);
        };
    }
}
```

### Observer Pattern

One-to-many dependency, notifies subscribers of state changes.

**Python:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

class EventObserver(ABC):
    @abstractmethod
    def update(self, event_type: str, data: Any) -> None: ...

@dataclass
class EventBus:
    _subscribers: dict[str, list[EventObserver]] = field(default_factory=dict)

    def subscribe(self, event_type: str, observer: EventObserver) -> None:
        self._subscribers.setdefault(event_type, []).append(observer)

    def unsubscribe(self, event_type: str, observer: EventObserver) -> None:
        self._subscribers.get(event_type, []).remove(observer)

    def emit(self, event_type: str, data: Any) -> None:
        for observer in self._subscribers.get(event_type, []):
            try:
                observer.update(event_type, data)
            except Exception as e:
                logger.error(f"Observer error: {e}", exc_info=True)
```

**TypeScript:**
```typescript
type EventHandler = (data: unknown) => void;

class EventEmitter {
    private handlers: Map<string, Set<EventHandler>> = new Map();

    on(event: string, handler: EventHandler): void {
        if (!this.handlers.has(event)) {
            this.handlers.set(event, new Set());
        }
        this.handlers.get(event)!.add(handler);
    }

    off(event: string, handler: EventHandler): void {
        this.handlers.get(event)?.delete(handler);
    }

    emit(event: string, data: unknown): void {
        this.handlers.get(event)?.forEach(handler => {
            try { handler(data); } catch (e) {
                console.error(`Handler error for ${event}:`, e);
            }
        });
    }
}
```

### Strategy Pattern

Enables selecting an algorithm at runtime.

**Python:**
```python
from abc import ABC, abstractmethod

class CompressionStrategy(ABC):
    @abstractmethod
    def compress(self, data: bytes) -> bytes: ...

    @abstractmethod
    def decompress(self, data: bytes) -> bytes: ...

class GzipCompression(CompressionStrategy):
    def compress(self, data: bytes) -> bytes:
        return gzip.compress(data)

    def decompress(self, data: bytes) -> bytes:
        return gzip.decompress(data)

class ZlibCompression(CompressionStrategy):
    def compress(self, data: bytes) -> bytes:
        return zlib.compress(data)

    def decompress(self, data: bytes) -> bytes:
        return zlib.decompress(data)

class Compressor:
    def __init__(self, strategy: CompressionStrategy):
        self._strategy = strategy

    def compress(self, data: bytes) -> bytes:
        return self._strategy.compress(data)

    def set_strategy(self, strategy: CompressionStrategy) -> None:
        self._strategy = strategy
```

**Go:**
```go
type SortStrategy interface {
    Sort([]int) []int
}

type BubbleSort struct{}
func (b BubbleSort) Sort(data []int) []int {
    n := len(data)
    result := make([]int, n)
    copy(result, data)
    for i := 0; i < n-1; i++ {
        for j := 0; j < n-i-1; j++ {
            if result[j] > result[j+1] {
                result[j], result[j+1] = result[j+1], result[j]
            }
        }
    }
    return result
}

type QuickSort struct{}
func (q QuickSort) Sort(data []int) []int {
    result := make([]int, len(data))
    copy(result, data)
    sort.Ints(result)
    return result
}

type Sorter struct {
    strategy SortStrategy
}

func (s *Sorter) Sort(data []int) []int {
    return s.strategy.Sort(data)
}
```

### Adapter Pattern

Allows incompatible interfaces to work together.

**Python:**
```python
# Existing interface (incompatible)
class LegacyLogger:
    def log_message(self, msg: str, level: int) -> None: ...

# Target interface
class Logger(ABC):
    @abstractmethod
    def info(self, message: str) -> None: ...

    @abstractmethod
    def error(self, message: str) -> None: ...

class LegacyLoggerAdapter(Logger):
    LEVEL_MAP = {'info': 1, 'error': 3}

    def __init__(self, legacy: LegacyLogger):
        self._legacy = legacy

    def info(self, message: str) -> None:
        self._legacy.log_message(message, self.LEVEL_MAP['info'])

    def error(self, message: str) -> None:
        self._legacy.log_message(message, self.LEVEL_MAP['error'])

# Usage
legacy = LegacyLogger()
logger: Logger = LegacyLoggerAdapter(legacy)
logger.info("System started")
```

**Java:**
```java
// Target interface
interface MediaPlayer {
    void play(String audioType, String fileName);
}

// Adaptee
class AdvancedMediaPlayer {
    void playVlc(String fileName) {
        System.out.println("Playing vlc file: " + fileName);
    }
    void playMp4(String fileName) {
        System.out.println("Playing mp4 file: " + fileName);
    }
}

// Adapter
class MediaAdapter implements MediaPlayer {
    AdvancedMediaPlayer advancedMusicPlayer = new AdvancedMediaPlayer();

    public void play(String audioType, String fileName) {
        switch (audioType) {
            case "vlc" -> advancedMusicPlayer.playVlc(fileName);
            case "mp4" -> advancedMusicPlayer.playMp4(fileName);
            default -> throw new IllegalArgumentException("Unsupported format: " + audioType);
        }
    }
}
```

### Decorator Pattern

Attaches additional responsibilities to an object dynamically.

**Python:**
```python
from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)

def timed(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            logger.info(f"{func.__name__} took {elapsed*1000:.2f}ms")
    return wrapper

def retry(max_attempts: int = 3, delay: float = 1.0) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    logger.warning(f"Attempt {attempt} failed: {e}, retrying...")
                    time.sleep(delay * (2 ** (attempt - 1)))  # exponential backoff
        return wrapper
    return decorator
```

### Dependency Injection

Decouples component creation from usage.

**Python:**
```python
from dataclasses import dataclass
from typing import Protocol

class UserRepository(Protocol):
    def find_by_id(self, user_id: str) -> dict | None: ...
    def save(self, user: dict) -> None: ...

class EmailService(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...

@dataclass
class UserService:
    repo: UserRepository
    email: EmailService

    def register_user(self, user_data: dict) -> dict:
        existing = self.repo.find_by_id(user_data['id'])
        if existing:
            raise ValueError("User already exists")
        self.repo.save(user_data)
        self.email.send(user_data['email'], "Welcome!", "Account created.")
        return user_data

# Wiring
def configure() -> UserService:
    return UserService(
        repo=PostgresUserRepository(connection_pool),
        email=SmtpEmailService(smtp_config),
    )
```

**C#:**
```csharp
public interface IPaymentGateway
{
    Task<PaymentResult> ChargeAsync(decimal amount, string token);
}

public class OrderService
{
    private readonly IPaymentGateway _paymentGateway;
    private readonly IOrderRepository _repository;

    public OrderService(IPaymentGateway paymentGateway, IOrderRepository repository)
    {
        _paymentGateway = paymentGateway;
        _repository = repository;
    }

    public async Task<Order> PlaceOrderAsync(OrderDto dto)
    {
        var result = await _paymentGateway.ChargeAsync(dto.Total, dto.PaymentToken);
        if (!result.Success)
            throw new PaymentFailedException(result.ErrorMessage);

        var order = new Order { /* map from dto */ };
        await _repository.SaveAsync(order);
        return order;
    }
}

// Startup.cs DI registration
services.AddScoped<IPaymentGateway, StripeGateway>();
services.AddScoped<IOrderRepository, PostgresOrderRepository>();
services.AddScoped<OrderService>();
```

---

## Language-Specific Deep Dives

### Python

**Setup & Project Structure:**
```python
# pyproject.toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "myproject"
version = "0.1.0"
dependencies = [
    "fastapi>=0.104.0",
    "sqlalchemy>=2.0.0",
    "pydantic>=2.0.0",
    "httpx>=0.25.0",
]
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
    "mypy>=1.6.0",
    "pre-commit>=3.5.0",
]
```

**Conventions:**
- PEP 8 (ruff enforces automatically)
- snake_case for functions/variables
- PascalCase for classes
- UPPER_CASE for constants
- Type hints on all functions (Python 3.10+)
- Docstrings: Google style or NumPy style

**Linting:**
```bash
ruff check src/                 # Lint
ruff format src/                # Format
mypy src/ --strict              # Type check
bandit -r src/                  # Security scan
safety check                    # Dependency vulnerabilities
```

**Testing:**
```python
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

@pytest.fixture
def db_session():
    session = create_test_session()
    yield session
    session.rollback()
    session.close()

@pytest.mark.asyncio
async def test_create_user_success(db_session):
    service = UserService(db_session)
    user = await service.create_user(
        email="test@example.com",
        name="Test User"
    )
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.created_at.tzinfo == timezone.utc

@pytest.mark.parametrize("email,expected", [
    ("", ValueError),
    ("not-an-email", ValueError),
    (None, TypeError),
])
@pytest.mark.asyncio
async def test_create_user_invalid_email(email, expected, db_session):
    service = UserService(db_session)
    with pytest.raises(expected):
        await service.create_user(email=email, name="Test")

def test_edge_case_empty_list():
    assert calculate_average([]) is None

def test_edge_case_single_element():
    assert calculate_average([42]) == 42.0

def test_edge_case_large_numbers():
    assert calculate_average([1e308, 1e308]) == float('inf')
```

**Async/Concurrency:**
```python
import asyncio
import aiohttp
from asyncio import Semaphore

sem = Semaphore(10)  # Max 10 concurrent requests

async def fetch_url(session: aiohttp.ClientSession, url: str) -> dict:
    async with sem:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                return await resp.json()
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {url}")
            return {"error": "timeout", "url": url}
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error for {url}: {e}")
            return {"error": str(e), "url": url}

async def fetch_all(urls: list[str]) -> list[dict]:
    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_url(session, url) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)
```

### JavaScript / TypeScript

**Setup & Project Structure:**
```json
{
  "name": "my-api",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "eslint src/",
    "format": "prettier --write src/",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "express": "^4.18.2",
    "zod": "^3.22.0",
    "pino": "^8.16.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "vitest": "^1.0.0",
    "eslint": "^8.55.0",
    "@types/express": "^4.17.21"
  }
}
```

**Conventions:**
- camelCase for variables/functions
- PascalCase for classes/types/interfaces
- Semicolons required
- 2-space indentation
- Explicit `unknown` instead of `any`
- Prefer `const` over `let`, never use `var`
- Use optional chaining `?.` and nullish coalescing `??`

**Testing (Vitest):**
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { UserService } from './user.service';
import { DatabaseError } from './errors';

const mockRepo = {
    findById: vi.fn(),
    save: vi.fn(),
};

describe('UserService', () => {
    let service: UserService;

    beforeEach(() => {
        vi.clearAllMocks();
        service = new UserService(mockRepo);
    });

    it('creates a user successfully', async () => {
        mockRepo.save.mockResolvedValueOnce({ id: '1', email: 'test@test.com' });
        const result = await service.createUser({ email: 'test@test.com' });
        expect(result.id).toBe('1');
        expect(mockRepo.save).toHaveBeenCalledOnce();
    });

    it('rejects duplicate email', async () => {
        mockRepo.findById.mockResolvedValueOnce({ id: '1', email: 'test@test.com' });
        await expect(service.createUser({ email: 'test@test.com' }))
            .rejects.toThrow('User already exists');
    });

    it('handles database error gracefully', async () => {
        mockRepo.save.mockRejectedValueOnce(new DatabaseError('connection failed'));
        await expect(service.createUser({ email: 'test@test.com' }))
            .rejects.toThrow(DatabaseError);
    });
});
```

**Async/Concurrency:**
```typescript
async function fetchWithRetry<T>(
    fn: () => Promise<T>,
    retries: number = 3
): Promise<T> {
    for (let i = 0; i < retries; i++) {
        try {
            return await fn();
        } catch (error) {
            if (i === retries - 1) throw error;
            const delay = Math.min(1000 * Math.pow(2, i), 10000);
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
    throw new Error('Unreachable');
}

// Parallel execution with concurrency control
async function concurrentMap<T, R>(
    items: T[],
    fn: (item: T) => Promise<R>,
    concurrency: number = 5
): Promise<R[]> {
    const results: R[] = [];
    const executing = new Set<Promise<void>>();

    for (const item of items) {
        const promise = fn(item).then(result => {
            results.push(result);
        });
        executing.add(promise);

        if (executing.size >= concurrency) {
            await Promise.race(executing);
            executing.delete(promise);
        }
    }
    await Promise.all(executing);
    return results;
}
```

### Go

**Setup & Project Structure:**
```
myapp/
├── cmd/
│   └── server/
│       └── main.go
├── internal/
│   ├── handler/
│   ├── service/
│   ├── repository/
│   └── model/
├── pkg/
│   └── middleware/
├── migrations/
├── go.mod
├── go.sum
├── Makefile
└── Dockerfile
```

```makefile
.PHONY: build test lint run

build:
	go build -o bin/server ./cmd/server

run:
	go run ./cmd/server

test:
	go test -v -race -coverprofile=coverage.out ./...

lint:
	golangci-lint run ./...

migrate:
	go run ./cmd/migrate
```

**Conventions:**
- `gofmt` formatting (non-negotiable)
- PascalCase for exported, camelCase for unexported
- Error handling: always check errors immediately
- Use `context.Context` as first parameter in API/server functions
- Interface satisfaction is implicit
- Avoid global state

**Testing (table-driven):**
```go
func TestCalculateTotal(t *testing.T) {
    tests := []struct {
        name     string
        items    []LineItem
        expected float64
        wantErr  bool
    }{
        {
            name:     "empty cart",
            items:    []LineItem{},
            expected: 0,
            wantErr:  false,
        },
        {
            name: "single item",
            items: []LineItem{{Price: 10.0, Quantity: 2}},
            expected: 20.0,
            wantErr: false,
        },
        {
            name: "negative price",
            items: []LineItem{{Price: -5.0, Quantity: 1}},
            expected: 0,
            wantErr: true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result, err := CalculateTotal(tt.items)
            if (err != nil) != tt.wantErr {
                t.Errorf("CalculateTotal() error = %v, wantErr %v", err, tt.wantErr)
            }
            if result != tt.expected {
                t.Errorf("CalculateTotal() = %v, want %v", result, tt.expected)
            }
        })
    }
}
```

**Concurrency:**
```go
func ProcessJobs(ctx context.Context, jobs []Job, workers int) []Result {
    jobCh := make(chan Job, len(jobs))
    resultCh := make(chan Result, len(jobs))

    // Start workers
    var wg sync.WaitGroup
    for i := 0; i < workers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for job := range jobCh {
                result, err := processJob(ctx, job)
                if err != nil {
                    logger.Error("job failed", "job_id", job.ID, "error", err)
                    continue
                }
                resultCh <- result
            }
        }()
    }

    // Send jobs
    for _, job := range jobs {
        jobCh <- job
    }
    close(jobCh)

    // Collect results
    go func() {
        wg.Wait()
        close(resultCh)
    }()

    var results []Result
    for result := range resultCh {
        results = append(results, result)
    }
    return results
}
```

### Rust

**Setup & Project Structure:**
```toml
[package]
name = "myapp"
version = "0.1.0"
edition = "2021"

[dependencies]
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
anyhow = "1"
thiserror = "1"
tracing = "0.1"
tracing-subscriber = "0.3"
reqwest = { version = "0.11", features = ["json"] }
sqlx = { version = "0.7", features = ["runtime-tokio", "postgres"] }

[dev-dependencies]
tokio-test = "0.4"
mockall = "0.12"
```

**Conventions:**
- `rustfmt` for formatting
- `clippy` for linting
- PascalCase for types/traits/enums
- snake_case for functions/variables
- Constants: SCREAMING_SNAKE_CASE
- Error handling: `thiserror` for library errors, `anyhow` for application errors
- Prefer `Result<T, E>` over panics
- Use `Option<T>` instead of null

**Error Handling:**
```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum UserError {
    #[error("user not found: {0}")]
    NotFound(String),
    #[error("database error: {0}")]
    Database(#[from] sqlx::Error),
    #[error("validation error: {0}")]
    Validation(String),
    #[error("unauthorized")]
    Unauthorized,
}

pub async fn get_user(pool: &PgPool, user_id: Uuid) -> Result<User, UserError> {
    let user = sqlx::query_as::<_, User>("SELECT * FROM users WHERE id = $1")
        .bind(user_id)
        .fetch_optional(pool)
        .await?
        .ok_or(UserError::NotFound(user_id.to_string()))?;
    Ok(user)
}
```

**Testing:**
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_create_user() {
        let pool = create_test_db().await;
        let service = UserService::new(pool);

        let user = service
            .create_user("test@example.com", "Test User")
            .await
            .expect("should create user");

        assert_eq!(user.email, "test@example.com");
        assert!(!user.id.is_nil());
    }

    #[tokio::test]
    async fn test_duplicate_email_rejected() {
        let pool = create_test_db().await;
        let service = UserService::new(pool);

        service.create_user("dup@example.com", "First").await.unwrap();
        let result = service.create_user("dup@example.com", "Second").await;

        assert!(matches!(result, Err(UserError::Validation(_))));
    }

    #[tokio::test]
    async fn test_get_nonexistent_user() {
        let pool = create_test_db().await;
        let service = UserService::new(pool);

        let result = service.get_user(Uuid::new_v4()).await;
        assert!(matches!(result, Err(UserError::NotFound(_))));
    }
}
```

**Async/Concurrency:**
```rust
use tokio::sync::Semaphore;
use std::sync::Arc;

async fn fetch_urls(urls: Vec<String>) -> Vec<Result<String, reqwest::Error>> {
    let client = reqwest::Client::new();
    let semaphore = Arc::new(Semaphore::new(10));
    let mut handles = vec![];

    for url in urls {
        let client = client.clone();
        let permit = semaphore.clone().acquire_owned().await.unwrap();
        handles.push(tokio::spawn(async move {
            let _permit = permit;
            client.get(&url).send().await?.text().await
        }));
    }

    let mut results = vec![];
    for handle in handles {
        results.push(handle.await.unwrap());
    }
    results
}
```

### C++

**Setup:**
```cmake
cmake_minimum_required(VERSION 3.20)
project(myapp VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(fmt CONFIG REQUIRED)
find_package(spdlog CONFIG REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)

add_executable(myapp
    src/main.cpp
    src/user_service.cpp
    src/database.cpp
)

target_include_directories(myapp PRIVATE include)
target_link_libraries(myapp PRIVATE fmt::fmt spdlog::spdlog nlohmann_json::nlohmann_json)

# Testing
enable_testing()
find_package(GTest REQUIRED)
add_executable(tests
    tests/test_user_service.cpp
    tests/test_database.cpp
)
target_link_libraries(tests PRIVATE GTest::GTest GTest::Main)
add_test(NAME unit_tests COMMAND tests)
```

**Conventions:**
- snake_case for functions/variables
- PascalCase for classes
- UPPER_CASE for macros
- Use RAII for resource management
- Prefer `std::unique_ptr` over raw pointers
- Use `const` wherever possible
- Modern C++ (17/20) features preferred

**Error Handling:**
```cpp
#include <expected>
#include <string>
#include <system_error>

enum class UserErrorCode {
    NotFound = 1,
    DuplicateEmail,
    DatabaseError,
};

class UserError : public std::runtime_error {
public:
    UserError(UserErrorCode code, std::string message)
        : std::runtime_error(message), code_(code) {}
    UserErrorCode code() const { return code_; }
private:
    UserErrorCode code_;
};

std::expected<User, UserError> GetUser(const Database& db, const std::string& id) {
    auto result = db.Query("SELECT * FROM users WHERE id = ?", id);
    if (!result) {
        return std::unexpected(UserError(UserErrorCode::DatabaseError, "Query failed"));
    }
    if (result->empty()) {
        return std::unexpected(UserError(UserErrorCode::NotFound, "User " + id + " not found"));
    }
    return User::FromRow(result->front());
}
```

### Java

**Setup:**
```xml
<!-- pom.xml -->
<project>
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>myapp</artifactId>
    <version>1.0.0</version>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
    </parent>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
```

**Conventions:**
- camelCase for methods/variables
- PascalCase for classes
- UPPER_SNAKE_CASE for constants
- Getters/setters follow JavaBeans spec
- Use `@Override` annotation consistently
- Prefer interfaces over abstract classes

**Error Handling:**
```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(EntityNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ErrorResponse handleNotFound(EntityNotFoundException ex) {
        return new ErrorResponse("NOT_FOUND", ex.getMessage());
    }

    @ExceptionHandler(ValidationException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ErrorResponse handleValidation(ValidationException ex) {
        return new ErrorResponse("VALIDATION_ERROR", ex.getMessage());
    }

    @ExceptionHandler(DatabaseException.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public ErrorResponse handleDatabase(DatabaseException ex) {
        log.error("Database error", ex);
        return new ErrorResponse("DATABASE_ERROR", "An internal error occurred");
    }

    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public ErrorResponse handleGeneric(Exception ex) {
        log.error("Unhandled exception", ex);
        return new ErrorResponse("INTERNAL_ERROR", "An unexpected error occurred");
    }
}
```

### SQL

**Connection Patterns:**
```python
# PostgreSQL with connection pooling
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    "postgresql+psycopg://user:pass@localhost:5432/dbname",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)
SessionLocal = sessionmaker(bind=engine)

# Context manager for safe transactions
@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

**Migrations (Alembic):**
```python
"""migration version 0002_add_user_table

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'

def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )
    op.create_index('ix_users_email', 'users', ['email'])

def downgrade() -> None:
    op.drop_table('users')
```

**Query Patterns:**
```sql
-- Parameterized query (safe from SQL injection)
SELECT * FROM users WHERE email = $1 AND status = $2;

-- Efficient pagination (keyset pagination, not OFFSET)
SELECT * FROM orders
WHERE created_at < $1 AND id != $2
ORDER BY created_at DESC, id DESC
LIMIT 50;

-- Upsert
INSERT INTO users (id, email, name)
VALUES ($1, $2, $3)
ON CONFLICT (email) DO UPDATE
SET name = EXCLUDED.name, updated_at = NOW();

-- Recursive CTE for hierarchies
WITH RECURSIVE org_tree AS (
    SELECT id, name, parent_id, 1 AS depth
    FROM organizations WHERE parent_id IS NULL
    UNION ALL
    SELECT o.id, o.name, o.parent_id, t.depth + 1
    FROM organizations o
    JOIN org_tree t ON o.parent_id = t.id
)
SELECT * FROM org_tree ORDER BY depth, name;

-- Window functions for analytics
SELECT
    department_id,
    employee_name,
    salary,
    RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) as rank_in_dept,
    AVG(salary) OVER (PARTITION BY department_id) as avg_dept_salary,
    salary - AVG(salary) OVER (PARTITION BY department_id) as diff_from_avg
FROM employees;
```

### HTML/CSS

**Structure:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Page description for SEO">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'">
    <title>My App</title>
    <link rel="stylesheet" href="/styles/main.css">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
</head>
<body>
    <header role="banner">
        <nav aria-label="Main navigation">
            <ul>
                <li><a href="/" aria-current="page">Home</a></li>
                <li><a href="/about">About</a></li>
            </ul>
        </nav>
    </header>
    <main role="main">
        <h1>Welcome</h1>
        <p>Content here.</p>
    </main>
    <footer role="contentinfo">
        <p>&copy; 2024 My App</p>
    </footer>
    <script type="module" src="/scripts/app.js" defer></script>
</body>
</html>
```

**CSS Conventions:**
```css
/* Custom properties for theming */
:root {
    --color-primary: #2563eb;
    --color-primary-hover: #1d4ed8;
    --color-bg: #ffffff;
    --color-text: #1a1a2e;
    --spacing-xs: 0.25rem;
    --spacing-sm: 0.5rem;
    --spacing-md: 1rem;
    --spacing-lg: 2rem;
    --border-radius: 0.5rem;
    --max-width: 1200px;
    --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
}

/* BEM naming convention */
.card { }
.card__title { }
.card__body { }
.card__body--featured { }
.card__button { }
.card__button--disabled { }

/* Responsive design */
.container {
    width: 100%;
    max-width: var(--max-width);
    margin: 0 auto;
    padding: 0 var(--spacing-md);
}

@media (max-width: 768px) {
    .container {
        padding: 0 var(--spacing-sm);
    }
    .card {
        grid-template-columns: 1fr;
    }
}

@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}
```

### Shell (Bash / PowerShell)

**Bash:**
```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

log_info()  { printf "${GREEN}[INFO]${NC}  %s\n" "$*"; }
log_warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
log_error() { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; }

cleanup() {
    log_info "Cleaning up..."
    rm -rf "$TEMP_DIR"
    kill "${PID:-}" 2>/dev/null || true
}
trap cleanup EXIT ERR

main() {
    local input_file="${1:?Usage: $0 <input_file>}"
    local output_dir="${2:-./output}"

    if [[ ! -f "$input_file" ]]; then
        log_error "File not found: $input_file"
        exit 1
    fi

    mkdir -p "$output_dir"
    log_info "Processing $input_file..."

    while IFS= read -r line; do
        [[ -z "$line" || "$line" =~ ^# ]] && continue
        echo "$line" >> "$output_dir/processed.txt"
    done < "$input_file"
}

main "$@"
```

**PowerShell:**
```powershell
<#
.SYNOPSIS
    Process data files with error handling and logging
.DESCRIPTION
    Reads input files, transforms data, and writes output
.PARAMETER InputPath
    Path to input file or directory
.PARAMETER OutputPath
    Path to output directory
.EXAMPLE
    .\process.ps1 -InputPath .\data -OutputPath .\results
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path $_ })]
    [string]$InputPath,
    [Parameter()]
    [string]$OutputPath = "./output"
)

$ErrorActionPreference = 'Stop'
$InformationPreference = 'Continue'

function Write-Log {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateSet('Info', 'Warn', 'Error')]
        [string]$Level,
        [string]$Message
    )
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $prefix = switch ($Level) {
        'Info'  { '[INFO]' }
        'Warn'  { '[WARN]' }
        'Error' { '[ERROR]' }
    }
    Write-Information "$prefix $timestamp $Message"
}

try {
    if (-not (Test-Path -LiteralPath $OutputPath)) {
        New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
        Write-Log -Level Info -Message "Created output directory: $OutputPath"
    }

    Get-ChildItem -LiteralPath $InputPath -Filter '*.csv' | ForEach-Object {
        try {
            $data = Import-Csv -LiteralPath $_.FullName -Encoding UTF8
            $processed = $data | Where-Object { $_.Status -eq 'Active' }
            $outputFile = Join-Path -Path $OutputPath -ChildPath "processed_$($_.Name)"
            $processed | Export-Csv -LiteralPath $outputFile -NoTypeInformation -Encoding UTF8
            Write-Log -Level Info -Message "Processed $($_.Name): $($processed.Count) records"
        }
        catch {
            Write-Log -Level Error -Message "Failed to process $($_.Name): $_"
        }
    }
}
catch {
    Write-Log -Level Error -Message "Script failed: $_"
    exit 1
}
```

---

## Testing Methodology

### Test Pyramid

```
        ╱╲
       ╱ E2E ╲          Few — test critical user journeys
      ╱────────╲
     ╱Integration╲      Some — test component interactions
    ╱──────────────╲
   ╱  Unit Tests     ╲  Many — test individual functions/classes
  ╱────────────────────╲
```

### Unit Tests

Test individual functions in isolation. Mock all external dependencies.

```python
# Python
def test_calculate_discount():
    service = DiscountService()
    assert service.calculate(100, 'STANDARD') == 100
    assert service.calculate(100, 'VIP') == 90
    assert service.calculate(100, 'EMPLOYEE') == 75
    assert service.calculate(None, 'VIP') is None
    assert service.calculate(-50, 'VIP') is None
```

```typescript
// TypeScript
describe('DiscountService', () => {
    it.each([
        [100, 'STANDARD', 100],
        [100, 'VIP', 90],
        [100, 'EMPLOYEE', 75],
        [0, 'VIP', 0],
        [-50, 'VIP', null],
    ])('calculates %i with %s = %i', (amount, tier, expected) => {
        expect(calculateDiscount(amount, tier)).toBe(expected);
    });
});
```

```rust
#[test]
fn test_calculate_discount() {
    let cases = vec![
        (100.0, "STANDARD", Some(100.0)),
        (100.0, "VIP", Some(90.0)),
        (100.0, "EMPLOYEE", Some(75.0)),
        (-50.0, "VIP", None),
    ];
    for (amount, tier, expected) in cases {
        assert_eq!(calculate_discount(amount, tier), expected);
    }
}
```

### Integration Tests

Test how components work together. May use test databases, test containers.

```python
@pytest.mark.integration
async def test_user_registration_flow(test_client, test_db):
    # Register user
    resp = await test_client.post("/api/users", json={
        "email": "new@example.com",
        "password": "SecurePass123!"
    })
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    # Verify user exists in database
    user = await test_db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    assert user is not None
    assert user["email"] == "new@example.com"

    # Verify welcome email was sent
    email = await test_db.fetchrow("SELECT * FROM emails WHERE recipient = $1", "new@example.com")
    assert email is not None
    assert "Welcome" in email["subject"]

    # Login with new credentials
    resp = await test_client.post("/api/auth/login", json={
        "email": "new@example.com",
        "password": "SecurePass123!"
    })
    assert resp.status_code == 200
    assert "token" in resp.json()
```

### E2E Tests

Test full user journeys as a real user would.

```typescript
import { test, expect } from '@playwright/test';

test('user completes purchase flow', async ({ page }) => {
    await page.goto('/products');
    await page.click('[data-testid="product-1"]');
    await page.click('[data-testid="add-to-cart"]');
    await page.click('[data-testid="checkout"]');

    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="card"]', '4242424242424242');
    await page.fill('[name="expiry"]', '12/28');
    await page.fill('[name="cvc"]', '123');
    await page.click('[data-testid="pay"]');

    await expect(page.locator('[data-testid="order-confirmation"]')).toBeVisible();
    await expect(page.locator('[data-testid="order-number"]')).not.toBeEmpty();
});
```

### TDD (Test-Driven Development)

```
RED → Write failing test first
GREEN → Write minimal code to pass
REFACTOR → Clean up code while keeping tests green
```

Workflow:
1. Write a test for the desired behavior (it fails - RED)
2. Write the simplest code to make the test pass (GREEN)
3. Refactor the code while keeping tests green
4. Repeat for next requirement

### Property-Based Testing

Instead of testing specific inputs, test properties that should always hold true.

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_sort_preserves_length(lst):
    result = sorted(lst)
    assert len(result) == len(lst)

@given(st.lists(st.integers()))
def test_sort_is_ordered(lst):
    result = sorted(lst)
    assert all(result[i] <= result[i+1] for i in range(len(result)-1))

@given(st.lists(st.integers()))
def test_sort_contains_same_elements(lst):
    result = sorted(lst)
    assert sorted(result) == sorted(lst)

@given(st.lists(st.integers(min_value=1, max_value=100), min_size=1))
def test_sort_first_is_minimum(lst):
    result = sorted(lst)
    assert result[0] == min(lst)

@given(st.dictionaries(st.text(), st.integers()))
def test_json_roundtrip(data):
    encoded = json.dumps(data, sort_keys=True)
    decoded = json.loads(encoded)
    assert decoded == data
```

```typescript
import { fc, test } from '@fast-check/vitest';

test.prop([fc.array(fc.integer())])('sort preserves length', (arr) => {
    const sorted = [...arr].sort((a, b) => a - b);
    expect(sorted).toHaveLength(arr.length);
});

test.prop([fc.array(fc.integer())])('sort is ordered', (arr) => {
    const sorted = [...arr].sort((a, b) => a - b);
    for (let i = 0; i < sorted.length - 1; i++) {
        expect(sorted[i]).toBeLessThanOrEqual(sorted[i + 1]);
    }
});
```

### Coverage Requirements

| Metric | Target |
|--------|--------|
| Line coverage | >= 80% |
| Branch coverage | >= 70% |
| Function coverage | >= 90% |
| Critical path coverage | 100% |

Generate coverage reports:
```bash
# Python
pytest --cov=src --cov-report=html --cov-report=term-missing

# TypeScript
vitest run --coverage

# Go
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out

# Rust
cargo tarpaulin --out Html

# Java
mvn verify -Pcoverage
```

---

## Security Checklist — Comprehensive

### Input Validation (ALL ENDPOINTS)
- Validate all user input on server side (never trust client-side validation)
- Use allowlists (whitelist) over blocklists (blacklist)
- Validate: type, length, format, range, allowed values
- Reject unexpected characters in string fields
- Validate file uploads: extension, MIME type, size, content scanning
- Sanitize output to prevent stored XSS

### Authentication & Authorization
- Use standard auth libraries (never roll your own crypto)
- Passwords: bcrypt/argon2 with cost factor >= 12
- JWT: short expiry (15 min for access, 7 days for refresh)
- Implement rate limiting on auth endpoints (5 attempts per minute)
- MFA for sensitive operations
- Session invalidation on logout
- Principle of least privilege for API keys
- RBAC/ABAC for authorization

### XSS Prevention
- Template auto-escaping (React JSX, Jinja2, Handlebars)
- Content-Security-Policy header: `default-src 'self'; script-src 'self'`
- Set HttpOnly and Secure flags on cookies
- Sanitize HTML input with DOMPurify (JS) or bleach (Python)
- Never use `innerHTML` or `dangerouslySetInnerHTML` without sanitization
- Encode output based on context: HTML entity, URL, JavaScript, CSS

### SQL Injection Prevention
- ALWAYS use parameterized queries / prepared statements
- NEVER concatenate user input into SQL strings
- Use ORMs with parameterized queries (SQLAlchemy, Prisma, Entity Framework)
- For raw SQL: always use `$1, $2` (PostgreSQL) or `?` (MySQL/SQLite) placeholders
- Limit database user permissions (no DROP TABLE from app user)
- Use stored procedures for complex operations (additional layer)

### CSRF Protection
- SameSite cookies: `SameSite=Lax` or `SameSite=Strict`
- CSRF tokens for state-changing requests
- `Origin` / `Referer` header validation
- Do NOT use GET requests for state-changing operations
- Custom request headers for API endpoints

### Rate Limiting
- Per-IP: 100 requests/minute for general endpoints
- Per-IP: 5 requests/minute for auth endpoints
- Per-User: 1000 requests/hour
- Per-Endpoint: configurable per route
- Return `429 Too Many Requests` with `Retry-After` header
- Use token bucket or sliding window algorithm

### Secrets Management
- NEVER hardcode secrets, API keys, passwords, tokens
- Use environment variables or secret manager (HashiCorp Vault, AWS Secrets Manager)
- `.env` files are LOCAL ONLY — never commit to version control
- Rotate secrets regularly (90-day max)
- Scan for secrets in codebase (truffleHog, Gitleaks)
- Use `SecretsManager` in CI/CD pipelines

### Additional Security Measures
- HTTPS everywhere (TLS 1.2+)
- HSTS header
- Proper CORS configuration (specific origins, not `*` for credentials)
- No sensitive data in URLs (use POST, not GET)
- Encrypt sensitive data at rest (AES-256-GCM)
- Encrypt sensitive data in transit (TLS)
- Regular dependency scanning (npm audit, pip audit, snyk)
- Proper error handling — don't leak stack traces to users
- Log security events (failed logins, unauthorized access attempts)
- Regular penetration testing

---

## Code Review Checklist

### Correctness
- Does the code fulfill the requirements?
- Are all edge cases handled? (empty, null, boundary, error)
- Are there off-by-one errors?
- Do recursion/iteration have proper termination conditions?
- Are race conditions possible?
- Are floating-point comparisons done with epsilon?
- Is there proper error propagation, not silent swallowing?

### Performance
- Are there N+1 query problems?
- Are data structures appropriate (hash map vs list vs tree)?
- Are there memory leaks? (unclosed files, sockets, connections)
- Is there unnecessary object allocation in hot paths?
- Are database queries indexed?
- Is there caching for expensive operations?
- Are large files processed in streaming fashion?
- Is async used properly (no sync-over-async)?

### Security
- Are all inputs validated and sanitized?
- Are all SQL queries parameterized?
- Are secrets handled properly (not logged, not hardcoded)?
- Is authentication checked on every protected endpoint?
- Is authorization checked (user can only access their own data)?
- Are there CSRF protections?
- Is rate limiting in place?
- Are security-related events logged?
- Is the attack surface minimized?

### Style & Maintainability
- Does the code follow language conventions?
- Are naming conventions consistent?
- Are functions/classes single-purpose?
- Is there duplicated code that should be abstracted?
- Are magic numbers replaced with named constants?
- Are comments explaining "why" not "what"?
- Is the code testable? (DI, interfaces, no global state)
- Is complex logic broken into smaller functions?

### Test Coverage
- Are there unit tests for each public function?
- Are edge cases tested?
- Are error paths tested?
- Are integration tests written for data flow?
- Do tests have descriptive names?
- Are mocks used appropriately?
- Is the test code itself clean and maintainable?
- Do tests avoid testing implementation details?

---

## API Design Patterns

### RESTful API Design

**URL Structure:**
```
GET    /api/v1/users              # List users
POST   /api/v1/users              # Create user
GET    /api/v1/users/:id          # Get user
PUT    /api/v1/users/:id          # Update user
DELETE /api/v1/users/:id          # Delete user
GET    /api/v1/users/:id/orders   # User's orders (sub-resource)
```

**Response Format:**
```json
{
    "status": "success",
    "data": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "name": "John Doe",
        "created_at": "2024-01-15T10:30:00Z"
    }
}
```

**Error Response:**
```json
{
    "status": "error",
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Email is required",
        "details": [
            {
                "field": "email",
                "message": "must not be empty",
                "code": "required"
            }
        ],
        "request_id": "req_abc123"
    }
}
```

**Pagination:**
```json
{
    "status": "success",
    "data": [...],
    "meta": {
        "page": 1,
        "per_page": 50,
        "total": 1234,
        "total_pages": 25,
        "next": "/api/v1/users?page=2&per_page=50",
        "prev": null
    }
}
```

### GraphQL API Design

```graphql
type User {
    id: ID!
    email: String!
    name: String!
    posts: [Post!]!
    createdAt: DateTime!
}

type Post {
    id: ID!
    title: String!
    content: String!
    author: User!
    comments: [Comment!]!
    createdAt: DateTime!
}

type Query {
    user(id: ID!): User
    users(page: Int, limit: Int): UserConnection!
    posts(search: String): [Post!]!
}

type Mutation {
    createUser(input: CreateUserInput!): User!
    updateUser(id: ID!, input: UpdateUserInput!): User!
    deleteUser(id: ID!): Boolean!
}

input CreateUserInput {
    email: String! @constraint(format: "email")
    name: String! @constraint(minLength: 1, maxLength: 100)
    password: String! @constraint(minLength: 8)
}

type UserConnection {
    edges: [UserEdge!]!
    pageInfo: PageInfo!
}

type UserEdge {
    node: User!
    cursor: String!
}
```

### gRPC API Design

```protobuf
syntax = "proto3";

package users.v1;

service UserService {
    rpc GetUser(GetUserRequest) returns (User);
    rpc ListUsers(ListUsersRequest) returns (ListUsersResponse);
    rpc CreateUser(CreateUserRequest) returns (User);
    rpc UpdateUser(UpdateUserRequest) returns (User);
    rpc DeleteUser(DeleteUserRequest) returns (DeleteUserResponse);
    rpc StreamUserUpdates(StreamUserUpdatesRequest) returns (stream User);
}

message User {
    string id = 1;
    string email = 2;
    string name = 3;
    google.protobuf.Timestamp created_at = 4;
}

message GetUserRequest {
    string id = 1;
}

message ListUsersRequest {
    int32 page = 1;
    int32 page_size = 2;
}

service HealthService {
    rpc Check(HealthCheckRequest) returns (HealthCheckResponse);
}
```

### WebSocket API Design

```python
import asyncio
import json
import logging
from typing import Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active[user_id] = websocket
        logger.info(f"WebSocket connected: user={user_id}")

    async def disconnect(self, user_id: str) -> None:
        self.active.pop(user_id, None)
        logger.info(f"WebSocket disconnected: user={user_id}")

    async def send_personal(self, user_id: str, message: dict) -> bool:
        ws = self.active.get(user_id)
        if ws is None:
            return False
        try:
            await ws.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {e}")
            await self.disconnect(user_id)
            return False

    async def broadcast(self, message: dict) -> None:
        disconnected = []
        for user_id, ws in self.active.items():
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(user_id)
        for uid in disconnected:
            await self.disconnect(uid)

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")
            payload = data.get("payload")

            if event_type == "ping":
                await manager.send_personal(user_id, {"type": "pong"})
            elif event_type == "subscribe":
                # handle subscription
                pass
            else:
                await manager.send_personal(user_id, {
                    "type": "error",
                    "payload": {"message": f"Unknown event type: {event_type}"}
                })
    except WebSocketDisconnect:
        await manager.disconnect(user_id)
```

---

## Database Patterns

### SQL Database Best Practices

**Schema Design:**
- Use UUIDs for primary keys (avoid sequential IDs in public APIs)
- Add `created_at` and `updated_at` timestamps to every table
- Use proper data types (TIMESTAMPTZ, not VARCHAR for dates)
- Add foreign key constraints with ON DELETE CASCADE or SET NULL
- Create indexes on foreign keys and frequently queried columns
- Use composite indexes for multi-column queries
- Avoid NULLable columns where possible (use NOT NULL with defaults)
- Use ENUMs or lookup tables for constrained values
- Implement soft deletes with `deleted_at TIMESTAMPTZ` column

**Connection Pooling:**
```python
# PostgreSQL with PgBouncer or built-in pool
pool = await asyncpg.create_pool(
    dsn="postgresql://user:pass@localhost:5432/db",
    min_size=5,
    max_size=20,
    max_inactive_connection_lifetime=300.0,
    command_timeout=30,
)
```

**Query Optimization:**
- Use EXPLAIN ANALYZE to identify slow queries
- Use connection pooling (not per-request connections)
- Batch inserts with bulk operations
- Use materialized views for expensive aggregations
- Partition large tables by date or tenant
- Use read replicas for read-heavy workloads

### NoSQL Database Patterns

**MongoDB:**
```python
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.myapp
collection = db.users

# Schema validation
db.command({
    "collMod": "users",
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["email", "name"],
            "properties": {
                "email": {"bsonType": "string", "pattern": "^[\\w.-]+@[\\w.-]+\\.\\w{2,}$"},
                "name": {"bsonType": "string"},
                "created_at": {"bsonType": "date"},
            }
        }
    }
})

# Aggregation pipeline
pipeline = [
    {"$match": {"status": "active"}},
    {"$group": {"_id": "$department", "count": {"$sum": 1}, "avg_salary": {"$avg": "$salary"}}},
    {"$sort": {"count": -1}},
    {"$limit": 10}
]
results = await collection.aggregate(pipeline).to_list(length=10)
```

**Redis (Caching & Pub/Sub):**
```python
import redis.asyncio as redis

r = await redis.from_url("redis://localhost:6379")

# Cache-aside pattern
async def get_user(user_id: str) -> dict:
    cache_key = f"user:{user_id}"
    cached = await r.get(cache_key)
    if cached:
        return json.loads(cached)
    user = await db.fetch_user(user_id)
    if user:
        await r.setex(cache_key, 3600, json.dumps(user))  # 1 hour TTL
    return user

# Rate limiting with sliding window
async def check_rate_limit(user_id: str, max_requests: int, window: int) -> bool:
    key = f"ratelimit:{user_id}:{int(time.time() / window)}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, window)
    return count <= max_requests

# Distributed locking
async def acquire_lock(lock_name: str, timeout: int = 10) -> bool:
    return await r.set(f"lock:{lock_name}", "1", nx=True, ex=timeout)

async def release_lock(lock_name: str) -> None:
    await r.delete(f"lock:{lock_name}")
```

### ORM/ODM Patterns

**SQLAlchemy (Python):**
```python
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
import uuid
from datetime import datetime, timezone

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    posts = relationship("Post", back_populates="author", lazy="selectin")

class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    author = relationship("User", back_populates="posts")
```

**Prisma (TypeScript):**
```prisma
model User {
    id        String   @id @default(uuid())
    email     String   @unique
    name      String
    password  String
    posts     Post[]
    createdAt DateTime @default(now())
    updatedAt DateTime @updatedAt

    @@index([email])
}

model Post {
    id        String   @id @default(uuid())
    title     String
    content   String
    published Boolean  @default(false)
    author    User     @relation(fields: [authorId], references: [id])
    authorId  String
    createdAt DateTime @default(now())
    updatedAt DateTime @updatedAt

    @@index([authorId])
}
```

### Migrations Strategy

- One migration per schema change
- Migrations are reversible (up/down)
- Test migrations against a copy of production data
- Use naming convention: `YYYYMMDD_description`
- Never edit applied migrations
- Use migration frameworks: Alembic (Python), Flyway (Java), dbmate (Go), Prisma Migrate (TS)

---

## Logging and Monitoring

### Structured Logging (All Languages)

```python
# Python structlog
import structlog
logger = structlog.get_logger()
logger.info("user.login", user_id="abc123", ip="192.168.1.1", auth_method="oauth")
```

```typescript
// TypeScript pino
import pino from 'pino';
const logger = pino({
    level: process.env.LOG_LEVEL || 'info',
    formatters: {
        level(label) { return { level: label }; },
    },
});
logger.info({ userId: 'abc123', action: 'purchase' }, 'Order completed');
```

```go
// Go slog
slog.Info("user logged in",
    "user_id", "abc123",
    "ip", r.RemoteAddr,
    "duration_ms", time.Since(start).Milliseconds(),
)
```

```rust
// Rust tracing
use tracing::{info, error, instrument};
#[instrument(skip(user))]
fn process_order(user: &User, order: &Order) -> Result<()> {
    info!("processing order");
    // ...
}
```

### Log Levels
| Level | Use Case | Example |
|-------|----------|---------|
| ERROR | Application failure | Database connection lost |
| WARN  | Unexpected but handled | Rate limit approaching |
| INFO  | Normal operations | User created, order placed |
| DEBUG | Detailed troubleshooting | Query parameters, timing |
| TRACE | Very detailed flow | Function entry/exit |

### Monitoring Metrics

Key metrics to collect (Prometheus format):
```python
from prometheus_client import Counter, Histogram, Gauge

request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
active_connections = Gauge('active_connections', 'Number of active connections')
error_count = Counter('application_errors_total', 'Application errors', ['type'])
db_pool_size = Gauge('db_pool_size', 'Database connection pool size')
db_pool_available = Gauge('db_pool_available', 'Available database connections')
```

### Health Check Endpoint
```python
@app.get("/health")
async def health_check():
    # Check database
    try:
        await db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {e}"

    # Check cache
    try:
        await redis.ping()
        cache_status = "healthy"
    except Exception as e:
        cache_status = f"unhealthy: {e}"

    status_code = 200 if all(s == "healthy" for s in [db_status, cache_status]) else 503
    return {
        "status": "healthy" if status_code == 200 else "degraded",
        "checks": {
            "database": db_status,
            "cache": cache_status,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": __version__,
    }
```

---

## CI/CD Pipeline Design

### GitHub Actions Example

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install ruff mypy
      - run: ruff check src/
      - run: mypy src/

  test:
    needs: lint
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: testdb
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
      redis:
        image: redis:7
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: pytest --cov=src --cov-report=xml --timeout=30
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379
      - uses: codecov/codecov-action@v3

  security:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install bandit safety
      - run: bandit -r src/ -f json -o bandit-report.json
      - run: safety check

  build:
    needs: security
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and Push Docker Image
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy to Production
        run: |
          echo "Deploying ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}"
          # kubectl set image, helm upgrade, terraform apply, etc.
```

### Stage Gates

```
[Commit] → [Lint] → [Unit Tests] → [Integration Tests] → [Security Scan] →
[Build Image] → [Deploy Staging] → [E2E Tests] → [Deploy Prod (manual gate)]
```

---

## Documentation Generation

### README Template
```markdown
# Project Name

Brief description of what this project does.

## Features

- Feature 1 description
- Feature 2 description
- Feature 3 description

## Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Redis 7+

## Installation

```bash
git clone https://github.com/org/project.git
cd project
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your configuration
```

## Usage

```bash
# Start the server
python -m src.main

# Run tests
pytest

# Lint
ruff check src/

# Type check
mypy src/
```

## API Documentation

See [API.md](./docs/API.md) for full API reference.

## Architecture

See [ARCHITECTURE.md](./docs/ARCHITECTURE.md) for system design.

## Contributing

See [CONTRIBUTING.md](./docs/CONTRIBUTING.md).

## License

MIT
```

### Inline Documentation Standards

**Python (Google-style docstrings):**
```python
def calculate_discount(amount: float, customer_tier: str) -> float | None:
    """Calculate discount for a customer based on their tier.

    Args:
        amount: The total purchase amount in USD. Must be non-negative.
        customer_tier: The customer's tier level.
            Valid values: 'STANDARD', 'VIP', 'EMPLOYEE'.

    Returns:
        The discounted amount, or None if the input is invalid.

    Raises:
        ValueError: If customer_tier is not a recognized tier.

    Examples:
        >>> calculate_discount(100.0, 'VIP')
        90.0
        >>> calculate_discount(-50.0, 'VIP')
        None
    """
```

**TypeScript (JSDoc):**
```typescript
/**
 * Creates a new user in the system.
 *
 * @param input - User creation data
 * @param input.email - User's email address (must be unique)
 * @param input.name - User's display name
 * @param input.password - User's password (min 8 chars)
 * @returns The created user with generated ID and timestamps
 * @throws {ValidationError} If input validation fails
 * @throws {DuplicateError} If email already exists
 * @throws {DatabaseError} If database operation fails
 *
 * @example
 * const user = await createUser({
 *   email: 'john@example.com',
 *   name: 'John Doe',
 *   password: 'SecurePass123!'
 * });
 */
export async function createUser(input: CreateUserInput): Promise<User>
```

**Rust (doc comments):**
```rust
/// Calculates the discounted price for a customer.
///
/// Applies tier-based discount percentage to the given amount.
///
/// # Arguments
/// * `amount` - The original price. Must be non-negative.
/// * `tier` - Customer tier: "standard", "vip", or "employee".
///
/// # Returns
/// `Some(f64)` with the discounted price, or `None` if amount is negative.
///
/// # Examples
/// ```
/// use myapp::pricing::calculate_discount;
/// assert_eq!(calculate_discount(100.0, "vip"), Some(90.0));
/// assert_eq!(calculate_discount(-10.0, "vip"), None);
/// ```
pub fn calculate_discount(amount: f64, tier: &str) -> Option<f64> { }
```

### Auto-generated API Docs

- **Python**: FastAPI auto-generates OpenAPI/Swagger docs at `/docs`
- **TypeScript**: Swagger/OpenAPI with `zod-to-openapi` or `@nestjs/swagger`
- **Go**: `swaggo/swag` generates Swagger from comments
- **Rust**: `utoipa` generates OpenAPI from Rust types
- **Java**: SpringDoc OpenAPI

---

## Async / Concurrency Patterns

### Comparison by Language

| Language | Async Mechanism | Concurrency Model | Best For |
|----------|----------------|-------------------|----------|
| Python | asyncio / await | Cooperative (event loop) | I/O-bound tasks |
| JS/TS | async/await | Event loop (single-threaded) | I/O-bound, UI |
| Go | goroutines + channels | M:N threading (CSP) | Concurrent systems |
| Rust | tokio/async-std | Cooperative (green threads) | High-performance I/O |
| C++ | std::async, coroutines | Native threads | CPU-bound |
| Java | CompletableFuture, virtual threads | Platform threads / Loom | Enterprise apps |
| C# | async/await (TPL) | Task-based | .NET ecosystem |
| Kotlin | coroutines | Structured concurrency | Android, JVM |

### Common Async Pitfalls & Solutions

1. **Callback Hell**: Replace with async/await chains
2. **Unhandled Promise Rejections**: Always add `.catch()` or try/catch
3. **Fire-and-Forget Without Error Handling**: Log errors from background tasks
4. **Starvation**: Ensure fair scheduling, avoid CPU-bound work in event loop
5. **Deadlocks**: Never block in async code (no `.Result` in C#, no `loop.run_until_complete` nested)
6. **Resource Leaks**: Use context managers (`async with`) for sessions/files
7. **Backpressure**: Implement throttling/semaphores for producer-consumer patterns

---

## Error Handling Patterns — All Languages

### Python
```python
class AppError(Exception):
    """Base application exception."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            code="NOT_FOUND",
            status_code=404,
        )

class ValidationError(AppError):
    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"Validation failed for {field}: {reason}",
            code="VALIDATION_ERROR",
            status_code=400,
        )

# Global exception handler (FastAPI)
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(f"{exc.code}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )
```

### Go
```go
type AppError struct {
    Code       string `json:"code"`
    Message    string `json:"message"`
    StatusCode int    `json:"-"`
    Err        error  `json:"-"`
}

func (e *AppError) Error() string {
    return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func (e *AppError) Unwrap() error { return e.Err }

var (
    ErrNotFound   = &AppError{Code: "NOT_FOUND", StatusCode: 404}
    ErrValidation = &AppError{Code: "VALIDATION_ERROR", StatusCode: 400}
    ErrAuth       = &AppError{Code: "UNAUTHORIZED", StatusCode: 401}
    ErrForbidden  = &AppError{Code: "FORBIDDEN", StatusCode: 403}
)
```

### TypeScript
```typescript
class AppError extends Error {
    constructor(
        message: string,
        public code: string,
        public statusCode: number = 500
    ) {
        super(message);
        this.name = 'AppError';
    }
}

class NotFoundError extends AppError {
    constructor(resource: string, id: string) {
        super(`${resource} not found: ${id}`, 'NOT_FOUND', 404);
    }
}

// Express error handler middleware
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
    if (err instanceof AppError) {
        logger.warn(`${err.code}: ${err.message}`);
        res.status(err.statusCode).json({
            status: 'error',
            error: { code: err.code, message: err.message }
        });
    } else {
        logger.error('Unhandled error', err);
        res.status(500).json({
            status: 'error',
            error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred' }
        });
    }
});
```

### Rust
```rust
#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("not found: {0}")]
    NotFound(String),
    #[error("validation error: {0}")]
    Validation(String),
    #[error("authentication failed")]
    Unauthorized,
    #[error("forbidden")]
    Forbidden,
    #[error("database error: {0}")]
    Database(#[from] sqlx::Error),
    #[error("internal error: {0}")]
    Internal(String),
}

impl AppError {
    pub fn status_code(&self) -> u16 {
        match self {
            AppError::NotFound(_) => 404,
            AppError::Validation(_) => 400,
            AppError::Unauthorized => 401,
            AppError::Forbidden => 403,
            AppError::Database(_) | AppError::Internal(_) => 500,
        }
    }
}

impl axum::response::IntoResponse for AppError {
    fn into_response(self) -> axum::response::Response {
        let body = json!({
            "error": {
                "code": format!("{:?}", self).to_uppercase(),
                "message": self.to_string(),
            }
        });
        (StatusCode::from_u16(self.status_code()).unwrap(), Json(body)).into_response()
    }
}
```

---

## FRIDAY-Specific Instructions

### Skill File Reading Protocol

1. **BEFORE generating ANY code**, FRIDAY MUST read this skill file (`SKILL.md`) in its entirety.
2. For specialized code (SVG, charts, docx generation, etc.), read the corresponding skill file(s).
3. If multiple skill files are relevant, read ALL of them before planning.
4. The skill files define conventions, patterns, and requirements that MUST be followed.
5. If requirements from different skill files conflict, ask the user for clarification.

### Plan→Build Enforcement

1. The Plan→Build two-phase workflow is ABSOLUTELY MANDATORY.
2. Phase 1 (Plan) MUST be completed BEFORE any code is written.
3. The plan MUST be presented to the user for approval on any task estimated >200 lines.
4. Do NOT begin Phase 2 until the plan is explicitly approved.
5. If the user requests changes during Plan review, update the plan and re-present.

### When to Generate Which Type

| User Request | Skill to Consult | Output Type |
|---|---|---|
| "Create a chart" | chart/SKILL.md | Chart code + data |
| "Generate SVG" | svg/SKILL.md | SVG markup |
| "Create a document" | docx/SKILL.md | DOCX generation code |
| "Visualize data" | chart/SKILL.md + code_gen/SKILL.md | Both |
| "Build a web scraper" | This skill | Python/Node scraper |
| "Build an API" | This skill | FastAPI/Express REST |
| "Security audit" | This skill (security section) | Code with security fixes |
| "Refactor code" | This skill (patterns section) | Refactored code |

### Code Quality Gates

Before any code is delivered to the user, FRIDAY MUST verify:

```
1. Parse/Compile: Passes language parser/compiler
2. Lint: Zero linting errors (ruff, eslint, clippy, etc.)
3. Types: Zero type errors (mypy, tsc, gotype, etc.)
4. Tests: All tests pass (or tests are provided with instructions)
5. Security: No hardcoded secrets, no injection vectors
6. Error Handling: Every fallible operation is handled
7. Logging: Appropriate log statements at key points
8. Docs: README + docstrings for public API
```

If any gate fails, FRIDAY MUST fix the issue before presenting the code.

### Line Count Guidelines

- Minimum 100 lines for any production module (not config, not test)
- No upper limit — 20k+ line files are acceptable if well-structured
- Break very large files (10k+ lines) into modules if cohesion allows
- Tests should be roughly 1:1 with implementation line count
- Error handling should account for ~15-20% of total lines

### Final Reminder

**READ THIS SKILL FILE BEFORE GENERATING CODE. FOLLOW THE PLAN→BUILD WORKFLOW. NEVER SKIP PLANNING. NEVER GENERATE INCOMPLETE CODE.**
