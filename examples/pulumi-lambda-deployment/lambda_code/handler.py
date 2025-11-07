"""Lambda function handler."""

import json
import os
from datetime import datetime


def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    
    This is a simple example Lambda function that processes events
    and returns a response.
    
    Args:
        event: Lambda event object
        context: Lambda context object
        
    Returns:
        Dict with statusCode and body
    """
    
    # Log the incoming event
    print(f"Received event: {json.dumps(event)}")
    
    # Get environment variables
    environment = os.environ.get('ENVIRONMENT', 'dev')
    app_name = os.environ.get('APP_NAME', 'DriftGuards-Lambda')
    
    # Process the event
    try:
        # Extract data from event
        path = event.get('path', '/')
        method = event.get('httpMethod', 'GET')
        body = event.get('body')
        
        # Parse body if present
        if body:
            try:
                body_data = json.loads(body)
            except json.JSONDecodeError:
                body_data = body
        else:
            body_data = None
        
        # Build response
        response_data = {
            'message': f'Hello from {app_name}!',
            'timestamp': datetime.utcnow().isoformat(),
            'environment': environment,
            'request': {
                'path': path,
                'method': method,
                'body': body_data
            },
            'function_info': {
                'function_name': context.function_name,
                'function_version': context.function_version,
                'memory_limit': context.memory_limit_in_mb,
                'request_id': context.request_id
            }
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data, indent=2)
        }
        
    except Exception as e:
        print(f"Error processing event: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }


# For local testing
if __name__ == '__main__':
    # Test event
    test_event = {
        'path': '/test',
        'httpMethod': 'GET',
        'body': json.dumps({'test': 'data'})
    }
    
    # Mock context
    class Context:
        function_name = 'test-function'
        function_version = '$LATEST'
        memory_limit_in_mb = 128
        request_id = 'test-request-id'
    
    result = lambda_handler(test_event, Context())
    print(json.dumps(result, indent=2))
