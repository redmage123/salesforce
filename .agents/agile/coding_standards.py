#!/usr/bin/env python3
"""
Shared coding standards for developer prompts (DRY principle).

This module contains the comprehensive coding standards applied to all
developer agents across 24 programming languages.
"""

CODING_STANDARDS_ALL_LANGUAGES = r"""**MANDATORY CODING STANDARDS (ALL LANGUAGES):**

APPLIES TO: Python, C, C++, Rust, Java, Groovy, Go, JavaScript, TypeScript, Ruby, Swift, Objective-C, Kotlin, C#, Scala, Haskell, Erlang, Perl, Fortran, R, MATLAB, PHP, HTML, CSS, XML, Assembly (x86/x64, ARM, SPARC), SQL (PostgreSQL, SQL Server, MySQL, DB2), GraphQL, NoSQL (MongoDB, Cassandra, Redis, DynamoDB, Elasticsearch, Neo4j), Forth

═══════════════════════════════════════════════════════════════════════════════
1. API VERIFICATION (CRITICAL - PREVENTS RUNTIME ERRORS)
═══════════════════════════════════════════════════════════════════════════════
BEFORE calling ANY method/function from another class or module, you MUST:

1. VERIFY METHOD NAME EXISTS:
   - Check the actual class/module definition
   - Confirm the exact method name spelling
   - Verify it's a public method (not private/protected unless intended)

2. VERIFY PARAMETER LIST:
   - Check exact parameter names and order
   - Verify required vs optional parameters
   - Check for keyword-only arguments (Python *,)
   - Validate default values if relying on them

3. VERIFY RETURN TYPE:
   - Check what the method actually returns (primitive, object, collection, None)
   - If returning an object, check its structure/attributes
   - Verify error conditions (does it return None or raise exception?)
   - Check if return value needs attribute access (.content, .data, etc.)

4. EXAMPLE VERIFICATION WORKFLOW:
   ```python
   # WRONG - Assumes method name and return type:
   result = self.board.update_card_metadata(card_id, metadata)

   # CORRECT - Verified first:
   # 1. Checked kanban_manager.py: method is "update_card", not "update_card_metadata"
   # 2. Checked signature: update_card(card_id: str, updates: Dict[str, Any]) -> bool
   # 3. Checked return: returns bool, not None
   result = self.board.update_card(card_id, metadata)
   if not result:
       raise UpdateError(f"Failed to update card {card_id}")
   ```

5. COMMON FAILURE PATTERNS TO AVOID:
   - Calling .split() on object instead of .content or .text attribute
   - Assuming method exists based on similar classes
   - Wrong parameter names (system_message vs system_prompt)
   - Not checking if return value is object vs primitive
   - Reading empty string as file path (causes IsADirectoryError)

═══════════════════════════════════════════════════════════════════════════════
2. EXCEPTION HANDLING & ERROR MANAGEMENT
═══════════════════════════════════════════════════════════════════════════════
- ALWAYS create custom exception/error types (never use raw/generic exceptions)
- Use exception hierarchy (inherit from base project exception class)
- Include contextual information in errors (file, line, operation, state)
- Use Result<T, E> pattern in Rust, Optional/Either in functional languages
- Never silently swallow exceptions (log or propagate)
- Use try-with-resources (Java), defer (Go), RAII (C++), context managers (Python)

═══════════════════════════════════════════════════════════════════════════════
3. SOLID PRINCIPLES (Universal)
═══════════════════════════════════════════════════════════════════════════════
- Single Responsibility: One reason to change per class/module
- Open/Closed: Extend via composition/inheritance, not modification
- Liskov Substitution: Subtypes must be substitutable for base types
- Interface Segregation: Small, focused interfaces/traits/protocols
- Dependency Inversion: Depend on abstractions (interfaces), not concrete implementations

═══════════════════════════════════════════════════════════════════════════════
4. ANTI-PATTERN AVOIDANCE (Strict Rules)
═══════════════════════════════════════════════════════════════════════════════
- NEVER nested loops (use streams/iterators/comprehensions/SIMD/vectorization)
- NEVER nested if statements (use guard clauses, early returns, pattern matching)
- NEVER if-elif-elif-else chains >3 levels (use maps/dictionaries/strategy pattern/match expressions)
- NEVER god classes/methods (max 50 lines/method, 200 lines/class)
- NEVER magic numbers/strings (use const/constexpr/enum/static final)
- NEVER mutable global state (use dependency injection)
- NEVER shared mutable state in concurrent code (use message passing/channels/actors)

═══════════════════════════════════════════════════════════════════════════════
5. FUNCTIONAL PROGRAMMING PRINCIPLES
═══════════════════════════════════════════════════════════════════════════════
- Prefer immutable data structures (const, final, readonly, frozen)
- Use pure functions (no side effects, deterministic output)
- Use higher-order functions: map, filter, reduce, flatMap
- Leverage language-specific features:
  * Python: comprehensions, itertools, functools
  * JavaScript/TypeScript: array methods, async/await
  * Java: Stream API, Optional
  * Rust: iterators, combinators
  * C++: ranges, algorithms
  * Go: goroutines with channels
  * Ruby: blocks, procs, lambdas
  * Swift: closures, map/filter/reduce
- Apply memoization for expensive computations (cache results)

**LAMBDAS, STREAMS, PIPELINES, AND COROUTINES (EXPLICITLY ALLOWED AND ENCOURAGED):**

For ALL languages that support these constructs, their use is ALLOWED and ENCOURAGED:

1. **LAMBDAS (Anonymous Functions):**
   - Python: lambda x: x * 2, use for simple transformations
   - Java: (x) -> x * 2, use with Stream API and functional interfaces
   - JavaScript/TypeScript: (x) => x * 2, arrow functions
   - C#: x => x * 2, LINQ expressions
   - Kotlin: { x -> x * 2 }, lambda expressions
   - Scala: (x: Int) => x * 2, anonymous functions
   - C++: [](int x) { return x * 2; }, lambda expressions
   - Rust: |x| x * 2, closures
   - Swift: { x in x * 2 }, closure expressions
   - Go: func(x int) int { return x * 2 }, function literals
   - Ruby: lambda { |x| x * 2 }, proc { |x| x * 2 }
   - Haskell: \x -> x * 2, lambda abstractions

2. **JAVA STREAMS (HIGHLY ENCOURAGED):**
   - Use Stream API for ALL collection operations (map, filter, reduce, collect)
   - Parallel streams for CPU-intensive operations (parallelStream())
   - Examples:
     * list.stream().filter(x -> x > 0).map(x -> x * 2).collect(Collectors.toList())
     * IntStream.range(0, 100).parallel().sum()
     * map.entrySet().stream().filter(e -> e.getValue() > threshold)
   - Use Optional for null safety
   - Method references over lambdas when possible: String::toUpperCase

3. **PYTHON GENERATORS AND PIPELINES (ALLOWED AND ENCOURAGED):**
   - Generators for lazy evaluation and memory efficiency:
     * def fibonacci(): a, b = 0, 1; while True: yield a; a, b = b, a + b
     * Use yield from for delegating to sub-generators
   - Pipeline composition with itertools:
     * from itertools import islice, chain, takewhile, dropwhile
     * pipeline = (x * 2 for x in range(100) if x % 2 == 0)
   - Generator expressions over list comprehensions for large datasets:
     * total = sum(x**2 for x in huge_list)  # Memory efficient
   - Use toolz/fn.py for functional pipeline composition

4. **PYTHON COROUTINES (ALLOWED AND ENCOURAGED):**
   - async/await for I/O-bound concurrency:
     * async def fetch_data(url): return await aiohttp.get(url)
     * await asyncio.gather(*[fetch(url) for url in urls])
   - asyncio for event loops and tasks
   - Use aiohttp, aiofiles, asyncpg for async I/O
   - async generators: async def gen(): for i in range(10): yield await fetch(i)
   - async context managers: async with aiofiles.open() as f

5. **C# STREAMS AND LAMBDAS (ALLOWED AND ENCOURAGED):**
   - LINQ for ALL collection operations (Select, Where, Aggregate, GroupBy)
   - Examples:
     * var result = collection.Where(x => x > 0).Select(x => x * 2).ToList()
     * var groups = items.GroupBy(x => x.Category).ToDictionary(g => g.Key, g => g.ToList())
   - Parallel LINQ (PLINQ) for CPU-bound operations:
     * collection.AsParallel().Where(x => IsPrime(x)).Sum()
   - async/await with Task and Task<T>:
     * await Task.WhenAll(tasks)
     * await Task.Run(() => CpuIntensiveWork())
   - IAsyncEnumerable for async streams (C# 8.0+):
     * await foreach (var item in GetAsyncStream()) { }

6. **ADDITIONAL LANGUAGE SUPPORT:**
   - Kotlin: sequences for lazy evaluation, flow for async streams
   - Scala: for-comprehensions, Futures, Akka Streams
   - JavaScript: async iterators, generator functions, Promise.all/race
   - Rust: Iterator trait, async/await with tokio or async-std
   - F#: Computation expressions, async workflows, Seq module
   - Haskell: Lazy evaluation by default, do-notation for monads
   - Erlang/Elixir: Stream module, lazy enumeration

**WHEN TO USE THESE CONSTRUCTS:**
- Lambdas: Simple transformations, callbacks, event handlers
- Streams (Java/C#): Collection processing, data transformation pipelines
- Generators (Python): Large datasets, infinite sequences, lazy evaluation
- Coroutines (Python/C#): I/O-bound operations, concurrent HTTP requests, database queries
- Pipelines: Multi-step data transformations, ETL operations, data processing

**PERFORMANCE BENEFITS:**
- Memory efficiency (lazy evaluation, no intermediate collections)
- Parallelization opportunities (parallel streams, async operations)
- Composability (chain operations declaratively)
- Readability (express intent clearly with functional style)

═══════════════════════════════════════════════════════════════════════════════
6. CODE QUALITY & DOCUMENTATION
═══════════════════════════════════════════════════════════════════════════════
- Write EXPLICIT comments explaining WHAT and WHY (not just repeating code)
- Document all assumptions, invariants, preconditions, postconditions
- Use type systems fully:
  * Python: type hints with mypy
  * TypeScript: strict mode, no any
  * Java: generics, annotations
  * Rust: strong static typing
  * C++: concepts (C++20), templates
  * Go: interfaces
  * Swift: protocols, associated types
- Keep methods small: <50 lines per function/method
- Keep classes focused: <200 lines per class
- Use descriptive names (no abbreviations like "usr", "temp", "mgr")
- Follow language conventions (PEP 8, rustfmt, gofmt, etc.)

═══════════════════════════════════════════════════════════════════════════════
7. DESIGN PATTERNS (Use When Appropriate)
═══════════════════════════════════════════════════════════════════════════════
Creational:
- Factory Pattern: Complex object creation
- Builder Pattern: Step-by-step construction
- Singleton: Use sparingly (prefer dependency injection)

Structural:
- Adapter: Interface compatibility
- Decorator: Add behavior without inheritance
- Facade: Simplify complex subsystems
- Repository: Data access abstraction

Behavioral:
- Strategy: Algorithm variations
- Observer: Event-driven systems (pub/sub)
- Command: Encapsulate requests
- State: State machine patterns
- Template Method: Algorithm skeleton

Concurrency:
- Actor Model: Message-passing concurrency
- Producer-Consumer: Work queues
- Pipeline: Stream processing

═══════════════════════════════════════════════════════════════════════════════
8. ARCHITECTURAL PATTERNS
═══════════════════════════════════════════════════════════════════════════════
- Dependency Injection: Constructor/property injection (avoid service locator)
- Repository Pattern: Abstract data access layer
- Service Layer: Business logic separation
- Command Query Separation (CQS): Separate reads from writes
- Event Sourcing: Track state changes as events
- Saga Pattern: Distributed transactions
- Hexagonal/Clean Architecture: Domain at center, dependencies point inward

═══════════════════════════════════════════════════════════════════════════════
9. ERROR HANDLING & RESILIENCE
═══════════════════════════════════════════════════════════════════════════════
- Circuit Breaker: Prevent cascade failures (open after N failures)
- Bulkhead: Isolate failures (thread pools, connection pools)
- Retry with Exponential Backoff: For transient failures (max retries, jitter)
- Timeout Guards: NEVER wait indefinitely (set reasonable timeouts)
- Graceful Degradation: Fallback strategies (cached data, default values)
- Idempotency: All state-changing operations must be safely retryable

═══════════════════════════════════════════════════════════════════════════════
10. CONCURRENCY & PARALLELISM
═══════════════════════════════════════════════════════════════════════════════
- Use async/await for I/O-bound operations
- Use thread pools for CPU-bound parallel tasks
- AVOID shared mutable state (use immutable data + transformations)
- Use locks/mutexes minimally (prefer lock-free data structures)
- Prefer message passing over shared memory (Go channels, Rust mpsc, Akka actors)
- Use atomic operations for counters/flags
- Language-specific:
  * Python: asyncio, ThreadPoolExecutor, multiprocessing
  * JavaScript: Promises, async/await, Web Workers
  * Java: CompletableFuture, ExecutorService, java.util.concurrent
  * Rust: tokio, async-std, rayon
  * Go: goroutines, channels, sync package
  * C++: std::async, std::thread, std::mutex

═══════════════════════════════════════════════════════════════════════════════
11. TESTING STANDARDS
═══════════════════════════════════════════════════════════════════════════════
- Unit Tests: 85%+ code coverage, test edge cases
- Property-Based Testing: Generate test cases (Hypothesis, QuickCheck, fast-check)
- Mutation Testing: Validate test quality (kill mutants)
- Integration Tests: Test component interactions
- Contract Testing: For APIs (Pact, Spring Cloud Contract)
- Snapshot Testing: For complex outputs
- Test Doubles: Mocks, stubs, fakes, spies (know the difference)
- TDD: Write tests first when possible

═══════════════════════════════════════════════════════════════════════════════
12. SECURITY STANDARDS (OWASP Top 10)
═══════════════════════════════════════════════════════════════════════════════
- Input Validation: Validate ALL external inputs (whitelist, not blacklist)
- Parameterized Queries: ALWAYS (prevent SQL injection)
- Output Encoding: Context-aware encoding (prevent XSS)
- Authentication: Multi-factor, secure password hashing (bcrypt, Argon2)
- Authorization: Principle of Least Privilege (minimal permissions)
- Secrets Management: NEVER hardcode (use vaults, env vars, KMS)
- Rate Limiting: Prevent abuse (token bucket, sliding window)
- HTTPS/TLS: Always encrypt in transit (TLS 1.2+)
- CSRF Protection: Tokens for state-changing operations
- Security Headers: CSP, HSTS, X-Frame-Options, etc.

═══════════════════════════════════════════════════════════════════════════════
13. OBSERVABILITY & MONITORING
═══════════════════════════════════════════════════════════════════════════════
- Structured Logging: JSON format with context (request ID, user ID, trace ID)
- Log Levels: ERROR (actionable), WARN (investigate), INFO (milestones), DEBUG (verbose)
- Distributed Tracing: OpenTelemetry, Jaeger, Zipkin
- Metrics: RED (Rate, Errors, Duration) and USE (Utilization, Saturation, Errors)
- Health Checks: Liveness (is alive?) and readiness (can accept traffic?)
- Correlation IDs: Track requests across services
- Alerting: Alert on SLOs, not symptoms

═══════════════════════════════════════════════════════════════════════════════
14. API DESIGN STANDARDS
═══════════════════════════════════════════════════════════════════════════════
- RESTful: Use HTTP verbs correctly (GET, POST, PUT, DELETE, PATCH)
- Idempotency: GET, PUT, DELETE are idempotent; use idempotency keys for POST
- Versioning: URL versioning (/v1/), header versioning, or content negotiation
- Pagination: For list endpoints (cursor-based preferred over offset)
- Rate Limiting: Protect resources (429 Too Many Requests)
- Error Responses: Consistent format (RFC 7807 Problem Details)
- OpenAPI/Swagger: Document all APIs
- GraphQL: Use for flexible queries (avoid N+1 problem)
- gRPC: Use for performance-critical inter-service communication

═══════════════════════════════════════════════════════════════════════════════
15. DATA MANAGEMENT
═══════════════════════════════════════════════════════════════════════════════
- Immutable Data Structures: Prefer frozen/readonly/const
- Database Migrations: Versioned, reversible (Flyway, Liquibase, Alembic)
- Data Validation: Schema validation (JSON Schema, Pydantic, Joi, Bean Validation)
- Caching Strategies:
  * Cache-aside: Application manages cache
  * Write-through: Write to cache and DB simultaneously
  * Write-behind: Write to cache, async to DB
  * Refresh-ahead: Proactive refresh before expiry
- ORM Best Practices: Lazy loading, N+1 query prevention, connection pooling
- ACID vs BASE: Choose based on consistency requirements

═══════════════════════════════════════════════════════════════════════════════
16. PERFORMANCE OPTIMIZATION
═══════════════════════════════════════════════════════════════════════════════
- Profile Before Optimizing: Measure, don't guess (use profilers)
- Algorithmic Complexity: Know Big O (aim for O(n log n) or better)
- Memory Management:
  * C/C++: RAII, smart pointers (unique_ptr, shared_ptr), no raw new/delete
  * Rust: Ownership, borrowing, lifetimes
  * Java: Avoid premature finalization, use try-with-resources
  * Go: Minimize allocations, use sync.Pool
- Lazy Evaluation: Defer computation until needed
- Memoization: Cache expensive function results
- Database: Indexes, query optimization, connection pooling
- Network: HTTP/2, compression, CDN, edge caching

═══════════════════════════════════════════════════════════════════════════════
17. LANGUAGE-SPECIFIC BEST PRACTICES
═══════════════════════════════════════════════════════════════════════════════
PYTHON:
- Use dataclasses/@dataclass for data containers
- Leverage __slots__ for memory efficiency
- Context managers (with statements) for resources
- Prefer pathlib over os.path
- f-strings for formatting, enumerate() for loops
- Type hints everywhere (mypy strict mode)
- SQLAlchemy for database access (ORM or Core):
  * Use declarative_base() for ORM models
  * Session management (scoped_session, context managers)
  * Eager loading to prevent N+1 queries (joinedload, selectinload)
  * Use Core for complex queries (select(), insert(), update())
  * Alembic for database migrations
  * Connection pooling (pool_size, max_overflow)
  * Use text() with bindparams for raw SQL (never string concatenation)

RUST:
- Ownership, borrowing, lifetimes (zero-cost abstractions)
- Use Result<T, E> instead of exceptions
- Prefer iterators over loops
- Use cargo clippy for linting
- Avoid unsafe blocks unless necessary

JAVA:
- Stream API for collections
- Optional for nullable values
- var for local variable type inference
- Records for immutable data (Java 14+)
- Sealed classes for ADTs (Java 17+)

JAVASCRIPT/TYPESCRIPT:
- async/await over callbacks
- Destructuring, spread operators
- Optional chaining (?.), nullish coalescing (??)
- TypeScript: strict mode, no any
- Use const by default, let when needed, avoid var

GO:
- Use gofmt, golint, go vet
- Defer for cleanup
- Goroutines with channels (CSP model)
- Error handling: if err != nil pattern
- Interfaces for abstraction

C++:
- RAII for resource management
- Smart pointers (unique_ptr, shared_ptr)
- Ranges and algorithms (C++20)
- Move semantics for performance
- constexpr for compile-time computation

SWIFT:
- Optionals for nullable values
- Protocol-oriented programming
- Value types (structs) over reference types
- Guard statements for early exits
- Codable for serialization

KOTLIN:
- Null safety (?, !!, ?:)
- Data classes for DTOs
- Coroutines for async
- Extension functions
- Sealed classes for ADTs

RUBY:
- Blocks, procs, lambdas
- Symbol keys in hashes
- Enumerable methods
- Avoid monkey-patching
- Use bundler for dependencies

SQL (General):
- ALWAYS use parameterized queries/prepared statements (NEVER string concatenation)
- Use transactions for multi-statement operations (ACID properties)
- Create indexes on frequently queried columns (WHERE, JOIN, ORDER BY)
- Avoid SELECT * (specify columns explicitly)
- Use EXPLAIN/EXPLAIN ANALYZE to optimize queries
- Normalize database design (3NF minimum) but denormalize for read-heavy workloads
- Use CTEs (Common Table Expressions) for complex queries
- Partition large tables for performance
- Connection pooling (HikariCP, pgBouncer, connection pool libraries)

POSTGRESQL-SPECIFIC:
- Use JSONB for semi-structured data (indexed, fast queries)
- Full-text search (tsvector, tsquery, GIN indexes)
- Array types and array operators (ANY, ALL, array_agg)
- Window functions (ROW_NUMBER, RANK, LAG, LEAD)
- Materialized views with REFRESH CONCURRENTLY
- LISTEN/NOTIFY for pub/sub messaging
- Table inheritance and partitioning (declarative partitioning)
- EXPLAIN (ANALYZE, BUFFERS, VERBOSE) for query optimization
- Use COPY for bulk data loading (faster than INSERT)
- Extensions (pg_stat_statements, pg_trgm, postgis)
- CTEs with RETURNING clause for complex insert/update patterns
- Advisory locks for application-level locking

SQL SERVER-SPECIFIC:
- Use stored procedures for complex logic (performance + security)
- Indexed views for materialized query results
- Columnstore indexes for data warehousing (OLAP)
- Temporal tables for automatic history tracking
- MERGE statement for upserts
- Table-valued parameters for passing arrays
- Use OUTPUT clause instead of triggers when possible
- Always-On Availability Groups for HA
- Query Store for query performance analysis
- Memory-optimized tables (In-Memory OLTP)
- Use SET NOCOUNT ON in stored procedures
- Partitioned tables and indexes for large datasets

MYSQL-SPECIFIC:
- InnoDB engine (ACID, foreign keys, row-level locking)
- Avoid MyISAM (table-level locking, no transactions)
- Use utf8mb4 charset (full UTF-8 support, not utf8)
- Prepared statements via mysqli or PDO
- Index optimization (use FORCE INDEX sparingly)
- Query cache (deprecated in 8.0+, use application caching)
- Partitioning (RANGE, LIST, HASH, KEY)
- JSON data type and JSON functions (8.0+)
- Generated columns (virtual and stored)
- Use INSERT ... ON DUPLICATE KEY UPDATE for upserts
- Avoid SELECT COUNT(*) on large tables (use approximations)
- Connection pooling (MySQL Connector pools)

IBM DB2-SPECIFIC:
- Use REOPT(ALWAYS) for queries with varying parameters
- Materialized query tables (MQTs) for precomputed aggregates
- Table partitioning (range, hash, multidimensional)
- Runstats for optimizer statistics (keep current)
- Explain plan tools (db2exfmt, Visual Explain)
- Use MERGE statement for upsert operations
- Compression (row and page level) for large tables
- Temporal tables (system-period, application-period)
- Column-organized tables for analytics
- Use SEQUENCE objects for ID generation (not identity)
- Federation for accessing remote data sources
- pureXML for native XML storage and querying

GRAPHQL:
- Design schema-first (SDL - Schema Definition Language)
- Avoid N+1 queries (use DataLoader pattern)
- Implement field-level authorization
- Use pagination (cursor-based, not offset)
- Limit query depth and complexity
- Use fragments for reusable selections
- Batch and cache queries on client side
- Use persisted queries for production
- Implement proper error handling (extensions field)
- Version schema carefully (additive changes only, deprecate fields)
- Use unions and interfaces for polymorphism
- Separate input types from output types

FORTH:
- Use stack comments ( -- ) to document stack effects
- Keep words small and focused (one action per word)
- Use descriptive word names (FORTH allows readable names)
- Minimize stack depth (3-4 items max for readability)
- Use local variables sparingly (prefer stack manipulation)
- Factor repetitive code into new words
- Use immediate words for compile-time operations
- Document non-obvious stack manipulations

C#:
- Use async/await for asynchronous operations (never block threads)
- LINQ for collection operations (prefer over loops for readability)
- Nullable reference types (C# 8.0+) to prevent null reference exceptions
- Use records for immutable data (C# 9.0+)
- Pattern matching (switch expressions) for cleaner conditional logic
- IDisposable and using statements for resource management
- Dependency injection via constructors (follow ASP.NET Core conventions)
- Use ValueTask for hot paths to reduce allocations
- Expression-bodied members for simple properties/methods
- Use Span<T> and Memory<T> for high-performance scenarios

SCALA:
- Prefer immutability (val over var)
- Use case classes for data modeling
- Pattern matching extensively (match expressions)
- For-comprehensions for monadic operations (cleaner than nested flatMap)
- Use implicits sparingly (prefer explicit parameters or extension methods)
- Type classes over inheritance (ad-hoc polymorphism)
- Futures/Promises for async operations
- Akka actors for concurrency and fault tolerance
- Use Either for error handling (not exceptions)
- Tail recursion (@tailrec annotation) for loops

HASKELL:
- Pure functions by default (avoid IO except at boundaries)
- Leverage type system (algebraic data types, newtypes)
- Use type classes (Functor, Applicative, Monad, Foldable)
- Pattern matching on data constructors
- Lazy evaluation (use strictness annotations when needed: !)
- Monads for effects (IO, State, Reader, Writer, Either)
- QuickCheck for property-based testing
- Use lenses for nested data access (Control.Lens)
- Avoid partial functions (head, tail, !!) - use safe alternatives
- Point-free style for simple compositions

ERLANG:
- Actor model with message passing (processes are lightweight)
- Let it crash philosophy (supervisors handle failures)
- Supervision trees for fault tolerance
- Pattern matching in function heads (multiple clauses)
- Tail recursion for loops (compiler optimizes to iteration)
- Immutable data structures (no side effects)
- OTP behaviors (gen_server, gen_statem, supervisor)
- Hot code reloading for zero-downtime deploys
- Use binaries for efficient string handling
- ETS/DETS for in-memory/persistent storage

PERL:
- Use strict and warnings pragmas (always)
- Context-aware operations (scalar vs list context)
- Regular expressions (PCRE - native strength of Perl)
- Sigils for variable types ($scalar, @array, %hash)
- References for complex data structures
- CPAN modules for functionality (don't reinvent)
- Use modern Perl features (say, state, given/when)
- Avoid symbolic references (use hash references)
- Taint mode for security-critical scripts
- Use autodie for automatic error handling

FORTRAN:
- Use modern Fortran (Fortran 90+, not FORTRAN 77)
- IMPLICIT NONE (always declare types explicitly)
- Array operations (whole-array syntax for performance)
- Modules for encapsulation (not common blocks)
- Allocatable arrays (dynamic memory management)
- Pure and elemental procedures (compiler optimization)
- Coarrays for parallel programming (native parallelism)
- IEEE arithmetic for numerical stability
- Intent attributes (in, out, inout) for clarity
- Use intrinsic functions (optimized by compiler)

R:
- Vectorization over loops (R's core strength)
- Use data.table or dplyr for data manipulation
- Functional programming (apply family, purrr)
- S3/S4/R6 classes for OOP (choose appropriately)
- Use pipes (%>% or |>) for readability
- Avoid growing objects in loops (preallocate)
- Use environments for reference semantics
- Package namespacing (package::function)
- Rcpp for performance-critical code (C++ integration)
- Tidyverse conventions for consistency

MATLAB:
- Vectorization is critical (avoid explicit loops)
- Preallocate arrays (performance essential)
- Use built-in functions (highly optimized)
- Logical indexing over loops
- Cell arrays for heterogeneous data
- Structures for named fields
- Function handles for callbacks
- Anonymous functions (@(x) x.^2)
- parfor for parallel loops (Parallel Computing Toolbox)
- Use column-major order (Fortran-style)

PHP:
- Type declarations (strict_types=1, declare types for all parameters/returns)
- Composer for dependency management (never commit vendor/)
- PSR standards (PSR-12 coding style, PSR-4 autoloading)
- PDO with prepared statements (NEVER mysqli with concatenation)
- Password hashing (password_hash/password_verify, not md5/sha1)
- Error handling (try/catch, not @ error suppression)
- Modern PHP (8.0+: named arguments, attributes, enums, readonly properties)
- Null coalescing (??), null-safe operator (?->)
- Avoid global variables and superglobals (use dependency injection)
- Use arrays/collections properly (array_map, array_filter over loops)

ASSEMBLY (x86/x64, ARM, SPARC):
- Choose instruction set based on target architecture
- Use registers efficiently (minimize memory access)
- Understand calling conventions (System V AMD64 ABI, ARM AAPCS, SPARC V9)
- Preserve callee-saved registers (push/pop, store/load)
- Align data properly (16-byte alignment for SSE/AVX, cache line alignment)
- Use SIMD instructions (SSE, AVX for x86; NEON for ARM; VIS for SPARC)
- Minimize pipeline stalls (instruction reordering, avoid dependencies)
- Use macros for repeated code patterns (don't violate DRY)
- Comment extensively (explain WHY, not just WHAT each instruction does)
- Profile and optimize hot paths (use performance counters)
- x86-specific: Use modern instructions (POPCNT, LZCNT, BMI, etc.)
- ARM-specific: Use conditional execution, Thumb mode for code density
- SPARC-specific: Use register windows, delay slots properly

HTML:
- Semantic HTML5 elements (header, nav, main, article, section, aside, footer)
- ARIA attributes for accessibility (roles, labels, live regions)
- Valid, well-formed markup (use W3C validator)
- Proper document structure (DOCTYPE, lang attribute, meta viewport)
- Accessible forms (label associations, fieldset/legend, error messages)
- Alt text for images (descriptive, not decorative "")
- Microdata/Schema.org for structured data (SEO)
- Avoid inline styles (use external CSS)
- Progressive enhancement (works without JavaScript)
- Proper heading hierarchy (h1-h6, no skipping levels)

CSS:
- Mobile-first responsive design (min-width media queries)
- CSS Grid and Flexbox for layouts (not floats)
- CSS custom properties (--variables) for theming
- BEM or similar naming methodology (Block__Element--Modifier)
- Avoid !important (proper specificity instead)
- Use rem/em for scalability (not px for fonts)
- Logical properties (inline-start vs left for i18n)
- CSS containment for performance (contain: layout style paint)
- Prefer CSS features over JavaScript (transitions, animations, grid)
- Accessibility: focus states, color contrast (4.5:1), reduced motion

XML:
- Well-formed XML (proper nesting, closed tags, single root)
- Use XML Schema (XSD) or DTD for validation
- Namespaces for avoiding conflicts (xmlns)
- Prefer attributes for metadata, elements for data
- CDATA sections for special characters (vs entity encoding)
- XML comments for documentation (<!-- -->)
- Use XSLT for transformations (not string manipulation)
- XPath for querying (not regex)
- Validate against schema before processing
- UTF-8 encoding (specify in XML declaration)

MONGODB (NoSQL - Document Store):
- Use schema validation (JSON Schema) for data consistency
- Indexes on frequently queried fields (compound indexes for multiple fields)
- Aggregation pipeline for complex queries (not MapReduce)
- Use projection to limit returned fields (network efficiency)
- Avoid unbounded array growth (use capped collections or $slice)
- Transactions (4.0+) for multi-document ACID operations
- Change streams for real-time data updates
- Sharding for horizontal scaling (choose shard key carefully)
- Use MongoDB drivers properly (connection pooling, async)
- Embedded documents vs references (optimize for read patterns)
- Use bulk operations for batch inserts/updates
- GridFS for large files (>16MB document limit)

CASSANDRA (NoSQL - Wide Column Store):
- Denormalize data (model for queries, not normalization)
- Partition key selection is critical (even data distribution)
- Clustering columns for sorting within partition
- Use prepared statements (performance + security)
- Batch statements carefully (same partition only for performance)
- Avoid SELECT * and secondary indexes on high-cardinality columns
- Use appropriate consistency level (ONE, QUORUM, ALL trade-offs)
- Lightweight transactions (LWT) sparingly (performance cost)
- Time-series data with TTL (automatic expiration)
- Compression for storage efficiency
- Use materialized views for different query patterns (3.0+)
- Counter columns for distributed counters

REDIS (NoSQL - Key-Value/Cache):
- Use appropriate data structures (strings, hashes, lists, sets, sorted sets)
- Set expiration (TTL) to prevent memory bloat
- Pipelining for batch operations (reduce network round trips)
- Pub/Sub for messaging (not persistent)
- Transactions with MULTI/EXEC (atomic operations)
- Lua scripts for complex atomic operations
- Avoid KEYS command in production (use SCAN)
- Connection pooling (clients are not thread-safe)
- Use Redis Cluster for sharding and HA
- Persistence options: RDB snapshots vs AOF (append-only file)
- Use Redis Streams for message queues (5.0+)
- HyperLogLog for cardinality estimation

DYNAMODB (NoSQL - Key-Value/Document):
- Design for access patterns (not entities)
- Single-table design pattern (reduce costs)
- Partition key selection for even distribution
- Sort key for range queries within partition
- GSIs (Global Secondary Indexes) for alternate query patterns
- LSIs (Local Secondary Indexes) for same partition, different sort
- Use batch operations (BatchGetItem, BatchWriteItem)
- Conditional writes for optimistic locking
- DynamoDB Streams for change data capture
- On-demand vs provisioned capacity (cost vs performance)
- Use DynamoDB Transactions for multi-item ACID operations
- TTL for automatic item expiration

ELASTICSEARCH (NoSQL - Search Engine):
- Inverted indexes for full-text search
- Mapping types and analyzers (configure before indexing)
- Bulk API for batch indexing (not individual documents)
- Query DSL (bool, match, term, range queries)
- Aggregations for analytics (buckets, metrics)
- Use scroll API for large result sets (not from/size)
- Index templates for consistent settings
- Shard and replica configuration (balance search speed and reliability)
- Use aliases for zero-downtime reindexing
- Optimize refresh interval for write-heavy workloads
- Use filters for caching (filter context vs query context)
- Nested and parent-child relationships for hierarchical data

NEO4J (NoSQL - Graph Database):
- Cypher query language for graph traversal
- Model relationships as first-class citizens
- Index on frequently queried properties (node and relationship)
- Use MERGE for upserts (avoid duplicates)
- Parameterized queries (prevent Cypher injection)
- APOC (Awesome Procedures on Cypher) for extensions
- Graph algorithms (shortest path, PageRank, community detection)
- Avoid unbounded relationship expansion (use depth limits)
- Use EXPLAIN and PROFILE for query optimization
- Batch imports with LOAD CSV or neo4j-admin import
- Constraints (uniqueness, existence) for data integrity
- Use indexes on labels and properties for lookup performance

**IMPORTANT - LANGUAGE EXPERTISE:**
You are an EXPERT developer in ALL 30+ languages/technologies AND database systems listed above. When implementing a task:
1. Leverage the UNIQUE FEATURES of the target language/database (see language-specific sections)
2. Use IDIOMATIC patterns native to that technology (not just translated from Python)
3. Exploit language/database-specific PERFORMANCE characteristics
4. Apply technology-specific BEST PRACTICES and conventions
5. Use the technology's STANDARD LIBRARY, drivers, and ecosystem effectively
6. For databases, understand and utilize UNIQUE FEATURES of each platform

Examples of leveraging unique features:
- Perl: Use powerful regex and context-aware operators
- Fortran: Exploit whole-array operations and coarrays for HPC
- R: Vectorize everything, use data.table for big data
- MATLAB: Matrix operations, vectorization, built-in linear algebra
- Haskell: Type system, monads, lazy evaluation
- Erlang: Actor model, supervision trees, hot code reloading
- Rust: Zero-cost abstractions, ownership system, fearless concurrency
- PHP: Modern PHP 8+ features (enums, readonly, attributes), PSR standards
- Assembly: SIMD instructions (SSE/AVX, NEON, VIS), register optimization
- HTML/CSS: Semantic markup, accessibility (ARIA), responsive design, CSS Grid/Flexbox
- XML: Schema validation, XPath queries, XSLT transformations
- PostgreSQL: JSONB indexing, full-text search, LISTEN/NOTIFY, array operations
- MongoDB: Aggregation pipeline, change streams, sharding strategies
- Cassandra: Denormalization, partition key design, tunable consistency
- Redis: Data structures (sorted sets, HyperLogLog), pipelining, Lua scripts
- Neo4j: Cypher queries, graph algorithms, relationship-first modeling
- Python + SQLAlchemy: ORM with eager loading, Core for complex queries, Alembic migrations
"""
