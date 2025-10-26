#!/usr/bin/env python3
"""
Store Refactoring Instructions in KG and RAG

Stores all refactoring guidelines and best practices for retrieval by developers
"""

from rag_agent import RAGAgent
from knowledge_graph import KnowledgeGraph


def store_refactoring_instructions_in_rag(rag_agent: RAGAgent):
    """Store refactoring instructions in RAG database"""

    print("Storing refactoring instructions in RAG...")

    # 1. Loop to Comprehension Instructions
    rag_agent.store_artifact(
        artifact_type="architecture_decision",
        card_id="REFACTORING-001",
        task_title="Loop to Comprehension Refactoring",
        content="""
# Loop to Comprehension Refactoring Pattern

## Rule
Convert simple for loops to list/dict/set comprehensions when:
- Loop body has only 1-2 statements
- Loop is building a list/dict/set via append/add/update
- No complex conditional logic

## Example

### Before:
```python
results = []
for item in items:
    results.append(item.upper())
```

### After:
```python
results = [item.upper() for item in items]
```

## Benefits
- More Pythonic
- Often faster
- More readable for simple cases
- Reduces lines of code

## When NOT to use
- Complex conditional logic
- Multiple operations per iteration
- Side effects needed (logging, API calls, etc.)
        """,
        metadata={
            "refactoring_type": "loop_to_comprehension",
            "priority": "high",
            "language": "python"
        }
    )

    # 2. If/Elif to Dictionary Mapping
    rag_agent.store_artifact(
        artifact_type="architecture_decision",
        card_id="REFACTORING-002",
        task_title="If/Elif Chain to Dictionary Mapping",
        content="""
# If/Elif Chain to Dictionary Mapping Pattern

## Rule
Replace if/elif chains with dictionary lookups when:
- 3+ branches
- Each branch returns a similar type of value
- No complex conditional expressions

## Example

### Before:
```python
if status == "PASS":
    message = "All tests passed"
elif status == "FAIL":
    message = "Tests failed"
elif status == "SKIP":
    message = "Tests skipped"
else:
    message = "Unknown status"
```

### After:
```python
status_messages = {
    "PASS": "All tests passed",
    "FAIL": "Tests failed",
    "SKIP": "Tests skipped"
}
message = status_messages.get(status, "Unknown status")
```

## Benefits
- More maintainable
- Easier to add new cases
- Configuration-driven
- Eliminates repeated code structure

## Advanced: Dictionary of Functions
```python
status_handlers = {
    "PASS": lambda: handle_success(),
    "FAIL": lambda: handle_failure(),
    "SKIP": lambda: handle_skip()
}
handler = status_handlers.get(status, lambda: handle_unknown())
result = handler()
```
        """,
        metadata={
            "refactoring_type": "if_elif_to_mapping",
            "priority": "high",
            "language": "python"
        }
    )

    # 3. Extract Long Methods
    rag_agent.store_artifact(
        artifact_type="architecture_decision",
        card_id="REFACTORING-003",
        task_title="Extract Long Methods Pattern",
        content="""
# Extract Long Methods Pattern

## Rule
Extract helper methods from functions longer than 50 lines:
- Identify distinct phases/responsibilities
- Extract each phase into separate method
- Use descriptive method names

## Example

### Before (100 lines):
```python
def process_order(order):
    # Lines 1-30: Validation
    if not order.items:
        raise ValueError("Empty order")
    # ... 30 lines of validation

    # Lines 31-60: Calculate totals
    subtotal = 0
    for item in order.items:
        subtotal += item.price * item.quantity
    # ... 30 lines of calculation

    # Lines 61-100: Send notification
    email_body = create_email(order)
    send_email(order.customer.email, email_body)
    # ... 40 lines of notification
```

### After (20 lines):
```python
def process_order(order):
    self._validate_order(order)
    totals = self._calculate_order_totals(order)
    self._send_order_notification(order, totals)
    return totals

def _validate_order(self, order):
    # 30 lines of validation

def _calculate_order_totals(self, order):
    # 30 lines of calculation
    return totals

def _send_order_notification(self, order, totals):
    # 40 lines of notification
```

## Benefits
- Single Responsibility Principle
- Easier to test
- Improved readability
- Better code reuse
        """,
        metadata={
            "refactoring_type": "extract_method",
            "priority": "critical",
            "language": "python"
        }
    )

    # 4. Use next() for First Match
    rag_agent.store_artifact(
        artifact_type="architecture_decision",
        card_id="REFACTORING-004",
        task_title="Use next() for First Match Pattern",
        content="""
# Use next() for First Match Pattern

## Rule
Replace loops that find the first matching element with next() and generator

## Example

### Before:
```python
result = None
for item in items:
    if item.status == "active":
        result = item
        break
```

### After:
```python
result = next((item for item in items if item.status == "active"), None)
```

## Benefits
- More Pythonic
- Single expression
- Explicit default value
- Lazy evaluation (stops at first match)

## Advanced: With Dictionary
```python
# Find first column with matching ID
column = next((col for col in columns if col.get('column_id') == column_id), None)
```
        """,
        metadata={
            "refactoring_type": "next_for_first_match",
            "priority": "medium",
            "language": "python"
        }
    )

    # 5. Use Collections Module
    rag_agent.store_artifact(
        artifact_type="architecture_decision",
        card_id="REFACTORING-005",
        task_title="Use Collections Module (defaultdict, Counter)",
        content="""
# Use Collections Module Pattern

## Rule
Use specialized collections instead of manual tracking:
- defaultdict for counting/grouping
- Counter for frequency counting
- chain for flattening iterables

## Example 1: defaultdict

### Before:
```python
counts = {}
for item in items:
    if item.category not in counts:
        counts[item.category] = 0
    counts[item.category] += 1
```

### After:
```python
from collections import defaultdict
counts = defaultdict(int)
for item in items:
    counts[item.category] += 1
```

## Example 2: Counter

### Before:
```python
issue_types = {}
for issue in issues:
    issue_type = issue.get('type', 'unknown')
    if issue_type not in issue_types:
        issue_types[issue_type] = 0
    issue_types[issue_type] += 1
```

### After:
```python
from collections import Counter
issue_types = Counter(issue.get('type', 'unknown') for issue in issues)
```

## Example 3: chain

### Before:
```python
all_issues = []
for task in tasks:
    all_issues.extend(task.get('issues', []))
```

### After:
```python
from itertools import chain
all_issues = list(chain.from_iterable(task.get('issues', []) for task in tasks))
```

## Benefits
- Standard library tools
- More efficient
- Clearer intent
- Less error-prone
        """,
        metadata={
            "refactoring_type": "use_collections",
            "priority": "medium",
            "language": "python"
        }
    )

    # 6. Stream Operations (Java, JavaScript, Rust, Go)
    rag_agent.store_artifact(
        artifact_type="architecture_decision",
        card_id="REFACTORING-006",
        task_title="Stream/Functional Operations (Multi-Language)",
        content="""
# Stream/Functional Operations Pattern

## Rule
Use stream/functional operations instead of imperative loops

## Java Example

### Before:
```java
List<String> results = new ArrayList<>();
for (User user : users) {
    if (user.isActive()) {
        results.add(user.getName().toUpperCase());
    }
}
```

### After:
```java
List<String> results = users.stream()
    .filter(User::isActive)
    .map(user -> user.getName().toUpperCase())
    .collect(Collectors.toList());
```

## JavaScript/TypeScript Example

### Before:
```javascript
const results = [];
for (const item of items) {
    if (item.active) {
        results.push(item.name.toUpperCase());
    }
}
```

### After:
```javascript
const results = items
    .filter(item => item.active)
    .map(item => item.name.toUpperCase());
```

## Rust Example

### Before:
```rust
let mut results = Vec::new();
for item in items {
    if item.is_active {
        results.push(item.name.to_uppercase());
    }
}
```

### After:
```rust
let results: Vec<_> = items
    .iter()
    .filter(|item| item.is_active)
    .map(|item| item.name.to_uppercase())
    .collect();
```

## Go Example

### Before:
```go
results := make([]string, 0)
for _, item := range items {
    if item.Active {
        results = append(results, strings.ToUpper(item.Name))
    }
}
```

### After (using generics in Go 1.18+):
```go
results := lo.FilterMap(items, func(item Item, _ int) (string, bool) {
    if item.Active {
        return strings.ToUpper(item.Name), true
    }
    return "", false
})
```

## Benefits
- More declarative
- Chainable operations
- Easier to parallelize
- Self-documenting code
        """,
        metadata={
            "refactoring_type": "stream_operations",
            "priority": "high",
            "language": "java,javascript,typescript,rust,go"
        }
    )

    # 7. Strategy Pattern for Conditionals (All Languages)
    rag_agent.store_artifact(
        artifact_type="architecture_decision",
        card_id="REFACTORING-007",
        task_title="Strategy Pattern for Complex Conditionals",
        content="""
# Strategy Pattern for Complex Conditionals

## Rule
Replace complex switch/case or if/elif chains with strategy pattern when:
- Multiple algorithms for same operation
- Behavior varies by type/mode/state
- Code duplication across branches

## Java Example

### Before:
```java
public void processPayment(String paymentType, double amount) {
    if (paymentType.equals("CREDIT_CARD")) {
        // 50 lines of credit card processing
    } else if (paymentType.equals("PAYPAL")) {
        // 50 lines of PayPal processing
    } else if (paymentType.equals("CRYPTO")) {
        // 50 lines of crypto processing
    }
}
```

### After:
```java
interface PaymentStrategy {
    void process(double amount);
}

class CreditCardStrategy implements PaymentStrategy {
    public void process(double amount) { /* ... */ }
}

class PayPalStrategy implements PaymentStrategy {
    public void process(double amount) { /* ... */ }
}

Map<String, PaymentStrategy> strategies = Map.of(
    "CREDIT_CARD", new CreditCardStrategy(),
    "PAYPAL", new PayPalStrategy(),
    "CRYPTO", new CryptoStrategy()
);

strategies.get(paymentType).process(amount);
```

## TypeScript Example

### Before:
```typescript
function validateField(type: string, value: any): boolean {
    switch(type) {
        case 'email': return /^[^@]+@[^@]+$/.test(value);
        case 'phone': return /^\d{10}$/.test(value);
        case 'zip': return /^\d{5}$/.test(value);
        default: return false;
    }
}
```

### After:
```typescript
type Validator = (value: any) => boolean;

const validators: Record<string, Validator> = {
    email: (value) => /^[^@]+@[^@]+$/.test(value),
    phone: (value) => /^\d{10}$/.test(value),
    zip: (value) => /^\d{5}$/.test(value)
};

function validateField(type: string, value: any): boolean {
    return validators[type]?.(value) ?? false;
}
```

## Rust Example

### Before:
```rust
fn handle_event(event_type: &str, data: &str) {
    match event_type {
        "CREATE" => { /* 30 lines */ },
        "UPDATE" => { /* 30 lines */ },
        "DELETE" => { /* 30 lines */ },
        _ => {}
    }
}
```

### After:
```rust
trait EventHandler {
    fn handle(&self, data: &str);
}

struct CreateHandler;
impl EventHandler for CreateHandler {
    fn handle(&self, data: &str) { /* ... */ }
}

let handlers: HashMap<&str, Box<dyn EventHandler>> = [
    ("CREATE", Box::new(CreateHandler) as Box<dyn EventHandler>),
    ("UPDATE", Box::new(UpdateHandler) as Box<dyn EventHandler>),
    ("DELETE", Box::new(DeleteHandler) as Box<dyn EventHandler>),
].iter().cloned().collect();

handlers.get(event_type).map(|h| h.handle(data));
```

## Benefits
- Open/Closed Principle
- Easier to add new strategies
- Better testability
- Eliminates code duplication
        """,
        metadata={
            "refactoring_type": "strategy_pattern",
            "priority": "critical",
            "language": "java,python,javascript,typescript,rust,go"
        }
    )

    # 8. Null Object Pattern (All Languages)
    rag_agent.store_artifact(
        artifact_type="architecture_decision",
        card_id="REFACTORING-008",
        task_title="Null Object Pattern",
        content="""
# Null Object Pattern

## Rule
Replace null checks with null object to eliminate defensive programming

## Java Example

### Before:
```java
User user = userService.findById(id);
if (user != null) {
    logger.log(user.getName());
    sendEmail(user.getEmail());
}
```

### After:
```java
class NullUser extends User {
    public String getName() { return "Guest"; }
    public String getEmail() { return "noreply@example.com"; }
    public boolean isNull() { return true; }
}

User user = userService.findById(id).orElse(new NullUser());
logger.log(user.getName());
if (!user.isNull()) {
    sendEmail(user.getEmail());
}
```

## Python Example

### Before:
```python
config = get_config()
if config is not None:
    timeout = config.get('timeout', 30)
    retries = config.get('retries', 3)
else:
    timeout = 30
    retries = 3
```

### After:
```python
class NullConfig:
    def get(self, key, default=None):
        defaults = {'timeout': 30, 'retries': 3}
        return defaults.get(key, default)

    def is_null(self):
        return True

config = get_config() or NullConfig()
timeout = config.get('timeout')
retries = config.get('retries')
```

## TypeScript Example

### Before:
```typescript
const user = await findUser(id);
if (user) {
    analytics.track(user.id, 'login');
    notify(user.email, 'Welcome back!');
}
```

### After:
```typescript
class NullUser implements IUser {
    id = '';
    email = 'noreply@example.com';
    isNull() { return true; }
}

const user = await findUser(id) ?? new NullUser();
if (!user.isNull()) {
    analytics.track(user.id, 'login');
    notify(user.email, 'Welcome back!');
}
```

## Benefits
- Eliminates null checks
- Polymorphic behavior
- Cleaner code
- Default behavior built-in
        """,
        metadata={
            "refactoring_type": "null_object_pattern",
            "priority": "medium",
            "language": "java,python,javascript,typescript,go,rust"
        }
    )

    # 9. Builder Pattern for Complex Construction
    rag_agent.store_artifact(
        artifact_type="architecture_decision",
        card_id="REFACTORING-009",
        task_title="Builder Pattern for Complex Object Construction",
        content="""
# Builder Pattern for Complex Object Construction

## Rule
Use builder pattern when:
- Constructor has 4+ parameters
- Many optional parameters
- Step-by-step construction needed

## Java Example

### Before:
```java
Order order = new Order(
    customerId,
    items,
    shippingAddress,
    billingAddress,
    paymentMethod,
    null,  // coupon
    false, // giftWrap
    null,  // giftMessage
    true   // sendConfirmation
);
```

### After:
```java
Order order = Order.builder()
    .customerId(customerId)
    .items(items)
    .shippingAddress(shippingAddress)
    .billingAddress(billingAddress)
    .paymentMethod(paymentMethod)
    .sendConfirmation(true)
    .build();
```

## Python Example

### Before:
```python
query = DatabaseQuery(
    table='users',
    columns=['id', 'name', 'email'],
    where={'active': True, 'role': 'admin'},
    order_by='name',
    limit=100,
    offset=0,
    join=None,
    group_by=None
)
```

### After:
```python
query = (DatabaseQuery()
    .from_table('users')
    .select(['id', 'name', 'email'])
    .where(active=True, role='admin')
    .order_by('name')
    .limit(100)
    .build())
```

## Rust Example

### Before:
```rust
let config = Config {
    host: "localhost".to_string(),
    port: 8080,
    timeout_ms: 5000,
    retries: 3,
    ssl_enabled: false,
    ssl_cert: None,
    ssl_key: None,
    log_level: LogLevel::Info,
};
```

### After:
```rust
let config = Config::builder()
    .host("localhost")
    .port(8080)
    .timeout_ms(5000)
    .retries(3)
    .log_level(LogLevel::Info)
    .build()?;
```

## TypeScript Example

### Before:
```typescript
const request = new HttpRequest(
    'POST',
    '/api/users',
    { name: 'John' },
    { 'Content-Type': 'application/json', 'Authorization': token },
    5000,
    3,
    true
);
```

### After:
```typescript
const request = new HttpRequestBuilder()
    .method('POST')
    .url('/api/users')
    .body({ name: 'John' })
    .header('Content-Type', 'application/json')
    .header('Authorization', token)
    .timeout(5000)
    .retries(3)
    .build();
```

## Benefits
- Readable construction
- Immutable objects
- Validation during build
- Named parameters effect
- Optional parameters clear
        """,
        metadata={
            "refactoring_type": "builder_pattern",
            "priority": "high",
            "language": "java,python,javascript,typescript,rust,go"
        }
    )

    # 10. Early Return Pattern (All Languages)
    rag_agent.store_artifact(
        artifact_type="architecture_decision",
        card_id="REFACTORING-010",
        task_title="Early Return Pattern (Guard Clauses)",
        content="""
# Early Return Pattern (Guard Clauses)

## Rule
Replace nested if statements with early returns to reduce complexity

## Python Example

### Before:
```python
def process_user(user):
    if user is not None:
        if user.is_active:
            if user.has_permission('write'):
                if user.quota_remaining > 0:
                    # actual logic here
                    return perform_action(user)
                else:
                    return "No quota"
            else:
                return "No permission"
        else:
            return "Inactive user"
    else:
        return "User not found"
```

### After:
```python
def process_user(user):
    if user is None:
        return "User not found"

    if not user.is_active:
        return "Inactive user"

    if not user.has_permission('write'):
        return "No permission"

    if user.quota_remaining <= 0:
        return "No quota"

    return perform_action(user)
```

## Java Example

### Before:
```java
public Result processOrder(Order order) {
    if (order != null) {
        if (order.getItems().size() > 0) {
            if (order.getCustomer() != null) {
                if (order.getCustomer().hasValidPayment()) {
                    return processPayment(order);
                }
            }
        }
    }
    return Result.failure("Invalid order");
}
```

### After:
```java
public Result processOrder(Order order) {
    if (order == null) {
        return Result.failure("Order is null");
    }

    if (order.getItems().isEmpty()) {
        return Result.failure("No items");
    }

    if (order.getCustomer() == null) {
        return Result.failure("No customer");
    }

    if (!order.getCustomer().hasValidPayment()) {
        return Result.failure("Invalid payment");
    }

    return processPayment(order);
}
```

## JavaScript/TypeScript Example

### Before:
```typescript
function validateInput(data: FormData): string | null {
    if (data.name) {
        if (data.email) {
            if (data.email.includes('@')) {
                if (data.age >= 18) {
                    return null; // valid
                } else {
                    return "Must be 18+";
                }
            } else {
                return "Invalid email";
            }
        } else {
            return "Email required";
        }
    } else {
        return "Name required";
    }
}
```

### After:
```typescript
function validateInput(data: FormData): string | null {
    if (!data.name) return "Name required";
    if (!data.email) return "Email required";
    if (!data.email.includes('@')) return "Invalid email";
    if (data.age < 18) return "Must be 18+";

    return null; // valid
}
```

## Rust Example

### Before:
```rust
fn validate_config(config: &Config) -> Result<(), String> {
    if config.host.is_some() {
        if config.port > 0 {
            if config.timeout_ms > 0 {
                Ok(())
            } else {
                Err("Invalid timeout".to_string())
            }
        } else {
            Err("Invalid port".to_string())
        }
    } else {
        Err("Missing host".to_string())
    }
}
```

### After:
```rust
fn validate_config(config: &Config) -> Result<(), String> {
    if config.host.is_none() {
        return Err("Missing host".to_string());
    }

    if config.port <= 0 {
        return Err("Invalid port".to_string());
    }

    if config.timeout_ms <= 0 {
        return Err("Invalid timeout".to_string());
    }

    Ok(())
}
```

## Benefits
- Reduced cyclomatic complexity
- Easier to read and understand
- Fail fast principle
- Reduced indentation
        """,
        metadata={
            "refactoring_type": "early_return",
            "priority": "critical",
            "language": "python,java,javascript,typescript,rust,go"
        }
    )

    # 11. Generator Pattern for Memory Efficiency
    rag_agent.store_artifact(
        artifact_type="architecture_decision",
        card_id="REFACTORING-011",
        task_title="Generator Pattern for Memory Efficiency",
        content="""
# Generator Pattern for Memory Efficiency

## Rule
Use generators when processing large datasets or when only one element is needed at a time:
- Replace list building with yield statements
- Use generator expressions instead of list comprehensions when iterating once
- Avoid loading entire collections into memory when streaming is sufficient
- Use generators with next() for first-match searches

## Python Example

### Before (List):
```python
def get_active_users(users):
    active = []
    for user in users:
        if user.is_active:
            active.append(user)
    return active

# Or even with comprehension:
def get_active_users(users):
    return [user for user in users if user.is_active]

# Usage - loads all users into memory
active_users = get_active_users(million_users)
first_active = active_users[0]  # Only need first, but loaded all!
```

### After (Generator):
```python
def get_active_users(users):
    # Generator yielding active users one at a time
    for user in users:
        if user.is_active:
            yield user

# Or with generator expression:
def get_active_users(users):
    return (user for user in users if user.is_active)

# Usage - memory efficient, lazy evaluation
active_users = get_active_users(million_users)
first_active = next(active_users, None)  # Only processes until first match!
```

### First-Match Pattern with next():
```python
# Before: Iterates entire list
def find_user_by_id(users, user_id):
    for user in users:
        if user.id == user_id:
            return user
    return None

# After: Generator with next()
def find_user_by_id(users, user_id):
    return next(
        (user for user in users if user.id == user_id),
        None  # Default if not found
    )
```

### Real Example from supervisor_agent.py:
```python
# Before: For loop for first match
def get_stage_result(self, stage_name: str) -> Optional[Dict[str, Any]]:
    for state_entry in reversed(self.state_machine._state_stack):
        context = state_entry.get('context', {})
        if context.get('stage') == stage_name and 'result' in context:
            return context['result']
    return None

# After: Generator with next()
def get_stage_result(self, stage_name: str) -> Optional[Dict[str, Any]]:
    return next(
        (
            context['result']
            for state_entry in reversed(self.state_machine._state_stack)
            if (context := state_entry.get('context', {})).get('stage') == stage_name
            and 'result' in context
        ),
        None
    )
```

### Collecting Unique Items with Generator:
```python
# Before: Loop with accumulator
def get_all_stage_results(self):
    stage_results = {}
    for state_entry in reversed(self.state_machine._state_stack):
        context = state_entry.get('context', {})
        stage = context.get('stage')
        result = context.get('result')
        if stage and result and stage not in stage_results:
            stage_results[stage] = result
    return stage_results

# After: Generator function
def get_all_stage_results(self):
    seen_stages = set()

    def _unique_stage_results():
        for state_entry in reversed(self.state_machine._state_stack):
            context = state_entry.get('context', {})
            stage = context.get('stage')
            result = context.get('result')
            if stage and result and stage not in seen_stages:
                seen_stages.add(stage)
                yield (stage, result)

    return dict(_unique_stage_results())
```

## JavaScript/TypeScript Example

### Before:
```typescript
function* getActiveUsers(users: User[]): Generator<User> {
    for (const user of users) {
        if (user.isActive) {
            yield user;
        }
    }
}

// Usage
const activeUsers = getActiveUsers(millionUsers);
const firstActive = activeUsers.next().value; // Only processes until first match
```

### With Iterators:
```typescript
class ActiveUserIterator implements Iterator<User> {
    private index = 0;

    constructor(private users: User[]) {}

    next(): IteratorResult<User> {
        while (this.index < this.users.length) {
            const user = this.users[this.index++];
            if (user.isActive) {
                return { value: user, done: false };
            }
        }
        return { value: undefined, done: true };
    }
}
```

## Rust Example (Iterators)

### Before:
```rust
fn get_active_users(users: &[User]) -> Vec<User> {
    users.iter()
        .filter(|u| u.is_active)
        .cloned()
        .collect()  // Allocates entire Vec
}
```

### After:
```rust
fn get_active_users(users: &[User]) -> impl Iterator<Item = &User> {
    users.iter()
        .filter(|u| u.is_active)  // Lazy, no allocation
}

// Usage
let first_active = get_active_users(&users).next();  // Only processes until first
```

## Java Example (Streams)

### Before:
```java
public List<User> getActiveUsers(List<User> users) {
    return users.stream()
        .filter(User::isActive)
        .collect(Collectors.toList());  // Allocates entire list
}
```

### After:
```java
public Stream<User> getActiveUsers(List<User> users) {
    return users.stream()
        .filter(User::isActive);  // Lazy evaluation
}

// Usage
Optional<User> firstActive = getActiveUsers(users).findFirst();  // Short-circuits
```

## Go Example (Channels)

### Before:
```go
func getActiveUsers(users []User) []User {
    active := make([]User, 0)
    for _, user := range users {
        if user.IsActive {
            active = append(active, user)
        }
    }
    return active
}
```

### After (Channel Generator):
```go
func getActiveUsers(users []User) <-chan User {
    ch := make(chan User)
    go func() {
        defer close(ch)
        for _, user := range users {
            if user.IsActive {
                ch <- user  // Lazy, processes on demand
            }
        }
    }()
    return ch
}

// Usage
for user := range getActiveUsers(users) {
    // Process first, then break if needed
    processUser(user)
    break
}
```

## Benefits
- **Memory Efficient**: Only one item in memory at a time
- **Lazy Evaluation**: Computes values on demand
- **Short-Circuit**: Can stop early with next() or findFirst()
- **Composable**: Chain multiple generators/iterators
- **Infinite Sequences**: Can represent infinite data streams
- **Better Performance**: Avoid unnecessary allocations for first-match searches

## When to Use Generators
✅ Processing large files line-by-line
✅ Database query result streaming
✅ First-match searches (with next())
✅ Infinite sequences (Fibonacci, primes)
✅ Pipeline transformations (map/filter chains)
✅ Pagination or batch processing

## When NOT to Use Generators
❌ Need random access to elements
❌ Need to iterate multiple times (generator exhausts)
❌ Need length/size without consuming
❌ Small datasets where list is more readable
        """,
        metadata={
            "refactoring_type": "generator_pattern",
            "priority": "high",
            "language": "python,java,javascript,typescript,rust,go"
        }
    )

    print("✅ Stored 11 refactoring instruction artifacts in RAG (multi-language)")


def store_refactoring_patterns_in_kg(kg: KnowledgeGraph):
    """Store refactoring patterns in Knowledge Graph"""

    print("Storing refactoring patterns in Knowledge Graph...")

    # Create refactoring pattern entities
    kg.add_entity("RefactoringPattern", "LoopToComprehension", {
        "description": "Convert for loops to comprehensions",
        "priority": "high",
        "applicable_to": "python"
    })

    kg.add_entity("RefactoringPattern", "IfElifToMapping", {
        "description": "Convert if/elif chains to dictionary mapping",
        "priority": "high",
        "applicable_to": "python"
    })

    kg.add_entity("RefactoringPattern", "ExtractMethod", {
        "description": "Extract long methods into smaller helper methods",
        "priority": "critical",
        "applicable_to": "all_languages"
    })

    kg.add_entity("RefactoringPattern", "NextForFirstMatch", {
        "description": "Use next() with generator for first match",
        "priority": "medium",
        "applicable_to": "python"
    })

    kg.add_entity("RefactoringPattern", "UseCollections", {
        "description": "Use collections module (defaultdict, Counter, chain)",
        "priority": "medium",
        "applicable_to": "python"
    })

    kg.add_entity("RefactoringPattern", "StreamOperations", {
        "description": "Use stream/functional operations instead of loops",
        "priority": "high",
        "applicable_to": "java,javascript,typescript,rust,go"
    })

    kg.add_entity("RefactoringPattern", "StrategyPattern", {
        "description": "Replace complex conditionals with strategy pattern",
        "priority": "critical",
        "applicable_to": "all_languages"
    })

    kg.add_entity("RefactoringPattern", "NullObjectPattern", {
        "description": "Replace null checks with null object",
        "priority": "medium",
        "applicable_to": "all_languages"
    })

    kg.add_entity("RefactoringPattern", "BuilderPattern", {
        "description": "Use builder for complex object construction",
        "priority": "high",
        "applicable_to": "all_languages"
    })

    kg.add_entity("RefactoringPattern", "EarlyReturnPattern", {
        "description": "Use guard clauses and early returns",
        "priority": "critical",
        "applicable_to": "all_languages"
    })

    # Link patterns to code quality
    kg.add_relation("LoopToComprehension", "improves", "CodeQuality")
    kg.add_relation("IfElifToMapping", "improves", "Maintainability")
    kg.add_relation("ExtractMethod", "improves", "Testability")
    kg.add_relation("NextForFirstMatch", "improves", "Readability")
    kg.add_relation("UseCollections", "improves", "Performance")
    kg.add_relation("StreamOperations", "improves", "CodeQuality")
    kg.add_relation("StrategyPattern", "improves", "Extensibility")
    kg.add_relation("NullObjectPattern", "improves", "Robustness")
    kg.add_relation("BuilderPattern", "improves", "Usability")
    kg.add_relation("EarlyReturnPattern", "improves", "Readability")

    print("✅ Stored 10 refactoring patterns in Knowledge Graph")


if __name__ == "__main__":
    # Initialize RAG and KG
    rag = RAGAgent(db_path="db", verbose=True)

    # Store instructions
    store_refactoring_instructions_in_rag(rag)

    # If KG available, store patterns
    try:
        from knowledge_graph_factory import create_knowledge_graph
        kg = create_knowledge_graph()
        store_refactoring_patterns_in_kg(kg)
    except Exception as e:
        print(f"⚠️  Could not store in KG: {e}")

    print("\n✅ All refactoring instructions stored successfully!")
