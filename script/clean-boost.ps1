#!/usr/bin/env pwsh
#Requires -Version 7.0

<#
.SYNOPSIS
    Remove non-build content from deps/boost/: docs, examples, html docs, images, website assets,
    CI config, Jamfiles and build tools.

.DESCRIPTION
    Deletes directories such as doc/, more/, status/, example/, tools/, .github/ under deps/boost/,
    files such as index.html, *.htm/*.html, appveyor.yml, boost.png, *.css,
    and Jamfile-related files such as Jamroot, boost-build.jam, boostcpp.jam, Jamfile.v2, build.jam
    (both at the top level and inside libraries).
    Keeps CMake config, tools/cmake, README, LICENSE, scripts, library sources, and each library's meta/ and test/.

.PARAMETER BoostRoot
    Path to the boost directory; defaults to ..\deps\boost relative to this script.

.PARAMETER DryRun
    Only list what would be deleted, without deleting anything.

.PARAMETER Force
    Skip the confirmation prompt and delete directly.

.EXAMPLE
    pwsh ./script/clean-boost.ps1 -DryRun
    pwsh ./script/clean-boost.ps1
    pwsh ./script/clean-boost.ps1 -Force
#>

[CmdletBinding()]
param(
    [string]$BoostRoot = (Join-Path $PSScriptRoot '..' 'deps' 'boost'),
    [switch]$DryRun,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $BoostRoot -PathType Container)) {
    throw "boost directory not found: $BoostRoot"
}

$boostRootResolved = (Resolve-Path -LiteralPath $BoostRoot).Path

# Directory names to delete (at any depth; all are docs/examples/website/CI related).
# The cmake/ subdirectory of a tools/ directory is preserved (referenced by CMakeLists.txt).
$DeletedDirNames = @(
    'doc', 'docs', 'example', 'examples', 'more', 'status',
    '.github', '.travis', '.circleci', '.ci', '.appveyor', '.azure-pipelines'
)

# The Full directory names to delete (at only one directory; Related with `$BoostRoot`)
# Clear `boost/tools/` and ignore `boost/libs/**/tools/`
$DeletedRawDirNames = @('tools')
for ($i = 0; $i -lt $DeletedRawDirNames.Count; ++$i) {
    $DeletedRawDirNames[$i] = (Resolve-Path -LiteralPath (Join-Path $BoostRoot $DeletedRawDirNames[$i])).Path
}
Write-Debug "`$DeletedRawDirNames = $DeletedRawDirNames"

# File names to delete (at any depth)
$DeletedFileNames = @(
    'index.html', 'index.htm', 'INSTALL', 'bootstrap.bat', 'bootstrap.sh',
    'Jamroot', 'boost-build.jam', 'boostcpp.jam', 'bootstrap.jam',
    'Jamfile.v2', 'build.jam',
    'appveyor.yml', '.travis.yml', '.appveyor.yml', '.cirrus.yml', 'azure-pipelines.yml'
)

# Image/style files only at the boost root (boost.png, boost.css, rst.css, ...).
# Test data images inside library test/ directories are left untouched.
$DeletedRootExtensions = @('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.css')

# Doc-only web files deleted at any depth
$DeletedAnywhereExtensions = @('.htm', '.html')

# Directories are deleted together with all their content, so handle deepest first
$targetDirs = Get-ChildItem -LiteralPath $BoostRoot -Recurse -Directory -Force |
    Where-Object { ($_.Name -in $DeletedDirNames) -or ($_.FullName -in $DeletedRawDirNames) } |
    Sort-Object { $_.FullName.Length } -Descending

Write-Debug "`$targetDirs = $targetDirs"

$targetFiles = Get-ChildItem -LiteralPath $BoostRoot -Recurse -File -Force |
    Where-Object {
        ($_.Name -in $DeletedFileNames) -or
        (($_.DirectoryName -eq $boostRootResolved) -and ($_.Extension.ToLower() -in $DeletedRootExtensions)) -or
        ($_.Extension.ToLower() -in $DeletedAnywhereExtensions)
    }

$dirCount = $targetDirs.Count
$fileCount = $targetFiles.Count

if ($dirCount -eq 0 -and $fileCount -eq 0) {
    Write-Host 'Nothing to clean up.' -ForegroundColor Green
    return
}

Write-Host "Found $dirCount directories and $fileCount files to remove:" -ForegroundColor Yellow
foreach ($d in $targetDirs) {
    Write-Host ('  [dir]  ' + $d.FullName.Substring($boostRootResolved.Length))
}
foreach ($f in $targetFiles) {
    Write-Host ('  [file] ' + $f.FullName.Substring($boostRootResolved.Length))
}

$toolsWithCmake = $targetDirs | Where-Object {
    $_.Name -eq 'tools' -and
        (Test-Path -LiteralPath (Join-Path $_.FullName 'cmake') -PathType Container)
}
foreach ($t in $toolsWithCmake) {
    Write-Host ('  [keep]  ' + (Join-Path $t.FullName 'cmake').Substring($boostRootResolved.Length) +
        ' (needed by CMake build)') -ForegroundColor Cyan
}

if ($DryRun) {
    Write-Host '(DryRun mode, nothing was deleted)' -ForegroundColor Cyan
    return
}

if (-not $Force) {
    $answer = Read-Host 'Confirm deletion of the above? [y/N]'
    if ($answer -notin @('y', 'Y', 'yes')) {
        Write-Host 'Cancelled.' -ForegroundColor Cyan
        return
    }
}

$freedBytes = 0L
foreach ($d in $targetDirs) {
    if (-not (Test-Path -LiteralPath $d.FullName)) { continue }

    $cmakeSub = Join-Path $d.FullName 'cmake'
    $keepCmake = ($d.Name -eq 'tools' -and (Test-Path -LiteralPath $cmakeSub -PathType Container))

    if ($keepCmake) {
        $children = Get-ChildItem -LiteralPath $d.FullName -Force |
            Where-Object { $_.Name -ne 'cmake' }
        foreach ($child in $children) {
            $freedBytes += (Get-ChildItem -LiteralPath $child.FullName -Recurse -File -Force |
                Measure-Object -Property Length -Sum).Sum
            Remove-Item -LiteralPath $child.FullName -Recurse -Force
        }
    } else {
        $freedBytes += (Get-ChildItem -LiteralPath $d.FullName -Recurse -File -Force |
            Measure-Object -Property Length -Sum).Sum
        Remove-Item -LiteralPath $d.FullName -Recurse -Force
    }
}
foreach ($f in $targetFiles) {
    if (Test-Path -LiteralPath $f.FullName) {
        $freedBytes += $f.Length
        Remove-Item -LiteralPath $f.FullName -Force
    }
}

$freedMB = [math]::Round($freedBytes / 1MB, 2)
Write-Host "Done. Freed approximately $freedMB MB." -ForegroundColor Green
