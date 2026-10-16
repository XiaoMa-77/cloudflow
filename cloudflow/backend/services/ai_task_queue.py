from __future__ import annotations

from queue import Queue
from threading import Lock, Thread

_task_queue: Queue[int] = Queue()
_worker_started = False
_worker_lock = Lock()


def enqueue_ai_task(record_id: int) -> None:
    _task_queue.put(record_id)


def start_ai_worker(app) -> None:
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return

        thread = Thread(target=_worker_loop, args=(app,), daemon=True, name='ai-analysis-worker')
        thread.start()
        _worker_started = True


def _worker_loop(app) -> None:
    while True:
        record_id = _task_queue.get()
        try:
            with app.app_context():
                from services.user_portal import process_ai_analysis_task

                process_ai_analysis_task(record_id)
        except Exception:
            # Keep worker alive even if a task fails unexpectedly.
            pass
        finally:
            _task_queue.task_done()
