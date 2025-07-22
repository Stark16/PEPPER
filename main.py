import multiprocessing
import subprocess
import time
from worker import Worker  # or whatever your infinite loop function is

def start_server():
    # Start the FastAPI server as a subprocess
    subprocess.Popen(["python", "pepper.py"])  # make sure pepper.py has `if __name__ == "__main__"` block

def start_worker():
    # Your worker loop - can be imported and started directly
    OBJ_Worker = Worker()
    OBJ_Worker.start_worker_loop()

if __name__ == "__main__":
    # Step 1: Start FastAPI server
    print("\n\n\t\t [🚀-INIT] Launching Pepper server and worker...")
    server_process = multiprocessing.Process(target=start_server)
    server_process.start()

    # Optional: Wait a few seconds to let server initialize
    time.sleep(1)

    # Step 2: Start the request worker in this process
    start_worker()  # This blocks forever (infinite loop)
