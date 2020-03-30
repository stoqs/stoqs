# See: https://stackoverflow.com/questions/1557571/how-do-i-get-time-of-a-python-programs-execution/1557906#1557906
# python3
import atexit
from time import time, strftime, localtime
from datetime import datetime, timedelta

MINUTES = 'Minutes to execute:'

def secondsToStr(elapsed=None):
    if elapsed is None:
        return strftime("%Y-%m-%d %H:%M:%S", localtime())
    else:
        return str(timedelta(seconds=elapsed))

def log(s, elapsed=None):
    line = "="*40
    print(line, flush=True)
    print(secondsToStr(), '-', s, flush=True)
    if elapsed:
        print("Elapsed time:", secondsToStr(elapsed), flush=True)
        print(f"{MINUTES} {elapsed / 60.0:.1f}", flush=True)
    print(line, flush=True)

def endlog():
    end = datetime.now()
    elapsed = end - start
    log("End Execution",elapsed.total_seconds())

start = datetime.now()
atexit.register(endlog)
log("Start Execution")
