# set_serpapi_key.ps1
# Prompt for a SerpApi key and set it persistently for the current user using setx.

Param()

$key = Read-Host "Enter your SerpApi key (it will be set as a user environment variable)"
if (-not $key) {
    Write-Host "No key entered. Aborting." -ForegroundColor Yellow
    exit 1
}

# Set it persistently for the current user
setx SERPAPI_KEY $key
Write-Host "SERPAPI_KEY set for current user. Close and re-open your terminals/VS Code to pick it up." -ForegroundColor Green
