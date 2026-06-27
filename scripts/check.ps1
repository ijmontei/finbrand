$ErrorActionPreference = "Stop"

Push-Location "$PSScriptRoot\..\backend"
try {
  python -m unittest discover -s tests
}
finally {
  Pop-Location
}

Push-Location "$PSScriptRoot\..\frontend"
try {
  if (Test-Path "node_modules") {
    npm run build
  }
  else {
    Write-Host "Skipping frontend build because node_modules is not installed."
  }
}
finally {
  Pop-Location
}

