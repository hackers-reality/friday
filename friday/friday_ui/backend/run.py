import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import uvicorn
from friday.friday_ui.backend.main import app
uvicorn.run(app, host="0.0.0.0", port=8000)
