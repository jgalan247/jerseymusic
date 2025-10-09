#!/bin/bash
# restart_services.sh - Restart Jersey Events application services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔄 Jersey Events - Service Restart${NC}"
echo "Timestamp: $(date)"
echo "Project Directory: $PROJECT_DIR"
echo ""

# Function to check if a service exists
service_exists() {
    local service_name="$1"
    systemctl list-unit-files | grep -q "$service_name" || systemctl list-units | grep -q "$service_name"
}

# Function to get service status
get_service_status() {
    local service_name="$1"
    systemctl is-active "$service_name" 2>/dev/null || echo "unknown"
}

# Function to restart a service safely
restart_service() {
    local service_name="$1"
    local wait_time="${2:-5}"

    echo -e "${YELLOW}🔄 Restarting $service_name...${NC}"

    if service_exists "$service_name"; then
        local old_status=$(get_service_status "$service_name")
        echo -e "${BLUE}📊 Current status: $old_status${NC}"

        # Restart the service
        sudo systemctl restart "$service_name"

        # Wait for service to start
        sleep "$wait_time"

        # Check new status
        local new_status=$(get_service_status "$service_name")
        echo -e "${BLUE}📊 New status: $new_status${NC}"

        if [ "$new_status" = "active" ]; then
            echo -e "${GREEN}✅ $service_name restarted successfully${NC}"
        else
            echo -e "${RED}❌ $service_name failed to start${NC}"
            echo "Checking service logs..."
            sudo journalctl -u "$service_name" --no-pager -n 10
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  Service $service_name not found or not configured${NC}"
        return 1
    fi
}

# Function for development restart (no sudo needed)
restart_development() {
    echo -e "${BLUE}🚧 Development Environment Restart${NC}"

    # Stop any running development server
    echo -e "${YELLOW}🛑 Stopping any running development servers...${NC}"
    pkill -f "python manage.py runserver" || echo "No development server running"

    # Navigate to project directory
    cd "$PROJECT_DIR"

    # Activate virtual environment if exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo -e "${GREEN}📦 Virtual environment activated${NC}"
    elif [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        echo -e "${GREEN}📦 Virtual environment activated${NC}"
    fi

    # Check Django configuration
    echo -e "${YELLOW}🔍 Checking Django configuration...${NC}"
    python manage.py check --deploy || echo "Configuration check completed with warnings"

    # Collect static files if in production-like setup
    if [ "$DJANGO_ENV" = "production" ] || [ "$DJANGO_SETTINGS_MODULE" = "events.settings.production" ]; then
        echo -e "${YELLOW}📦 Collecting static files...${NC}"
        python manage.py collectstatic --noinput
    fi

    echo -e "${GREEN}✅ Development environment prepared${NC}"
    echo -e "${BLUE}💡 To start development server: python manage.py runserver${NC}"
}

# Function to test application health
test_application_health() {
    local base_url="${1:-http://localhost:8000}"
    local timeout=30

    echo -e "${YELLOW}🏥 Testing application health...${NC}"

    # Test basic connectivity
    local health_endpoints=(
        "/"
        "/accounts/login/"
        "/admin/"
    )

    for endpoint in "${health_endpoints[@]}"; do
        echo -e "${BLUE}🔍 Testing: $base_url$endpoint${NC}"

        if curl -f -s --max-time "$timeout" "$base_url$endpoint" > /dev/null; then
            echo -e "${GREEN}✅ $endpoint is responding${NC}"
        else
            echo -e "${RED}❌ $endpoint is not responding${NC}"
        fi
    done

    # Test SumUp OAuth endpoints (should redirect to login)
    local oauth_endpoints=(
        "/accounts/sumup/connect/"
        "/accounts/sumup/callback/"
    )

    for endpoint in "${oauth_endpoints[@]}"; do
        echo -e "${BLUE}🔍 Testing OAuth: $base_url$endpoint${NC}"

        local response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$timeout" "$base_url$endpoint")
        if [ "$response_code" = "302" ]; then
            echo -e "${GREEN}✅ $endpoint is redirecting correctly${NC}"
        else
            echo -e "${YELLOW}⚠️  $endpoint returned status: $response_code${NC}"
        fi
    done
}

# Function to show service status
show_service_status() {
    local services=("$@")

    echo -e "${BLUE}📊 Service Status Summary${NC}"
    echo "=========================="

    for service in "${services[@]}"; do
        if service_exists "$service"; then
            local status=$(get_service_status "$service")
            local color
            case "$status" in
                "active")
                    color="$GREEN"
                    ;;
                "failed"|"inactive")
                    color="$RED"
                    ;;
                *)
                    color="$YELLOW"
                    ;;
            esac
            echo -e "${color}$service: $status${NC}"
        else
            echo -e "${YELLOW}$service: not found${NC}"
        fi
    done

    echo "=========================="
}

# Function to show help
show_help() {
    echo "Jersey Events Service Restart Script"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  production    - Restart production services (requires sudo)"
    echo "  development   - Prepare development environment"
    echo "  status        - Show service status"
    echo "  health [url]  - Test application health (default: http://localhost:8000)"
    echo "  help          - Show this help"
    echo ""
    echo "Production Services:"
    echo "  jersey-events - Main Django application"
    echo "  nginx         - Web server"
    echo "  postgresql    - Database (if used)"
    echo ""
    echo "Examples:"
    echo "  $0 production                    # Restart production services"
    echo "  $0 development                   # Prepare dev environment"
    echo "  $0 health                        # Test localhost:8000"
    echo "  $0 health https://example.com    # Test production site"
}

# Main execution
main() {
    case "${1:-development}" in
        "production")
            echo -e "${BLUE}🚀 Production Service Restart${NC}"

            # Define production services
            local services=(
                "jersey-events"
                "nginx"
                "postgresql"
            )

            # Show current status
            show_service_status "${services[@]}"

            echo ""
            echo -e "${RED}⚠️  This will restart production services${NC}"
            echo -e "${RED}⚠️  Application may be temporarily unavailable${NC}"
            read -p "Continue with production restart? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Production restart cancelled"
                exit 0
            fi

            # Restart services
            local failed_services=()
            for service in "${services[@]}"; do
                if ! restart_service "$service" 5; then
                    failed_services+=("$service")
                fi
            done

            echo ""
            show_service_status "${services[@]}"

            if [ ${#failed_services[@]} -eq 0 ]; then
                echo -e "${GREEN}🎉 All services restarted successfully!${NC}"

                # Test health if possible
                local site_url="${SITE_URL:-https://localhost}"
                test_application_health "$site_url"
            else
                echo -e "${RED}❌ Some services failed to restart: ${failed_services[*]}${NC}"
                exit 1
            fi
            ;;

        "development")
            restart_development
            ;;

        "status")
            local services=(
                "jersey-events"
                "nginx"
                "postgresql"
                "redis"
            )
            show_service_status "${services[@]}"
            ;;

        "health")
            local url="${2:-http://localhost:8000}"
            test_application_health "$url"
            ;;

        "help"|"--help"|"-h")
            show_help
            ;;

        *)
            echo -e "${RED}❌ Unknown command: $1${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac

    echo ""
    echo -e "${GREEN}✅ Service restart operations completed${NC}"
}

# Run main function with all arguments
main "$@"