import sys, uvicorn
sys.path.insert(0, '.')
from friday.townhall_web import app
uvicorn.run(app, host='127.0.0.1', port=7071, log_level='info')
