#!/bin/bash
# NeuroLake Migration Module - Quick Start Script for Linux/Mac

echo "===================================="
echo " NeuroLake Migration Module"
echo " Docker Quick Start"
echo "===================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

echo "[OK] Docker is running"
echo ""

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "[WARNING] ANTHROPIC_API_KEY not set!"
    echo ""
    read -p "Enter your Anthropic API key: " API_KEY
    export ANTHROPIC_API_KEY=$API_KEY
fi

echo "[OK] API key configured"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
ENV=development
LOG_LEVEL=info
EOF
fi

echo "Starting NeuroLake Migration Dashboard..."
echo ""
echo "This may take a few minutes on first run (downloading images)"
echo ""

docker-compose -f docker-compose.migration.yml up -d --build

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Failed to start containers!"
    echo "Check the logs with: docker-compose -f docker-compose.migration.yml logs"
    exit 1
fi

echo ""
echo "===================================="
echo " SUCCESS! Dashboard is starting..."
echo "===================================="
echo ""
echo "  Access the dashboard at:"
echo "  http://localhost:8501"
echo ""
echo "  View logs: docker-compose -f docker-compose.migration.yml logs -f"
echo "  Stop:      docker-compose -f docker-compose.migration.yml down"
echo ""
echo "  Opening browser in 5 seconds..."
echo "===================================="

sleep 5

# Try to open browser (works on most systems)
if command -v xdg-open > /dev/null; then
    xdg-open http://localhost:8501
elif command -v open > /dev/null; then
    open http://localhost:8501
else
    echo "Please open http://localhost:8501 in your browser"
fi

echo ""
echo "Dashboard opened in browser!"
echo "Press Ctrl+C to stop viewing logs..."
echo ""

docker-compose -f docker-compose.migration.yml logs -f
