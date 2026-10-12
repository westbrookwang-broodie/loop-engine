[CmdletBinding()]
param(
    [switch]$Force,
    [string]$Target = (Join-Path $HOME '.zcode')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($Target)) { throw 'Target must not be empty.' }
$targetRoot = [System.IO.Path]::GetFullPath($Target)
$sourceRoot = [System.IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $PSScriptRoot) 'zcode'))
$comparison = [System.StringComparison]::Ordinal
if ([System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT) {
    $comparison = [System.StringComparison]::OrdinalIgnoreCase
}
$separator = [System.IO.Path]::DirectorySeparatorChar
$targetPrefix = $targetRoot.TrimEnd($separator) + $separator
$sourcePrefix = $sourceRoot.TrimEnd($separator) + $separator
if ($targetPrefix.Equals($sourcePrefix, $comparison) -or
    $targetPrefix.StartsWith($sourcePrefix, $comparison) -or
    $sourcePrefix.StartsWith($targetPrefix, $comparison)) {
    throw 'Target and source root must not overlap.'
}
$files = @(
    'agents/code-writer.md',
    'agents/code-reviewer.md',
    'agents/code-generate-test.md',
    'agents/discriminator.md',
    'commands/loop-engine.md',
    'skills/loop-engine/SKILL.md'
)
$problems = [System.Collections.Generic.List[string]]::new()

function Get-ExistingItem([string]$Path) {
    $itemErrors = @()
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue -ErrorVariable itemErrors
    foreach ($itemError in $itemErrors) {
        if ($itemError.CategoryInfo.Category -notin @('ObjectNotFound')) {
            throw $itemError
        }
    }
    return $item
}

function Test-Directories([string]$Path) {
    $directory = $Path
    while (-not [string]::IsNullOrEmpty($directory)) {
        $item = Get-ExistingItem $directory
        if ($null -ne $item) {
            if (-not $item.PSIsContainer -or
                (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)) {
                $problems.Add("Unsafe directory: $directory")
            }
        }
        $parent = [System.IO.Directory]::GetParent($directory)
        if ($null -eq $parent) { break }
        $directory = $parent.FullName
    }
}

# Inspect all sources and destinations before creating directories or copying.
foreach ($relative in $files) {
    $source = Join-Path $sourceRoot $relative
    $destination = Join-Path $targetRoot $relative
    Test-Directories (Split-Path -Parent $source)
    Test-Directories (Split-Path -Parent $destination)
    $sourceItem = Get-ExistingItem $source
    if ($null -eq $sourceItem -or $sourceItem.PSIsContainer -or
        (($sourceItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)) {
        $problems.Add("Missing or unsafe source: $relative")
    }
    $destinationItem = Get-ExistingItem $destination
    if ($null -ne $destinationItem) {
        if (-not $Force -or $destinationItem.PSIsContainer -or
            (($destinationItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)) {
            $problems.Add("Destination conflict: $relative")
        }
    }
}
if ($problems.Count -gt 0) {
    throw ("Nothing copied. Resolve conflicts or explicitly use -Force for regular files.`n" +
        ($problems -join "`n"))
}

foreach ($relative in $files) {
    $source = Join-Path $sourceRoot $relative
    $destination = Join-Path $targetRoot $relative
    $parent = Split-Path -Parent $destination
    Test-Directories $parent
    if ($problems.Count -gt 0) { throw ($problems -join "`n") }
    [System.IO.Directory]::CreateDirectory($parent) | Out-Null
    $temporary = Join-Path $parent ('.loop-engine-install.' + [System.Guid]::NewGuid().ToString('N'))
    try {
        # CreateNew reserves an installer-owned regular staging file.
        $output = [System.IO.File]::Open($temporary, [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        try {
            $input = [System.IO.File]::OpenRead($source)
            try { $input.CopyTo($output) } finally { $input.Dispose() }
        } finally { $output.Dispose() }
        Test-Directories $parent
        if ($problems.Count -gt 0) { throw ($problems -join "`n") }
        $item = Get-ExistingItem $destination
        if ($null -ne $item) {
            if (-not $Force -or $item.PSIsContainer -or
                (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)) {
                throw "Unsafe replacement target: $relative"
            }
            # Replace the directory entry, never truncate the old hard-linked inode.
            [System.IO.File]::Replace($temporary, $destination,
                [System.Management.Automation.Language.NullString]::Value)
        } else {
            [System.IO.File]::Move($temporary, $destination)
        }
    } finally {
        # Delete only this installer's staging file on an unsuccessful replacement.
        if ([System.IO.File]::Exists($temporary)) { [System.IO.File]::Delete($temporary) }
    }
    Write-Output "Installed $relative"
}
