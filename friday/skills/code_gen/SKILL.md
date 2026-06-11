---
name: code_gen
description: Use this skill when generating code in ANY programming language — write complete, production-quality code, not snippets
---

# Advanced Code Generation Skill

## Overview
FRIDAY generates production-quality code in ANY programming language. Code is complete, tested, documented, and follows best practices. There is NO line limit — FRIDAY writes as many lines as needed (single files can be 20k+ lines).

## Triggers
- "write code", "create a script", "build an app", "implement"
- "program", "function", "class", "module", "library"
- "API", "CLI", "GUI", "web app", "microservice"
- "refactor", "rewrite", "convert to [language]"
- "generate [language] code", "port to [language]"
- ANY coding-related request in ANY language

## Supported Languages & Frameworks
### Systems & Languages
| Language | Notes |
|----------|-------|
| Python | Primary — all expertise levels |
| JavaScript/TypeScript | Node.js, Deno, Bun |
| Go | CLI tools, APIs, concurrency |
| Rust | Systems programming, WASM |
| C | Embedded, systems, kernel |
| C++ | Games, high-performance, Qt |
| C# | .NET, Unity, desktop apps |
| Java | Spring, Android, enterprise |
| Kotlin | Android, JVM |
| Swift | iOS, macOS |
| Ruby | Rails, Sinatra |
| PHP | Laravel, WordPress |
| R | Data science, statistics |
| Julia | Scientific computing |
| Dart/Flutter | Cross-platform mobile |
| Lua | Game modding, embedded |
| Zig | Systems, cross-compilation |
| Haskell | Functional, academic |
| Elixir | Phoenix, distributed |
| Scala | Big data, Spark |
| Perl | Glue scripts, legacy |
| SQL | All dialects (PostgreSQL, MySQL, SQLite, MSSQL, Oracle) |
| Shell | Bash, PowerShell, Zsh |
| Assembly | x86, ARM, RISC-V |

### Web Frontend
- React/Next.js, Vue/Nuxt, Angular, Svelte/SvelteKit, SolidJS, Qwik
- HTML5, CSS3, Tailwind, Bootstrap, Material UI, Shadcn
- Web Components, vanilla JS

### Backend & API
- FastAPI, Django, Flask, Express, Koa, Gin, Fiber, Echo
- Actix, Rocket, Axum (Rust), Spring Boot
- GraphQL (Apollo, Yoga), gRPC, REST
- WebSocket, SSE, WebRTC

### Mobile
- React Native, Flutter, SwiftUI, Kotlin Compose
- Xamarin, .NET MAUI

### Infrastructure
- Docker, Docker Compose, Kubernetes, Terraform, Ansible
- CI/CD (GitHub Actions, GitLab CI, Jenkins)

## Code Patterns — ALL Languages

### Project Structure
```
project/
├── src/           # Source code
├── tests/         # Test files
├── docs/          # Documentation
├── scripts/       # Utility scripts
├── config/        # Configuration
├── README.md
├── Makefile / Cargo.toml / package.json / go.mod / build.gradle
└── Dockerfile (if applicable)
```

### Each file MUST include:
1. Module/file header comment (purpose, author, date)
2. All necessary imports at the top
3. Type annotations / type definitions where available
4. Complete docstrings/comments for public API
5. Error handling (try/except, Result, Option, error types)
6. Main entry point guard (`if __name__`, `fn main()`, etc.)

### Error Handling Patterns
```python
def process_data(data: dict) -> dict | None:
    try:
        result = transform(data)
        validate(result)
        return result
    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise
```

```go
func ProcessData(data map[string]interface{}) (*Result, error) {
    result, err := transform(data)
    if err != nil {
        return nil, fmt.Errorf("transform failed: %w", err)
    }
    if err := validate(result); err != nil {
        return nil, fmt.Errorf("validation failed: %w", err)
    }
    return result, nil
}
```

```rust
fn process_data(data: &HashMap<String, Value>) -> Result<Data, Box<dyn Error>> {
    let result = transform(data)?;
    validate(&result)?;
    Ok(result)
}
```

## Guidelines for ALL Code Generation

### DO:
- **Write COMPLETE code** — no placeholders, no "TODO", no `...`
- **Follow language-specific conventions** — PEP8 for Python, `gofmt` for Go, `rustfmt` for Rust
- **Include error handling** — every I/O, network, parse, and cast operation
- **Add logging** — use the language's standard logging library
- **Write tests** — unit tests with the language's standard test framework
- **Use type hints** — every function parameter and return value
- **Add docstrings/comments** — every public function, class, and module
- **Handle edge cases** — empty input, null values, boundary conditions
- **Optimize for readability** — clear variable names, consistent style
- **Include setup/install instructions** — README with dependencies and commands
- **Support 20k+ lines** when needed — build modular code with proper abstraction
- **Use async/await** where appropriate (Python asyncio, JS Promises, Rust tokio, Go goroutines)
- **Include a Makefile or task file** for build/test/run commands

### NEVER:
- NEVER generate incomplete code with `# TODO` or `pass` or `...`
- NEVER skip error handling
- NEVER use deprecated libraries or APIs
- NEVER generate code that imports packages not specified in requirements
- NEVER skip testing — at minimum include how to test
- NEVER produce code that can't run without manual fixes
- NEVER write flat scripts for complex tasks — use proper architecture
- NEVER use `os.system()` or `subprocess.call()` where library exists
- NEVER hardcode secrets, keys, or credentials
- NEVER produce less than 100 lines for a production module

## Scale Guidelines
| Size | Lines | When |
|------|-------|------|
| Small utility | 20-150 | Single-purpose script, helper function |
| Module | 150-1000 | Well-defined component with tests |
| Large module | 1000-5000 | Full feature with multiple sub-components |
| Application | 5000-50000 | Complete app with CLI, API, database, tests |
| Enterprise | 50000+ | Multi-service system with docs, CI/CD, deployment |

## Testing Requirements
- Python: `pytest` or `unittest` with fixtures
- JS/TS: `vitest` or `jest`
- Go: `go test` with table-driven tests
- Rust: `#[test]` with `cargo test`
- Java: JUnit 5
- C#: NUnit / xUnit
- Ruby: RSpec
- PHP: PHPUnit

## Verification
1. Check code compiles/parses without errors
2. Run linter (`ruff`, `eslint`, `golint`, `clippy`)
3. Run type checker (`mypy`, `tsc`, `gotype`)
4. Run tests (all pass)
5. Test with sample input
6. Verify error handling works
7. Check documentation is accurate
