---
language: bash
domain: systems
type: pattern
title: Reading and parsing /etc/fstab
tags: bash, fstab, mount, filesystem, parsing
---

# Reading and Parsing /etc/fstab

Parse /etc/fstab to understand mounted filesystems and their options.

## Basic fstab Format

```
# <file system>               <mount point>   <type>  <options>       <dump>  <pass>
/dev/sda1                    /               ext4    defaults        1       1
/dev/sda2                    /home           ext4    defaults        1       2
UUID=123-456-789             /boot           ext4    defaults        0       2
tmpfs                        /tmp            tmpfs   defaults        0       0
```

## Parse with awk

```bash
#!/usr/bin/env bash

# Skip comments and empty lines, show all fields
awk '!/^#/ && !/^$/ {print "Device:" $1, "Mount:" $2, "Type:" $3, "Options:" $4}' /etc/fstab
```

## Get All Mount Points

```bash
#!/usr/bin/env bash

get_mount_points() {
    awk '!/^#/ && !/^$/ {print $2}' /etc/fstab
}

# Or using findmnt (more modern)
findmnt -n -o TARGET /etc/fstab
```

## Find Root Filesystem

```bash
#!/usr/bin/env bash

get_root_fs() {
    awk '$2 == "/" {print $1}' /etc/fstab
}
```

## Get Filesystem Type

```bash
#!/usr/bin/env bash

get_fs_type() {
    local mount_point=$1
    awk -v mp="$mount_point" '$2 == mp {print $3}' /etc/fstab
}

# Usage
root_type=$(get_fs_type "/")
echo "Root filesystem: $root_type"
```

## Parse Mount Options

```bash
#!/usr/bin/env bash

# Get options for a mount point
get_mount_options() {
    local mount_point=$1
    awk -v mp="$mount_point" '$2 == mp {print $4}' /etc/fstab
}

# Check if option is present
has_option() {
    local mount_point=$1
    local option=$2
    
    opts=$(get_mount_options "$mount_point")
    if [[ ",$opts," == *",$option,"* ]]; then
        return 0
    fi
    return 1
}

# Usage: check if / is mounted ro
if has_option "/" "ro"; then
    echo "Root is read-only"
fi
```

## UUID Handling

```bash
#!/usr/bin/env bash

# Get UUID for a mount point
get_uuid_for_mount() {
    local mount_point=$1
    local device=$(awk -v mp="$mount_point" '$2 == mp {print $1}' /etc/fstab)
    
    if [[ "$device" == UUID=* ]]; then
        echo "${device#UUID=}"
    elif [[ -b "$device" ]]; then
        blkid -s UUID -o value "$device"
    fi
}

# Find mount point by UUID
find_mount_by_uuid() {
    local uuid=$1
    awk -v u="$uuid" '
        $1 ~ "UUID=" substr(u, index(u, "=")+1) {print $2}
        /^[^#]/ && $1 != "" {
            dev = $1
            cmd = "blkid -s UUID -o value " dev
            cmd | getline uuid_out
            if (uuid_out == u) print $2
        }
    ' /etc/fstab
}
```

## Validate fstab

```bash
#!/usr/bin/env bash

validate_fstab() {
    local errors=0
    
    while read -r line; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        
        # Check field count
        fields=$(echo "$line" | awk '{print NF}')
        if [[ $fields -lt 4 ]]; then
            echo "Invalid line (too few fields): $line"
            ((errors++))
        fi
    done < /etc/fstab
    
    echo "Validation complete. Errors: $errors"
}
```

This pattern enables filesystem configuration inspection.