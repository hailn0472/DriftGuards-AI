"""
AWS SQS Queues deployment using Pulumi
Creates various SQS queues with different configurations for messaging patterns
"""

import pulumi
import pulumi_aws as aws
import random
import string
import json

# Generate random suffix for unique naming
def generate_random_suffix(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

random_suffix = generate_random_suffix()

# Create a standard SQS queue for general messaging
standard_queue = aws.sqs.Queue(
    f"standard-queue-{random_suffix}",
    name=f"standard-queue-{random_suffix}",
    visibility_timeout_seconds=30,
    message_retention_seconds=1209600,  # 14 days
    max_message_size=262144,  # 256 KB
    delay_seconds=0,
    receive_wait_time_seconds=0,
    
    tags={
        "Name": f"standard-queue-{random_suffix}",
        "Environment": "dev",
        "Service": "sqs",
        "Type": "standard"
    }
)

# Create a FIFO queue for ordered messaging
fifo_queue = aws.sqs.Queue(
    f"fifo-queue-{random_suffix}",
    name=f"fifo-queue-{random_suffix}.fifo",
    fifo_queue=True,
    content_based_deduplication=True,
    visibility_timeout_seconds=30,
    message_retention_seconds=1209600,  # 14 days
    max_message_size=262144,  # 256 KB
    delay_seconds=0,
    receive_wait_time_seconds=0,
    
    tags={
        "Name": f"fifo-queue-{random_suffix}",
        "Environment": "dev",
        "Service": "sqs",
        "Type": "fifo"
    }
)

# Create a high-throughput queue with long polling
high_throughput_queue = aws.sqs.Queue(
    f"high-throughput-queue-{random_suffix}",
    name=f"high-throughput-queue-{random_suffix}",
    visibility_timeout_seconds=60,
    message_retention_seconds=345600,  # 4 days
    max_message_size=262144,  # 256 KB
    delay_seconds=0,
    receive_wait_time_seconds=20,  # Long polling
    
    tags={
        "Name": f"high-throughput-queue-{random_suffix}",
        "Environment": "dev",
        "Service": "sqs",
        "Type": "high-throughput"
    }
)

# Create a dead letter queue
dead_letter_queue = aws.sqs.Queue(
    f"dead-letter-queue-{random_suffix}",
    name=f"dead-letter-queue-{random_suffix}",
    visibility_timeout_seconds=30,
    message_retention_seconds=1209600,  # 14 days
    max_message_size=262144,  # 256 KB
    
    tags={
        "Name": f"dead-letter-queue-{random_suffix}",
        "Environment": "dev",
        "Service": "sqs",
        "Type": "dead-letter"
    }
)

# Create a queue with dead letter queue configuration
main_queue_with_dlq = aws.sqs.Queue(
    f"main-queue-with-dlq-{random_suffix}",
    name=f"main-queue-with-dlq-{random_suffix}",
    visibility_timeout_seconds=30,
    message_retention_seconds=1209600,  # 14 days
    max_message_size=262144,  # 256 KB
    delay_seconds=0,
    receive_wait_time_seconds=10,
    
    redrive_policy=pulumi.Output.all(dead_letter_queue.arn).apply(
        lambda args: json.dumps({
            "deadLetterTargetArn": args[0],
            "maxReceiveCount": 3
        })
    ),
    
    tags={
        "Name": f"main-queue-with-dlq-{random_suffix}",
        "Environment": "dev",
        "Service": "sqs",
        "Type": "main-with-dlq"
    }
)

# Create a delayed processing queue
delayed_queue = aws.sqs.Queue(
    f"delayed-queue-{random_suffix}",
    name=f"delayed-queue-{random_suffix}",
    visibility_timeout_seconds=300,  # 5 minutes
    message_retention_seconds=1209600,  # 14 days
    max_message_size=262144,  # 256 KB
    delay_seconds=900,  # 15 minutes delay
    receive_wait_time_seconds=20,
    
    tags={
        "Name": f"delayed-queue-{random_suffix}",
        "Environment": "dev",
        "Service": "sqs",
        "Type": "delayed"
    }
)

# Create queue policies for cross-account access (example)
queue_policy_document = pulumi.Output.all(standard_queue.arn).apply(
    lambda args: json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowSendMessage",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "sqs:SendMessage",
                "Resource": args[0],
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": aws.get_caller_identity().account_id
                    }
                }
            }
        ]
    })
)

# Apply policy to standard queue
standard_queue_policy = aws.sqs.QueuePolicy(
    f"standard-queue-policy-{random_suffix}",
    queue_url=standard_queue.id,
    policy=queue_policy_document
)

# Export queue information
pulumi.export("standard_queue_url", standard_queue.id)
pulumi.export("standard_queue_arn", standard_queue.arn)
pulumi.export("standard_queue_name", standard_queue.name)

pulumi.export("fifo_queue_url", fifo_queue.id)
pulumi.export("fifo_queue_arn", fifo_queue.arn)
pulumi.export("fifo_queue_name", fifo_queue.name)

pulumi.export("high_throughput_queue_url", high_throughput_queue.id)
pulumi.export("high_throughput_queue_arn", high_throughput_queue.arn)
pulumi.export("high_throughput_queue_name", high_throughput_queue.name)

pulumi.export("dead_letter_queue_url", dead_letter_queue.id)
pulumi.export("dead_letter_queue_arn", dead_letter_queue.arn)
pulumi.export("dead_letter_queue_name", dead_letter_queue.name)

pulumi.export("main_queue_with_dlq_url", main_queue_with_dlq.id)
pulumi.export("main_queue_with_dlq_arn", main_queue_with_dlq.arn)
pulumi.export("main_queue_with_dlq_name", main_queue_with_dlq.name)

pulumi.export("delayed_queue_url", delayed_queue.id)
pulumi.export("delayed_queue_arn", delayed_queue.arn)
pulumi.export("delayed_queue_name", delayed_queue.name)

pulumi.export("random_suffix", random_suffix)

# Export queue configurations for SDK usage
pulumi.export("queue_configurations", {
    "standard": {
        "url": standard_queue.id,
        "arn": standard_queue.arn,
        "name": standard_queue.name,
        "type": "standard",
        "visibility_timeout": 30,
        "long_polling": False
    },
    "fifo": {
        "url": fifo_queue.id,
        "arn": fifo_queue.arn,
        "name": fifo_queue.name,
        "type": "fifo",
        "visibility_timeout": 30,
        "content_based_deduplication": True
    },
    "high_throughput": {
        "url": high_throughput_queue.id,
        "arn": high_throughput_queue.arn,
        "name": high_throughput_queue.name,
        "type": "standard",
        "visibility_timeout": 60,
        "long_polling": True,
        "receive_wait_time": 20
    },
    "dead_letter": {
        "url": dead_letter_queue.id,
        "arn": dead_letter_queue.arn,
        "name": dead_letter_queue.name,
        "type": "dead-letter",
        "visibility_timeout": 30
    },
    "main_with_dlq": {
        "url": main_queue_with_dlq.id,
        "arn": main_queue_with_dlq.arn,
        "name": main_queue_with_dlq.name,
        "type": "standard",
        "visibility_timeout": 30,
        "dead_letter_queue": dead_letter_queue.arn,
        "max_receive_count": 3
    },
    "delayed": {
        "url": delayed_queue.id,
        "arn": delayed_queue.arn,
        "name": delayed_queue.name,
        "type": "standard",
        "visibility_timeout": 300,
        "delay_seconds": 900,
        "long_polling": True
    }
})

# Export AWS SQS endpoint
pulumi.export("sqs_endpoint", f"https://sqs.{aws.get_region().name}.amazonaws.com")

# Export useful commands for testing
pulumi.export("testing_commands", {
    "send_message_standard": f"aws sqs send-message --queue-url {standard_queue.id} --message-body 'Hello World'",
    "receive_message_standard": f"aws sqs receive-message --queue-url {standard_queue.id}",
    "send_message_fifo": f"aws sqs send-message --queue-url {fifo_queue.id} --message-body 'Hello FIFO' --message-group-id 'group1'",
    "receive_message_fifo": f"aws sqs receive-message --queue-url {fifo_queue.id}"
})