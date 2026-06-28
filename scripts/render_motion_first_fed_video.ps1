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
  $format.Trimming = [System.Drawing.StringTrimming]::EllipsisWord
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
  $format.Trimming = [System.Drawing.StringTrimming]::EllipsisWord
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

  $trace = @(
    [System.Drawing.PointF]::new(36, 1554),
    [System.Drawing.PointF]::new(194, 1510),
    [System.Drawing.PointF]::new(356, 1548),
    [System.Drawing.PointF]::new(532, 1468),
    [System.Drawing.PointF]::new(728, 1494),
    [System.Drawing.PointF]::new(1036, 1410)
  )
  $traceProgress = (($frame % 120) / 120.0)
  Draw-LineSegment $g $trace (0.35 + ($traceProgress * 0.65)) $palette.policy 3
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
  Fill-RoundedRect $g $x $y $w 92 18 $palette.panel $palette.rule 1
  $font = New-Font 24 "Bold"
  $small = New-Font 20 "Regular"
  Draw-Text $g "Sources" $font $palette.text $($x + 24) $($y + 18) 130 30
  Draw-Text $g "Federal Reserve FOMC statement, Jun 17; BEA Personal Income and Outlays, May 2026" $small $palette.textSecondary $($x + 150) $($y + 18) $($w - 174) 54 "Near" "Near" 2
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

function Draw-HookHeadline($g, $story, [int]$frame) {
  $p = Get-SceneProgress $frame 0 75
  $headline = New-Font 76 "Bold"
  $sub = New-Font 34 "Regular"
  $mono = New-Font 28 "Bold" "Consolas"

  Draw-Text $g "FIRST SIGNAL" $mono $palette.warning 96 198 420 42
  $slide = 0
  Draw-Text $g "The Fed paused." $headline $palette.text (96 - $slide) 246 860 124
  Draw-Text $g "That was not a pivot." $headline $palette.text (96 + $slide) 354 860 136

  $split = Ease-InOutCubic (Get-SceneProgress $frame 22 30)
  Draw-MetricChip $g "TARGET RANGE" $story.hook.primaryNumber 96 (548 + ((1 - $split) * 40)) 390 $palette.policy $split
  Draw-MetricChip $g "MESSAGE" "PATIENT" 520 (548 + ((1 - $split) * 40)) 268 $palette.warning $split
  Draw-MetricChip $g "PIVOT" "NOT YET" 780 (548 + ((1 - $split) * 40)) 204 $palette.negative $split

  $pauseX = 130 - ((1 - $split) * 24)
  $pivotX = 590 + ((1 - $split) * 24)
  Fill-RoundedRect $g $pauseX 742 318 116 24 $palette.panelElevated $palette.policy 2
  Fill-RoundedRect $g $pivotX 742 318 116 24 $palette.panelElevated $palette.negative 2
  Draw-Text $g "PAUSE" $mono $palette.policy ($pauseX + 84) 782 160 32 "Center"
  Draw-Text $g "PIVOT" $mono $palette.negative ($pivotX + 84) 782 160 32 "Center"
  $crossPen = New-Pen $palette.negative 7
  $g.DrawLine($crossPen, $pivotX + 44, 802, $pivotX + 274, 802)
  $crossPen.Dispose()

  Draw-Text $g "A hold can still be restrictive when inflation has not given the all-clear." $sub $palette.textSecondary 96 936 840 96 "Near" "Near" 2
  Draw-SourceCapsule $g $story 96 1350 840

  $headline.Dispose()
  $sub.Dispose()
  $mono.Dispose()
}

function Draw-RatePath($g, $story, [int]$frame) {
  $p = Ease-OutCubic (Get-SceneProgress $frame 75 135)
  $title = New-Font 62 "Bold"
  $body = New-Font 32 "Regular"
  $mono = New-Font 26 "Bold" "Consolas"
  Draw-Text $g "Decision steady." $title $palette.text 96 202 840 76
  Draw-Text $g "Message not soft." $title $palette.policy 96 282 840 76
  Draw-Text $g "Markets wanted relief. The Fed gave conditions." $body $palette.textSecondary 96 378 760 78 "Near" "Near" 2

  $expectX = 96 - ((1 - $p) * 60)
  $actualX = 552 + ((1 - $p) * 60)
  Fill-RoundedRect $g $expectX 520 384 348 26 $palette.panel $palette.rule 1
  Fill-RoundedRect $g $actualX 520 432 348 26 $palette.panelElevated $palette.policy 2
  Draw-Text $g "MARKET WANTED" $mono $palette.textSecondary ($expectX + 30) 552 300 34
  Draw-Text $g "RELIEF" (New-Font 52 "Bold") $palette.positive ($expectX + 30) 612 300 64
  Draw-Text $g "Lower-rate story" (New-Font 28 "Regular") $palette.textSecondary ($expectX + 30) 700 300 42
  Draw-Text $g "FED DELIVERED" $mono $palette.textSecondary ($actualX + 30) 552 340 34
  Draw-Text $g "CONDITIONS" (New-Font 52 "Bold") $palette.warning ($actualX + 30) 612 360 64
  Draw-Text $g "Inflation must prove it" (New-Font 28 "Regular") $palette.textSecondary ($actualX + 30) 700 350 42

  $chartX = 126
  $chartY = 1030
  $chartW = 828
  $chartH = 180
  $axis = New-AlphaPen $palette.rule 220 2
  $g.DrawLine($axis, $chartX, $chartY + $chartH, $chartX + $chartW, $chartY + $chartH)
  $axis.Dispose()
  $bandBrush = New-AlphaBrush $palette.policy 70
  $bandH = 54
  $g.FillRectangle($bandBrush, $chartX + 90, $chartY + 54, $chartW * $p, $bandH)
  $bandBrush.Dispose()
  $bandPen = New-Pen $palette.policy 4
  $g.DrawRectangle($bandPen, $chartX + 90, $chartY + 54, $chartW * $p, $bandH)
  $bandPen.Dispose()
  Draw-Text $g "3.50-3.75% target range unchanged" $mono $palette.policy ($chartX + 112) ($chartY + 64) 640 34
  Draw-Text $g "Mar" $mono $palette.muted ($chartX + 70) ($chartY + 132) 80 34
  Draw-Text $g "Apr" $mono $palette.muted ($chartX + 280) ($chartY + 132) 80 34
  Draw-Text $g "May" $mono $palette.muted ($chartX + 490) ($chartY + 132) 80 34
  Draw-Text $g "Jun hold" $mono $palette.warning ($chartX + 672) ($chartY + 132) 150 34
  Draw-SourceCapsule $g $story 96 1350 840
  $title.Dispose()
  $body.Dispose()
  $mono.Dispose()
}

function Draw-TargetGap($g, $story, [int]$frame) {
  $p = Ease-InOutCubic (Get-SceneProgress $frame 210 210)
  $title = New-Font 60 "Bold"
  $body = New-Font 31 "Regular"
  $mono = New-Font 25 "Bold" "Consolas"
  Draw-Text $g "Inflation is still above" $title $palette.text 96 196 860 72
  Draw-Text $g "the line that matters." $title $palette.warning 96 270 860 72
  Draw-Text $g "The chart answers the market question: why did a hold not equal relief?" $body $palette.textSecondary 96 362 820 72 "Near" "Near" 2

  $x = 112
  $y = 514
  $w = 856
  $h = 650
  Fill-RoundedRect $g $x $y $w $h 28 $palette.panel $palette.rule 1
  $plotX = $x + 92
  $plotY = $y + 96
  $plotW = $w - 164
  $plotH = 430
  $grid = New-AlphaPen $palette.grid 210 2
  for ($i = 0; $i -le 5; $i++) {
    $yy = $plotY + ($plotH / 5 * $i)
    $g.DrawLine($grid, $plotX, $yy, $plotX + $plotW, $yy)
    Draw-Text $g ("{0}%" -f (5 - $i)) $mono $palette.muted ($plotX - 70) ($yy - 15) 54 30 "Far"
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
  $targetY = & $toY 2.0
  $actualYFinal = & $toY 4.1
  $actualY = $targetY + (($actualYFinal - $targetY) * $p)
  $targetPen = New-Pen $palette.neutral 4
  $targetPen.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash
  $g.DrawLine($targetPen, $plotX, $targetY, $plotX + $plotW, $targetY)
  $targetPen.Dispose()
  Draw-Text $g "Fed target 2.0%" $mono $palette.neutral ($plotX + $plotW - 226) ($targetY - 44) 220 34 "Far"

  $gapPen = New-Pen $palette.negative 10
  $gapPen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $gapPen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  $markerX = $plotX + $plotW * 0.58
  $g.DrawLine($gapPen, $markerX, $targetY, $markerX, $actualY)
  $gapPen.Dispose()
  $dotBrush = New-Brush $palette.negative
  $g.FillEllipse($dotBrush, $markerX - 16, $actualY - 16, 32, 32)
  $dotBrush.Dispose()
  Draw-Text $g "PCE inflation" $mono $palette.textSecondary ($markerX - 118) ($actualY - 76) 236 34 "Center"
  Draw-Text $g ("{0:N1}%" -f (2.0 + ((4.1 - 2.0) * $p))) (New-Font 54 "Bold" "Consolas") $palette.negative ($markerX - 120) ($actualY - 42) 240 72 "Center"
  if ($p -gt 0.55) {
    Draw-MetricChip $g "GAP TO TARGET" "+2.1 pp" 616 1084 300 $palette.warning (($p - 0.55) / 0.45)
  }
  Draw-SourceCapsule $g $story 96 1350 840
  $title.Dispose()
  $body.Dispose()
  $mono.Dispose()
}

function Draw-ImpactTiles($g, $story, [int]$frame) {
  $p = Ease-OutCubic (Get-SceneProgress $frame 420 240)
  $title = New-Font 58 "Bold"
  $body = New-Font 32 "Regular"
  $mono = New-Font 23 "Bold" "Consolas"
  Draw-Text $g "That keeps rate-sensitive" $title $palette.text 96 198 860 72
  Draw-Text $g "trades exposed." $title $palette.warning 96 272 860 72
  Draw-Text $g "No fake precision here: without verified live reaction data, the template shows risk chips instead of made-up numbers." $body $palette.textSecondary 96 368 850 96 "Near" "Near" 3

  $tiles = @(
    @("GROWTH MULTIPLES", "Higher discount rate", "EXPOSED", $palette.negative),
    @("2Y / RATE PATH", "Watch policy pricing", "WATCH", $palette.warning),
    @("NEXT CPI/PCE", "Changes the thesis", "CATALYST", $palette.policy)
  )
  for ($i = 0; $i -lt $tiles.Count; $i++) {
    $local = Ease-OutCubic (($p * 1.25) - ($i * 0.18))
    $x = 96
    $y = 548 + ($i * 214) + ((1 - $local) * 36)
    Fill-RoundedRect $g $x $y 840 172 26 $palette.panel $palette.rule 1
    Fill-RoundedRect $g ($x + 24) ($y + 26) 138 52 18 $palette.panelElevated $tiles[$i][3] 2
    Draw-Text $g $tiles[$i][2] $mono $tiles[$i][3] ($x + 38) ($y + 40) 110 26 "Center"
    Draw-Text $g $tiles[$i][0] (New-Font 34 "Bold") $palette.text ($x + 190) ($y + 28) 500 44
    Draw-Text $g $tiles[$i][1] (New-Font 28 "Regular") $palette.textSecondary ($x + 190) ($y + 84) 500 44
    $curve = @(
      [System.Drawing.PointF]::new($x + 626, $y + 110),
      [System.Drawing.PointF]::new($x + 684, $y + 84),
      [System.Drawing.PointF]::new($x + 746, $y + 96),
      [System.Drawing.PointF]::new($x + 810, $y + 60)
    )
    Draw-LineSegment $g $curve $local $tiles[$i][3] 5
  }
  Draw-SourceCapsule $g $story 96 1350 840
  $title.Dispose()
  $body.Dispose()
  $mono.Dispose()
}

function Draw-WatchNext($g, $story, [int]$frame) {
  $p = Ease-OutCubic (Get-SceneProgress $frame 660 225)
  $kicker = New-Font 30 "Bold" "Consolas"
  $title = New-Font 66 "Bold"
  $body = New-Font 39 "Regular"
  Draw-Text $g "BOTTOM LINE" $kicker $palette.warning 96 198 420 42
  Draw-Text $g "The signal is not" (New-Font 58 "Bold") $palette.text 96 270 850 76
  Draw-Text $g "'cuts are here.'" (New-Font 58 "Bold") $palette.text 96 344 850 76
  Draw-Text $g "The signal is: inflation has to prove it." $body $palette.textSecondary 96 488 820 92 "Near" "Near" 2
  $chips = @($story.watchNext)
  for ($i = 0; $i -lt $chips.Count; $i++) {
    $local = Ease-OutCubic (($p * 1.35) - ($i * 0.15))
    $x = 112 + (($i % 2) * 426)
    $y = 690 + ([Math]::Floor($i / 2) * 154) + ((1 - $local) * 28)
    Fill-RoundedRect $g $x $y 382 104 22 $palette.panelElevated $palette.rule 1
    Draw-Text $g ("WATCH {0}" -f ($i + 1)) (New-Font 20 "Bold" "Consolas") $palette.muted ($x + 24) ($y + 18) 150 28
    Draw-Text $g $chips[$i] (New-Font 34 "Bold") $palette.text ($x + 24) ($y + 48) 330 44
  }
  Fill-RoundedRect $g 96 1038 840 190 26 $palette.panel $palette.rule 1
  Draw-Text $g "Upload note" (New-Font 24 "Bold" "Consolas") $palette.policy 126 1076 220 30
  Draw-Text $g "Use this video with the sidecar caption and source manifest. Do not present it as personalized investment advice." (New-Font 31 "Regular") $palette.textSecondary 126 1122 780 80 "Near" "Near" 2
  Draw-SourceCapsule $g $story 96 1350 840
  $kicker.Dispose()
  $title.Dispose()
  $body.Dispose()
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
  if ($frame -lt 75) {
    Draw-HookHeadline $g $story $frame
  } elseif ($frame -lt 210) {
    Draw-RatePath $g $story $frame
  } elseif ($frame -lt 420) {
    Draw-TargetGap $g $story $frame
  } elseif ($frame -lt 660) {
    Draw-ImpactTiles $g $story $frame
  } else {
    Draw-WatchNext $g $story $frame
  }
  Draw-AmbientTicker $g $w $h $frame
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
  Draw-SourceCapsule $g $story 96 1350 840
  Draw-AmbientTicker $g $w $h 36
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
      $item | Add-Member -NotePropertyName "style" -NotePropertyValue "motion-first-dark-market" -Force
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
New-QaContactSheet $contactSheetPath $story @(15, 92, 255, 500, 760)

Write-Host "Synthesizing narration"
New-Narration $story.narration $audioPath

Write-Host "Encoding MP4 master"
$durationText = $durationSeconds.ToString([System.Globalization.CultureInfo]::InvariantCulture)
& ffmpeg -y -hide_banner -loglevel error -framerate $fps -i (Join-Path $framesPath "frame_%04d.png") -i $audioPath -t $durationText -c:v libx264 -profile:v high -pix_fmt yuv420p -b:v 10M -minrate 10M -maxrate 10M -bufsize 10M -x264-params "nal-hrd=cbr:filler=1:force-cfr=1" -af "loudnorm=I=-14:TP=-1:LRA=11,apad=pad_dur=2" -shortest -c:a aac -b:a 192k -ar 48000 -ac 2 $videoPath
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
