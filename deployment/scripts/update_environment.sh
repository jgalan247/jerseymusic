#!/bin/bash
# update_environment.sh - Update environment variables for SumUp OAuth integration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}⚙️  Jersey Events - Environment Configuration Update${NC}"
echo "Timestamp: $(date)"
echo "Project Directory: $PROJECT_DIR"
echo ""

# Function to detect environment file
detect_env_file() {
    local env_candidates=(
        "$PROJECT_DIR/.env"
        "$PROJECT_DIR/.env.local"
        "$PROJECT_DIR/.env.production"
        "/etc/jersey-events/.env"
    )

    for env_file in "${env_candidates[@]}"; do
        if [ -f "$env_file" ]; then
            echo "$env_file"
            return 0
        fi
    done

    # If no env file found, use default location
    echo "$PROJECT_DIR/.env"
    return 1
}

# Function to backup environment file
backup_env_file() {
    local env_file="$1"
    local backup_file="$env_file.backup.$(date +%Y%m%d_%H%M%S)"

    if [ -f "$env_file" ]; then
        cp "$env_file" "$backup_file"
        echo -e "${GREEN}✅ Environment backup created: $backup_file${NC}"
        return 0
    else
        echo -e "${YELLOW}📋 No existing environment file to backup${NC}"
        return 1
    fi
}

# Function to add or update environment variable
add_or_update_env_var() {
    local env_file="$1"
    local var_name="$2"
    local var_value="$3"
    local var_comment="$4"

    # Check if variable already exists
    if [ -f "$env_file" ] && grep -q "^${var_name}=" "$env_file"; then
        # Update existing variable
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/^${var_name}=.*/${var_name}=${var_value}/" "$env_file"
        else
            # Linux
            sed -i "s/^${var_name}=.*/${var_name}=${var_value}/" "$env_file"
        fi
        echo -e "${YELLOW}🔄 Updated: $var_name${NC}"
    else
        # Add new variable
        {
            echo ""
            echo "# $var_comment"
            echo "${var_name}=${var_value}"
        } >> "$env_file"
        echo -e "${GREEN}➕ Added: $var_name${NC}"
    fi
}

# Function to show required variables
show_required_variables() {
    echo -e "${BLUE}📋 Required SumUp OAuth Environment Variables:${NC}"
    echo ""
    echo "SUMUP_CLIENT_ID=your_sumup_client_id"
    echo "SUMUP_CLIENT_SECRET=your_sumup_client_secret"
    echo "SUMUP_REDIRECT_URI=https://your-domain.com/accounts/sumup/callback/"
    echo "SUMUP_BASE_URL=https://api.sumup.com"
    echo "SUMUP_API_URL=https://api.sumup.com/v0.1"
    echo "SITE_URL=https://your-domain.com"
    echo ""
    echo -e "${YELLOW}⚠️  Remember to replace placeholder values with actual credentials!${NC}"
}

# Function to validate environment
validate_environment() {
    local env_file="$1"

    if [ ! -f "$env_file" ]; then
        echo -e "${RED}❌ Environment file not found: $env_file${NC}"
        return 1
    fi

    echo -e "${BLUE}🔍 Validating environment configuration...${NC}"

    # Required variables
    local required_vars=(
        "SUMUP_CLIENT_ID"
        "SUMUP_CLIENT_SECRET"
        "SUMUP_REDIRECT_URI"
        "SITE_URL"
    )

    local missing_vars=()
    local placeholder_vars=()

    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" "$env_file"; then
            # Check if it has placeholder value
            local value=$(grep "^${var}=" "$env_file" | cut -d'=' -f2)
            if [[ "$value" == *"your_"* ]] || [[ "$value" == *"placeholder"* ]] || [[ "$value" == "" ]]; then
                placeholder_vars+=("$var")
            else
                echo -e "${GREEN}✅ $var is configured${NC}"
            fi
        else
            missing_vars+=("$var")
        fi
    done

    # Report missing variables
    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo -e "${RED}❌ Missing variables: ${missing_vars[*]}${NC}"
    fi

    # Report placeholder variables
    if [ ${#placeholder_vars[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Variables with placeholder values: ${placeholder_vars[*]}${NC}"
        echo -e "${YELLOW}⚠️  These need to be updated with actual values before production deployment${NC}"
    fi

    # Overall validation
    if [ ${#missing_vars[@]} -eq 0 ] && [ ${#placeholder_vars[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ Environment configuration is complete${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Environment configuration needs attention${NC}"
        return 1
    fi
}

# Function to update environment interactively
update_environment_interactive() {
    local env_file="$1"

    echo -e "${BLUE}🔧 Interactive Environment Configuration${NC}"
    echo ""

    # Ensure environment file exists
    if [ ! -f "$env_file" ]; then
        touch "$env_file"
        echo "# Jersey Events Environment Configuration" > "$env_file"
        echo "# Generated on $(date)" >> "$env_file"
    fi

    # Add/update SumUp variables
    echo -e "${YELLOW}📝 Adding SumUp OAuth configuration...${NC}"

    add_or_update_env_var "$env_file" "SUMUP_CLIENT_ID" "your_sumup_client_id" "SumUp OAuth Client ID"
    add_or_update_env_var "$env_file" "SUMUP_CLIENT_SECRET" "your_sumup_client_secret" "SumUp OAuth Client Secret"
    add_or_update_env_var "$env_file" "SUMUP_REDIRECT_URI" "https://your-domain.com/accounts/sumup/callback/" "SumUp OAuth Redirect URI"
    add_or_update_env_var "$env_file" "SUMUP_BASE_URL" "https://api.sumup.com" "SumUp Base URL"
    add_or_update_env_var "$env_file" "SUMUP_API_URL" "https://api.sumup.com/v0.1" "SumUp API URL"
    add_or_update_env_var "$env_file" "SITE_URL" "https://your-domain.com" "Site URL for OAuth callbacks"

    echo -e "${GREEN}✅ Environment variables added/updated${NC}"
}

# Function to show environment file contents (safely)
show_environment_preview() {
    local env_file="$1"

    if [ ! -f "$env_file" ]; then
        echo -e "${RED}❌ Environment file not found: $env_file${NC}"
        return 1
    fi

    echo -e "${BLUE}📄 Environment File Preview:${NC}"
    echo "=================================="

    # Show environment file but mask sensitive values
    while IFS= read -r line; do
        if [[ "$line" == *"SECRET"* ]] || [[ "$line" == *"KEY"* ]] || [[ "$line" == *"PASSWORD"* ]]; then
            # Mask sensitive values
            var_name=$(echo "$line" | cut -d'=' -f1)
            echo "${var_name}=***MASKED***"
        elif [[ "$line" =~ ^[A-Z_]+= ]]; then
            # Show other variables
            echo "$line"
        elif [[ "$line" =~ ^# ]] || [[ -z "$line" ]]; then
            # Show comments and empty lines
            echo "$line"
        fi
    done < "$env_file"

    echo "=================================="
}

# Main execution
main() {
    case "${1:-auto}" in
        "validate")
            ENV_FILE=$(detect_env_file)
            echo -e "${BLUE}🔍 Using environment file: $ENV_FILE${NC}"
            validate_environment "$ENV_FILE"
            ;;

        "show")
            ENV_FILE=$(detect_env_file)
            show_environment_preview "$ENV_FILE"
            ;;

        "required")
            show_required_variables
            ;;

        "auto"|"")
            # Automatic mode
            ENV_FILE=$(detect_env_file)
            echo -e "${BLUE}🔍 Detected environment file: $ENV_FILE${NC}"

            # Backup existing environment
            backup_env_file "$ENV_FILE"

            # Update environment
            update_environment_interactive "$ENV_FILE"

            # Validate result
            echo ""
            validate_environment "$ENV_FILE"

            echo ""
            echo -e "${GREEN}🎉 Environment configuration completed!${NC}"
            echo ""
            echo -e "${YELLOW}📍 NEXT STEPS:${NC}"
            echo "1. Edit $ENV_FILE and replace placeholder values with actual SumUp credentials"
            echo "2. Update SITE_URL with your actual domain"
            echo "3. Test environment: $0 validate"
            echo "4. Restart application services to load new environment"
            ;;

        *)
            echo -e "${RED}❌ Unknown command: $1${NC}"
            echo ""
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  auto      - Automatically add/update SumUp environment variables (default)"
            echo "  validate  - Validate current environment configuration"
            echo "  show      - Show current environment file contents (sensitive values masked)"
            echo "  required  - Show required environment variables"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"