#\!/bin/bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
EOF < /dev/null