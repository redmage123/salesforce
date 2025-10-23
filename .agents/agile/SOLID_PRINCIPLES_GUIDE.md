# SOLID Principles - Artemis Development Standard

## Mandatory for All Artemis Code

**EVERY developer agent MUST follow SOLID principles. This is non-negotiable.**

---

## The Five SOLID Principles

### S - Single Responsibility Principle (SRP)

**Definition:** A class should have one, and only one, reason to change.

**Rule:** Each class/module should do ONE thing and do it well.

**Examples:**

❌ **BAD - Violates SRP:**
```python
class UserManager:
    def create_user(self, name, email):
        # Handles user creation
        user = {"name": name, "email": email}

        # Validates email (DIFFERENT responsibility)
        if "@" not in email:
            raise ValueError("Invalid email")

        # Sends welcome email (DIFFERENT responsibility)
        send_email(email, "Welcome!")

        # Saves to database (DIFFERENT responsibility)
        db.save(user)

        return user
```

✅ **GOOD - Follows SRP:**
```python
class EmailValidator:
    """Single responsibility: Email validation"""
    def validate(self, email: str) -> bool:
        return "@" in email and "." in email

class EmailService:
    """Single responsibility: Email operations"""
    def send_welcome_email(self, email: str):
        send_email(email, "Welcome!")

class UserRepository:
    """Single responsibility: User data persistence"""
    def save(self, user: Dict):
        db.save(user)

class UserService:
    """Single responsibility: User business logic"""
    def __init__(self, validator: EmailValidator,
                 email_service: EmailService,
                 repository: UserRepository):
        self.validator = validator
        self.email_service = email_service
        self.repository = repository

    def create_user(self, name: str, email: str) -> Dict:
        if not self.validator.validate(email):
            raise ValueError("Invalid email")

        user = {"name": name, "email": email}
        self.repository.save(user)
        self.email_service.send_welcome_email(email)

        return user
```

**Benefits:**
- Easier to test (mock individual components)
- Easier to maintain (change email logic without touching user creation)
- Easier to understand (clear purpose per class)

---

### O - Open/Closed Principle (OCP)

**Definition:** Software entities should be open for extension, but closed for modification.

**Rule:** Add new functionality by EXTENDING, not MODIFYING existing code.

**Examples:**

❌ **BAD - Violates OCP:**
```python
class PaymentProcessor:
    def process_payment(self, amount: float, method: str):
        if method == "credit_card":
            # Credit card processing logic
            charge_credit_card(amount)
        elif method == "paypal":
            # PayPal logic
            charge_paypal(amount)
        elif method == "stripe":  # Adding new method = MODIFYING class
            charge_stripe(amount)
        # Every new payment method requires modifying this class!
```

✅ **GOOD - Follows OCP:**
```python
from abc import ABC, abstractmethod

class PaymentMethod(ABC):
    """Abstract base class for payment methods"""
    @abstractmethod
    def process(self, amount: float):
        pass

class CreditCardPayment(PaymentMethod):
    """Handles credit card payments"""
    def process(self, amount: float):
        charge_credit_card(amount)

class PayPalPayment(PaymentMethod):
    """Handles PayPal payments"""
    def process(self, amount: float):
        charge_paypal(amount)

class StripePayment(PaymentMethod):
    """Handles Stripe payments - NEW, no modification needed"""
    def process(self, amount: float):
        charge_stripe(amount)

class PaymentProcessor:
    """Processes payments - NEVER needs modification"""
    def process_payment(self, amount: float, method: PaymentMethod):
        method.process(amount)

# Usage:
processor = PaymentProcessor()
processor.process_payment(100.00, StripePayment())  # Extend without modifying
```

**Benefits:**
- Add new features without touching existing code
- Reduces risk of breaking existing functionality
- Supports plugin architectures

---

### L - Liskov Substitution Principle (LSP)

**Definition:** Subclasses should be substitutable for their base classes.

**Rule:** If S is a subtype of T, then objects of type T may be replaced with objects of type S without breaking the program.

**Examples:**

❌ **BAD - Violates LSP:**
```python
class Bird:
    def fly(self):
        return "Flying"

class Penguin(Bird):
    def fly(self):
        raise Exception("Penguins can't fly!")  # BREAKS substitution
```

✅ **GOOD - Follows LSP:**
```python
from abc import ABC, abstractmethod

class Bird(ABC):
    @abstractmethod
    def move(self):
        pass

class FlyingBird(Bird):
    def move(self):
        return "Flying"

    def fly(self):
        return "Flying high"

class Penguin(Bird):
    def move(self):
        return "Swimming"

    def swim(self):
        return "Swimming fast"

# Both can be used as Bird without breaking
def make_bird_move(bird: Bird):
    print(bird.move())  # Works for ALL birds

make_bird_move(FlyingBird())  # "Flying"
make_bird_move(Penguin())     # "Swimming"
```

**Benefits:**
- Polymorphism works correctly
- No unexpected behavior from subclasses
- Reliable inheritance hierarchies

---

### I - Interface Segregation Principle (ISP)

**Definition:** Clients should not be forced to depend on interfaces they don't use.

**Rule:** Many small, specific interfaces are better than one large, general interface.

**Examples:**

❌ **BAD - Violates ISP:**
```python
class Worker(ABC):
    @abstractmethod
    def work(self):
        pass

    @abstractmethod
    def eat(self):
        pass

    @abstractmethod
    def sleep(self):
        pass

class Robot(Worker):
    def work(self):
        return "Working"

    def eat(self):
        # Robots don't eat! Forced to implement unused method
        raise NotImplementedError("Robots don't eat")

    def sleep(self):
        # Robots don't sleep! Forced to implement unused method
        raise NotImplementedError("Robots don't sleep")
```

✅ **GOOD - Follows ISP:**
```python
class Workable(ABC):
    @abstractmethod
    def work(self):
        pass

class Eatable(ABC):
    @abstractmethod
    def eat(self):
        pass

class Sleepable(ABC):
    @abstractmethod
    def sleep(self):
        pass

class Human(Workable, Eatable, Sleepable):
    def work(self):
        return "Working"

    def eat(self):
        return "Eating"

    def sleep(self):
        return "Sleeping"

class Robot(Workable):  # Only implements what it needs
    def work(self):
        return "Working 24/7"
```

**Benefits:**
- Classes only implement what they need
- No dummy/exception-throwing methods
- More flexible composition

---

### D - Dependency Inversion Principle (DIP)

**Definition:** High-level modules should not depend on low-level modules. Both should depend on abstractions.

**Rule:** Depend on interfaces/abstractions, not concrete implementations.

**Examples:**

❌ **BAD - Violates DIP:**
```python
class MySQLDatabase:
    def save(self, data):
        # MySQL-specific save logic
        mysql_connection.insert(data)

class UserService:
    def __init__(self):
        self.db = MySQLDatabase()  # Tightly coupled to MySQL

    def create_user(self, user):
        self.db.save(user)

# Problem: Can't switch to PostgreSQL without modifying UserService
```

✅ **GOOD - Follows DIP:**
```python
from abc import ABC, abstractmethod

class Database(ABC):
    """Abstraction - defines contract"""
    @abstractmethod
    def save(self, data):
        pass

class MySQLDatabase(Database):
    """Concrete implementation"""
    def save(self, data):
        mysql_connection.insert(data)

class PostgreSQLDatabase(Database):
    """Another concrete implementation"""
    def save(self, data):
        postgres_connection.insert(data)

class UserService:
    """Depends on abstraction, not concrete class"""
    def __init__(self, database: Database):
        self.db = database  # Depends on interface

    def create_user(self, user):
        self.db.save(user)

# Easy to swap implementations
service = UserService(MySQLDatabase())
service = UserService(PostgreSQLDatabase())  # No UserService changes needed
```

**Benefits:**
- Easy to swap implementations (testing, production)
- Decoupled components
- Testability (mock interfaces)

---

## Artemis-Specific SOLID Guidelines

### For Pipeline Agents

**Current Violation Example:**
```python
# Pipeline Orchestrator has 2000+ lines - violates SRP
class ArtemisOrchestrator:
    def run_architecture_stage(self): ...
    def run_validation_stage(self): ...
    def run_arbitration_stage(self): ...
    def run_integration_stage(self): ...
    def run_testing_stage(self): ...
    # TOO MANY RESPONSIBILITIES
```

**SOLID Refactor:**
```python
# Each stage = separate class (SRP)
class ArchitectureStage:
    def execute(self, card: Dict, context: Dict) -> Dict:
        ...

class ValidationStage:
    def execute(self, card: Dict, context: Dict) -> Dict:
        ...

# Abstract pipeline stage (OCP + DIP)
class PipelineStage(ABC):
    @abstractmethod
    def execute(self, card: Dict, context: Dict) -> Dict:
        pass

# Orchestrator orchestrates, doesn't implement (SRP)
class ArtemisOrchestrator:
    def __init__(self, stages: List[PipelineStage]):
        self.stages = stages

    def run_pipeline(self, card: Dict):
        context = {}
        for stage in self.stages:
            result = stage.execute(card, context)
            context.update(result)
        return context
```

### For RAG Agent

**Current Violation:**
```python
class RAGAgent:
    def store_artifact(self): ...
    def query_similar(self): ...
    def get_recommendations(self): ...
    def extract_patterns(self): ...
    # Mixing storage, retrieval, analysis (violates SRP)
```

**SOLID Refactor:**
```python
class ArtifactRepository:
    """Single responsibility: Storage/retrieval"""
    def store(self, artifact: Artifact) -> str: ...
    def query(self, query_text: str, top_k: int) -> List[Dict]: ...

class RecommendationEngine:
    """Single responsibility: Generate recommendations"""
    def __init__(self, repository: ArtifactRepository):
        self.repository = repository

    def get_recommendations(self, task: str) -> Dict: ...

class PatternAnalyzer:
    """Single responsibility: Extract patterns"""
    def __init__(self, repository: ArtifactRepository):
        self.repository = repository

    def extract_patterns(self, pattern_type: str) -> Dict: ...

class RAGAgent:
    """Facade - coordinates components"""
    def __init__(self, repository: ArtifactRepository,
                 recommender: RecommendationEngine,
                 analyzer: PatternAnalyzer):
        self.repository = repository
        self.recommender = recommender
        self.analyzer = analyzer
```

---

## Mandatory Developer Checklist

Before submitting code, EVERY developer agent must verify:

- [ ] **S - Single Responsibility:** Does each class have ONE clear purpose?
- [ ] **O - Open/Closed:** Can I add features without modifying existing code?
- [ ] **L - Liskov Substitution:** Can subclasses replace base classes safely?
- [ ] **I - Interface Segregation:** Are interfaces minimal and focused?
- [ ] **D - Dependency Inversion:** Do I depend on abstractions, not concretions?

---

## Code Review Questions

**During Validation Stage:**

1. Does this class do more than one thing? → Violates SRP
2. Would adding a new feature require modifying this class? → Violates OCP
3. Can I replace the base class with this subclass everywhere? → Violates LSP
4. Does this interface have methods I don't need? → Violates ISP
5. Am I directly importing concrete classes instead of interfaces? → Violates DIP

---

## Benefits of SOLID in Artemis

1. **Testability:** Easy to mock/test individual components
2. **Maintainability:** Changes isolated to specific classes
3. **Extensibility:** Add new stages/agents without modifying core
4. **Parallel Development:** Developers work on separate components
5. **Quality:** Arbitration scores higher SOLID code higher

---

## Enforcement

**Validation Agent checks:**
- Class line counts (<200 lines = likely SRP compliant)
- Dependency graphs (abstractions > concretions)
- Interface adherence
- Test coverage (SOLID code is easier to test)

**Arbitration Agent scores:**
- +10 points: Perfect SOLID compliance
- +5 points: Good SOLID practices
- -10 points: Major SOLID violations

---

## References

- [SOLID Principles - Wikipedia](https://en.wikipedia.org/wiki/SOLID)
- [Clean Code - Robert C. Martin](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882)
- [Design Patterns - Gang of Four](https://en.wikipedia.org/wiki/Design_Patterns)

---

**This is the Artemis standard. No exceptions.**
