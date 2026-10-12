#!/usr/bin/env bash
set -euo pipefail

force=false
target="${HOME:?HOME must be set}/.zcode"
while (( $# )); do
    case "$1" in
        --force) force=true; shift ;;
        --target)
            if (( $# < 2 )) || [[ -z "$2" ]]; then
                printf '%s\n' '--target requires a directory.' >&2
                exit 2
            fi
            target="$2"; shift 2 ;;
        --help)
            printf '%s\n' 'Usage: bash install.sh [--force] [--target DIRECTORY]'
            exit 0 ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
done

script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_root="${script_dir%/*}/zcode"
files=(
    agents/code-writer.md
    agents/code-reviewer.md
    agents/code-generate-test.md
    agents/discriminator.md
    commands/loop-engine.md
    skills/loop-engine/SKILL.md
)

# Git Bash accepts native Windows arguments from PowerShell/Python callers.
# Convert them before checking whether the target is absolute.
if command -v cygpath >/dev/null 2>&1; then
    target="$(cygpath -u -- "$target")"
fi
[[ "$target" = /* ]] || target="$PWD/$target"
# Reject parent traversal rather than resolving through a possible symlink.
if [[ "/$target/" = */../* ]]; then
    printf '%s\n' 'Target must not contain parent traversal.' >&2
    exit 2
fi
while [[ "$target" != / && "$target" = */ ]]; do target="${target%/}"; done
# GNU coreutils are available in Git Bash and the Linux validation environment.
# Normalize separators/dot components without following untrusted links.
target="$(realpath -ms -- "$target")"
source_root="$(realpath -ms -- "$source_root")"
comparison_target="$target"
comparison_source="$source_root"
if command -v cygpath >/dev/null 2>&1; then
    comparison_target="$(cygpath -am -- "$target")"
    comparison_source="$(cygpath -am -- "$source_root")"
    comparison_target="${comparison_target,,}"
    comparison_source="${comparison_source,,}"
fi
comparison_target="${comparison_target%/}/"
comparison_source="${comparison_source%/}/"
if [[ "$comparison_target" = "$comparison_source" ||
      "$comparison_target" = "$comparison_source"* ||
      "$comparison_source" = "$comparison_target"* ]]; then
    printf '%s\n' 'Target and source root must not overlap.' >&2
    exit 1
fi

failed=false
check_directories() {
    local directory="$1"
    while [[ "$directory" != / && -n "$directory" ]]; do
        if [[ -L "$directory" ]] || { [[ -e "$directory" ]] && [[ ! -d "$directory" ]]; }; then
            printf 'Unsafe directory: %s\n' "$directory" >&2
            failed=true
        fi
        directory="${directory%/*}"
    done
}

# Preflight every source and destination before creating any directory or copying.
for relative in "${files[@]}"; do
    source_file="$source_root/$relative"
    destination="$target/$relative"
    check_directories "${source_file%/*}"
    check_directories "${destination%/*}"
    if [[ ! -f "$source_file" || -L "$source_file" ]]; then
        printf 'Missing or unsafe source: %s\n' "$relative" >&2
        failed=true
    fi
    if [[ -e "$destination" || -L "$destination" ]]; then
        if [[ "$force" != true ]] || [[ ! -f "$destination" || -L "$destination" ]]; then
            printf 'Destination conflict: %s\n' "$relative" >&2
            failed=true
        fi
    fi
done
if [[ "$failed" = true ]]; then
    printf '%s\n' 'Nothing copied. Resolve conflicts or explicitly use --force for regular files.' >&2
    exit 1
fi

temporary=''
cleanup_temporary() {
    # Remove only the installer-owned staging file, never a user file.
    if [[ -n "$temporary" && -f "$temporary" && ! -L "$temporary" ]]; then
        rm -- "$temporary"
    fi
}
trap cleanup_temporary EXIT

for relative in "${files[@]}"; do
    source_file="$source_root/$relative"
    destination="$target/$relative"
    parent="${destination%/*}"
    check_directories "$parent"
    [[ "$failed" = false ]] || exit 1
    mkdir -p -- "$parent"
    temporary="$(mktemp "$parent/.loop-engine-install.XXXXXXXX")"
    cp -- "$source_file" "$temporary"
    # Recheck immediately before replacing the directory entry. This never writes
    # through an existing destination inode, including an external hard link.
    check_directories "$parent"
    [[ "$failed" = false ]] || exit 1
    if [[ -L "$destination" ]] || { [[ -e "$destination" ]] && [[ ! -f "$destination" ]]; }; then
        printf 'Unsafe replacement target: %s\n' "$relative" >&2
        exit 1
    fi
    if [[ "$force" = true ]]; then
        mv -fT -- "$temporary" "$destination"
    else
        mv -nT -- "$temporary" "$destination"
        if [[ -e "$temporary" ]]; then
            printf 'Destination appeared during installation: %s\n' "$relative" >&2
            exit 1
        fi
    fi
    temporary=''
    printf 'Installed %s\n' "$relative"
done
