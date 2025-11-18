"""
AWS DynamoDB Tables deployment using Pulumi
Creates DynamoDB tables with different configurations and access patterns
"""

import pulumi
import pulumi_aws as aws
import random
import string

# Generate random suffix for unique naming
def generate_random_suffix(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

random_suffix = generate_random_suffix()

# Create a simple DynamoDB table for user data
users_table = aws.dynamodb.Table(
    f"users-table-{random_suffix}",
    name=f"users-table-{random_suffix}",
    billing_mode="PAY_PER_REQUEST",
    hash_key="user_id",
    
    attributes=[
        aws.dynamodb.TableAttributeArgs(
            name="user_id",
            type="S"
        ),
        aws.dynamodb.TableAttributeArgs(
            name="email",
            type="S"
        )
    ],
    
    global_secondary_indexes=[
        aws.dynamodb.TableGlobalSecondaryIndexArgs(
            name="email-index",
            hash_key="email",
            projection_type="ALL"
        )
    ],
    
    tags={
        "Name": f"users-table-{random_suffix}",
        "Environment": "dev",
        "Service": "dynamodb",
        "Purpose": "user-management"
    }
)

# Create a DynamoDB table for product catalog with composite key
products_table = aws.dynamodb.Table(
    f"products-table-{random_suffix}",
    name=f"products-table-{random_suffix}",
    billing_mode="PAY_PER_REQUEST",
    hash_key="category",
    range_key="product_id",
    
    attributes=[
        aws.dynamodb.TableAttributeArgs(
            name="category",
            type="S"
        ),
        aws.dynamodb.TableAttributeArgs(
            name="product_id",
            type="S"
        ),
        aws.dynamodb.TableAttributeArgs(
            name="brand",
            type="S"
        ),
        aws.dynamodb.TableAttributeArgs(
            name="price",
            type="N"
        )
    ],
    
    global_secondary_indexes=[
        aws.dynamodb.TableGlobalSecondaryIndexArgs(
            name="brand-index",
            hash_key="brand",
            range_key="price",
            projection_type="ALL"
        )
    ],
    
    local_secondary_indexes=[
        aws.dynamodb.TableLocalSecondaryIndexArgs(
            name="category-price-index",
            range_key="price",
            projection_type="ALL"
        )
    ],
    
    tags={
        "Name": f"products-table-{random_suffix}",
        "Environment": "dev",
        "Service": "dynamodb",
        "Purpose": "product-catalog"
    }
)

# Create a DynamoDB table with provisioned billing for high-throughput scenarios
orders_table = aws.dynamodb.Table(
    f"orders-table-{random_suffix}",
    name=f"orders-table-{random_suffix}",
    billing_mode="PROVISIONED",
    read_capacity=5,
    write_capacity=5,
    hash_key="order_id",
    range_key="timestamp",
    
    attributes=[
        aws.dynamodb.TableAttributeArgs(
            name="order_id",
            type="S"
        ),
        aws.dynamodb.TableAttributeArgs(
            name="timestamp",
            type="N"
        ),
        aws.dynamodb.TableAttributeArgs(
            name="customer_id",
            type="S"
        ),
        aws.dynamodb.TableAttributeArgs(
            name="status",
            type="S"
        )
    ],
    
    global_secondary_indexes=[
        aws.dynamodb.TableGlobalSecondaryIndexArgs(
            name="customer-orders-index",
            hash_key="customer_id",
            range_key="timestamp",
            read_capacity=5,
            write_capacity=5,
            projection_type="ALL"
        ),
        aws.dynamodb.TableGlobalSecondaryIndexArgs(
            name="status-index",
            hash_key="status",
            range_key="timestamp",
            read_capacity=5,
            write_capacity=5,
            projection_type="KEYS_ONLY"
        )
    ],
    
    tags={
        "Name": f"orders-table-{random_suffix}",
        "Environment": "dev",
        "Service": "dynamodb",
        "Purpose": "order-management"
    }
)

# Create a DynamoDB table for session management with TTL
sessions_table = aws.dynamodb.Table(
    f"sessions-table-{random_suffix}",
    name=f"sessions-table-{random_suffix}",
    billing_mode="PAY_PER_REQUEST",
    hash_key="session_id",
    
    attributes=[
        aws.dynamodb.TableAttributeArgs(
            name="session_id",
            type="S"
        )
    ],
    
    ttl=aws.dynamodb.TableTtlArgs(
        attribute_name="expires_at",
        enabled=True
    ),
    
    tags={
        "Name": f"sessions-table-{random_suffix}",
        "Environment": "dev",
        "Service": "dynamodb",
        "Purpose": "session-management"
    }
)

# Create a DynamoDB table for analytics with stream enabled
analytics_table = aws.dynamodb.Table(
    f"analytics-table-{random_suffix}",
    name=f"analytics-table-{random_suffix}",
    billing_mode="PAY_PER_REQUEST",
    hash_key="event_id",
    range_key="timestamp",
    
    attributes=[
        aws.dynamodb.TableAttributeArgs(
            name="event_id",
            type="S"
        ),
        aws.dynamodb.TableAttributeArgs(
            name="timestamp",
            type="N"
        ),
        aws.dynamodb.TableAttributeArgs(
            name="user_id",
            type="S"
        )
    ],
    
    global_secondary_indexes=[
        aws.dynamodb.TableGlobalSecondaryIndexArgs(
            name="user-events-index",
            hash_key="user_id",
            range_key="timestamp",
            projection_type="ALL"
        )
    ],
    
    stream_enabled=True,
    stream_view_type="NEW_AND_OLD_IMAGES",
    
    tags={
        "Name": f"analytics-table-{random_suffix}",
        "Environment": "dev",
        "Service": "dynamodb",
        "Purpose": "analytics"
    }
)

# Export table information
pulumi.export("users_table_name", users_table.name)
pulumi.export("users_table_arn", users_table.arn)

pulumi.export("products_table_name", products_table.name)
pulumi.export("products_table_arn", products_table.arn)

pulumi.export("orders_table_name", orders_table.name)
pulumi.export("orders_table_arn", orders_table.arn)

pulumi.export("sessions_table_name", sessions_table.name)
pulumi.export("sessions_table_arn", sessions_table.arn)

pulumi.export("analytics_table_name", analytics_table.name)
pulumi.export("analytics_table_arn", analytics_table.arn)
pulumi.export("analytics_table_stream_arn", analytics_table.stream_arn)

pulumi.export("random_suffix", random_suffix)

# Export table endpoints for SDK usage
pulumi.export("dynamodb_endpoint", "https://dynamodb.us-east-1.amazonaws.com")

# Export table configurations
pulumi.export("table_configurations", {
    "users": {
        "name": users_table.name,
        "hash_key": "user_id",
        "billing_mode": "PAY_PER_REQUEST",
        "gsi": ["email-index"]
    },
    "products": {
        "name": products_table.name,
        "hash_key": "category",
        "range_key": "product_id",
        "billing_mode": "PAY_PER_REQUEST",
        "gsi": ["brand-index"],
        "lsi": ["category-price-index"]
    },
    "orders": {
        "name": orders_table.name,
        "hash_key": "order_id",
        "range_key": "timestamp",
        "billing_mode": "PROVISIONED",
        "read_capacity": 5,
        "write_capacity": 5,
        "gsi": ["customer-orders-index", "status-index"]
    },
    "sessions": {
        "name": sessions_table.name,
        "hash_key": "session_id",
        "billing_mode": "PAY_PER_REQUEST",
        "ttl_enabled": True,
        "ttl_attribute": "expires_at"
    },
    "analytics": {
        "name": analytics_table.name,
        "hash_key": "event_id",
        "range_key": "timestamp",
        "billing_mode": "PAY_PER_REQUEST",
        "stream_enabled": True,
        "stream_view_type": "NEW_AND_OLD_IMAGES",
        "gsi": ["user-events-index"]
    }
})