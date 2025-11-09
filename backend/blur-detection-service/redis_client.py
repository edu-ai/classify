import os
from redis import Redis

redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
redis_client = Redis.from_url(redis_url)
# redis_client = Redis(host="redis", port=6379, decode_responses=False)
