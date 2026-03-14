#!/bin/bash
# Bazzite Quarantine Manager — safely release or inspect quarantined files
# Deploy to: /usr/local/bin/quarantine-release.sh (chmod 755)
# Usage: quarantine-release.sh <filename> [destination]
#        quarantine-release.sh --list
#        quarantine-release.sh --interactive
set -uo pipefail

QUARANTINE_DIR="/home/lch/security/quarantine"
LOG_DIR="/var/log/clamav-scans"
DEFAULT_DEST="/home/lch/Downloads"

# --- ANSI Colors ---
CYAN='\e[0;36m'
BCYAN='\e[1;36m'
GREEN='\e[0;32m'
RED='\e[0;31m'
YELLOW='\e[0;33m'
BWHITE='\e[1;37m'
DIM='\e[2m'
RESET='\e[0m'

# --- Root check ---
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Error: Must run as root${RESET}" >&2
    echo "Usage: sudo $0 {--list|--interactive|<filename> [destination]}" >&2
    exit 1
fi

# --- Banner ---
print_banner() {
    echo ""
    echo -e "  ${BCYAN}┌──────────────────────────────────────┐${RESET}"
    echo -e "  ${BCYAN}│${RESET}  🛡  ${BWHITE}BAZZITE QUARANTINE MANAGER${RESET}      ${BCYAN}│${RESET}"
    echo -e "  ${BCYAN}└──────────────────────────────────────┘${RESET}"
    echo ""
}

# --- List quarantined files ---
list_files() {
    print_banner

    if [[ ! -d "$QUARANTINE_DIR" ]] || [[ -z "$(ls -A "$QUARANTINE_DIR" 2>/dev/null)" ]]; then
        echo -e "  ${GREEN}No files in quarantine.${RESET}"
        echo ""
        return 0
    fi

    local count=0
    echo -e "  ${BWHITE}Quarantined Files:${RESET}"
    echo -e "  ${DIM}─────────────────────────────────────────────${RESET}"
    echo ""

    while IFS= read -r filepath; do
        count=$((count + 1))
        local filename
        filename=$(basename "$filepath")
        local filedate
        filedate=$(stat -c '%y' "$filepath" 2>/dev/null | cut -d'.' -f1)

        # Try to find the threat name from scan logs
        local threat=""
        if [[ -d "$LOG_DIR" ]]; then
            threat=$(grep -rh "$filename" "$LOG_DIR"/ 2>/dev/null | grep "FOUND" | head -1 | sed 's/^.*: //' | sed 's/ FOUND$//' || true)
        fi

        printf "  ${YELLOW}%3d${RESET}  %-30s  ${DIM}%s${RESET}\n" "$count" "$filename" "$filedate"
        if [[ -n "$threat" ]]; then
            printf "       ${RED}Threat: %s${RESET}\n" "$threat"
        fi
    done < <(find "$QUARANTINE_DIR" -type f 2>/dev/null | sort)

    echo ""
    echo -e "  ${DIM}Total: ${count} file(s) in quarantine${RESET}"
    echo ""
    return 0
}

# --- Release a single file ---
release_file() {
    local filename="$1"
    local dest="${2:-}"
    local filepath="${QUARANTINE_DIR}/${filename}"

    if [[ ! -e "$filepath" ]]; then
        echo -e "  ${RED}Error: '${filename}' not found in quarantine${RESET}" >&2
        return 1
    fi

    # Remove immutable flag
    chattr -i "$filepath" 2>/dev/null

    if [[ -z "$dest" ]]; then
        # Unlock in place
        chmod 644 "$filepath"
        echo -e "  ${GREEN}Unlocked:${RESET} ${filename} (still in quarantine, permissions restored)"
    else
        if [[ ! -d "$dest" ]]; then
            echo -e "  ${RED}Error: Destination '${dest}' does not exist${RESET}" >&2
            # Re-lock the file since we're aborting
            chmod 000 "$filepath" 2>/dev/null
            chattr +i "$filepath" 2>/dev/null
            return 1
        fi
        chmod 644 "$filepath"
        mv "$filepath" "${dest}/"
        echo -e "  ${GREEN}Released:${RESET} ${filename} → ${dest}/"
    fi
    return 0
}

# --- Interactive mode ---
interactive_mode() {
    print_banner

    if [[ ! -d "$QUARANTINE_DIR" ]] || [[ -z "$(ls -A "$QUARANTINE_DIR" 2>/dev/null)" ]]; then
        echo -e "  ${GREEN}No files in quarantine.${RESET}"
        echo ""
        return 0
    fi

    while true; do
        # Build file list
        local files=()
        local count=0
        while IFS= read -r filepath; do
            files+=("$filepath")
            count=$((count + 1))
        done < <(find "$QUARANTINE_DIR" -type f 2>/dev/null | sort)

        if [[ ${#files[@]} -eq 0 ]]; then
            echo -e "  ${GREEN}Quarantine is empty.${RESET}"
            echo ""
            break
        fi

        echo -e "  ${BWHITE}Quarantined Files:${RESET}"
        echo -e "  ${DIM}─────────────────────────────────────────────${RESET}"
        echo ""

        for i in "${!files[@]}"; do
            local num=$((i + 1))
            local filename
            filename=$(basename "${files[$i]}")
            local filedate
            filedate=$(stat -c '%y' "${files[$i]}" 2>/dev/null | cut -d'.' -f1)

            local threat=""
            if [[ -d "$LOG_DIR" ]]; then
                threat=$(grep -rh "$filename" "$LOG_DIR"/ 2>/dev/null | grep "FOUND" | head -1 | sed 's/^.*: //' | sed 's/ FOUND$//' || true)
            fi

            printf "  ${YELLOW}%3d${RESET}  %-30s  ${DIM}%s${RESET}\n" "$num" "$filename" "$filedate"
            if [[ -n "$threat" ]]; then
                printf "       ${RED}Threat: %s${RESET}\n" "$threat"
            fi
        done

        echo ""
        echo -ne "  Enter file number to release (or ${DIM}'q' to quit${RESET}): "
        read -r choice

        if [[ "$choice" == "q" || "$choice" == "Q" ]]; then
            echo ""
            echo -e "  ${DIM}Exiting quarantine manager.${RESET}"
            echo ""
            break
        fi

        # Validate number
        if ! [[ "$choice" =~ ^[0-9]+$ ]] || [[ "$choice" -lt 1 ]] || [[ "$choice" -gt ${#files[@]} ]]; then
            echo -e "  ${RED}Invalid selection.${RESET}"
            echo ""
            continue
        fi

        local selected="${files[$((choice - 1))]}"
        local selected_name
        selected_name=$(basename "$selected")

        echo -ne "  Destination (default: ${DIM}${DEFAULT_DEST}${RESET}): "
        read -r dest_input
        local dest="${dest_input:-$DEFAULT_DEST}"

        release_file "$selected_name" "$dest"
        echo ""
    done
}

# --- Main ---
case "${1:-}" in
    --list)
        list_files
        ;;
    --interactive)
        interactive_mode
        ;;
    "")
        echo "Usage: $0 {--list|--interactive|<filename> [destination]}" >&2
        exit 1
        ;;
    *)
        print_banner
        release_file "$1" "${2:-}"
        ;;
esac
