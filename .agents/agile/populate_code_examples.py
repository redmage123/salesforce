#!/usr/bin/env python3
"""
Populate RAG and Knowledge Graph with curated code examples for all 30+ languages.

This script stores high-quality code examples demonstrating:
- Design patterns (Factory, Repository, Strategy, etc.)
- Language-specific idioms
- Database best practices
- Security patterns
- Anti-patterns (with corrections)

Usage:
    python populate_code_examples.py --all
    python populate_code_examples.py --language python
    python populate_code_examples.py --pattern repository
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from code_example_types import CodeExample
from rag_agent import RAGAgent
from knowledge_graph import KnowledgeGraph


# =============================================================================
# CODE EXAMPLES BY LANGUAGE
# =============================================================================

PYTHON_EXAMPLES = [
    CodeExample(
        language="Python",
        pattern="Repository Pattern with SQLAlchemy",
        title="User Repository with Eager Loading",
        description="Repository pattern implementation using SQLAlchemy ORM with N+1 query prevention",
        code='''"""
User Repository - Demonstrates Repository Pattern with SQLAlchemy

Why: Separates data access logic from business logic (SRP)
Prevents: God classes, scattered SQL, N+1 query problems
"""
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import select
from typing import List, Optional
from dataclasses import dataclass


class UserNotFoundError(Exception):
    """Custom exception for user not found (never use generic exceptions)"""
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"User {user_id} not found")


@dataclass
class UserFilter:
    """Filter configuration (no magic values)"""
    active_only: bool = True
    with_profile: bool = True
    with_orders: bool = False


class UserRepository:
    """
    Repository for User entity data access.

    Follows:
    - Single Responsibility Principle (only data access)
    - Dependency Injection (session injected, not created)
    - Explicit over implicit (clear method names)
    """

    def __init__(self, session: Session):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session (injected dependency)
        """
        self._session = session

    def find_by_id(
        self,
        user_id: int,
        eager_load: bool = True
    ) -> Optional[User]:
        """
        Find user by ID with optional eager loading.

        Why: Prevent N+1 queries with eager loading option

        Args:
            user_id: User primary key
            eager_load: Load relationships immediately (prevents N+1)

        Returns:
            User if found, None otherwise
        """
        query = self._session.query(User).filter(User.id == user_id)

        if eager_load:
            # Prevent N+1: Load profile and orders in single query
            query = query.options(
                joinedload(User.profile),
                selectinload(User.orders)
            )

        return query.first()

    def find_active_users(self, limit: int = 100) -> List[User]:
        """
        Find active users using functional patterns.

        Why: Comprehension over loop, explicit limit (no unbounded queries)

        Args:
            limit: Maximum results (prevent memory issues)

        Returns:
            List of active users
        """
        # Use SQLAlchemy Core for better performance on large datasets
        stmt = (
            select(User)
            .where(User.active == True)
            .options(joinedload(User.profile))
            .limit(limit)
        )

        result = self._session.execute(stmt)
        return result.scalars().all()

    def save(self, user: User) -> User:
        """
        Persist user to database.

        Why: Repository handles persistence, not entity

        Args:
            user: User entity to save

        Returns:
            Saved user with ID populated
        """
        self._session.add(user)
        self._session.flush()  # Get ID without committing transaction
        return user
''',
        quality_score=95,
        tags=["design-pattern", "database", "SQLAlchemy", "ORM", "N+1-prevention"],
        complexity="intermediate",
        demonstrates=["Repository Pattern", "Dependency Injection", "Eager Loading", "Custom Exceptions"],
        prevents=["God Class", "N+1 Queries", "Scattered SQL", "Magic Numbers"]
    ),

    CodeExample(
        language="Python",
        pattern="Factory Pattern",
        title="Database Connection Factory",
        description="Factory pattern for creating database connections based on configuration",
        code='''"""
Database Connection Factory - Demonstrates Factory Pattern

Why: Encapsulates complex object creation logic
Prevents: Scattered connection logic, hardcoded credentials
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from enum import Enum
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


class DatabaseType(Enum):
    """Enum for database types (better than magic strings)"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"


class DatabaseConfig:
    """Configuration class (no magic numbers/strings)"""
    DEFAULT_POOL_SIZE = 10
    DEFAULT_MAX_OVERFLOW = 20
    DEFAULT_TIMEOUT = 30


class DatabaseConnection(ABC):
    """Abstract base for database connections (DIP - depend on abstraction)"""

    @abstractmethod
    def get_session(self) -> Session:
        """Get database session"""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connection"""
        pass


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL-specific connection with JSONB support"""

    def __init__(self, config: Dict[str, Any]):
        # Use environment variables, never hardcode credentials
        connection_string = (
            f"postgresql://{config['user']}:{config['password']}"
            f"@{config['host']}:{config['port']}/{config['database']}"
        )

        self._engine = create_engine(
            connection_string,
            pool_size=DatabaseConfig.DEFAULT_POOL_SIZE,
            max_overflow=DatabaseConfig.DEFAULT_MAX_OVERFLOW,
            pool_pre_ping=True,  # Verify connections before use
            echo=config.get('debug', False)
        )

        self._session_factory = sessionmaker(bind=self._engine)

    def get_session(self) -> Session:
        return self._session_factory()

    def close(self) -> None:
        self._engine.dispose()


class MySQLConnection(DatabaseConnection):
    """MySQL-specific connection with utf8mb4"""

    def __init__(self, config: Dict[str, Any]):
        connection_string = (
            f"mysql+pymysql://{config['user']}:{config['password']}"
            f"@{config['host']}:{config['port']}/{config['database']}"
            f"?charset=utf8mb4"  # Full UTF-8 support
        )

        self._engine = create_engine(
            connection_string,
            pool_size=DatabaseConfig.DEFAULT_POOL_SIZE,
            pool_recycle=3600  # Recycle connections every hour
        )

        self._session_factory = sessionmaker(bind=self._engine)

    def get_session(self) -> Session:
        return self._session_factory()

    def close(self) -> None:
        self._engine.dispose()


class DatabaseConnectionFactory:
    """
    Factory for creating database connections.

    Follows:
    - Factory Pattern (encapsulates object creation)
    - Open/Closed Principle (extend by adding new DB types)
    - Strategy Pattern (different strategies per DB type)
    """

    # Registry pattern: map enum to class
    _connection_classes = {
        DatabaseType.POSTGRESQL: PostgreSQLConnection,
        DatabaseType.MYSQL: MySQLConnection,
    }

    @classmethod
    def create(
        cls,
        db_type: DatabaseType,
        config: Dict[str, Any]
    ) -> DatabaseConnection:
        """
        Create database connection using Factory pattern.

        Why: Single place to create connections, easy to extend

        Args:
            db_type: Type of database (enum, not string)
            config: Connection configuration

        Returns:
            DatabaseConnection instance

        Raises:
            ValueError: If database type not supported
        """
        connection_class = cls._connection_classes.get(db_type)

        if connection_class is None:
            raise ValueError(
                f"Unsupported database type: {db_type}. "
                f"Supported types: {list(cls._connection_classes.keys())}"
            )

        return connection_class(config)


# Usage example
if __name__ == "__main__":
    # Configuration from environment (never hardcode)
    config = {
        'user': 'app_user',
        'password': 'from_env_var',
        'host': 'localhost',
        'port': 5432,
        'database': 'myapp'
    }

    # Create PostgreSQL connection using factory
    connection = DatabaseConnectionFactory.create(
        DatabaseType.POSTGRESQL,
        config
    )

    # Use connection
    with connection.get_session() as session:
        # Use session for queries
        pass

    connection.close()
''',
        quality_score=92,
        tags=["design-pattern", "factory", "database", "enum", "dependency-injection"],
        complexity="intermediate",
        demonstrates=["Factory Pattern", "Strategy Pattern", "Enum Usage", "Abstract Base Classes"],
        prevents=["Hardcoded Values", "Magic Strings", "Scattered Creation Logic"]
    ),
]


RUST_EXAMPLES = [
    CodeExample(
        language="Rust",
        pattern="Result Type Error Handling",
        title="Custom Error Types with Result",
        description="Rust-idiomatic error handling using Result<T, E> and custom error types",
        code='''//! User Repository - Demonstrates Rust Error Handling
//!
//! Why: Explicit error handling, no exceptions
//! Prevents: Silent failures, panic in production

use std::fmt;

/// Custom error type hierarchy (never use generic errors)
#[derive(Debug)]
pub enum UserError {
    NotFound { user_id: u64 },
    DatabaseError { message: String },
    ValidationError { field: String, reason: String },
}

impl fmt::Display for UserError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            UserError::NotFound { user_id } => {
                write!(f, "User {} not found", user_id)
            }
            UserError::DatabaseError { message } => {
                write!(f, "Database error: {}", message)
            }
            UserError::ValidationError { field, reason } => {
                write!(f, "Validation failed for {}: {}", field, reason)
            }
        }
    }
}

impl std::error::Error for UserError {}

/// User entity with ownership
#[derive(Debug, Clone)]
pub struct User {
    pub id: u64,
    pub name: String,
    pub email: String,
}

/// Repository trait (interface abstraction - DIP)
pub trait UserRepository {
    fn find_by_id(&self, id: u64) -> Result<User, UserError>;
    fn save(&mut self, user: User) -> Result<User, UserError>;
}

/// In-memory implementation (for demonstration)
pub struct InMemoryUserRepository {
    users: Vec<User>,
}

impl InMemoryUserRepository {
    pub fn new() -> Self {
        Self { users: Vec::new() }
    }

    /// Validate user using functional patterns
    fn validate_user(&self, user: &User) -> Result<(), UserError> {
        // Use pattern matching instead of nested ifs
        match user.name.len() {
            0 => Err(UserError::ValidationError {
                field: "name".to_string(),
                reason: "Name cannot be empty".to_string(),
            }),
            len if len > 100 => Err(UserError::ValidationError {
                field: "name".to_string(),
                reason: "Name too long (max 100 chars)".to_string(),
            }),
            _ => Ok(()),
        }?;

        // Validate email (simplified)
        if !user.email.contains('@') {
            return Err(UserError::ValidationError {
                field: "email".to_string(),
                reason: "Invalid email format".to_string(),
            });
        }

        Ok(())
    }
}

impl UserRepository for InMemoryUserRepository {
    fn find_by_id(&self, id: u64) -> Result<User, UserError> {
        // Use iterator instead of loop (functional pattern)
        self.users
            .iter()
            .find(|user| user.id == id)
            .cloned()
            .ok_or_else(|| UserError::NotFound { user_id: id })
    }

    fn save(&mut self, user: User) -> Result<User, UserError> {
        // Validate before saving
        self.validate_user(&user)?;

        // Use functional pattern with filter + collect
        // Remove existing user with same ID (upsert behavior)
        self.users = self.users
            .iter()
            .filter(|u| u.id != user.id)
            .cloned()
            .collect();

        self.users.push(user.clone());
        Ok(user)
    }
}

// Usage example with error propagation
fn process_user(repo: &mut impl UserRepository, user_id: u64) -> Result<String, UserError> {
    // ? operator propagates errors (no nested error handling)
    let user = repo.find_by_id(user_id)?;
    Ok(format!("Processing user: {}", user.name))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_find_user_success() {
        let mut repo = InMemoryUserRepository::new();
        let user = User {
            id: 1,
            name: "Alice".to_string(),
            email: "alice@example.com".to_string(),
        };

        repo.save(user.clone()).unwrap();

        let found = repo.find_by_id(1).unwrap();
        assert_eq!(found.name, "Alice");
    }

    #[test]
    fn test_find_user_not_found() {
        let repo = InMemoryUserRepository::new();
        let result = repo.find_by_id(999);

        assert!(result.is_err());
        match result {
            Err(UserError::NotFound { user_id }) => assert_eq!(user_id, 999),
            _ => panic!("Expected NotFound error"),
        }
    }
}
''',
        quality_score=94,
        tags=["error-handling", "Result", "ownership", "iterators", "pattern-matching"],
        complexity="intermediate",
        demonstrates=["Result Type", "Custom Errors", "Ownership", "Iterators", "Pattern Matching"],
        prevents=["Panic in Production", "Exceptions", "Nested Error Handling"]
    ),
]


JAVASCRIPT_EXAMPLES = [
    CodeExample(
        language="JavaScript",
        pattern="Promise-based Error Handling",
        title="Async/Await with Proper Error Handling",
        description="Modern JavaScript async patterns with comprehensive error handling",
        code='''/**
 * User Service - Demonstrates Modern JavaScript Async Patterns
 *
 * Why: Avoid callback hell, explicit error handling
 * Prevents: Unhandled promise rejections, callback pyramids
 */

// Custom error classes (never use generic Error)
class UserNotFoundError extends Error {
    constructor(userId) {
        super(`User ${userId} not found`);
        this.name = 'UserNotFoundError';
        this.userId = userId;
    }
}

class ValidationError extends Error {
    constructor(field, reason) {
        super(`Validation failed for ${field}: ${reason}`);
        this.name = 'ValidationError';
        this.field = field;
        this.reason = reason;
    }
}

/**
 * User service with async/await patterns
 */
class UserService {
    constructor(database) {
        this.db = database;
    }

    /**
     * Find user by ID with error handling
     * @param {number} userId - User ID
     * @returns {Promise<Object>} User object
     * @throws {UserNotFoundError} If user not found
     */
    async findById(userId) {
        try {
            // Use parameterized queries (prevent SQL injection)
            const user = await this.db.query(
                'SELECT * FROM users WHERE id = $1',
                [userId]
            );

            if (!user) {
                throw new UserNotFoundError(userId);
            }

            return user;
        } catch (error) {
            // Re-throw custom errors, wrap database errors
            if (error instanceof UserNotFoundError) {
                throw error;
            }
            throw new Error(`Database error: ${error.message}`);
        }
    }

    /**
     * Find multiple users with Promise.all (parallel execution)
     * @param {number[]} userIds - Array of user IDs
     * @returns {Promise<Object[]>} Array of users
     */
    async findByIds(userIds) {
        // Execute in parallel (not sequential)
        const userPromises = userIds.map(id => this.findById(id));

        // Wait for all promises, collect errors
        const results = await Promise.allSettled(userPromises);

        // Separate successes from failures
        const users = [];
        const errors = [];

        results.forEach((result, index) => {
            if (result.status === 'fulfilled') {
                users.push(result.value);
            } else {
                errors.push({
                    userId: userIds[index],
                    error: result.reason
                });
            }
        });

        // Log errors but don't fail entire operation
        if (errors.length > 0) {
            console.warn('Some users not found:', errors);
        }

        return users;
    }

    /**
     * Create user with validation
     * @param {Object} userData - User data
     * @returns {Promise<Object>} Created user
     */
    async create(userData) {
        // Validate (never trust input)
        this.validateUser(userData);

        try {
            const user = await this.db.query(
                'INSERT INTO users (name, email) VALUES ($1, $2) RETURNING *',
                [userData.name, userData.email]
            );

            return user;
        } catch (error) {
            // Handle unique constraint violation
            if (error.code === '23505') {
                throw new ValidationError('email', 'Email already exists');
            }
            throw error;
        }
    }

    /**
     * Validate user data
     * @param {Object} user - User data
     * @throws {ValidationError} If validation fails
     */
    validateUser(user) {
        if (!user.name || user.name.trim().length === 0) {
            throw new ValidationError('name', 'Name cannot be empty');
        }

        // Email regex validation
        const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
        if (!emailRegex.test(user.email)) {
            throw new ValidationError('email', 'Invalid email format');
        }
    }

    /**
     * Update user with optimistic locking
     * @param {number} userId - User ID
     * @param {Object} updates - Fields to update
     * @returns {Promise<Object>} Updated user
     */
    async update(userId, updates) {
        const user = await this.findById(userId);

        // Merge updates (spread operator - no mutation)
        const updatedUser = { ...user, ...updates, updatedAt: new Date() };

        const result = await this.db.query(
            `UPDATE users
             SET name = $1, email = $2, updated_at = $3
             WHERE id = $4 AND updated_at = $5
             RETURNING *`,
            [
                updatedUser.name,
                updatedUser.email,
                updatedUser.updatedAt,
                userId,
                user.updatedAt  // Optimistic locking
            ]
        );

        if (!result) {
            throw new Error('Update conflict - record was modified');
        }

        return result;
    }
}

/**
 * Usage examples with proper error handling
 */
async function example() {
    const service = new UserService(database);

    try {
        // Single user
        const user = await service.findById(123);
        console.log('User:', user);

        // Multiple users (parallel)
        const users = await service.findByIds([1, 2, 3, 4, 5]);
        console.log('Users:', users);

        // Create with validation
        const newUser = await service.create({
            name: 'Alice',
            email: 'alice@example.com'
        });
        console.log('Created:', newUser);

    } catch (error) {
        if (error instanceof UserNotFoundError) {
            console.error(`User ${error.userId} not found`);
        } else if (error instanceof ValidationError) {
            console.error(`Validation failed: ${error.message}`);
        } else {
            console.error('Unexpected error:', error);
        }
    }
}

// Export for use
module.exports = { UserService, UserNotFoundError, ValidationError };
''',
        quality_score=94,
        tags=["async-await", "promises", "error-handling", "ES6+", "validation"],
        complexity="intermediate",
        demonstrates=["Async/Await", "Promise.allSettled", "Custom Errors", "Spread Operator", "Parameterized Queries"],
        prevents=["Callback Hell", "Unhandled Promises", "SQL Injection", "Race Conditions"]
    ),
]


TYPESCRIPT_EXAMPLES = [
    CodeExample(
        language="TypeScript",
        pattern="Type-Safe Repository",
        title="Generic Repository with Strict Types",
        description="TypeScript generic repository with full type safety and discriminated unions",
        code='''/**
 * Generic Repository - Demonstrates TypeScript Type Safety
 *
 * Why: Compile-time type checking, better IDE support
 * Prevents: Runtime type errors, null pointer exceptions
 */

/** Result type (functional error handling) */
type Result<T, E = Error> =
    | { success: true; value: T }
    | { success: false; error: E };

/** User entity with strict types */
interface User {
    readonly id: number;
    name: string;
    email: string;
    createdAt: Date;
    updatedAt?: Date;
}

/** User creation input (no ID yet) */
type CreateUserInput = Omit<User, 'id' | 'createdAt' | 'updatedAt'>;

/** User update input (partial, no ID/timestamps) */
type UpdateUserInput = Partial<Omit<User, 'id' | 'createdAt' | 'updatedAt'>>;

/** Custom error types with discriminated union */
type RepositoryError =
    | { type: 'NOT_FOUND'; id: number }
    | { type: 'VALIDATION'; field: string; message: string }
    | { type: 'DATABASE'; message: string };

/** Generic repository interface (DIP - depend on abstraction) */
interface Repository<T, TId> {
    findById(id: TId): Promise<Result<T, RepositoryError>>;
    findAll(limit?: number): Promise<Result<T[], RepositoryError>>;
    create(data: Omit<T, 'id'>): Promise<Result<T, RepositoryError>>;
    update(id: TId, data: Partial<T>): Promise<Result<T, RepositoryError>>;
    delete(id: TId): Promise<Result<boolean, RepositoryError>>;
}

/** User repository implementation with full type safety */
class UserRepository implements Repository<User, number> {
    private db: Database;

    constructor(database: Database) {
        this.db = database;
    }

    /**
     * Find user by ID with Result type (no exceptions)
     */
    async findById(id: number): Promise<Result<User, RepositoryError>> {
        try {
            const user = await this.db.query<User>(
                'SELECT * FROM users WHERE id = $1',
                [id]
            );

            if (!user) {
                return {
                    success: false,
                    error: { type: 'NOT_FOUND', id }
                };
            }

            return { success: true, value: user };
        } catch (error) {
            return {
                success: false,
                error: {
                    type: 'DATABASE',
                    message: error instanceof Error ? error.message : 'Unknown error'
                }
            };
        }
    }

    /**
     * Find all users with type-safe limit
     */
    async findAll(limit: number = 100): Promise<Result<User[], RepositoryError>> {
        try {
            const users = await this.db.query<User[]>(
                'SELECT * FROM users LIMIT $1',
                [limit]
            );

            return { success: true, value: users };
        } catch (error) {
            return {
                success: false,
                error: {
                    type: 'DATABASE',
                    message: error instanceof Error ? error.message : 'Unknown error'
                }
            };
        }
    }

    /**
     * Create user with input validation
     */
    async create(input: CreateUserInput): Promise<Result<User, RepositoryError>> {
        // Validate input (type guards)
        const validationError = this.validateUserInput(input);
        if (validationError) {
            return { success: false, error: validationError };
        }

        try {
            const user = await this.db.query<User>(
                `INSERT INTO users (name, email, created_at)
                 VALUES ($1, $2, NOW())
                 RETURNING *`,
                [input.name, input.email]
            );

            return { success: true, value: user };
        } catch (error) {
            return {
                success: false,
                error: { type: 'DATABASE', message: (error as Error).message }
            };
        }
    }

    /**
     * Update user with partial updates (type-safe)
     */
    async update(
        id: number,
        updates: UpdateUserInput
    ): Promise<Result<User, RepositoryError>> {
        // Build dynamic UPDATE query (only update provided fields)
        const fields = Object.keys(updates) as Array<keyof UpdateUserInput>;
        const setClause = fields.map((field, i) => `${field} = $${i + 2}`).join(', ');

        try {
            const user = await this.db.query<User>(
                `UPDATE users SET ${setClause}, updated_at = NOW()
                 WHERE id = $1
                 RETURNING *`,
                [id, ...Object.values(updates)]
            );

            if (!user) {
                return {
                    success: false,
                    error: { type: 'NOT_FOUND', id }
                };
            }

            return { success: true, value: user };
        } catch (error) {
            return {
                success: false,
                error: { type: 'DATABASE', message: (error as Error).message }
            };
        }
    }

    /**
     * Delete user
     */
    async delete(id: number): Promise<Result<boolean, RepositoryError>> {
        try {
            const result = await this.db.query(
                'DELETE FROM users WHERE id = $1',
                [id]
            );

            return { success: true, value: result.rowCount > 0 };
        } catch (error) {
            return {
                success: false,
                error: { type: 'DATABASE', message: (error as Error).message }
            };
        }
    }

    /**
     * Validate user input with type guards
     */
    private validateUserInput(input: CreateUserInput): RepositoryError | null {
        // Name validation
        if (!input.name || input.name.trim().length === 0) {
            return {
                type: 'VALIDATION',
                field: 'name',
                message: 'Name cannot be empty'
            };
        }

        // Email validation
        const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
        if (!emailRegex.test(input.email)) {
            return {
                type: 'VALIDATION',
                field: 'email',
                message: 'Invalid email format'
            };
        }

        return null;
    }
}

/**
 * Usage example with type-safe error handling
 */
async function example() {
    const repo = new UserRepository(database);

    // Create user
    const createResult = await repo.create({
        name: 'Alice',
        email: 'alice@example.com'
    });

    if (createResult.success) {
        console.log('Created user:', createResult.value);
        // TypeScript knows createResult.value is User
    } else {
        // TypeScript knows createResult.error is RepositoryError
        switch (createResult.error.type) {
            case 'VALIDATION':
                console.error(
                    `Validation error: ${createResult.error.field} - ${createResult.error.message}`
                );
                break;
            case 'DATABASE':
                console.error(`Database error: ${createResult.error.message}`);
                break;
            case 'NOT_FOUND':
                console.error(`User ${createResult.error.id} not found`);
                break;
        }
    }

    // Update user (type-safe partial updates)
    const updateResult = await repo.update(1, { name: 'Alice Smith' });
    // TypeScript ensures only valid User fields are updated

    // Find user
    const findResult = await repo.findById(1);
    if (findResult.success) {
        const user = findResult.value;
        console.log(user.name);  // TypeScript knows user.name exists
    }
}

export { UserRepository, User, CreateUserInput, UpdateUserInput, RepositoryError };
''',
        quality_score=96,
        tags=["TypeScript", "generics", "type-safety", "discriminated-unions", "Result-type"],
        complexity="advanced",
        demonstrates=["Generics", "Discriminated Unions", "Type Guards", "Utility Types", "Result Pattern"],
        prevents=["Runtime Type Errors", "Null Pointer Exceptions", "Invalid Updates"]
    ),
]


JAVA_EXAMPLES = [
    CodeExample(
        language="Java",
        pattern="Stream API Functional Pattern",
        title="Modern Java with Streams and Optional",
        description="Java 17+ features: Stream API, Optional, Records, Pattern Matching",
        code='''/**
 * User Service - Demonstrates Modern Java Patterns
 *
 * Why: Functional programming, null safety, immutability
 * Prevents: NullPointerException, mutable state, imperative loops
 */

import java.util.*;
import java.util.stream.*;
import java.time.LocalDateTime;

/** User record (immutable, Java 14+) */
record User(
    Long id,
    String name,
    String email,
    LocalDateTime createdAt
) {
    // Compact constructor with validation
    public User {
        Objects.requireNonNull(id, "ID cannot be null");
        Objects.requireNonNull(name, "Name cannot be null");
        Objects.requireNonNull(email, "Email cannot be null");

        if (name.isBlank()) {
            throw new IllegalArgumentException("Name cannot be empty");
        }

        if (!email.matches("^[^\\\\s@]+@[^\\\\s@]+\\\\.[^\\\\s@]+$")) {
            throw new IllegalArgumentException("Invalid email format");
        }
    }
}

/** Custom exception hierarchy */
sealed interface UserException permits UserNotFoundException, ValidationException {
    String getMessage();
}

record UserNotFoundException(Long userId) implements UserException {
    @Override
    public String getMessage() {
        return "User " + userId + " not found";
    }
}

record ValidationException(String field, String reason) implements UserException {
    @Override
    public String getMessage() {
        return "Validation failed for " + field + ": " + reason;
    }
}

/** User repository with functional patterns */
class UserRepository {
    private final Map<Long, User> storage = new ConcurrentHashMap<>();

    /**
     * Find user by ID using Optional (null safety)
     *
     * @param id User ID
     * @return Optional containing user if found
     */
    public Optional<User> findById(Long id) {
        return Optional.ofNullable(storage.get(id));
    }

    /**
     * Find users by IDs using Stream API
     *
     * @param ids Collection of user IDs
     * @return List of found users
     */
    public List<User> findByIds(Collection<Long> ids) {
        return ids.stream()
            .map(this::findById)
            .flatMap(Optional::stream)  // Filter out empty Optionals
            .collect(Collectors.toUnmodifiableList());  // Immutable result
    }

    /**
     * Find active users created after date (functional filtering)
     *
     * @param after Filter by creation date
     * @return List of users
     */
    public List<User> findCreatedAfter(LocalDateTime after) {
        return storage.values().stream()
            .filter(user -> user.createdAt().isAfter(after))
            .sorted(Comparator.comparing(User::createdAt).reversed())
            .limit(100)  // Prevent unbounded queries
            .collect(Collectors.toUnmodifiableList());
    }

    /**
     * Group users by email domain using Stream collectors
     *
     * @return Map of domain -> users
     */
    public Map<String, List<User>> groupByEmailDomain() {
        return storage.values().stream()
            .collect(Collectors.groupingBy(
                user -> user.email().substring(user.email().indexOf('@') + 1),
                Collectors.toList()
            ));
    }

    /**
     * Calculate statistics using Stream reduce
     *
     * @return User statistics
     */
    public record UserStats(long total, long withLongNames, String mostCommonDomain) {}

    public UserStats calculateStats() {
        var domainCounts = storage.values().stream()
            .map(user -> user.email().substring(user.email().indexOf('@') + 1))
            .collect(Collectors.groupingBy(
                domain -> domain,
                Collectors.counting()
            ));

        var mostCommonDomain = domainCounts.entrySet().stream()
            .max(Map.Entry.comparingByValue())
            .map(Map.Entry::getKey)
            .orElse("none");

        var longNameCount = storage.values().stream()
            .filter(user -> user.name().length() > 20)
            .count();

        return new UserStats(
            storage.size(),
            longNameCount,
            mostCommonDomain
        );
    }

    /**
     * Save user with validation
     *
     * @param user User to save
     * @return Saved user
     */
    public User save(User user) {
        storage.put(user.id(), user);
        return user;
    }

    /**
     * Update user using pattern matching (Java 17+)
     *
     * @param id User ID
     * @param updates Update function
     * @return Optional containing updated user
     */
    public Optional<User> update(Long id, UserUpdater updates) {
        return findById(id).map(existingUser -> {
            // Create new record with updates (immutability)
            var updated = new User(
                existingUser.id(),
                updates.name().orElse(existingUser.name()),
                updates.email().orElse(existingUser.email()),
                existingUser.createdAt()
            );
            save(updated);
            return updated;
        });
    }

    record UserUpdater(Optional<String> name, Optional<String> email) {}
}

/**
 * Usage examples with modern Java patterns
 */
class UserServiceExample {
    public static void main(String[] args) {
        var repo = new UserRepository();

        // Create users
        var user1 = new User(1L, "Alice", "alice@example.com", LocalDateTime.now());
        var user2 = new User(2L, "Bob", "bob@example.com", LocalDateTime.now());

        repo.save(user1);
        repo.save(user2);

        // Find with Optional (null safety)
        repo.findById(1L).ifPresentOrElse(
            user -> System.out.println("Found: " + user.name()),
            () -> System.out.println("User not found")
        );

        // Stream processing
        var users = repo.findByIds(List.of(1L, 2L, 3L));
        users.forEach(user -> System.out.println(user.name()));

        // Grouping
        var byDomain = repo.groupByEmailDomain();
        byDomain.forEach((domain, userList) ->
            System.out.println(domain + ": " + userList.size())
        );

        // Statistics
        var stats = repo.calculateStats();
        System.out.println("Total users: " + stats.total());
        System.out.println("Most common domain: " + stats.mostCommonDomain());

        // Update with Optional
        repo.update(
            1L,
            new UserRepository.UserUpdater(
                Optional.of("Alice Smith"),
                Optional.empty()
            )
        ).ifPresent(updated -> System.out.println("Updated: " + updated.name()));
    }
}
''',
        quality_score=95,
        tags=["Java", "Stream-API", "Optional", "Records", "Functional-Programming"],
        complexity="intermediate",
        demonstrates=["Stream API", "Optional", "Records", "Pattern Matching", "Collectors"],
        prevents=["NullPointerException", "Mutable State", "Imperative Loops"]
    ),
]


# Import database examples
try:
    import code_examples_database
    ALL_DATABASE_EXAMPLES = code_examples_database.ALL_DATABASE_EXAMPLES
except (ImportError, AttributeError) as e:
    print(f"Warning: Database examples not available ({e}). Continuing with language examples only...")
    ALL_DATABASE_EXAMPLES = {}

# Continue with more languages...
LANGUAGE_EXAMPLES = {
    "Python": PYTHON_EXAMPLES,
    "Rust": RUST_EXAMPLES,
    "JavaScript": JAVASCRIPT_EXAMPLES,
    "TypeScript": TYPESCRIPT_EXAMPLES,
    "Java": JAVA_EXAMPLES,
    **ALL_DATABASE_EXAMPLES,  # Merge database examples
}


class CodeExamplePopulator:
    """Populates RAG and Knowledge Graph with code examples"""

    def __init__(
        self,
        rag_agent: Optional[RAGAgent] = None,
        knowledge_graph: Optional[KnowledgeGraph] = None
    ):
        """
        Initialize populator.

        Args:
            rag_agent: RAG agent for storing examples (optional)
            knowledge_graph: Knowledge graph for relationships (optional)
        """
        self.rag = rag_agent or RAGAgent()
        self.kg = knowledge_graph

    def populate_rag(self, examples: List[CodeExample]) -> int:
        """
        Store code examples in RAG database.

        Args:
            examples: List of code examples to store

        Returns:
            Number of examples stored
        """
        count = 0

        for example in examples:
            # Create comprehensive content for RAG
            content = f"""
# {example.title}

**Language:** {example.language}
**Pattern:** {example.pattern}
**Complexity:** {example.complexity}
**Quality Score:** {example.quality_score}/100

## Description
{example.description}

## Demonstrates
{', '.join(example.demonstrates)}

## Prevents Anti-Patterns
{', '.join(example.prevents)}

## Code Example

```{example.language.lower()}
{example.code}
```

## Tags
{', '.join(example.tags)}
"""

            # Store in RAG with rich metadata
            self.rag.store_artifact(
                artifact_type="code_example",
                card_id=f"code_example_{example.language.lower()}_{count}",
                task_title=example.title,
                content=content,
                metadata={
                    "language": example.language,
                    "pattern": example.pattern,
                    "quality_score": example.quality_score,
                    "complexity": example.complexity,
                    "tags": example.tags,
                    "demonstrates": example.demonstrates,
                    "prevents": example.prevents,
                    "timestamp": datetime.now().isoformat()
                }
            )

            count += 1
            print(f"✓ Stored: {example.language} - {example.title}")

        return count

    def populate_knowledge_graph(self, examples: List[CodeExample]) -> int:
        """
        Create knowledge graph relationships for code examples.

        Args:
            examples: List of code examples

        Returns:
            Number of relationships created
        """
        if not self.kg:
            print("Knowledge Graph not available, skipping...")
            return 0

        count = 0

        for example in examples:
            entity_name = f"{example.language}_{example.pattern.replace(' ', '_')}"

            # Create code example entity
            self.kg.add_entity(
                entity_type="CodeExample",
                name=entity_name,
                properties={
                    "language": example.language,
                    "pattern": example.pattern,
                    "quality_score": example.quality_score,
                    "complexity": example.complexity
                }
            )

            # Create relationships
            # Example -> Pattern
            self.kg.add_relation(
                from_entity=entity_name,
                to_entity=example.pattern,
                relation_type="DEMONSTRATES"
            )

            # Example -> Language
            self.kg.add_relation(
                from_entity=entity_name,
                to_entity=example.language,
                relation_type="WRITTEN_IN"
            )

            # Example -> Concepts
            for concept in example.demonstrates:
                self.kg.add_relation(
                    from_entity=entity_name,
                    to_entity=concept,
                    relation_type="TEACHES"
                )

            # Example -> Anti-Patterns (prevention)
            for anti_pattern in example.prevents:
                self.kg.add_relation(
                    from_entity=entity_name,
                    to_entity=anti_pattern,
                    relation_type="PREVENTS"
                )

            count += 1
            print(f"✓ Created KG relationships for: {example.title}")

        return count

    def populate_all(
        self,
        language: Optional[str] = None,
        pattern: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Populate both RAG and Knowledge Graph.

        Args:
            language: Filter by language (optional)
            pattern: Filter by pattern (optional)

        Returns:
            Dictionary with counts
        """
        # Filter examples
        examples_to_store = []

        for lang, examples in LANGUAGE_EXAMPLES.items():
            if language and lang.lower() != language.lower():
                continue

            for example in examples:
                if pattern and pattern.lower() not in example.pattern.lower():
                    continue

                examples_to_store.append(example)

        # Populate RAG
        rag_count = self.populate_rag(examples_to_store)

        # Populate KG
        kg_count = self.populate_knowledge_graph(examples_to_store)

        return {
            "rag_examples": rag_count,
            "kg_relationships": kg_count,
            "total_examples": len(examples_to_store)
        }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Populate RAG and KG with code examples"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Populate all examples"
    )
    parser.add_argument(
        "--language",
        type=str,
        help="Filter by language (e.g., python, rust)"
    )
    parser.add_argument(
        "--pattern",
        type=str,
        help="Filter by pattern (e.g., repository, factory)"
    )
    parser.add_argument(
        "--rag-only",
        action="store_true",
        help="Only populate RAG (skip Knowledge Graph)"
    )

    args = parser.parse_args()

    # Initialize populator
    populator = CodeExamplePopulator(
        knowledge_graph=None if args.rag_only else KnowledgeGraph()
    )

    # Populate
    results = populator.populate_all(
        language=args.language,
        pattern=args.pattern
    )

    print("\n" + "=" * 70)
    print("Population Complete!")
    print("=" * 70)
    print(f"RAG Examples Stored: {results['rag_examples']}")
    print(f"KG Relationships Created: {results['kg_relationships']}")
    print(f"Total Examples: {results['total_examples']}")


if __name__ == "__main__":
    main()
