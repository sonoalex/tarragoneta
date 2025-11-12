#!/usr/bin/env python
"""
RQ Worker for processing background jobs (emails)
Run this as a separate process in Railway
"""
import os
from redis import Redis
from rq import Worker, Queue, Connection
from app import create_app

# Create app context for worker
app = create_app()

def run_worker():
    """Run RQ worker to process email queue"""
    redis_url = os.environ.get('REDIS_URL', os.environ.get('REDISCLOUD_URL', 'redis://localhost:6379/0'))
    
    with app.app_context():
        redis_conn = Redis.from_url(redis_url, decode_responses=True)
        queue = Queue('emails', connection=redis_conn)
        
        print("🚀 Starting RQ worker for email queue...")
        print(f"📧 Listening on queue: emails")
        print(f"🔗 Redis: {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
        print("")
        print("Press Ctrl+C to stop the worker")
        print("")
        
        worker = Worker([queue], connection=redis_conn)
        worker.work()

if __name__ == '__main__':
    run_worker()

