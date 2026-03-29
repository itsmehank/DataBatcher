import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from project_config import find_available_port
from src.real_estate.backend.web_app import create_app


app = create_app()


if __name__ == "__main__":
    preferred_port = int(os.getenv("RE_WEB_PORT", "5001"))
    run_port = find_available_port(preferred_port)
    print(f"웹 UI 실행 포트: {run_port}")
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", host="127.0.0.1", port=run_port)
