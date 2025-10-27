from rq import Worker, Queue, Connection
from redis_client import redis_client
from blur_tasks import analyze_single_photo

queue = Queue("blur_analysis", connection=redis_client)

def enqueue_photo_analysis(photo_id, user_id, threshold=0.30, method="hybrid", use_face_detection=True):
    queue.enqueue(analyze_single_photo, photo_id, user_id, threshold, method, use_face_detection)

if __name__ == "__main__":
    with Connection(redis_client):
        worker = Worker(["blur_analysis"])
        worker.work()
