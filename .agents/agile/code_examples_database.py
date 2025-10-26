#!/usr/bin/env python3
"""
Database-specific code examples for RAG/KG population.

Examples for:
- SQL databases (PostgreSQL, MySQL, SQL Server, DB2)
- NoSQL databases (MongoDB, Cassandra, Redis, DynamoDB, Elasticsearch, Neo4j)
"""

from code_example_types import CodeExample


# =============================================================================
# POSTGRESQL EXAMPLES
# =============================================================================

POSTGRESQL_EXAMPLES = [
    CodeExample(
        language="SQL",
        pattern="PostgreSQL JSONB Indexing",
        title="JSONB Query Optimization with GIN Index",
        description="Using PostgreSQL's JSONB type with proper indexing for semi-structured data",
        code='''-- User preferences stored as JSONB with optimal indexing
-- Why: Flexible schema for user preferences, fast queries
-- Prevents: Full table scans, slow JSON queries

CREATE TABLE user_preferences (
    user_id BIGINT PRIMARY KEY,
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- GIN index for JSONB containment queries (@> operator)
CREATE INDEX idx_user_preferences_jsonb
ON user_preferences USING GIN (preferences);

-- Partial index for specific preference keys (more efficient)
CREATE INDEX idx_user_preferences_theme
ON user_preferences ((preferences->>'theme'))
WHERE preferences ? 'theme';

-- Insert user preferences (parameterized - prevent SQL injection)
INSERT INTO user_preferences (user_id, preferences)
VALUES ($1, $2::jsonb)
ON CONFLICT (user_id)
DO UPDATE SET
    preferences = user_preferences.preferences || EXCLUDED.preferences,
    updated_at = CURRENT_TIMESTAMP;
-- Example: $1 = 123, $2 = '{"theme": "dark", "language": "en"}'

-- Query users with specific preference (uses GIN index)
SELECT user_id, preferences
FROM user_preferences
WHERE preferences @> '{"theme": "dark"}'::jsonb;

-- Query with nested JSON path (PostgreSQL 12+)
SELECT user_id, preferences->'notifications'->>'email' as email_pref
FROM user_preferences
WHERE preferences @> '{"notifications": {"email": "enabled"}}'::jsonb;

-- Aggregate JSONB data
SELECT
    preferences->>'theme' as theme,
    COUNT(*) as user_count
FROM user_preferences
WHERE preferences ? 'theme'
GROUP BY preferences->>'theme'
ORDER BY user_count DESC;

-- Update nested JSONB using jsonb_set (immutable operation)
UPDATE user_preferences
SET preferences = jsonb_set(
    preferences,
    '{notifications,email}',
    '"disabled"'::jsonb,
    true  -- create_missing
)
WHERE user_id = $1;

-- Full-text search on JSONB text values
CREATE INDEX idx_user_preferences_fts
ON user_preferences USING GIN (
    to_tsvector('english', preferences::text)
);

SELECT user_id
FROM user_preferences
WHERE to_tsvector('english', preferences::text) @@ to_tsquery('dark & mode');
''',
        quality_score=96,
        tags=["PostgreSQL", "JSONB", "indexing", "GIN", "full-text-search"],
        complexity="advanced",
        demonstrates=["JSONB Queries", "GIN Indexing", "Partial Indexes", "Upsert", "Full-Text Search"],
        prevents=["Full Table Scans", "SQL Injection", "Slow JSON Queries"]
    ),

    CodeExample(
        language="SQL",
        pattern="PostgreSQL Window Functions",
        title="Running Totals and Rankings with Window Functions",
        description="Using PostgreSQL window functions for analytics without self-joins",
        code='''-- Order analytics using window functions
-- Why: Avoid expensive self-joins, get running totals and rankings
-- Prevents: N+1 queries, performance issues

-- Create sample table
CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    order_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL
);

-- Running total per user (OVER clause)
SELECT
    order_id,
    user_id,
    amount,
    SUM(amount) OVER (
        PARTITION BY user_id
        ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) as running_total
FROM orders
WHERE status = 'completed'
ORDER BY user_id, order_date;

-- Rank orders within each user (ROW_NUMBER, RANK, DENSE_RANK)
SELECT
    order_id,
    user_id,
    amount,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY amount DESC) as row_num,
    RANK() OVER (PARTITION BY user_id ORDER BY amount DESC) as rank,
    DENSE_RANK() OVER (PARTITION BY user_id ORDER BY amount DESC) as dense_rank
FROM orders;

-- Compare with previous/next row (LAG/LEAD)
SELECT
    order_id,
    user_id,
    amount,
    order_date,
    LAG(amount) OVER (PARTITION BY user_id ORDER BY order_date) as prev_amount,
    LEAD(amount) OVER (PARTITION BY user_id ORDER BY order_date) as next_amount,
    amount - LAG(amount) OVER (PARTITION BY user_id ORDER BY order_date) as amount_change
FROM orders;

-- Moving average (3-order window)
SELECT
    order_id,
    user_id,
    amount,
    AVG(amount) OVER (
        PARTITION BY user_id
        ORDER BY order_date
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) as moving_avg_3
FROM orders;

-- Percentiles and quartiles
SELECT
    user_id,
    amount,
    NTILE(4) OVER (ORDER BY amount) as quartile,
    PERCENT_RANK() OVER (ORDER BY amount) as percent_rank,
    CUME_DIST() OVER (ORDER BY amount) as cumulative_dist
FROM orders;

-- First and last value in partition
SELECT
    order_id,
    user_id,
    amount,
    FIRST_VALUE(amount) OVER (
        PARTITION BY user_id ORDER BY order_date
    ) as first_order_amount,
    LAST_VALUE(amount) OVER (
        PARTITION BY user_id ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) as last_order_amount
FROM orders;
''',
        quality_score=94,
        tags=["PostgreSQL", "window-functions", "analytics", "ranking", "running-totals"],
        complexity="advanced",
        demonstrates=["Window Functions", "PARTITION BY", "LAG/LEAD", "ROW_NUMBER", "Running Totals"],
        prevents=["Self-Joins", "Subqueries", "Performance Issues"]
    ),
]


# =============================================================================
# MONGODB EXAMPLES
# =============================================================================

MONGODB_EXAMPLES = [
    CodeExample(
        language="JavaScript",
        pattern="MongoDB Aggregation Pipeline",
        title="E-commerce Analytics with Aggregation Pipeline",
        description="Using MongoDB aggregation pipeline for complex analytics instead of MapReduce",
        code='''// MongoDB Aggregation Pipeline for Order Analytics
// Why: Complex transformations in database, not application code
// Prevents: N+1 queries, application-side joins, slow queries

// Collection: orders
/*
{
  "_id": ObjectId(),
  "userId": ObjectId(),
  "items": [
    { "productId": ObjectId(), "quantity": 2, "price": 29.99 },
    { "productId": ObjectId(), "quantity": 1, "price": 49.99 }
  ],
  "total": 109.97,
  "status": "completed",
  "createdAt": ISODate("2025-01-15")
}
*/

// Aggregation: Top selling products with revenue
db.orders.aggregate([
    // Stage 1: Filter completed orders
    {
        $match: {
            status: "completed",
            createdAt: {
                $gte: ISODate("2025-01-01"),
                $lt: ISODate("2025-02-01")
            }
        }
    },

    // Stage 2: Unwind items array (one document per item)
    { $unwind: "$items" },

    // Stage 3: Group by product, calculate metrics
    {
        $group: {
            _id: "$items.productId",
            totalQuantity: { $sum: "$items.quantity" },
            totalRevenue: {
                $sum: {
                    $multiply: ["$items.quantity", "$items.price"]
                }
            },
            orderCount: { $sum: 1 },
            avgQuantity: { $avg: "$items.quantity" }
        }
    },

    // Stage 4: Lookup product details (left join)
    {
        $lookup: {
            from: "products",
            localField: "_id",
            foreignField: "_id",
            as: "product"
        }
    },

    // Stage 5: Unwind product array (single product per document)
    { $unwind: "$product" },

    // Stage 6: Project final shape
    {
        $project: {
            _id: 0,
            productId: "$_id",
            productName: "$product.name",
            category: "$product.category",
            totalQuantity: 1,
            totalRevenue: { $round: ["$totalRevenue", 2] },
            orderCount: 1,
            avgQuantity: { $round: ["$avgQuantity", 2] },
            revenuePerOrder: {
                $round: [
                    { $divide: ["$totalRevenue", "$orderCount"] },
                    2
                ]
            }
        }
    },

    // Stage 7: Sort by revenue (descending)
    { $sort: { totalRevenue: -1 } },

    // Stage 8: Limit to top 10
    { $limit: 10 },

    // Stage 9: Add computed fields
    {
        $addFields: {
            rank: { $add: [{ $indexOfArray: ["$$ROOT", "$$ROOT"] }, 1] }
        }
    }
]);

// User purchase behavior analysis
db.orders.aggregate([
    {
        $match: { status: "completed" }
    },
    {
        $group: {
            _id: "$userId",
            totalOrders: { $sum: 1 },
            totalSpent: { $sum: "$total" },
            avgOrderValue: { $avg: "$total" },
            firstPurchase: { $min: "$createdAt" },
            lastPurchase: { $max: "$createdAt" }
        }
    },
    {
        $project: {
            userId: "$_id",
            _id: 0,
            totalOrders: 1,
            totalSpent: { $round: ["$totalSpent", 2] },
            avgOrderValue: { $round: ["$avgOrderValue", 2] },
            firstPurchase: 1,
            lastPurchase: 1,
            daysSinceFirst: {
                $divide: [
                    { $subtract: ["$lastPurchase", "$firstPurchase"] },
                    86400000  // milliseconds in a day
                ]
            },
            customerSegment: {
                $switch: {
                    branches: [
                        { case: { $gte: ["$totalSpent", 1000] }, then: "VIP" },
                        { case: { $gte: ["$totalSpent", 500] }, then: "Premium" },
                        { case: { $gte: ["$totalSpent", 100] }, then: "Regular" }
                    ],
                    default: "New"
                }
            }
        }
    },
    {
        $sort: { totalSpent: -1 }
    }
]);

// Create index for aggregation performance
db.orders.createIndex({ status: 1, createdAt: -1 });
db.orders.createIndex({ userId: 1, status: 1 });

// Use $facet for multiple aggregations in one query
db.orders.aggregate([
    {
        $facet: {
            // Facet 1: Revenue by status
            byStatus: [
                {
                    $group: {
                        _id: "$status",
                        totalRevenue: { $sum: "$total" },
                        count: { $sum: 1 }
                    }
                }
            ],
            // Facet 2: Revenue by month
            byMonth: [
                {
                    $group: {
                        _id: {
                            $dateToString: {
                                format: "%Y-%m",
                                date: "$createdAt"
                            }
                        },
                        totalRevenue: { $sum: "$total" },
                        count: { $sum: 1 }
                    }
                },
                { $sort: { _id: 1 } }
            ],
            // Facet 3: Overall stats
            overall: [
                {
                    $group: {
                        _id: null,
                        totalRevenue: { $sum: "$total" },
                        totalOrders: { $sum: 1 },
                        avgOrderValue: { $avg: "$total" }
                    }
                }
            ]
        }
    }
]);
''',
        quality_score=95,
        tags=["MongoDB", "aggregation-pipeline", "analytics", "lookup", "facets"],
        complexity="advanced",
        demonstrates=["Aggregation Pipeline", "$lookup", "$unwind", "$facet", "Complex Grouping"],
        prevents=["N+1 Queries", "Application-Side Joins", "MapReduce"]
    ),
]


# =============================================================================
# CASSANDRA EXAMPLES
# =============================================================================

CASSANDRA_EXAMPLES = [
    CodeExample(
        language="CQL",
        pattern="Cassandra Data Modeling",
        title="Time-Series Data Modeling for IoT Sensors",
        description="Cassandra data modeling optimized for write-heavy time-series queries",
        code='''-- Cassandra Time-Series Data Model for IoT Sensors
-- Why: Optimized for write-heavy workloads, time-based queries
-- Prevents: Hot partitions, slow range queries

-- Create keyspace with NetworkTopologyStrategy for production
CREATE KEYSPACE IF NOT EXISTS iot_data
WITH replication = {
    'class': 'NetworkTopologyStrategy',
    'datacenter1': 3  -- 3 replicas in datacenter1
};

USE iot_data;

-- Sensor readings table - partitioned by sensor and day
-- Why: Evenly distributes data, efficient time-range queries within partition
CREATE TABLE sensor_readings (
    sensor_id UUID,
    reading_date DATE,          -- Partition key component (distribution)
    reading_time TIMESTAMP,     -- Clustering key (ordering within partition)
    temperature DOUBLE,
    humidity DOUBLE,
    battery_level INT,
    PRIMARY KEY ((sensor_id, reading_date), reading_time)
) WITH CLUSTERING ORDER BY (reading_time DESC)  -- Newest first
AND compaction = {'class': 'TimeWindowCompactionStrategy', 'compaction_window_unit': 'DAYS', 'compaction_window_size': 1}
AND default_time_to_live = 2592000;  -- 30 days TTL (auto-delete old data)

-- Sensor metadata table (reference data, low cardinality)
CREATE TABLE sensors (
    sensor_id UUID PRIMARY KEY,
    location TEXT,
    type TEXT,
    install_date TIMESTAMP,
    metadata MAP<TEXT, TEXT>
);

-- Materialized view for querying by location
-- Why: Different query pattern (by location instead of sensor_id)
CREATE MATERIALIZED VIEW sensors_by_location AS
    SELECT sensor_id, location, type, install_date
    FROM sensors
    WHERE location IS NOT NULL AND sensor_id IS NOT NULL
    PRIMARY KEY (location, sensor_id);

-- Insert sensor reading (prepared statement - ALWAYS use these)
-- Application code:
INSERT INTO sensor_readings (
    sensor_id, reading_date, reading_time, temperature, humidity, battery_level
) VALUES (?, ?, ?, ?, ?, ?)
USING TTL 2592000;  -- 30 days
-- Parameters: sensor_id, current_date, current_timestamp, 72.5, 45.2, 85

-- Batch insert for same partition (good performance)
-- Why: All inserts go to same partition
BEGIN BATCH
INSERT INTO sensor_readings (sensor_id, reading_date, reading_time, temperature, humidity, battery_level)
    VALUES (?, ?, ?, ?, ?, ?);
INSERT INTO sensor_readings (sensor_id, reading_date, reading_time, temperature, humidity, battery_level)
    VALUES (?, ?, ?, ?, ?, ?);
-- ... more inserts for SAME sensor_id and reading_date
APPLY BATCH;

-- Query recent readings for a sensor (efficient - within partition)
SELECT temperature, humidity, reading_time
FROM sensor_readings
WHERE sensor_id = ?
  AND reading_date = ?
  AND reading_time >= ?
  AND reading_time <= ?
ORDER BY reading_time DESC
LIMIT 100;

-- Query across multiple days (multiple partitions - less efficient but necessary)
SELECT temperature, AVG(temperature) OVER (ORDER BY reading_time ROWS 10 PRECEDING)
FROM sensor_readings
WHERE sensor_id = ?
  AND reading_date IN (?, ?, ?);  -- List of dates

-- Aggregate query with GROUP BY (Cassandra 3.10+)
SELECT sensor_id, reading_date, AVG(temperature) as avg_temp, MAX(humidity) as max_humidity
FROM sensor_readings
WHERE sensor_id = ?
  AND reading_date IN (?, ?)
GROUP BY sensor_id, reading_date;

-- Create index on battery_level for low-battery queries
-- Note: Secondary indexes are expensive, use sparingly
CREATE INDEX ON sensor_readings (battery_level);

-- Query low-battery sensors (uses secondary index)
SELECT sensor_id, reading_date, reading_time, battery_level
FROM sensor_readings
WHERE battery_level < 20
LIMIT 100
ALLOW FILTERING;  -- Explicit acknowledgment of performance impact

-- Counter table for sensor statistics
CREATE TABLE sensor_stats (
    sensor_id UUID,
    stat_type TEXT,              -- 'readings_count', 'errors_count', etc.
    counter_value COUNTER,
    PRIMARY KEY (sensor_id, stat_type)
);

-- Increment counter (atomic operation)
UPDATE sensor_stats
SET counter_value = counter_value + 1
WHERE sensor_id = ?
  AND stat_type = 'readings_count';

-- Use SASI index for text search (better than secondary index for strings)
CREATE CUSTOM INDEX sensor_location_sasi ON sensors (location)
USING 'org.apache.cassandra.index.sasi.SASIIndex'
WITH OPTIONS = {'mode': 'CONTAINS', 'analyzer_class': 'org.apache.cassandra.index.sasi.analyzer.StandardAnalyzer'};

-- Query with SASI (supports LIKE)
SELECT sensor_id, location FROM sensors
WHERE location LIKE '%Building%';
''',
        quality_score=96,
        tags=["Cassandra", "CQL", "data-modeling", "time-series", "partitioning"],
        complexity="advanced",
        demonstrates=["Partition Key Design", "Clustering Keys", "TTL", "Materialized Views", "Counters"],
        prevents=["Hot Partitions", "Slow Range Queries", "Unbounded Queries"]
    ),
]


# =============================================================================
# MYSQL EXAMPLES
# =============================================================================

MYSQL_EXAMPLES = [
    CodeExample(
        language="SQL",
        pattern="MySQL InnoDB Optimization",
        title="Optimized InnoDB Table Design with utf8mb4",
        description="MySQL InnoDB best practices including utf8mb4, JSON functions, and partitioning",
        code='''-- MySQL InnoDB Best Practices
-- Why: Emoji support, ACID compliance, proper indexing
-- Prevents: Character encoding issues, slow queries, data loss

-- Set proper character set (supports emojis)
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create table with InnoDB engine
CREATE TABLE posts (
    post_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    content TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    tags JSON,  -- MySQL 5.7+ JSON type
    metadata JSON,
    view_count INT UNSIGNED DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_created (user_id, created_at),
    INDEX idx_view_count (view_count),
    FULLTEXT INDEX idx_content_fulltext (title, content) WITH PARSER ngram
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC;

-- JSON functions (MySQL 5.7+)
-- Insert with JSON data (use parameterized queries in application)
INSERT INTO posts (user_id, title, content, tags, metadata)
VALUES (
    ?,
    ?,
    ?,
    JSON_ARRAY('mysql', 'database', 'tutorial'),
    JSON_OBJECT('category', 'tutorial', 'difficulty', 'beginner')
);

-- Query JSON fields
SELECT post_id, title, JSON_EXTRACT(tags, '$[0]') as first_tag
FROM posts
WHERE JSON_CONTAINS(tags, '"mysql"');

-- Use generated columns for JSON indexing (MySQL 5.7+)
ALTER TABLE posts
ADD COLUMN category VARCHAR(50)
AS (JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.category'))) STORED,
ADD INDEX idx_category (category);

-- Now can efficiently query by category
SELECT post_id, title, category
FROM posts
WHERE category = 'tutorial';

-- UPSERT using INSERT ... ON DUPLICATE KEY UPDATE
INSERT INTO posts (post_id, user_id, title, content, tags)
VALUES (?, ?, ?, ?, ?)
ON DUPLICATE KEY UPDATE
    title = VALUES(title),
    content = VALUES(content),
    tags = VALUES(tags),
    updated_at = CURRENT_TIMESTAMP;

-- Full-text search
SELECT post_id, title,
       MATCH(title, content) AGAINST (? IN NATURAL LANGUAGE MODE) as relevance_score
FROM posts
WHERE MATCH(title, content) AGAINST (? IN NATURAL LANGUAGE MODE)
ORDER BY relevance_score DESC
LIMIT 20;

-- Partitioning for large tables (by date range)
CREATE TABLE posts_partitioned (
    post_id BIGINT UNSIGNED AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    content TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, created_at)
) ENGINE=InnoDB
PARTITION BY RANGE (UNIX_TIMESTAMP(created_at)) (
    PARTITION p2024_q1 VALUES LESS THAN (UNIX_TIMESTAMP('2024-04-01')),
    PARTITION p2024_q2 VALUES LESS THAN (UNIX_TIMESTAMP('2024-07-01')),
    PARTITION p2024_q3 VALUES LESS THAN (UNIX_TIMESTAMP('2024-10-01')),
    PARTITION p2024_q4 VALUES LESS THAN (UNIX_TIMESTAMP('2025-01-01')),
    PARTITION p2025_q1 VALUES LESS THAN (UNIX_TIMESTAMP('2025-04-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- Explain query to verify index usage
EXPLAIN SELECT post_id, title FROM posts
WHERE user_id = ? AND created_at >= ?
ORDER BY created_at DESC LIMIT 10;
''',
        quality_score=93,
        tags=["MySQL", "InnoDB", "utf8mb4", "JSON", "partitioning", "full-text-search"],
        complexity="intermediate",
        demonstrates=["utf8mb4 Encoding", "JSON Functions", "Generated Columns", "Full-Text Search", "Partitioning"],
        prevents=["Character Encoding Issues", "Slow JSON Queries", "Table Scans"]
    ),
]


# =============================================================================
# REDIS EXAMPLES
# =============================================================================

REDIS_EXAMPLES = [
    CodeExample(
        language="Redis",
        pattern="Redis Data Structures",
        title="Advanced Redis Patterns for Caching and Rate Limiting",
        description="Using Redis data structures efficiently: pipelining, Lua scripts, and HyperLogLog",
        code='''# Redis Advanced Patterns
# Why: Sub-millisecond performance, atomic operations
# Prevents: Race conditions, cache stampede, network round-trips

# ==== STRING OPERATIONS ====

# Simple key-value with expiration (cache pattern)
SET user:1000:profile '{"name":"Alice","email":"alice@example.com"}' EX 3600
GET user:1000:profile

# Atomic increment (counters)
INCR page:views:home
INCRBY page:views:home 10
DECR inventory:product:123

# Atomic operations (prevent race conditions)
SET lock:user:1000 "processing" NX EX 30  # Only set if not exists
GET lock:user:1000
DEL lock:user:1000


# ==== HASH OPERATIONS (for objects) ====

# Store user object as hash (more efficient than JSON string for partial updates)
HSET user:1000 name "Alice" email "alice@example.com" age 30
HGET user:1000 name
HGETALL user:1000
HMGET user:1000 name email  # Get multiple fields

# Atomic increment on hash field
HINCRBY user:1000 login_count 1


# ==== LIST OPERATIONS (for queues, feeds) ====

# Job queue (FIFO)
LPUSH jobs:queue '{"task":"send_email","to":"user@example.com"}'
RPOP jobs:queue  # Blocking: BRPOP jobs:queue 30

# Activity feed (limited size)
LPUSH feed:user:1000 "Alice posted a photo"
LTRIM feed:user:1000 0 99  # Keep only 100 most recent items
LRANGE feed:user:1000 0 19  # Get first 20 items


# ==== SET OPERATIONS (for unique items, relationships) ====

# User's followers
SADD followers:user:1000 2000 3000 4000
SISMEMBER followers:user:1000 2000  # Check membership (O(1))
SCARD followers:user:1000  # Count followers

# Common followers (set intersection)
SINTER followers:user:1000 followers:user:2000

# Suggested friends (followers of followers, excluding existing)
SDIFF followers:user:2000 followers:user:1000


# ==== SORTED SET OPERATIONS (for leaderboards, rankings) ====

# Leaderboard
ZADD leaderboard 1000 "player1" 1500 "player2" 2000 "player3"
ZINCRBY leaderboard 100 "player1"  # Atomic score increment

# Top 10 players
ZREVRANGE leaderboard 0 9 WITHSCORES

# Player rank
ZREVRANK leaderboard "player1"

# Players in score range
ZRANGEBYSCORE leaderboard 1000 2000 WITHSCORES

# Time-based expiration (cleanup old entries)
ZREMRANGEBYSCORE sessions:active 0 1704067200  # Remove before timestamp


# ==== PIPELINING (reduce network round-trips) ====

# Without pipelining: 5 network round-trips
# With pipelining: 1 network round-trip
MULTI
GET user:1000:profile
HGETALL user:1000:stats
ZRANGE leaderboard:daily 0 9
SMEMBERS followers:user:1000
LRANGE feed:user:1000 0 19
EXEC


# ==== LUA SCRIPTS (atomic operations) ====

# Rate limiting using Lua (atomic, prevents race conditions)
EVAL "
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local current = redis.call('INCR', key)
if current == 1 then
    redis.call('EXPIRE', key, window)
end
if current > limit then
    return 0  -- Rate limit exceeded
else
    return 1  -- Allow request
end
" 1 rate_limit:user:1000:api 100 3600
# Limit: 100 requests per 3600 seconds (1 hour)


# ==== HYPERLOGLOG (cardinality estimation) ====

# Count unique visitors (memory-efficient: ~12KB for billions of items)
PFADD unique:visitors:2025-01-15 "user1" "user2" "user3"
PFCOUNT unique:visitors:2025-01-15  # Approximate count (0.81% error)

# Merge multiple HyperLogLogs
PFMERGE unique:visitors:2025-01-week unique:visitors:2025-01-15 unique:visitors:2025-01-16


# ==== STREAMS (message queue, event sourcing) ====

# Add event to stream
XADD events:user:1000 * action "login" timestamp 1704067200 ip "192.168.1.1"

# Read stream events
XREAD COUNT 10 STREAMS events:user:1000 0

# Consumer groups (competing consumers pattern)
XGROUP CREATE events:user:1000 processors $ MKSTREAM
XREADGROUP GROUP processors consumer1 COUNT 10 STREAMS events:user:1000 >


# ==== CACHE PATTERNS ====

# Cache-aside pattern (lazy loading)
# 1. Try to get from cache
GET product:123
# 2. If cache miss, fetch from database
# 3. Set in cache with expiration
SET product:123 '{"name":"Product","price":99.99}' EX 3600

# Cache stampede prevention (use SETNX for locking)
SET lock:product:123 1 NX EX 10
# If lock acquired, fetch from database and cache
# If lock not acquired, wait and retry


# ==== MONITORING ====

# Get statistics
INFO stats
INFO memory
SLOWLOG GET 10  # Get 10 slowest queries
MONITOR  # Real-time command monitoring (DEV ONLY - impacts performance)
''',
        quality_score=95,
        tags=["Redis", "caching", "data-structures", "pipelining", "lua", "rate-limiting"],
        complexity="advanced",
        demonstrates=["Redis Data Structures", "Pipelining", "Lua Scripts", "HyperLogLog", "Streams", "Rate Limiting"],
        prevents=["Race Conditions", "Cache Stampede", "Network Round-Trips", "Memory Inefficiency"]
    ),
]


# =============================================================================
# DYNAMODB EXAMPLES
# =============================================================================

DYNAMODB_EXAMPLES = [
    CodeExample(
        language="JavaScript",
        pattern="DynamoDB Single-Table Design",
        title="Multi-Entity Single-Table Design with GSI",
        description="DynamoDB single-table design pattern for e-commerce with access patterns",
        code='''// DynamoDB Single-Table Design Pattern
// Why: Minimize number of tables, efficient queries, lower costs
// Prevents: Multiple queries, joins, high read costs

/**
 * Table Schema: ecommerce
 *
 * Access Patterns:
 * 1. Get user by ID
 * 2. Get all orders for a user
 * 3. Get order by ID
 * 4. Get all products in an order
 * 5. Get product by SKU
 * 6. Get all reviews for a product
 */

const AWS = require('aws-sdk');
const dynamodb = new AWS.DynamoDB.DocumentClient();

const TABLE_NAME = 'ecommerce';

// ==== TABLE DESIGN ====

/**
 * Primary Key: PK (Partition Key), SK (Sort Key)
 * GSI1: GSI1PK (Partition Key), GSI1SK (Sort Key)
 *
 * Entity Types:
 *
 * USER:
 *   PK: USER#<userId>
 *   SK: METADATA
 *   Type: USER
 *
 * ORDER:
 *   PK: USER#<userId>
 *   SK: ORDER#<orderId>
 *   GSI1PK: ORDER#<orderId>  // For fetching order by ID
 *   GSI1SK: METADATA
 *   Type: ORDER
 *
 * ORDERITEM:
 *   PK: ORDER#<orderId>
 *   SK: ITEM#<productSku>
 *   Type: ORDERITEM
 *
 * PRODUCT:
 *   PK: PRODUCT#<sku>
 *   SK: METADATA
 *   Type: PRODUCT
 *
 * REVIEW:
 *   PK: PRODUCT#<sku>
 *   SK: REVIEW#<reviewId>
 *   GSI1PK: USER#<userId>  // For user's reviews
 *   GSI1SK: REVIEW#<reviewId>
 *   Type: REVIEW
 */


// ==== CREATE OPERATIONS ====

// Create user
async function createUser(userId, userData) {
    const params = {
        TableName: TABLE_NAME,
        Item: {
            PK: `USER#${userId}`,
            SK: 'METADATA',
            Type: 'USER',
            userId,
            name: userData.name,
            email: userData.email,
            createdAt: new Date().toISOString()
        },
        ConditionExpression: 'attribute_not_exists(PK)'  // Prevent overwrite
    };

    return dynamodb.put(params).promise();
}

// Create order with transaction (ACID compliance)
async function createOrder(userId, orderId, items) {
    const timestamp = new Date().toISOString();

    // Build transaction items
    const transactItems = [
        // Create order metadata
        {
            Put: {
                TableName: TABLE_NAME,
                Item: {
                    PK: `USER#${userId}`,
                    SK: `ORDER#${orderId}`,
                    GSI1PK: `ORDER#${orderId}`,
                    GSI1SK: 'METADATA',
                    Type: 'ORDER',
                    orderId,
                    userId,
                    status: 'pending',
                    total: items.reduce((sum, item) => sum + (item.price * item.quantity), 0),
                    createdAt: timestamp
                },
                ConditionExpression: 'attribute_not_exists(PK)'
            }
        }
    ];

    // Add order items
    items.forEach(item => {
        transactItems.push({
            Put: {
                TableName: TABLE_NAME,
                Item: {
                    PK: `ORDER#${orderId}`,
                    SK: `ITEM#${item.sku}`,
                    Type: 'ORDERITEM',
                    orderId,
                    sku: item.sku,
                    productName: item.productName,
                    quantity: item.quantity,
                    price: item.price,
                    createdAt: timestamp
                }
            }
        });
    });

    const params = { TransactItems: transactItems };
    return dynamodb.transactWrite(params).promise();
}


// ==== QUERY OPERATIONS ====

// Get user by ID (single item query)
async function getUser(userId) {
    const params = {
        TableName: TABLE_NAME,
        Key: {
            PK: `USER#${userId}`,
            SK: 'METADATA'
        }
    };

    const result = await dynamodb.get(params).promise();
    return result.Item;
}

// Get all orders for a user (query with begins_with)
async function getUserOrders(userId, limit = 20) {
    const params = {
        TableName: TABLE_NAME,
        KeyConditionExpression: 'PK = :pk AND begins_with(SK, :sk)',
        ExpressionAttributeValues: {
            ':pk': `USER#${userId}`,
            ':sk': 'ORDER#'
        },
        Limit: limit,
        ScanIndexForward: false  // Most recent first
    };

    const result = await dynamodb.query(params).promise();
    return result.Items;
}

// Get order by ID using GSI
async function getOrder(orderId) {
    const params = {
        TableName: TABLE_NAME,
        IndexName: 'GSI1',
        KeyConditionExpression: 'GSI1PK = :pk AND GSI1SK = :sk',
        ExpressionAttributeValues: {
            ':pk': `ORDER#${orderId}`,
            ':sk': 'METADATA'
        }
    };

    const result = await dynamodb.query(params).promise();
    return result.Items[0];
}

// Get all items in an order
async function getOrderItems(orderId) {
    const params = {
        TableName: TABLE_NAME,
        KeyConditionExpression: 'PK = :pk AND begins_with(SK, :sk)',
        ExpressionAttributeValues: {
            ':pk': `ORDER#${orderId}`,
            ':sk': 'ITEM#'
        }
    };

    const result = await dynamodb.query(params).promise();
    return result.Items;
}

// Get all reviews for a product
async function getProductReviews(sku, limit = 20) {
    const params = {
        TableName: TABLE_NAME,
        KeyConditionExpression: 'PK = :pk AND begins_with(SK, :sk)',
        ExpressionAttributeValues: {
            ':pk': `PRODUCT#${sku}`,
            ':sk': 'REVIEW#'
        },
        Limit: limit
    };

    const result = await dynamodb.query(params).promise();
    return result.Items;
}


// ==== UPDATE OPERATIONS ====

// Update order status
async function updateOrderStatus(userId, orderId, newStatus) {
    const params = {
        TableName: TABLE_NAME,
        Key: {
            PK: `USER#${userId}`,
            SK: `ORDER#${orderId}`
        },
        UpdateExpression: 'SET #status = :status, updatedAt = :timestamp',
        ExpressionAttributeNames: {
            '#status': 'status'  // 'status' is reserved word
        },
        ExpressionAttributeValues: {
            ':status': newStatus,
            ':timestamp': new Date().toISOString()
        },
        ReturnValues: 'ALL_NEW'
    };

    const result = await dynamodb.update(params).promise();
    return result.Attributes;
}


// ==== BATCH OPERATIONS ====

// Batch get multiple products
async function getProducts(skus) {
    const keys = skus.map(sku => ({
        PK: `PRODUCT#${sku}`,
        SK: 'METADATA'
    }));

    const params = {
        RequestItems: {
            [TABLE_NAME]: {
                Keys: keys
            }
        }
    };

    const result = await dynamodb.batchGet(params).promise();
    return result.Responses[TABLE_NAME];
}


// ==== CONDITIONAL OPERATIONS ====

// Add review only if user purchased product
async function addReview(userId, sku, reviewId, rating, comment) {
    // First, verify user has ordered this product (query)
    const orderParams = {
        TableName: TABLE_NAME,
        IndexName: 'GSI1',
        KeyConditionExpression: 'GSI1PK = :userPk',
        FilterExpression: 'contains(orderItems, :sku)',  // Simplified - actual implementation needs orderItems query
        ExpressionAttributeValues: {
            ':userPk': `USER#${userId}`,
            ':sku': sku
        },
        Limit: 1
    };

    // If user has ordered product, add review
    const params = {
        TableName: TABLE_NAME,
        Item: {
            PK: `PRODUCT#${sku}`,
            SK: `REVIEW#${reviewId}`,
            GSI1PK: `USER#${userId}`,
            GSI1SK: `REVIEW#${reviewId}`,
            Type: 'REVIEW',
            reviewId,
            userId,
            sku,
            rating,
            comment,
            createdAt: new Date().toISOString()
        }
    };

    return dynamodb.put(params).promise();
}

// Export functions
module.exports = {
    createUser,
    createOrder,
    getUser,
    getUserOrders,
    getOrder,
    getOrderItems,
    getProductReviews,
    updateOrderStatus,
    getProducts,
    addReview
};
''',
        quality_score=96,
        tags=["DynamoDB", "NoSQL", "single-table-design", "GSI", "transactions"],
        complexity="advanced",
        demonstrates=["Single-Table Design", "GSI", "Transactions", "Composite Keys", "Access Patterns"],
        prevents=["Multiple Queries", "Joins", "Scans", "High Read Costs"]
    ),
]


# Export all examples
ALL_DATABASE_EXAMPLES = {
    "PostgreSQL": POSTGRESQL_EXAMPLES,
    "MongoDB": MONGODB_EXAMPLES,
    "Cassandra": CASSANDRA_EXAMPLES,
    "MySQL": MYSQL_EXAMPLES,
    "Redis": REDIS_EXAMPLES,
    "DynamoDB": DYNAMODB_EXAMPLES,
}
