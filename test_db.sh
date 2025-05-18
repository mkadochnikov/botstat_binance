св #!/bin/bash
# Script to test database connectivity and update database

echo "Testing database connectivity and updating database..."

# Set the path to the project directory
PROJECT_DIR="$(dirname "$(readlink -f "$0")")"
cd "$PROJECT_DIR"

# Check if the backend is running
echo "Checking if backend is running..."
if ! curl -s http://localhost:8008/ > /dev/null; then
    echo "Backend is not running. Starting backend..."
    cd "$PROJECT_DIR/app"
    nohup uvicorn main:app --host 0.0.0.0 --port 8008 > backend.log 2>&1 &
    echo "Backend started. Waiting for it to initialize..."
    sleep 5
else
    echo "Backend is already running."
fi

# Test database connection
echo "Testing database connection..."
cd "$PROJECT_DIR"
python -c "
import sys
sys.path.append('$PROJECT_DIR/app')
from app.utils.db.database import test_database_connection
if test_database_connection():
    print('Database connection successful')
else:
    print('Database connection failed')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "Database connection test failed. Check database_operations.log for details."
    exit 1
fi

# Run database update
echo "Running database update..."
python update_db.py --wait --timeout 120

# Check if update was successful
if [ $? -ne 0 ]; then
    echo "Database update failed. Check update_db.log for details."
    exit 1
fi

echo "Database update completed successfully."

# Check database content
echo "Checking database content..."
python -c "
import sys
sys.path.append('$PROJECT_DIR/app')
from app.utils.db.database import get_all_atr_data
data = get_all_atr_data()
print(f'Found {len(data)} records in database')
if len(data) == 0:
    print('Database is empty')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "Database is empty after update. Check logs for details."
    exit 1
fi

echo "Test completed successfully. Database contains data."
echo "You can now run the frontend with: cd $PROJECT_DIR/app && streamlit run streamlit_app.py"
