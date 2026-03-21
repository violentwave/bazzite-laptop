#!/bin/bash
# API Key Manager for Bazzite AI Layer
# Manages ~/.config/bazzite-ai/keys.env and auto-encrypts to configs/keys.env.enc
set -euo pipefail

KEYS_ENV="$HOME/.config/bazzite-ai/keys.env"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENCRYPTED="$PROJECT_DIR/configs/keys.env.enc"
SOPS_CFG="$HOME/.config/bazzite-ai/.sops.yaml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# All known API keys
KNOWN_KEYS=(
    "GEMINI_API_KEY"
    "GROQ_API_KEY"
    "MISTRAL_API_KEY"
    "OPENROUTER_API_KEY"
    "ZAI_API_KEY"
    "CEREBRAS_API_KEY"
    "CLOUDFLARE_API_KEY"
    "VT_API_KEY"
    "OTX_API_KEY"
    "ABUSEIPDB_KEY"
)

# Expected prefixes for validation
declare -A KEY_PREFIXES=(
    ["GEMINI_API_KEY"]="AIza"
    ["GROQ_API_KEY"]="gsk_"
    ["MISTRAL_API_KEY"]=""
    ["OPENROUTER_API_KEY"]="sk-or-"
    ["ZAI_API_KEY"]=""
    ["CEREBRAS_API_KEY"]=""
    ["CLOUDFLARE_API_KEY"]=""
    ["VT_API_KEY"]=""
    ["OTX_API_KEY"]=""
    ["ABUSEIPDB_KEY"]=""
)

ensure_keys_file() {
    mkdir -p "$(dirname "$KEYS_ENV")"
    if [[ ! -f "$KEYS_ENV" ]]; then
        touch "$KEYS_ENV"
        chmod 600 "$KEYS_ENV"
        echo -e "${YELLOW}Created $KEYS_ENV${NC}"
    fi
}

get_key_value() {
    local key_name="$1"
    if [[ -f "$KEYS_ENV" ]]; then
        grep -E "^${key_name}=" "$KEYS_ENV" 2>/dev/null | head -1 | cut -d= -f2-
    fi
}

show_status() {
    echo -e "\n${CYAN}═══ API Key Status ═══${NC}\n"

    local llm_keys=("GEMINI_API_KEY" "GROQ_API_KEY" "MISTRAL_API_KEY" "OPENROUTER_API_KEY" "ZAI_API_KEY" "CEREBRAS_API_KEY" "CLOUDFLARE_API_KEY")
    local intel_keys=("VT_API_KEY" "OTX_API_KEY" "ABUSEIPDB_KEY")

    echo -e "${CYAN}LLM Providers:${NC}"
    for key in "${llm_keys[@]}"; do
        show_key_line "$key"
    done

    echo -e "\n${CYAN}Threat Intelligence:${NC}"
    for key in "${intel_keys[@]}"; do
        show_key_line "$key"
    done

    echo ""
    if [[ -f "$ENCRYPTED" ]]; then
        local enc_age
        enc_age=$(stat -c %Y "$ENCRYPTED" 2>/dev/null || echo 0)
        local key_age
        key_age=$(stat -c %Y "$KEYS_ENV" 2>/dev/null || echo 0)
        if [[ $key_age -gt $enc_age ]]; then
            echo -e "${YELLOW}⚠ keys.env is newer than encrypted file — run 'encrypt' to sync${NC}"
        else
            echo -e "${GREEN}✓ Encrypted file is up to date${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ No encrypted backup exists yet${NC}"
    fi
}

show_key_line() {
    local key_name="$1"
    local value
    value=$(get_key_value "$key_name")

    if [[ -z "$value" ]]; then
        printf "  ${RED}✗${NC} %-25s ${RED}NOT SET${NC}\n" "$key_name"
    else
        local preview="${value:0:6}...${value: -4}"
        local prefix="${KEY_PREFIXES[$key_name]:-}"
        if [[ -n "$prefix" && "${value:0:${#prefix}}" != "$prefix" ]]; then
            printf "  ${YELLOW}⚠${NC} %-25s ${YELLOW}%s${NC} ${RED}(expected prefix: %s)${NC}\n" "$key_name" "$preview" "$prefix"
        else
            printf "  ${GREEN}✓${NC} %-25s ${GREEN}%s${NC}\n" "$key_name" "$preview"
        fi
    fi
}

set_key() {
    local key_name="$1"
    local key_value="${2:-}"

    # Validate key name
    local valid=false
    for k in "${KNOWN_KEYS[@]}"; do
        if [[ "$k" == "$key_name" ]]; then valid=true; break; fi
    done
    if [[ "$valid" != "true" ]]; then
        echo -e "${RED}Unknown key: $key_name${NC}"
        echo "Valid keys: ${KNOWN_KEYS[*]}"
        return 1
    fi

    # Prompt for value if not provided
    if [[ -z "$key_value" ]]; then
        echo -n "Enter value for $key_name: "
        read -rs key_value
        echo ""
    fi

    if [[ -z "$key_value" ]]; then
        echo -e "${RED}Empty value — key not set${NC}"
        return 1
    fi

    # Validate prefix if known
    local prefix="${KEY_PREFIXES[$key_name]:-}"
    if [[ -n "$prefix" && "${key_value:0:${#prefix}}" != "$prefix" ]]; then
        echo -e "${YELLOW}Warning: $key_name usually starts with '$prefix' but yours starts with '${key_value:0:4}'${NC}"
        echo -n "Continue anyway? [y/N] "
        read -r confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            echo "Aborted."
            return 1
        fi
    fi

    ensure_keys_file

    # Remove existing line and add new one
    if grep -qE "^${key_name}=" "$KEYS_ENV" 2>/dev/null; then
        sed -i "/^${key_name}=/d" "$KEYS_ENV"
    fi
    echo "${key_name}=${key_value}" >> "$KEYS_ENV"
    chmod 600 "$KEYS_ENV"

    echo -e "${GREEN}✓ $key_name updated${NC}"

    # Auto-encrypt
    auto_encrypt
}

remove_key() {
    local key_name="$1"
    if grep -qE "^${key_name}=" "$KEYS_ENV" 2>/dev/null; then
        sed -i "/^${key_name}=/d" "$KEYS_ENV"
        echo -e "${GREEN}✓ $key_name removed${NC}"
        auto_encrypt
    else
        echo -e "${YELLOW}$key_name was not set${NC}"
    fi
}

auto_encrypt() {
    if [[ -f "$SOPS_CFG" ]]; then
        echo -n "Encrypting to configs/keys.env.enc... "
        if SOPS_CONFIG="$SOPS_CFG" sops -e --input-type dotenv --output-type dotenv "$KEYS_ENV" > "$ENCRYPTED" 2>/dev/null; then
            echo -e "${GREEN}done${NC}"
        else
            echo -e "${YELLOW}skipped (sops not configured or GPG key missing)${NC}"
        fi
    else
        echo -e "${YELLOW}Skipping encryption — no .sops.yaml found${NC}"
    fi
}

edit_keys() {
    ensure_keys_file
    "${EDITOR:-nano}" "$KEYS_ENV"
    chmod 600 "$KEYS_ENV"
    echo -e "\n${CYAN}Updated key status:${NC}"
    show_status
    auto_encrypt
}

usage() {
    echo -e "${CYAN}Bazzite API Key Manager${NC}"
    echo ""
    echo "Usage: $(basename "$0") <command> [args]"
    echo ""
    echo "Commands:"
    echo "  status                    Show all key status (set/missing, prefix validation)"
    echo "  set <KEY_NAME> [value]    Set a key (prompts for value if not provided)"
    echo "  remove <KEY_NAME>         Remove a key"
    echo "  edit                      Open keys.env in editor"
    echo "  encrypt                   Re-encrypt keys.env to configs/keys.env.enc"
    echo "  help                      Show this help"
    echo ""
    echo "Examples:"
    echo "  $(basename "$0") status"
    echo "  $(basename "$0") set GEMINI_API_KEY"
    echo "  $(basename "$0") set GROQ_API_KEY gsk_abc123..."
    echo "  $(basename "$0") edit"
}

# Main
case "${1:-status}" in
    status)   show_status ;;
    set)      set_key "${2:-}" "${3:-}" ;;
    remove)   remove_key "${2:-}" ;;
    edit)     edit_keys ;;
    encrypt)  auto_encrypt ;;
    help|-h)  usage ;;
    *)        echo -e "${RED}Unknown command: $1${NC}"; usage; exit 1 ;;
esac
