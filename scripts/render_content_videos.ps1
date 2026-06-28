param(
  [string]$ContentDir = "content\2026-06-28-market-signal",
  [string]$OutputDir = "",
  [int[]]$ShortNumbers = @(1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
  [switch]$RenderLongform
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Speech

$root = (Resolve-Path ".").Path
$contentPath = if ([System.IO.Path]::IsPathRooted($ContentDir)) { $ContentDir } else { Join-Path $root $ContentDir }
$outputPath = if ($OutputDir) {
  if ([System.IO.Path]::IsPathRooted($OutputDir)) { $OutputDir } else { Join-Path $root $OutputDir }
} else {
  Join-Path $contentPath "videos"
}
$workPath = Join-Path $outputPath "_work"
New-Item -ItemType Directory -Force -Path $outputPath, $workPath | Out-Null

$palette = @{
  bg = "#F4EFE4"
  panel = "#FAF7EF"
  panelStrong = "#F7F1E6"
  secondary = "#DDECE9"
  line = "#D8D2C3"
  ink = "#1D1E20"
  body = "#2D2A26"
  muted = "#6E6A61"
  teal = "#2E6F6B"
  red = "#A73234"
  amber = "#D99028"
  walnut = "#6D4A32"
  olive = "#56704A"
  ceramicTeal = "#5DA6A4"
}

function ConvertTo-Slug([string]$value) {
  $slug = $value.ToLowerInvariant() -replace "[^a-z0-9]+", "-"
  $slug = $slug.Trim("-")
  if ($slug.Length -gt 72) { $slug = $slug.Substring(0, 72).Trim("-") }
  return $slug
}

function New-Color([string]$hex) {
  return [System.Drawing.ColorTranslator]::FromHtml($hex)
}

function New-Brush([string]$hex) {
  return [System.Drawing.SolidBrush]::new((New-Color $hex))
}

function New-Pen([string]$hex, [float]$width = 1) {
  return [System.Drawing.Pen]::new((New-Color $hex), $width)
}

function New-RoundedRectPath([float]$x, [float]$y, [float]$w, [float]$h, [float]$r) {
  $path = [System.Drawing.Drawing2D.GraphicsPath]::new()
  $d = $r * 2
  $path.AddArc($x, $y, $d, $d, 180, 90)
  $path.AddArc($x + $w - $d, $y, $d, $d, 270, 90)
  $path.AddArc($x + $w - $d, $y + $h - $d, $d, $d, 0, 90)
  $path.AddArc($x, $y + $h - $d, $d, $d, 90, 90)
  $path.CloseFigure()
  return $path
}

function Fill-RoundedRect($g, [float]$x, [float]$y, [float]$w, [float]$h, [float]$r, [string]$fill, [string]$stroke = "", [float]$strokeWidth = 1) {
  $path = New-RoundedRectPath $x $y $w $h $r
  $brush = New-Brush $fill
  $g.FillPath($brush, $path)
  $brush.Dispose()
  if ($stroke) {
    $pen = New-Pen $stroke $strokeWidth
    $g.DrawPath($pen, $path)
    $pen.Dispose()
  }
  $path.Dispose()
}

function Draw-WrappedText($g, [string]$text, $font, [string]$hex, [float]$x, [float]$y, [float]$w, [float]$h, [int]$maxLines = 0) {
  $brush = New-Brush $hex
  $format = [System.Drawing.StringFormat]::new()
  $format.Trimming = [System.Drawing.StringTrimming]::EllipsisWord
  $format.FormatFlags = [System.Drawing.StringFormatFlags]::LineLimit
  $rect = [System.Drawing.RectangleF]::new($x, $y, $w, $h)
  if ($maxLines -gt 0) {
    $lineHeight = $font.GetHeight($g) * 1.18
    $rect.Height = [Math]::Min($h, $lineHeight * $maxLines)
  }
  $g.DrawString($text, $font, $brush, $rect, $format)
  $format.Dispose()
  $brush.Dispose()
}

function Draw-BrandHeader($g, [int]$width, [int]$height, [string]$section, [string]$title) {
  $brandFont = [System.Drawing.Font]::new("Segoe UI", 22, [System.Drawing.FontStyle]::Bold)
  $sectionFont = [System.Drawing.Font]::new("Segoe UI", 20, [System.Drawing.FontStyle]::Bold)
  Draw-WrappedText $g "MARKET SIGNAL STUDIO" $brandFont $palette.muted 70 58 ($width - 140) 42 1
  $chipX = 70
  $chipY = 112
  $chipW = [Math]::Min(520, 34 + ($section.Length * 13))
  Fill-RoundedRect $g $chipX $chipY $chipW 48 18 "#FBEFD5" "" 0
  $sectionBrush = New-Brush $palette.walnut
  $g.DrawString($section, $sectionFont, $sectionBrush, [System.Drawing.PointF]::new($chipX + 18, $chipY + 8))
  $sectionBrush.Dispose()
  $titleSize = if ($width -gt $height) { 36 } else { 46 }
  $titleFont = [System.Drawing.Font]::new("Segoe UI", $titleSize, [System.Drawing.FontStyle]::Bold)
  Draw-WrappedText $g $title $titleFont $palette.ink 70 182 ($width - 140) 190 4
  $brandFont.Dispose()
  $sectionFont.Dispose()
  $titleFont.Dispose()
}

function Draw-SignalLine($g, [float]$x, [float]$y, [float]$w, [float]$h, [string]$accent) {
  $gridPen = New-Pen "#E7DFCF" 2
  for ($i = 1; $i -lt 4; $i++) {
    $yy = $y + ($h / 4 * $i)
    $g.DrawLine($gridPen, $x, $yy, $x + $w, $yy)
  }
  $gridPen.Dispose()
  $pen = New-Pen $accent 7
  $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  $points = @(
    [System.Drawing.PointF]::new($x, $y + $h * 0.58),
    [System.Drawing.PointF]::new($x + $w * 0.18, $y + $h * 0.44),
    [System.Drawing.PointF]::new($x + $w * 0.36, $y + $h * 0.50),
    [System.Drawing.PointF]::new($x + $w * 0.55, $y + $h * 0.28),
    [System.Drawing.PointF]::new($x + $w * 0.73, $y + $h * 0.38),
    [System.Drawing.PointF]::new($x + $w, $y + $h * 0.20)
  )
  $g.DrawLines($pen, $points)
  $pen.Dispose()
  $brush = New-Brush $accent
  $last = $points[-1]
  $g.FillEllipse($brush, $last.X - 10, $last.Y - 10, 20, 20)
  $brush.Dispose()
}

function Draw-Tiles($g, [string[]]$tiles, [float]$x, [float]$y, [float]$w) {
  $labelFont = [System.Drawing.Font]::new("Segoe UI", 18, [System.Drawing.FontStyle]::Bold)
  $valueFont = [System.Drawing.Font]::new("Segoe UI", 34, [System.Drawing.FontStyle]::Bold)
  $tileW = ($w - 28) / 3
  for ($i = 0; $i -lt 3; $i++) {
    $parts = $tiles[$i].Split("|", 2)
    $label = $parts[0]
    $value = if ($parts.Length -gt 1) { $parts[1] } else { "" }
    $tx = $x + (($tileW + 14) * $i)
    $fill = @($palette.secondary, "#FBEFD5", "#EEF2E5")[$i]
    $accent = @($palette.teal, $palette.amber, $palette.olive)[$i]
    Fill-RoundedRect $g $tx $y $tileW 128 18 $fill "" 0
    Draw-WrappedText $g $label $labelFont $palette.muted ($tx + 18) ($y + 16) ($tileW - 36) 28 1
    Draw-WrappedText $g $value $valueFont $accent ($tx + 18) ($y + 52) ($tileW - 36) 58 1
  }
  $labelFont.Dispose()
  $valueFont.Dispose()
}

function New-VideoSlide([string]$path, [int]$width, [int]$height, [string]$section, [string]$title, [string]$body, [string]$footer, [string[]]$tiles = @(), [string]$accent = "#2E6F6B") {
  $bitmap = [System.Drawing.Bitmap]::new($width, $height)
  $g = [System.Drawing.Graphics]::FromImage($bitmap)
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
  $g.Clear((New-Color $palette.bg))

  Fill-RoundedRect $g 38 38 ($width - 76) ($height - 76) 28 $palette.panel $palette.line 2
  Draw-BrandHeader $g $width $height $section $title

  $bodyTop = if ($height -gt $width) { 390 } else { 285 }
  $bodyHeight = if ($height -gt $width) { 520 } else { 235 }
  $bodyFont = [System.Drawing.Font]::new("Segoe UI", $(if ($height -gt $width) { 38 } else { 25 }), [System.Drawing.FontStyle]::Regular)

  if ($height -gt $width) {
    Fill-RoundedRect $g 70 $bodyTop ($width - 140) $bodyHeight 18 $palette.panelStrong $palette.line 1
    Draw-WrappedText $g $body $bodyFont $palette.body 104 ($bodyTop + 34) ($width - 208) ($bodyHeight - 68) 8
    $chartTop = $bodyTop + $bodyHeight + 52
    if ($tiles.Count -ge 3) {
      Draw-Tiles $g $tiles 70 $chartTop ($width - 140)
      $chartTop += 174
    }
    Fill-RoundedRect $g 70 $chartTop ($width - 140) 300 18 $palette.secondary "" 0
    Draw-SignalLine $g 116 ($chartTop + 62) ($width - 232) 170 $accent
  } else {
    $sideX = [int]($width * 0.62)
    $bodyW = $sideX - 100
    Fill-RoundedRect $g 70 $bodyTop $bodyW $bodyHeight 18 $palette.panelStrong $palette.line 1
    Draw-WrappedText $g $body $bodyFont $palette.body 104 ($bodyTop + 34) ($bodyW - 68) ($bodyHeight - 68) 6
    Fill-RoundedRect $g $sideX $bodyTop ($width - $sideX - 70) $bodyHeight 18 $palette.secondary "" 0
    Draw-SignalLine $g ($sideX + 34) ($bodyTop + 54) ($width - $sideX - 138) 130 $accent
  }

  $footerFont = [System.Drawing.Font]::new("Segoe UI", $(if ($height -gt $width) { 20 } else { 18 }), [System.Drawing.FontStyle]::Bold)
  Draw-WrappedText $g $footer $footerFont $palette.muted 70 ($height - 118) ($width - 140) 50 2

  $bodyFont.Dispose()
  $footerFont.Dispose()
  $g.Dispose()
  $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $bitmap.Dispose()
}

function New-Narration([string]$text, [string]$path) {
  $voice = [System.Speech.Synthesis.SpeechSynthesizer]::new()
  $voice.Rate = 1
  $voice.Volume = 100
  $voice.SetOutputToWaveFile($path)
  $voice.Speak($text)
  $voice.SetOutputToNull()
  $voice.Dispose()
}

function Get-AudioDuration([string]$path) {
  $raw = & ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $path
  return [double]::Parse($raw.Trim(), [System.Globalization.CultureInfo]::InvariantCulture)
}

function Join-SlidesToVideo([string[]]$slides, [string]$audioPath, [string]$outputPath) {
  $duration = Get-AudioDuration $audioPath
  $slideDuration = [Math]::Max(3.0, ($duration + 0.8) / $slides.Count)
  $concatPath = Join-Path (Split-Path $outputPath -Parent) (([System.IO.Path]::GetFileNameWithoutExtension($outputPath)) + ".concat.txt")
  $lines = New-Object System.Collections.Generic.List[string]
  foreach ($slide in $slides) {
    $safe = $slide.Replace("\", "/").Replace("'", "'\''")
    $lines.Add("file '$safe'")
    $lines.Add("duration $($slideDuration.ToString([System.Globalization.CultureInfo]::InvariantCulture))")
  }
  $last = $slides[-1].Replace("\", "/").Replace("'", "'\''")
  $lines.Add("file '$last'")
  $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
  [System.IO.File]::WriteAllLines($concatPath, [string[]]$lines, $utf8NoBom)

  & ffmpeg -y -hide_banner -loglevel error -f concat -safe 0 -i $concatPath -i $audioPath -vf "fps=30,format=yuv420p" -c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k -shortest $outputPath
  if ($LASTEXITCODE -ne 0) { throw "ffmpeg failed for $outputPath" }
}

function Parse-Shorts([string]$markdown) {
  $pattern = "(?ms)^## (?<num>\d+)\. (?<title>.+?)\r?\n\r?\nPlatform: (?<platform>.+?)\r?\nHook: (?<hook>.+?)\r?\n\r?\nScript:\r?\n(?<script>.+?)\r?\n\r?\nVisual:\r?\n(?<visual>.+?)\r?\n\r?\nCaption:\r?\n(?<caption>.+?)(?=\r?\n\r?\n## \d+\.|\z)"
  $items = @()
  foreach ($match in [regex]::Matches($markdown, $pattern)) {
    $items += [PSCustomObject]@{
      Number = [int]$match.Groups["num"].Value
      Title = $match.Groups["title"].Value.Trim()
      Platform = $match.Groups["platform"].Value.Trim()
      Hook = $match.Groups["hook"].Value.Trim()
      Script = ($match.Groups["script"].Value.Trim() -replace "\r?\n", " ")
      Visual = $match.Groups["visual"].Value.Trim()
      Caption = $match.Groups["caption"].Value.Trim()
    }
  }
  return $items
}

function Get-ShortTiles($item) {
  switch -Regex ($item.Title) {
    "Fed" { return @("Fed range|3.50-3.75%", "Inflation|above 2%", "Signal|can wait") }
    "Inflation" { return @("Income|+0.7%", "Spending|+0.7%", "PCE|+4.1% YoY") }
    "CPI|Energy" { return @("CPI|+4.2% YoY", "Core|+2.9% YoY", "Energy|+23.5% YoY") }
    "Jobs" { return @("Payrolls|+172k", "Unemployment|4.3%", "Signal|not broken") }
    "AI" { return @('NVDA rev|$81.6B', "Data center|+92%", 'MU guide|$50B') }
    default { return @("Inflation|sticky", "Fed|patient", "AI|real") }
  }
}

function Render-Short($item) {
  $slug = "{0:00}-{1}" -f $item.Number, (ConvertTo-Slug $item.Title)
  $videoDir = Join-Path $workPath $slug
  New-Item -ItemType Directory -Force -Path $videoDir | Out-Null
  $sentences = [regex]::Split($item.Script, "(?<=[.!?])\s+") | Where-Object { $_.Trim() }
  $body1 = $item.Hook
  $body2 = (($sentences | Select-Object -First 3) -join " ")
  $body3 = (($sentences | Select-Object -Skip 3 -First 3) -join " ")
  $body4 = (($sentences | Select-Object -Skip 6) -join " ")
  if (-not $body4) { $body4 = $item.Caption }

  $slides = @()
  $slides += Join-Path $videoDir "slide_01.png"
  New-VideoSlide $slides[-1] 1080 1920 "MARKET SIGNAL" $item.Title $body1 "Source-backed commentary. Not investment advice." (Get-ShortTiles $item) $palette.teal
  $slides += Join-Path $videoDir "slide_02.png"
  New-VideoSlide $slides[-1] 1080 1920 "THE DATA" $item.Title $body2 "Primary sources: BEA, Fed, BLS, NVIDIA, Micron." (Get-ShortTiles $item) $palette.amber
  $slides += Join-Path $videoDir "slide_03.png"
  New-VideoSlide $slides[-1] 1080 1920 "WHY IT MATTERS" $item.Title $body3 "Original angle: explain the signal, not the headline." (Get-ShortTiles $item) $palette.teal
  $slides += Join-Path $videoDir "slide_04.png"
  New-VideoSlide $slides[-1] 1080 1920 "CAVEAT" $item.Title $body4 "Verify final market data and source rights before posting." (Get-ShortTiles $item) $palette.red

  $audio = Join-Path $videoDir "voiceover.wav"
  New-Narration $item.Script $audio
  $output = Join-Path $outputPath ($slug + ".mp4")
  Join-SlidesToVideo $slides $audio $output

  return [PSCustomObject]@{
    type = "short"
    number = $item.Number
    title = $item.Title
    file = $output
    duration_sec = [Math]::Round((Get-AudioDuration $audio), 1)
  }
}

function Get-LongformScript([string]$markdown) {
  $scriptMatch = [regex]::Match($markdown, "(?ms)^## Script\r?\n\r?\n(?<script>.+?)\r?\n\r?\n## Visual Plan")
  if ($scriptMatch.Success) {
    return ($scriptMatch.Groups["script"].Value.Trim() -replace "\r?\n\r?\n", "`n")
  }
  return $markdown
}

function Render-Longform([string]$scriptText) {
  $videoDir = Join-Path $workPath "longform-market-three-stories"
  New-Item -ItemType Directory -Force -Path $videoDir | Out-Null
  $slides = @()
  $chapters = @(
    @("THE SETUP", "Inflation, Fed patience, and AI valuation are colliding at the same time.", @("Inflation|sticky", "Fed|patient", "AI|real"), $palette.teal),
    @("INFLATION", "PCE and CPI stayed hot enough to challenge easy-money hopes.", @("PCE|+4.1% YoY", "CPI|+4.2% YoY", "Energy|+23.5% YoY"), $palette.red),
    @("THE FED", "The Fed held rates and kept the burden of proof on inflation.", @("Rate range|3.50-3.75%", "Inflation|above 2%", "Signal|wait"), $palette.teal),
    @("LABOR", "Stable jobs do not force rescue cuts, even with cracks under the surface.", @("Payrolls|+172k", "Unemp.|4.3%", "Wages|+3.4% YoY"), $palette.olive),
    @("AI", "AI infrastructure demand is real, but valuation is more exposed when rates stay firm.", @('NVDA rev|$81.6B', 'Data center|$75.2B', 'MU guide|$50B'), $palette.amber),
    @("WATCH NEXT", "Watch inflation, jobs, AI capex commentary, and energy volatility.", @("Inflation|next print", "Jobs|stability", "Energy|volatility"), $palette.walnut)
  )
  for ($i = 0; $i -lt $chapters.Count; $i++) {
    $path = Join-Path $videoDir ("slide_{0:00}.png" -f ($i + 1))
    $chapter = $chapters[$i]
    New-VideoSlide $path 1280 720 $chapter[0] "The Market Is Fighting Three Stories" $chapter[1] "Long-form draft. Source-backed commentary. Not investment advice." $chapter[2] $chapter[3]
    $slides += $path
  }
  $audio = Join-Path $videoDir "voiceover.wav"
  New-Narration $scriptText $audio
  $output = Join-Path $outputPath "longform-the-market-is-fighting-three-stories.mp4"
  Join-SlidesToVideo $slides $audio $output
  return [PSCustomObject]@{
    type = "longform"
    title = "The Market Is Fighting Three Stories"
    file = $output
    duration_sec = [Math]::Round((Get-AudioDuration $audio), 1)
  }
}

$manifest = New-Object System.Collections.Generic.List[object]
$shortMarkdown = Get-Content -Raw (Join-Path $contentPath "shortform-scripts.md")
$shorts = Parse-Shorts $shortMarkdown
foreach ($item in $shorts | Where-Object { $ShortNumbers -contains $_.Number }) {
  Write-Host "Rendering short $($item.Number): $($item.Title)"
  $manifest.Add((Render-Short $item))
}

if ($RenderLongform) {
  Write-Host "Rendering long-form video draft"
  $longMarkdown = Get-Content -Raw (Join-Path $contentPath "youtube-script.md")
  $manifest.Add((Render-Longform (Get-LongformScript $longMarkdown)))
}

$manifestPath = Join-Path $outputPath "video_manifest.json"
$manifest | ConvertTo-Json -Depth 5 | Set-Content -Path $manifestPath -Encoding UTF8
Write-Host "Wrote video manifest: $manifestPath"
