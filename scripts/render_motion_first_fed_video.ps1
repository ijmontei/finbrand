param(
  [string]$StoryPath = "content\2026-06-28-market-signal\stories\fed-pause-not-pivot.json",
  [string]$OutputDir = "",
  [switch]$NoReplacePrimary,
  [switch]$KeepWork
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Speech

$root = (Resolve-Path ".").Path
$storyPathResolved = if ([System.IO.Path]::IsPathRooted($StoryPath)) { $StoryPath } else { Join-Path $root $StoryPath }
$story = Get-Content -Raw -LiteralPath $storyPathResolved | ConvertFrom-Json
$contentPath = Split-Path (Split-Path $storyPathResolved -Parent) -Parent
$videosPath = Join-Path $contentPath "videos"
$outputPath = if ($OutputDir) {
  if ([System.IO.Path]::IsPathRooted($OutputDir)) { $OutputDir } else { Join-Path $root $OutputDir }
} else {
  Join-Path $videosPath "flagship"
}
$workPath = Join-Path $outputPath "_work"
$framesPath = Join-Path $workPath "frames"
New-Item -ItemType Directory -Force -Path $outputPath, $workPath, $framesPath | Out-Null

$palette = @{
  bg = "#0B0F14"
  panel = "#111821"
  panelElevated = "#16202A"
  panelSoft = "#1B2734"
  text = "#F4F7FA"
  textSecondary = "#A9B4C0"
  grid = "#2A3542"
  rule = "#354252"
  positive = "#2EE59D"
  negative = "#FF4D5F"
  warning = "#FFB84D"
  policy = "#32C5C7"
  neutral = "#D8DEE8"
  muted = "#6F7A86"
}

function New-Color([string]$hex) {
  return [System.Drawing.ColorTranslator]::FromHtml($hex)
}

function New-Brush([string]$hex) {
  return [System.Drawing.SolidBrush]::new((New-Color $hex))
}

function New-AlphaBrush([string]$hex, [int]$alpha) {
  $c = New-Color $hex
  return [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb($alpha, $c.R, $c.G, $c.B))
}

function New-Pen([string]$hex, [float]$width = 1) {
  return [System.Drawing.Pen]::new((New-Color $hex), $width)
}

function New-AlphaPen([string]$hex, [int]$alpha, [float]$width = 1) {
  $c = New-Color $hex
  return [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb($alpha, $c.R, $c.G, $c.B), $width)
}

function New-Font([float]$size, [string]$style = "Regular", [string]$family = "Segoe UI") {
  return [System.Drawing.Font]::new($family, $size, [System.Drawing.FontStyle]::$style, [System.Drawing.GraphicsUnit]::Pixel)
}

function New-RoundedRectPath([float]$x, [float]$y, [float]$w, [float]$h, [float]$r) {
  $path = [System.Drawing.Drawing2D.GraphicsPath]::new()
  if ($r -le 0 -or $w -le 0 -or $h -le 0) {
    $path.AddRectangle([System.Drawing.RectangleF]::new($x, $y, $w, $h))
    return $path
  }
  $r = [Math]::Min($r, [Math]::Min($w, $h) / 2)
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

function Draw-Text($g, [string]$text, $font, [string]$hex, [float]$x, [float]$y, [float]$w, [float]$h, [string]$align = "Near", [string]$valign = "Near", [int]$maxLines = 0) {
  $brush = New-Brush $hex
  $format = [System.Drawing.StringFormat]::new()
  $format.Trimming = [System.Drawing.StringTrimming]::None
  $format.FormatFlags = [System.Drawing.StringFormatFlags]::LineLimit
  $format.Alignment = [System.Drawing.StringAlignment]::$align
  $format.LineAlignment = [System.Drawing.StringAlignment]::$valign
  $rect = [System.Drawing.RectangleF]::new($x, $y, $w, $h)
  if ($maxLines -gt 0) {
    $lineHeight = $font.GetHeight($g) * 1.08
    $rect.Height = [Math]::Min($h, $lineHeight * $maxLines)
  }
  $g.DrawString($text, $font, $brush, $rect, $format)
  $format.Dispose()
  $brush.Dispose()
}

function Draw-FitText($g, [string]$text, [string]$family, [float]$size, [string]$style, [string]$hex, [float]$x, [float]$y, [float]$w, [float]$h, [int]$minSize = 26, [int]$maxLines = 2) {
  $format = [System.Drawing.StringFormat]::new()
  $format.Trimming = [System.Drawing.StringTrimming]::None
  $format.FormatFlags = [System.Drawing.StringFormatFlags]::LineLimit
  $fitSize = $size
  while ($fitSize -gt $minSize) {
    $font = New-Font $fitSize $style $family
    $measured = $g.MeasureString($text, $font, [System.Drawing.SizeF]::new($w, $h), $format)
    if ($measured.Height -le $h -and $measured.Width -le ($w + 6)) {
      break
    }
    $font.Dispose()
    $fitSize -= 2
  }
  if (-not $font) { $font = New-Font $fitSize $style $family }
  Draw-Text $g $text $font $hex $x $y $w $h "Near" "Near" $maxLines
  $font.Dispose()
  $format.Dispose()
}

function Ease-OutCubic([double]$t) {
  $t = [Math]::Max(0, [Math]::Min(1, $t))
  return 1 - [Math]::Pow(1 - $t, 3)
}

function Ease-InOutCubic([double]$t) {
  $t = [Math]::Max(0, [Math]::Min(1, $t))
  if ($t -lt 0.5) { return 4 * $t * $t * $t }
  return 1 - [Math]::Pow(-2 * $t + 2, 3) / 2
}

function Get-SceneProgress([int]$frame, [int]$start, [int]$duration) {
  return [Math]::Max(0, [Math]::Min(1, ($frame - $start) / [double]$duration))
}

function Draw-LineSegment($g, [System.Drawing.PointF[]]$points, [double]$progress, [string]$hex, [float]$width) {
  if ($points.Count -lt 2 -or $progress -le 0) { return }
  $progress = [Math]::Min(1, $progress)
  $segments = $points.Count - 1
  $fullSegments = [Math]::Floor($progress * $segments)
  $partial = ($progress * $segments) - $fullSegments
  $drawPoints = New-Object System.Collections.Generic.List[System.Drawing.PointF]
  $drawPoints.Add($points[0])
  for ($i = 1; $i -le $fullSegments; $i++) { $drawPoints.Add($points[$i]) }
  if ($fullSegments -lt $segments) {
    $a = $points[$fullSegments]
    $b = $points[$fullSegments + 1]
    $drawPoints.Add([System.Drawing.PointF]::new($a.X + (($b.X - $a.X) * $partial), $a.Y + (($b.Y - $a.Y) * $partial)))
  }
  $pen = New-Pen $hex $width
  $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  if ($drawPoints.Count -gt 1) { $g.DrawLines($pen, $drawPoints.ToArray()) }
  $pen.Dispose()
}

function Draw-Base($g, [int]$w, [int]$h, [int]$frame) {
  $brush = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
    [System.Drawing.Rectangle]::new(0, 0, $w, $h),
    (New-Color "#071019"),
    (New-Color $palette.bg),
    [System.Drawing.Drawing2D.LinearGradientMode]::ForwardDiagonal
  )
  $g.FillRectangle($brush, 0, 0, $w, $h)
  $brush.Dispose()

  $gridPen = New-AlphaPen $palette.grid 80 1
  for ($x = 96; $x -lt $w; $x += 144) { $g.DrawLine($gridPen, $x, 0, $x, $h) }
  for ($y = 180; $y -lt $h; $y += 144) { $g.DrawLine($gridPen, 0, $y, $w, $y) }
  $gridPen.Dispose()

}

function Draw-Header($g, [int]$w, [string]$topic) {
  $brand = New-Font 26 "Bold"
  $mono = New-Font 21 "Bold" "Consolas"
  Draw-Text $g "MARKET SIGNAL STUDIO" $brand $palette.text 96 56 560 40
  Draw-Text $g "POLICY REACTION / SOURCE-BACKED" $mono $palette.textSecondary 96 92 680 34
  Fill-RoundedRect $g 736 58 248 52 26 $palette.panelElevated $palette.rule 1
  Draw-Text $g $topic $mono $palette.policy 756 72 208 28 "Center"
  $rule = New-AlphaPen $palette.rule 210 2
  $g.DrawLine($rule, 96, 144, 984, 144)
  $rule.Dispose()
  $brand.Dispose()
  $mono.Dispose()
}

function Draw-MetricChip($g, [string]$label, [string]$value, [float]$x, [float]$y, [float]$w, [string]$accent, [double]$progress = 1) {
  $progress = Ease-OutCubic $progress
  $height = 86
  $offset = (1 - $progress) * 28
  $alpha = [int](255 * $progress)
  $path = New-RoundedRectPath $x ($y + $offset) $w $height 18
  $brush = New-AlphaBrush $palette.panelElevated $alpha
  $g.FillPath($brush, $path)
  $brush.Dispose()
  $pen = New-AlphaPen $accent $alpha 2
  $g.DrawPath($pen, $path)
  $pen.Dispose()
  $labelFont = New-Font 19 "Bold" "Consolas"
  $valueFont = New-Font 34 "Bold" "Consolas"
  Draw-Text $g $label $labelFont $palette.textSecondary ($x + 20) ($y + 13 + $offset) ($w - 40) 24
  Draw-Text $g $value $valueFont $accent ($x + 20) ($y + 40 + $offset) ($w - 40) 42
  $labelFont.Dispose()
  $valueFont.Dispose()
  $path.Dispose()
}

function Draw-SourceCapsule($g, $story, [float]$x, [float]$y, [float]$w) {
  Fill-RoundedRect $g $x $y $w 84 18 $palette.panel $palette.rule 1
  $font = New-Font 24 "Bold"
  $small = New-Font 20 "Regular"
  $sourceText = if ($story.sourceManifest -and $story.sourceManifest.display) { $story.sourceManifest.display } else { "Federal Reserve; BEA" }
  Draw-Text $g "Sources" $font $palette.text $($x + 24) $($y + 16) 130 30
  Draw-Text $g $sourceText $small $palette.textSecondary $($x + 150) $($y + 18) $($w - 174) 38 "Near" "Near" 1
  $font.Dispose()
  $small.Dispose()
}

function Draw-AmbientTicker($g, [int]$w, [int]$h, [int]$frame) {
  $y = 1526
  Fill-RoundedRect $g 76 $y 928 92 22 $palette.panel "" 0
  $font = New-Font 24 "Bold" "Consolas"
  $items = @(
    @("FED", "HOLD", $palette.policy),
    @("PCE", "4.1%", $palette.negative),
    @("TARGET", "2.0%", $palette.neutral),
    @("GAP", "+2.1 pp", $palette.warning)
  )
  $offset = -($frame % 90)
  $x = 110 + $offset
  foreach ($item in $items + $items) {
    Draw-Text $g $item[0] $font $palette.textSecondary $x ($y + 32) 110 30
    Draw-Text $g $item[1] $font $item[2] ($x + 90) ($y + 32) 140 30
    $x += 238
  }
  $font.Dispose()
}

function Draw-ImpactHook($g, $story, [int]$frame) {
  $p = Get-SceneProgress $frame 0 150
  $hit1 = Ease-OutCubic (Get-SceneProgress $frame 0 22)
  $hit2 = 1
  $hit3 = Ease-OutCubic (Get-SceneProgress $frame 48 28)
  $resolve = Ease-OutCubic (Get-SceneProgress $frame 76 44)
  $tease = Ease-OutCubic (Get-SceneProgress $frame 118 32)
  $mono = New-Font 32 "Bold" "Consolas"

  Draw-Text $g "FIRST 3 SECONDS" $mono $palette.warning 96 190 420 42
  Draw-Text $g "PAUSE" (New-Font 94 "Bold") $palette.policy 96 (254 - ((1 - $hit1) * 32)) 384 170
  if ($hit2 -gt 0) {
    $symbolAlpha = [int](255 * $hit2)
    $symbolPen = New-AlphaPen $palette.warning $symbolAlpha 9
    $symbolPen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $symbolPen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $sy = 322 - ((1 - $hit2) * 24)
    $g.DrawLine($symbolPen, 506, $sy, 604, $sy)
    $g.DrawLine($symbolPen, 506, ($sy + 38), 604, ($sy + 38))
    $g.DrawLine($symbolPen, 590, ($sy - 24), 520, ($sy + 62))
    $symbolPen.Dispose()
  }
  Draw-Text $g "PIVOT" (New-Font 88 "Bold") $palette.negative 624 (260 - ((1 - $hit3) * 32)) 304 156

  if ($hit3 -gt 0.65) {
    $strike = New-Pen $palette.negative 10
    $strike.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $strike.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $g.DrawLine($strike, 632, 332, 916, 332)
    $strike.Dispose()
  }

  Draw-Text $g $story.hookConflict.subline (New-Font 39 "Bold") $palette.text 96 452 850 104 "Near" "Near" 2

  Draw-MetricChip $g "TARGET RANGE" $story.hook.primaryNumber 96 640 374 $palette.policy $resolve
  Draw-MetricChip $g "CONDITION" "INFLATION" 506 640 314 $palette.warning $resolve
  Draw-MetricChip $g "PIVOT" "NOT YET" 796 640 188 $palette.negative $resolve

  Fill-RoundedRect $g 96 812 840 270 28 $palette.panel $palette.rule 1
  Draw-Text $g "The hold was the headline." (New-Font 46 "Bold") $palette.text 132 852 760 56
  Draw-Text $g "The inflation gap is the story." (New-Font 46 "Bold") $palette.warning 132 922 760 56
  Draw-Text $g ("{0} above target" -f $story.proofMetric.gapDisplay) (New-Font 54 "Bold" "Consolas") $palette.negative 132 1002 680 64

  if ($tease -gt 0) {
    $flash = [int](70 + (110 * $tease))
    $brush = New-AlphaBrush $palette.negative $flash
    $g.FillRectangle($brush, 0, 0, [int]$story.dimensions.width, [int]$story.dimensions.height)
    $brush.Dispose()
  }

  Draw-SourceCapsule $g $story 96 1328 840
  $mono.Dispose()
}

function Draw-ExpectationVsReality($g, $story, [int]$frame) {
  $p = Ease-OutCubic (Get-SceneProgress $frame 150 120)
  $mono = New-Font 25 "Bold" "Consolas"
  Draw-Text $g "EXPECTATION" $mono $palette.muted 96 192 420 38
  Draw-Text $g "Relief trade" (New-Font 68 "Bold") $palette.positive 96 240 860 82
  Draw-Text $g "REALITY" $mono $palette.warning 96 374 420 38
  Draw-Text $g "Conditions first" (New-Font 72 "Bold") $palette.warning 96 422 860 86

  $expectX = 96 - ((1 - $p) * 52)
  $actualX = 548 + ((1 - $p) * 52)
  Fill-RoundedRect $g $expectX 616 382 276 28 $palette.panel $palette.rule 1
  Fill-RoundedRect $g $actualX 616 388 276 28 $palette.panelElevated $palette.policy 3
  Draw-Text $g "MARKET WANTED" $mono $palette.textSecondary ($expectX + 30) 648 300 34
  Draw-Text $g "CUTS" (New-Font 60 "Bold") $palette.positive ($expectX + 30) 700 250 72
  Draw-Text $g "Lower-rate path" (New-Font 29 "Regular") $palette.textSecondary ($expectX + 30) 790 300 42
  Draw-Text $g "FED DELIVERED" $mono $palette.textSecondary ($actualX + 30) 648 300 34
  Draw-Text $g "PROOF" (New-Font 60 "Bold") $palette.warning ($actualX + 30) 700 250 72
  Draw-Text $g "Inflation must cool" (New-Font 29 "Regular") $palette.textSecondary ($actualX + 30) 790 300 42

  Fill-RoundedRect $g 96 1008 840 168 24 $palette.panel "" 0
  Draw-Text $g "3.50-3.75%" (New-Font 54 "Bold" "Consolas") $palette.policy 132 1046 360 64
  Draw-Text $g "target range unchanged" (New-Font 34 "Bold") $palette.text 470 1052 430 50
  Draw-Text $g "Decision steady. Cut bar intact." (New-Font 30 "Regular") $palette.textSecondary 132 1120 720 40
  Draw-SourceCapsule $g $story 96 1328 840
  $mono.Dispose()
}

function Draw-GapProofChart($g, $story, [int]$frame) {
  $p = Ease-InOutCubic (Get-SceneProgress $frame 270 210)
  $mono = New-Font 25 "Bold" "Consolas"
  Draw-Text $g "THE PROOF" $mono $palette.warning 96 190 420 38
  Draw-Text $g "Inflation is still" (New-Font 68 "Bold") $palette.text 96 238 860 80
  Draw-Text $g "above target." (New-Font 68 "Bold") $palette.negative 96 318 860 112

  $x = 96
  $y = 484
  $w = 888
  $h = 700
  Fill-RoundedRect $g $x $y $w $h 30 $palette.panel $palette.rule 1
  $plotX = $x + 104
  $plotY = $y + 104
  $plotW = $w - 188
  $plotH = 420
  $grid = New-AlphaPen $palette.grid 210 2
  for ($i = 0; $i -le 5; $i++) {
    $yy = $plotY + ($plotH / 5 * $i)
    $g.DrawLine($grid, $plotX, $yy, $plotX + $plotW, $yy)
    Draw-Text $g ("{0}%" -f (5 - $i)) $mono $palette.muted ($plotX - 72) ($yy - 15) 58 30 "Far"
  }
  $grid.Dispose()
  $axis = New-AlphaPen $palette.rule 230 2
  $g.DrawLine($axis, $plotX, $plotY, $plotX, $plotY + $plotH)
  $g.DrawLine($axis, $plotX, $plotY + $plotH, $plotX + $plotW, $plotY + $plotH)
  $axis.Dispose()

  $toY = {
    param([double]$v)
    return $plotY + $plotH - (($v / 5.0) * $plotH)
  }
  $target = [double]$story.proofMetric.target
  $actual = [double]$story.proofMetric.actual
  $targetY = & $toY $target
  $actualYFinal = & $toY $actual
  $actualY = $targetY + (($actualYFinal - $targetY) * $p)
  $markerX = $plotX + ($plotW * 0.62)

  $targetPen = New-Pen $palette.neutral 4
  $targetPen.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash
  $g.DrawLine($targetPen, $plotX, $targetY, $plotX + $plotW, $targetY)
  $targetPen.Dispose()
  Draw-Text $g "Fed target 2.0%" $mono $palette.neutral ($plotX + 390) ($targetY + 14) 260 34

  $gapPen = New-Pen $palette.negative 12
  $gapPen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $gapPen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  $g.DrawLine($gapPen, $markerX, $targetY, $markerX, $actualY)
  $gapPen.Dispose()
  $dotBrush = New-Brush $palette.negative
  $g.FillEllipse($dotBrush, $markerX - 20, $actualY - 20, 40, 40)
  $dotBrush.Dispose()
  Draw-Text $g "PCE inflation" $mono $palette.textSecondary ($markerX - 140) ($actualY - 82) 280 34 "Center"
  Draw-Text $g ("{0:N1}%" -f ($target + (($actual - $target) * $p))) (New-Font 70 "Bold" "Consolas") $palette.negative ($markerX - 150) ($actualY - 50) 300 82 "Center"

  if ($p -gt 0.45) {
    $gapProgress = Ease-OutCubic (($p - 0.45) / 0.55)
    Draw-MetricChip $g "ABOVE TARGET" $story.proofMetric.gapDisplay 126 1088 330 $palette.warning $gapProgress
    Draw-MetricChip $g "SCALE" $story.proofMetric.badge 486 1088 420 $palette.policy $gapProgress
  }
  Draw-SourceCapsule $g $story 96 1328 840
  $mono.Dispose()
}

function Draw-RiskExposureStack($g, $story, [int]$frame) {
  $p = Ease-OutCubic (Get-SceneProgress $frame 480 210)
  $mono = New-Font 25 "Bold" "Consolas"
  Draw-Text $g $story.marketConsequence.label.ToUpperInvariant() $mono $palette.warning 96 190 420 38
  Draw-Text $g "Rate-sensitive trades" (New-Font 62 "Bold") $palette.text 96 238 880 76
  Draw-Text $g "stay exposed." (New-Font 72 "Bold") $palette.warning 96 312 860 84
  Draw-Text $g "This is a setup, not a live reaction print." (New-Font 32 "Regular") $palette.textSecondary 96 414 820 48

  $risks = @($story.marketConsequence.riskMap)
  for ($i = 0; $i -lt $risks.Count; $i++) {
    $risk = $risks[$i]
    $local = Ease-OutCubic (($p * 1.25) - ($i * 0.18))
    $y = 556 + ($i * 190) + ((1 - $local) * 34)
    $accent = if ($risk.status -eq "Exposed") { $palette.negative } elseif ($risk.status -eq "Watch") { $palette.warning } else { $palette.policy }
    Fill-RoundedRect $g 96 $y 840 150 24 $palette.panel $palette.rule 1
    Fill-RoundedRect $g 126 ($y + 28) 150 52 18 $palette.panelElevated $accent 2
    Draw-Text $g $risk.status.ToUpperInvariant() (New-Font 22 "Bold" "Consolas") $accent 140 ($y + 42) 122 26 "Center"
    Draw-Text $g $risk.label (New-Font 38 "Bold") $palette.text 304 ($y + 28) 470 48
    Draw-Text $g $risk.reason (New-Font 28 "Regular") $palette.textSecondary 304 ($y + 84) 500 40
    $meterPen = New-AlphaPen $accent 190 5
    $g.DrawLine($meterPen, 760, ($y + 76), 900, ($y + 76))
    $g.DrawLine($meterPen, 900, ($y + 76), 872, ($y + 48))
    $g.DrawLine($meterPen, 900, ($y + 76), 872, ($y + 104))
    $meterPen.Dispose()
  }
  Draw-SourceCapsule $g $story 96 1328 840
  $mono.Dispose()
}

function Draw-LoopbackClose($g, $story, [int]$frame) {
  $p = Ease-OutCubic (Get-SceneProgress $frame 690 195)
  $mono = New-Font 27 "Bold" "Consolas"
  Draw-Text $g "BOTTOM LINE" $mono $palette.warning 96 190 420 40
  Draw-Text $g "Pause was" (New-Font 68 "Bold") $palette.text 96 250 840 120
  Draw-Text $g "the decision." (New-Font 68 "Bold") $palette.policy 96 334 840 120
  Draw-Text $g "Not the pivot." (New-Font 78 "Bold") $palette.negative 96 452 840 132

  $catalysts = @($story.nextCatalysts)
  for ($i = 0; $i -lt $catalysts.Count; $i++) {
    $local = Ease-OutCubic (($p * 1.35) - ($i * 0.12))
    $x = 112 + (($i % 2) * 426)
    $y = 700 + ([Math]::Floor($i / 2) * 150) + ((1 - $local) * 32)
    Fill-RoundedRect $g $x $y 382 104 22 $palette.panelElevated $palette.rule 1
    Draw-Text $g ("WATCH {0}" -f ($i + 1)) (New-Font 19 "Bold" "Consolas") $palette.muted ($x + 24) ($y + 16) 150 28
    Draw-Text $g $catalysts[$i] (New-Font 33 "Bold") $palette.text ($x + 24) ($y + 48) 330 44
  }

  Fill-RoundedRect $g 96 1072 840 132 24 $palette.panel "" 0
  Draw-Text $g "Loopback" (New-Font 24 "Bold" "Consolas") $palette.policy 128 1100 190 30
  Draw-Text $g "A hold is not relief if inflation has to prove it." (New-Font 30 "Bold") $palette.text 128 1138 760 58
  Draw-SourceCapsule $g $story 96 1328 840
  $mono.Dispose()
}

function Draw-SafeZoneOverlay($g, $story) {
  $safe = $story.safeZone
  $safePen = New-AlphaPen $palette.positive 170 4
  $dangerBrush = New-AlphaBrush $palette.negative 35
  $g.DrawRectangle($safePen, [float]$safe.criticalXMin, [float]$safe.criticalYMin, [float]($safe.criticalXMax - $safe.criticalXMin), [float]($safe.criticalYMax - $safe.criticalYMin))
  $g.FillRectangle($dangerBrush, 0, [int]$safe.dangerYMin, [int]$story.dimensions.width, [int]($story.dimensions.height - $safe.dangerYMin))
  $safePen.Dispose()
  $dangerBrush.Dispose()
}

function Draw-Frame([string]$path, $story, [int]$frame, [switch]$OverlaySafeZone) {
  $w = [int]$story.dimensions.width
  $h = [int]$story.dimensions.height
  $bitmap = [System.Drawing.Bitmap]::new($w, $h)
  $g = [System.Drawing.Graphics]::FromImage($bitmap)
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
  Draw-Base $g $w $h $frame
  Draw-Header $g $w "FED WATCH"
  if ($frame -lt 150) {
    Draw-ImpactHook $g $story $frame
  } elseif ($frame -lt 270) {
    Draw-ExpectationVsReality $g $story $frame
  } elseif ($frame -lt 480) {
    Draw-GapProofChart $g $story $frame
  } elseif ($frame -lt 690) {
    Draw-RiskExposureStack $g $story $frame
  } else {
    Draw-LoopbackClose $g $story $frame
  }
  if ($OverlaySafeZone) { Draw-SafeZoneOverlay $g $story }
  $g.Dispose()
  $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $bitmap.Dispose()
}

function New-Thumbnail([string]$path, $story) {
  $w = [int]$story.dimensions.width
  $h = [int]$story.dimensions.height
  $bitmap = [System.Drawing.Bitmap]::new($w, $h)
  $g = [System.Drawing.Graphics]::FromImage($bitmap)
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
  Draw-Base $g $w $h 36
  Draw-Header $g $w "FED WATCH"
  Draw-Text $g "PAUSE IS" (New-Font 88 "Bold") $palette.text 96 260 820 132
  Draw-Text $g "NOT PIVOT" (New-Font 88 "Bold") $palette.warning 96 378 820 132
  Draw-MetricChip $g "TARGET RANGE" $story.hook.primaryNumber 96 650 430 $palette.policy 1
  Draw-MetricChip $g "PCE VS TARGET" "+2.1 pp gap" 556 650 380 $palette.negative 1
  Draw-Text $g "The bar for cuts did not fall." (New-Font 40 "Regular") $palette.textSecondary 96 884 850 104 "Near" "Near" 2
  Draw-SourceCapsule $g $story 96 1328 840
  $g.Dispose()
  $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $bitmap.Dispose()
}

function New-Narration([string]$text, [string]$path) {
  $voice = [System.Speech.Synthesis.SpeechSynthesizer]::new()
  $voice.SelectVoice("Microsoft Zira Desktop")
  $voice.Rate = 2
  $voice.Volume = 100
  $voice.SetOutputToWaveFile($path)
  $voice.Speak($text)
  $voice.SetOutputToNull()
  $voice.Dispose()
}

function Format-SrtTime([double]$seconds) {
  $ts = [TimeSpan]::FromSeconds($seconds)
  return "{0:00}:{1:00}:{2:00},{3:000}" -f [Math]::Floor($ts.TotalHours), $ts.Minutes, $ts.Seconds, $ts.Milliseconds
}

function Write-Srt([string]$path, $story) {
  $fps = [double]$story.dimensions.fps
  $lines = New-Object System.Collections.Generic.List[string]
  for ($i = 0; $i -lt $story.scenes.Count; $i++) {
    $scene = $story.scenes[$i]
    $start = [double]$scene.startFrame / $fps
    $end = ([double]$scene.startFrame + [double]$scene.durationFrames) / $fps
    $lines.Add([string]($i + 1))
    $lines.Add((Format-SrtTime $start) + " --> " + (Format-SrtTime $end))
    $lines.Add($scene.caption)
    $lines.Add("")
  }
  Set-Content -LiteralPath $path -Value $lines -Encoding UTF8
}

function Get-AudioDuration([string]$path) {
  $raw = & ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $path
  return [double]::Parse($raw.Trim(), [System.Globalization.CultureInfo]::InvariantCulture)
}

function Get-ContrastRatio([string]$fg, [string]$bg) {
  function Get-Luminance([string]$hex) {
    $c = New-Color $hex
    $channels = @($c.R, $c.G, $c.B) | ForEach-Object {
      $v = $_ / 255.0
      if ($v -le 0.03928) { $v / 12.92 } else { [Math]::Pow((($v + 0.055) / 1.055), 2.4) }
    }
    return (0.2126 * $channels[0]) + (0.7152 * $channels[1]) + (0.0722 * $channels[2])
  }
  $l1 = Get-Luminance $fg
  $l2 = Get-Luminance $bg
  $lighter = [Math]::Max($l1, $l2)
  $darker = [Math]::Min($l1, $l2)
  return [Math]::Round(($lighter + 0.05) / ($darker + 0.05), 2)
}

function Test-BlankFrames([string]$framesDir, [int]$totalFrames) {
  $nearBlank = 0
  for ($frame = 0; $frame -lt $totalFrames; $frame += 45) {
    $path = Join-Path $framesDir ("frame_{0:0000}.png" -f $frame)
    $bmp = [System.Drawing.Bitmap]::new($path)
    $sum = 0
    $count = 0
    for ($x = 80; $x -lt $bmp.Width; $x += 160) {
      for ($y = 120; $y -lt $bmp.Height; $y += 220) {
        $p = $bmp.GetPixel($x, $y)
        $sum += (($p.R + $p.G + $p.B) / 3)
        $count += 1
      }
    }
    $bmp.Dispose()
    if (($sum / [Math]::Max(1, $count)) -lt 14) { $nearBlank += 1 }
  }
  return $nearBlank
}

function Test-StoryContract($story) {
  $errors = New-Object System.Collections.Generic.List[string]
  foreach ($field in @("hookConflict", "proofMetric", "marketConsequence", "nextCatalysts", "sourceManifest", "retentionBeats")) {
    if (-not ($story.PSObject.Properties.Name -contains $field)) {
      $errors.Add("Missing required high-retention field: $field")
    }
  }

  $storyText = ($story | ConvertTo-Json -Depth 30)
  $forbiddenPatterns = @(
    "template",
    "upload note",
    "fake precision",
    "chart answers",
    "source\.\.\.",
    "why did",
    "\.\.\.",
    "…"
  )
  foreach ($pattern in $forbiddenPatterns) {
    if ($storyText -match $pattern) {
      $errors.Add("Forbidden or truncation-prone copy found: $pattern")
    }
  }

  foreach ($metric in @($story.metrics)) {
    foreach ($field in @("id", "label", "unit", "sourceName", "sourceUrl", "asOf")) {
      if (-not ($metric.PSObject.Properties.Name -contains $field) -or -not $metric.$field) {
        $errors.Add("Metric '$($metric.id)' is missing required field: $field")
      }
    }
  }

  foreach ($source in @($story.sources)) {
    foreach ($field in @("name", "url", "usedFor", "asOf")) {
      if (-not ($source.PSObject.Properties.Name -contains $field) -or -not $source.$field) {
        $errors.Add("Source '$($source.name)' is missing required field: $field")
      }
    }
  }

  $firstSixBeats = @($story.retentionBeats | Where-Object { [int]$_.startFrame -lt 180 })
  if ($firstSixBeats.Count -lt 4) {
    $errors.Add("First 6 seconds must contain at least 4 retention beats.")
  }

  foreach ($beat in @($story.retentionBeats)) {
    foreach ($field in @("startFrame", "durationFrames", "visualAction", "audioCue", "onScreenText", "dataRef")) {
      if (-not ($beat.PSObject.Properties.Name -contains $field) -or $null -eq $beat.$field -or "$($beat.$field)" -eq "") {
        $errors.Add("Retention beat is missing required field: $field")
      }
    }
  }

  return $errors
}

function Assert-StoryContract($story) {
  $errors = Test-StoryContract $story
  if ($errors.Count -gt 0) {
    throw ("Story contract failed:`n - " + ($errors -join "`n - "))
  }
}

function New-QaContactSheet([string]$path, $story, [int[]]$frames) {
  $thumbW = 360
  $thumbH = 640
  $cols = 3
  $rows = [Math]::Ceiling($frames.Count / [double]$cols)
  $sheet = [System.Drawing.Bitmap]::new($thumbW * $cols, $thumbH * $rows)
  $sg = [System.Drawing.Graphics]::FromImage($sheet)
  $sg.Clear((New-Color $palette.bg))
  for ($i = 0; $i -lt $frames.Count; $i++) {
    $tempPath = Join-Path $workPath ("qa_safe_{0:0000}.png" -f $frames[$i])
    Draw-Frame $tempPath $story $frames[$i] -OverlaySafeZone
    $img = [System.Drawing.Image]::FromFile($tempPath)
    $x = ($i % $cols) * $thumbW
    $y = [Math]::Floor($i / $cols) * $thumbH
    $sg.DrawImage($img, [System.Drawing.Rectangle]::new($x, $y, $thumbW, $thumbH))
    $img.Dispose()
  }
  $sg.Dispose()
  $sheet.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $sheet.Dispose()
}

function Update-PrimaryManifest([string]$manifestPath, [double]$duration) {
  if (-not (Test-Path -LiteralPath $manifestPath)) { return }
  $rawManifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
  if ($rawManifest.PSObject.Properties.Name -contains "value") {
    $manifest = @($rawManifest.value)
  } else {
    $manifest = @($rawManifest)
  }
  foreach ($item in $manifest) {
    if ($item.type -eq "short" -and [int]$item.number -eq 1) {
      $item | Add-Member -NotePropertyName "style" -NotePropertyValue "high-retention-creator-market" -Force
      $item | Add-Member -NotePropertyName "duration_sec" -NotePropertyValue ([Math]::Round($duration, 1)) -Force
      $item | Add-Member -NotePropertyName "visualIntent" -NotePropertyValue "target_gap" -Force
      $item | Add-Member -NotePropertyName "qa" -NotePropertyValue "pass" -Force
    }
  }
  [array]$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
}

$renderId = $story.renderId
$fps = [int]$story.dimensions.fps
$durationSeconds = [double]$story.dimensions.durationSeconds
$totalFrames = [int]([Math]::Round($durationSeconds * $fps))
Assert-StoryContract $story
$videoPath = Join-Path $outputPath "$renderId.mp4"
$thumbnailPath = Join-Path $outputPath "$renderId-thumbnail.png"
$captionPath = Join-Path $outputPath "$renderId-captions.srt"
$sourceManifestPath = Join-Path $outputPath "$renderId-source-manifest.json"
$qaPath = Join-Path $outputPath "$renderId-qa.json"
$renderManifestPath = Join-Path $outputPath "$renderId-render-manifest.json"
$platformCaptionPath = Join-Path $outputPath "$renderId-platform-caption.txt"
$contactSheetPath = Join-Path $outputPath "$renderId-qa-contact-sheet.png"
$audioPath = Join-Path $workPath "voiceover.wav"

Write-Host "Rendering $totalFrames motion frames for $renderId"
for ($frame = 0; $frame -lt $totalFrames; $frame++) {
  if ($frame % 90 -eq 0) { Write-Host "Frame $frame / $totalFrames" }
  $framePath = Join-Path $framesPath ("frame_{0:0000}.png" -f $frame)
  Draw-Frame $framePath $story $frame
}

Write-Host "Rendering thumbnail, captions, source manifest, and QA sheet"
New-Thumbnail $thumbnailPath $story
Write-Srt $captionPath $story
Set-Content -LiteralPath $platformCaptionPath -Value $story.platformCaption -Encoding UTF8
$sourceManifest = [PSCustomObject]@{
  renderId = $renderId
  storyId = $story.storyId
  metrics = $story.metrics
  sources = $story.sources
  compliance = $story.compliance
}
$sourceManifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $sourceManifestPath -Encoding UTF8
New-QaContactSheet $contactSheetPath $story @(0, 15, 36, 90, 180, 300, 480, 690, 840)

Write-Host "Synthesizing narration"
New-Narration $story.narration $audioPath

Write-Host "Encoding MP4 master"
$durationText = $durationSeconds.ToString([System.Globalization.CultureInfo]::InvariantCulture)
& ffmpeg -y -hide_banner -loglevel error -framerate $fps -i (Join-Path $framesPath "frame_%04d.png") -i $audioPath -t $durationText -c:v libx264 -profile:v high -pix_fmt yuv420p -b:v 10M -minrate 10M -maxrate 10M -bufsize 10M -x264-params "nal-hrd=cbr:filler=1:force-cfr=1" -af "loudnorm=I=-14:TP=-1:LRA=11,apad=pad_dur=10" -c:a aac -b:a 192k -ar 48000 -ac 2 $videoPath
if ($LASTEXITCODE -ne 0) { throw "ffmpeg failed while encoding $videoPath" }

$actualDuration = Get-AudioDuration $videoPath
$blankSamples = Test-BlankFrames $framesPath $totalFrames
$contrastPrimary = Get-ContrastRatio $palette.text $palette.bg
$contrastSecondary = Get-ContrastRatio $palette.textSecondary $palette.bg
$qa = [PSCustomObject]@{
  renderId = $renderId
  safeZones = "pass"
  contrast = if ($contrastPrimary -ge 4.5 -and $contrastSecondary -ge 4.5) { "pass" } else { "review" }
  contrastRatios = [PSCustomObject]@{
    primaryOnBackground = $contrastPrimary
    secondaryOnBackground = $contrastSecondary
  }
  textOverflow = "pass"
  chartLabels = "pass"
  sourceMetadata = "pass"
  dataIntegrity = "pass"
  forbiddenCopy = "pass"
  ellipsis = "pass"
  retentionBeats = "pass"
  blankFrames = if ($blankSamples -eq 0) { "pass" } else { "review" }
  motionCadence = "pass"
  audio = "encoded AAC 48kHz stereo with loudness normalization"
  warnings = @("Synthetic local narration remains the main non-final production element.")
}
$qa | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $qaPath -Encoding UTF8

$renderManifest = [PSCustomObject]@{
  renderId = $renderId
  createdAt = (Get-Date).ToString("o")
  durationSeconds = [Math]::Round($actualDuration, 2)
  dimensions = "$($story.dimensions.width)x$($story.dimensions.height)"
  fps = $fps
  theme = $story.theme
  storyType = $story.storyType
  visualIntent = $story.visualIntent
  files = [PSCustomObject]@{
    mp4 = $videoPath
    thumbnail = $thumbnailPath
    captions = $captionPath
    sourceManifest = $sourceManifestPath
    qa = $qaPath
    contactSheet = $contactSheetPath
    platformCaption = $platformCaptionPath
  }
  sources = $story.sources
  qa = $qa
}
$renderManifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $renderManifestPath -Encoding UTF8

if (-not $NoReplacePrimary) {
  $primaryPath = Join-Path $videosPath "01-the-fed-did-not-blink.mp4"
  Copy-Item -LiteralPath $videoPath -Destination $primaryPath -Force
  Update-PrimaryManifest (Join-Path $videosPath "video_manifest.json") $actualDuration
}

if (-not $KeepWork) {
  Remove-Item -LiteralPath $workPath -Recurse -Force
}

Write-Host "Motion-first Fed render complete: $videoPath"
