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
$workPath = Join-Path $outputPath "_work_pro"
New-Item -ItemType Directory -Force -Path $outputPath, $workPath | Out-Null

$palette = @{
  bg = "#F4EFE4"
  panel = "#FAF7EF"
  panelStrong = "#FFFBF2"
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
  lightRed = "#E07167"
  lightOlive = "#A8C28A"
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
  $fontStyle = [System.Drawing.FontStyle]::$style
  return [System.Drawing.Font]::new($family, $size, $fontStyle, [System.Drawing.GraphicsUnit]::Pixel)
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
  $shadowPath = New-RoundedRectPath ($x + 8) ($y + 10) $w $h $r
  $shadowBrush = New-AlphaBrush "#6D4A32" 18
  $g.FillPath($shadowBrush, $shadowPath)
  $shadowBrush.Dispose()
  $shadowPath.Dispose()

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

function Fill-FlatRoundedRect($g, [float]$x, [float]$y, [float]$w, [float]$h, [float]$r, [string]$fill, [string]$stroke = "", [float]$strokeWidth = 1) {
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
    $lineHeight = $font.GetHeight($g) * 1.13
    $rect.Height = [Math]::Min($h, $lineHeight * $maxLines)
  }
  $g.DrawString($text, $font, $brush, $rect, $format)
  $format.Dispose()
  $brush.Dispose()
}

function Draw-Line($g, [float]$x1, [float]$y1, [float]$x2, [float]$y2, [string]$color, [float]$width = 1) {
  $pen = New-Pen $color $width
  $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  $g.DrawLine($pen, $x1, $y1, $x2, $y2)
  $pen.Dispose()
}

function Draw-BrandTop($g, [int]$w, [int]$h, [string]$section) {
  $brand = New-Font 26 "Bold"
  $meta = New-Font 20 "Bold"
  Draw-Text $g "MARKET SIGNAL STUDIO" $brand $palette.ink 64 46 620 44
  Draw-Text $g "SOURCE-BACKED FINANCE" $meta $palette.muted 64 88 620 36
  Fill-FlatRoundedRect $g ($w - 314) 52 250 48 24 $palette.secondary "" 0
  Draw-Text $g $section $meta $palette.teal ($w - 292) 63 206 30 "Center"
  Draw-Line $g 64 140 ($w - 64) 140 $palette.line 2
  $brand.Dispose()
  $meta.Dispose()
}

function Draw-TickerTape($g, [int]$w, [int]$h, [object[]]$items) {
  $font = New-Font 20 "Bold"
  $y = $h - 76
  Fill-FlatRoundedRect $g 0 $y $w 76 0 "#EFE6D7" "" 0
  $x = 42
  foreach ($item in $items) {
    $label = $item.Label
    $value = $item.Value
    $color = if ($item.Negative) { $palette.red } else { $palette.teal }
    Draw-Text $g $label $font $palette.muted $x ($y + 24) 92 30
    Draw-Text $g $value $font $color ($x + 84) ($y + 24) 160 30
    Draw-Line $g ($x + 236) ($y + 18) ($x + 236) ($y + 58) $palette.line 2
    $x += 270
  }
  $font.Dispose()
}

function Draw-SourceStrip($g, [int]$w, [int]$h, [string]$source) {
  $font = New-Font 18 "Bold"
  Draw-Text $g $source $font $palette.muted 64 ($h - 142) ($w - 128) 36 "Center"
  $font.Dispose()
}

function Draw-Bars($g, [object[]]$data, [float]$x, [float]$y, [float]$w, [float]$h, [string]$title) {
  $titleFont = New-Font 30 "Bold"
  $labelFont = New-Font 18 "Bold"
  $valueFont = New-Font 24 "Bold"
  Draw-Text $g $title $titleFont $palette.ink $x ($y - 48) $w 38
  $gridPen = New-AlphaPen $palette.walnut 40 1
  for ($i = 0; $i -le 4; $i++) {
    $yy = $y + ($h / 4 * $i)
    $g.DrawLine($gridPen, $x, $yy, $x + $w, $yy)
  }
  $gridPen.Dispose()

  $values = @($data | ForEach-Object { [Math]::Abs([double]$_.Value) })
  $max = [Math]::Max(0.1, ($values | Measure-Object -Maximum).Maximum)
  $barGap = 22
  $barW = ($w - ($barGap * ($data.Count - 1))) / $data.Count
  for ($i = 0; $i -lt $data.Count; $i++) {
    $item = $data[$i]
    $value = [double]$item.Value
    $barH = [Math]::Max(8, ([Math]::Abs($value) / $max) * ($h - 78))
    $barX = $x + ($i * ($barW + $barGap))
    $barY = $y + $h - $barH - 52
    $color = if ($item.Color) { $item.Color } elseif ($value -lt 0) { $palette.red } else { $palette.teal }
    Fill-FlatRoundedRect $g $barX $barY $barW $barH 12 $color "" 0
    Draw-Text $g $item.Display $valueFont $color ($barX - 8) ($barY - 38) ($barW + 16) 32 "Center"
    Draw-Text $g $item.Label $labelFont $palette.body ($barX - 8) ($y + $h - 44) ($barW + 16) 46 "Center" "Near" 2
  }
  $titleFont.Dispose()
  $labelFont.Dispose()
  $valueFont.Dispose()
}

function Draw-LineChart($g, [object[]]$data, [float]$x, [float]$y, [float]$w, [float]$h, [string]$title, [string]$accent) {
  $titleFont = New-Font 30 "Bold"
  $labelFont = New-Font 18 "Bold"
  $valueFont = New-Font 24 "Bold"
  Draw-Text $g $title $titleFont $palette.ink $x ($y - 48) $w 38
  $gridPen = New-AlphaPen $palette.walnut 40 1
  for ($i = 0; $i -le 4; $i++) {
    $yy = $y + ($h / 4 * $i)
    $g.DrawLine($gridPen, $x, $yy, $x + $w, $yy)
  }
  $gridPen.Dispose()

  $values = @($data | ForEach-Object { [double]$_.Value })
  $min = [Math]::Min(0, ($values | Measure-Object -Minimum).Minimum)
  $max = [Math]::Max(1, ($values | Measure-Object -Maximum).Maximum)
  $range = [Math]::Max(0.1, $max - $min)
  $points = @()
  for ($i = 0; $i -lt $data.Count; $i++) {
    $px = $x + (($w / [Math]::Max(1, $data.Count - 1)) * $i)
    $py = $y + $h - ((([double]$data[$i].Value - $min) / $range) * ($h - 58)) - 28
    $points += [System.Drawing.PointF]::new($px, $py)
  }
  $fillPath = [System.Drawing.Drawing2D.GraphicsPath]::new()
  $fillPath.AddLine($x, $y + $h, $points[0].X, $points[0].Y)
  for ($i = 1; $i -lt $points.Count; $i++) { $fillPath.AddLine($points[$i - 1], $points[$i]) }
  $fillPath.AddLine($points[-1].X, $points[-1].Y, $x + $w, $y + $h)
  $fillPath.CloseFigure()
  $areaBrush = New-AlphaBrush $accent 45
  $g.FillPath($areaBrush, $fillPath)
  $areaBrush.Dispose()
  $fillPath.Dispose()

  $pen = New-Pen $accent 6
  $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
  $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
  if ($points.Count -gt 1) { $g.DrawLines($pen, $points) }
  $pen.Dispose()
  $dotBrush = New-Brush $accent
  foreach ($point in $points) { $g.FillEllipse($dotBrush, $point.X - 7, $point.Y - 7, 14, 14) }
  $dotBrush.Dispose()

  for ($i = 0; $i -lt $data.Count; $i++) {
    Draw-Text $g $data[$i].Label $labelFont $palette.muted ($points[$i].X - 54) ($y + $h + 8) 108 26 "Center"
  }
  Draw-Text $g $data[-1].Display $valueFont $accent ($points[-1].X - 100) ($points[-1].Y - 46) 200 34 "Center"
  $titleFont.Dispose()
  $labelFont.Dispose()
  $valueFont.Dispose()
}

function Draw-DividerMetric($g, [string]$metric, [string]$label, [float]$x, [float]$y, [float]$w, [float]$h, [string]$accent) {
  Fill-RoundedRect $g $x $y $w $h 24 $palette.panelStrong $palette.line 1
  $metricFont = New-Font 64 "Bold"
  $labelFont = New-Font 22 "Bold"
  Draw-Text $g $metric $metricFont $accent ($x + 24) ($y + 30) ($w - 48) 82 "Center"
  Draw-Text $g $label $labelFont $palette.muted ($x + 28) ($y + 118) ($w - 56) 56 "Center" "Near" 2
  $metricFont.Dispose()
  $labelFont.Dispose()
}

function Draw-Bullets($g, [string[]]$bullets, [float]$x, [float]$y, [float]$w, [string]$accent) {
  $font = New-Font 34 "Regular"
  $numFont = New-Font 22 "Bold"
  $lineY = $y
  for ($i = 0; $i -lt $bullets.Count; $i++) {
    Fill-FlatRoundedRect $g $x ($lineY + 2) 40 40 20 $accent "" 0
    Draw-Text $g ("{0}" -f ($i + 1)) $numFont $palette.panel ($x + 5) ($lineY + 8) 30 30 "Center"
    Draw-Text $g $bullets[$i] $font $palette.body ($x + 62) $lineY ($w - 62) 86 "Near" "Near" 2
    $lineY += 104
  }
  $font.Dispose()
  $numFont.Dispose()
}

function Draw-CompactBullets($g, [string[]]$bullets, [float]$x, [float]$y, [float]$w, [string]$accent) {
  $font = New-Font 23 "Regular"
  $numFont = New-Font 16 "Bold"
  $lineY = $y
  for ($i = 0; $i -lt $bullets.Count; $i++) {
    Fill-FlatRoundedRect $g $x ($lineY + 4) 30 30 15 $accent "" 0
    Draw-Text $g ("{0}" -f ($i + 1)) $numFont $palette.panel ($x + 4) ($lineY + 8) 22 20 "Center"
    Draw-Text $g $bullets[$i] $font $palette.body ($x + 48) $lineY ($w - 48) 42 "Near" "Near" 1
    $lineY += 52
  }
  $font.Dispose()
  $numFont.Dispose()
}

function Draw-Illustration($g, [string]$kind, [float]$x, [float]$y, [float]$w, [float]$h, [string]$accent) {
  Fill-RoundedRect $g $x $y $w $h 28 $palette.secondary "" 0
  $inkPen = New-Pen $palette.ink 4
  $mutedPen = New-AlphaPen $palette.walnut 95 3
  $accentPen = New-Pen $accent 6
  $accentBrush = New-Brush $accent
  $paperBrush = New-Brush $palette.panelStrong
  $mutedBrush = New-AlphaBrush $palette.walnut 70
  $lineFont = New-Font 20 "Bold"
  $bigFont = New-Font 34 "Bold"

  switch ($kind) {
    "fed" {
      $roof = @(
        [System.Drawing.PointF]::new($x + $w * .18, $y + $h * .36),
        [System.Drawing.PointF]::new($x + $w * .50, $y + $h * .18),
        [System.Drawing.PointF]::new($x + $w * .82, $y + $h * .36)
      )
      $g.FillPolygon($paperBrush, $roof)
      $g.DrawPolygon($inkPen, $roof)
      for ($i = 0; $i -lt 5; $i++) {
        $cx = $x + $w * .24 + ($i * $w * .13)
        Fill-FlatRoundedRect $g $cx ($y + $h * .42) ($w * .065) ($h * .30) 8 $palette.panelStrong $palette.ink 2
      }
      Fill-FlatRoundedRect $g ($x + $w * .17) ($y + $h * .76) ($w * .66) ($h * .09) 8 $palette.panelStrong $palette.ink 2
      Draw-Text $g "3.50-3.75%" $bigFont $accent ($x + $w * .20) ($y + $h * .86) ($w * .60) 46 "Center"
    }
    "consumer" {
      Fill-FlatRoundedRect $g ($x + $w * .18) ($y + $h * .18) ($w * .28) ($h * .62) 16 $palette.panelStrong $palette.ink 2
      for ($i = 0; $i -lt 6; $i++) {
        Draw-Line $g ($x + $w * .22) ($y + $h * (.28 + .07 * $i)) ($x + $w * .41) ($y + $h * (.28 + .07 * $i)) $palette.line 3
      }
      Fill-FlatRoundedRect $g ($x + $w * .55) ($y + $h * .34) ($w * .26) ($h * .34) 14 "#FBEFD5" $palette.ink 2
      Draw-Line $g ($x + $w * .60) ($y + $h * .34) ($x + $w * .64) ($y + $h * .23) $palette.ink 3
      Draw-Line $g ($x + $w * .76) ($y + $h * .34) ($x + $w * .72) ($y + $h * .23) $palette.ink 3
      Draw-Text $g "+0.7%" $bigFont $accent ($x + $w * .52) ($y + $h * .72) ($w * .34) 48 "Center"
    }
    "energy" {
      Fill-FlatRoundedRect $g ($x + $w * .18) ($y + $h * .22) ($w * .32) ($h * .58) 18 $palette.panelStrong $palette.ink 3
      Fill-FlatRoundedRect $g ($x + $w * .23) ($y + $h * .29) ($w * .22) ($h * .14) 8 $palette.secondary $palette.ink 2
      Draw-Line $g ($x + $w * .50) ($y + $h * .40) ($x + $w * .70) ($y + $h * .55) $palette.ink 4
      Draw-Line $g ($x + $w * .70) ($y + $h * .55) ($x + $w * .70) ($y + $h * .72) $palette.ink 4
      $g.FillEllipse($accentBrush, $x + $w * .62, $y + $h * .20, $w * .22, $w * .22)
      Draw-Text $g "+7.0%" $bigFont $palette.panel ($x + $w * .60) ($y + $h * .245) ($w * .26) 48 "Center"
    }
    "jobs" {
      for ($i = 0; $i -lt 5; $i++) {
        $bx = $x + $w * (.16 + .13 * $i)
        $bh = $h * (.23 + .06 * $i)
        Fill-FlatRoundedRect $g $bx ($y + $h * .72 - $bh) ($w * .09) $bh 6 $palette.panelStrong $palette.ink 2
      }
      $g.FillEllipse($accentBrush, $x + $w * .68, $y + $h * .25, $w * .12, $w * .12)
      Draw-Line $g ($x + $w * .74) ($y + $h * .38) ($x + $w * .74) ($y + $h * .62) $accent 7
      Draw-Line $g ($x + $w * .66) ($y + $h * .48) ($x + $w * .82) ($y + $h * .48) $accent 6
      Draw-Text $g "+172K" $bigFont $accent ($x + $w * .54) ($y + $h * .70) ($w * .38) 54 "Center"
    }
    "ai" {
      Fill-FlatRoundedRect $g ($x + $w * .18) ($y + $h * .22) ($w * .42) ($h * .46) 22 $palette.panelStrong $palette.ink 3
      for ($i = 0; $i -lt 5; $i++) {
        Draw-Line $g ($x + $w * (.20 + .08 * $i)) ($y + $h * .18) ($x + $w * (.20 + .08 * $i)) ($y + $h * .10) $palette.ink 3
        Draw-Line $g ($x + $w * (.20 + .08 * $i)) ($y + $h * .70) ($x + $w * (.20 + .08 * $i)) ($y + $h * .80) $palette.ink 3
      }
      for ($r = 0; $r -lt 3; $r++) {
        for ($c = 0; $c -lt 3; $c++) {
          $g.FillEllipse($accentBrush, $x + $w * (.27 + .09 * $c), $y + $h * (.33 + .09 * $r), 12, 12)
        }
      }
      Fill-FlatRoundedRect $g ($x + $w * .68) ($y + $h * .22) ($w * .14) ($h * .56) 10 $palette.panelStrong $palette.ink 2
      for ($i = 0; $i -lt 5; $i++) { Draw-Line $g ($x + $w * .70) ($y + $h * (.30 + .08 * $i)) ($x + $w * .80) ($y + $h * (.30 + .08 * $i)) $accent 3 }
      Draw-Text $g "AI CAPEX" $lineFont $palette.muted ($x + $w * .22) ($y + $h * .73) ($w * .56) 30 "Center"
    }
    default {
      $points = @(
        [System.Drawing.PointF]::new($x + $w * .12, $y + $h * .64),
        [System.Drawing.PointF]::new($x + $w * .30, $y + $h * .48),
        [System.Drawing.PointF]::new($x + $w * .46, $y + $h * .55),
        [System.Drawing.PointF]::new($x + $w * .64, $y + $h * .30),
        [System.Drawing.PointF]::new($x + $w * .86, $y + $h * .38)
      )
      $g.DrawLines($accentPen, $points)
      Draw-Text $g "SIGNAL MAP" $bigFont $accent ($x + $w * .18) ($y + $h * .72) ($w * .64) 48 "Center"
    }
  }

  $inkPen.Dispose()
  $mutedPen.Dispose()
  $accentPen.Dispose()
  $accentBrush.Dispose()
  $paperBrush.Dispose()
  $mutedBrush.Dispose()
  $lineFont.Dispose()
  $bigFont.Dispose()
}

function New-ProShortSlide([string]$path, $spec, [string]$scene) {
  $w = 1080
  $h = 1920
  $bitmap = [System.Drawing.Bitmap]::new($w, $h)
  $g = [System.Drawing.Graphics]::FromImage($bitmap)
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
  $g.Clear((New-Color $palette.bg))

  Draw-BrandTop $g $w $h $spec.Category
  $ticker = @(
    [PSCustomObject]@{ Label = "PCE"; Value = "+4.1%"; Negative = $true },
    [PSCustomObject]@{ Label = "FED"; Value = "HOLD"; Negative = $false },
    [PSCustomObject]@{ Label = "AI"; Value = "REAL"; Negative = $false },
    [PSCustomObject]@{ Label = "RISK"; Value = "RATES"; Negative = $true }
  )
  Draw-TickerTape $g $w $h $ticker

  $accent = $spec.Accent
  switch ($scene) {
    "hook" {
      $eyebrow = New-Font 24 "Bold"
      $hero = New-Font 92 "Bold"
      $deck = New-Font 38 "Regular"
      $metric = New-Font 78 "Bold"
      $metricLabel = New-Font 22 "Bold"
      Draw-Text $g "THE TAKEAWAY IN ONE SCREEN" $eyebrow $palette.red 64 192 680 38
      Draw-Text $g $spec.Eye $hero $palette.ink 64 250 952 300 "Near" "Near" 3
      Fill-FlatRoundedRect $g 64 610 8 180 4 $accent "" 0
      Draw-Text $g $spec.Deck $deck $palette.body 96 610 760 170 "Near" "Near" 3
      Draw-DividerMetric $g $spec.BigMetric $spec.BigMetricLabel 610 820 356 214 $accent
      Draw-Illustration $g $spec.Picture 92 1112 896 456 $accent
      Draw-SourceStrip $g $w $h $spec.Source
      $eyebrow.Dispose(); $hero.Dispose(); $deck.Dispose(); $metric.Dispose(); $metricLabel.Dispose()
    }
    "chart" {
      $title = New-Font 58 "Bold"
      $body = New-Font 32 "Regular"
      Draw-Text $g "THE DATA" $title $palette.ink 64 196 460 70
      Draw-Text $g $spec.ChartLead $body $palette.body 64 268 880 96 "Near" "Near" 2
      Fill-RoundedRect $g 64 424 952 640 26 $palette.panelStrong $palette.line 1
      if ($spec.ChartType -eq "line") {
        Draw-LineChart $g $spec.ChartData 118 548 844 360 $spec.ChartTitle $accent
      } else {
        Draw-Bars $g $spec.ChartData 118 548 844 360 $spec.ChartTitle
      }
      Fill-FlatRoundedRect $g 94 1140 892 200 24 "#FBEFD5" "" 0
      Draw-Text $g $spec.ChartRead $body $palette.body 130 1178 820 126 "Near" "Near" 3
      Draw-SourceStrip $g $w $h $spec.Source
      $title.Dispose(); $body.Dispose()
    }
    "evidence" {
      $title = New-Font 54 "Bold"
      $body = New-Font 30 "Regular"
      Draw-Text $g "WHY IT MATTERS" $title $palette.ink 64 196 760 72
      Draw-Text $g $spec.Context $body $palette.body 64 276 880 104 "Near" "Near" 2
      Draw-Illustration $g $spec.Picture 82 438 916 504 $accent
      Draw-Bullets $g $spec.Bullets 98 1036 860 $accent
      Draw-SourceStrip $g $w $h $spec.Source
      $title.Dispose(); $body.Dispose()
    }
    "bottom" {
      $kicker = New-Font 28 "Bold"
      $title = New-Font 62 "Bold"
      $body = New-Font 36 "Regular"
      Draw-Text $g "BOTTOM LINE" $kicker $palette.red 64 196 420 42
      Draw-Text $g $spec.BottomLine $title $palette.ink 64 256 930 310 "Near" "Near" 4
      Fill-RoundedRect $g 80 594 920 312 28 $palette.panelStrong $palette.line 1
      Draw-Text $g $spec.FinalRead $body $palette.body 120 650 840 188 "Near" "Near" 4
      Fill-FlatRoundedRect $g 100 1008 880 288 24 $palette.secondary "" 0
      Draw-Bullets $g $spec.Watch 132 1056 806 $palette.teal
      Draw-SourceStrip $g $w $h "Not investment advice. Verify final figures and rights before publishing."
      $kicker.Dispose(); $title.Dispose(); $body.Dispose()
    }
  }

  $g.Dispose()
  $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $bitmap.Dispose()
}

function New-ProLongSlide([string]$path, $scene) {
  $w = 1280
  $h = 720
  $bitmap = [System.Drawing.Bitmap]::new($w, $h)
  $g = [System.Drawing.Graphics]::FromImage($bitmap)
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
  $g.Clear((New-Color $palette.bg))

  Draw-BrandTop $g $w $h $scene.Section
  $title = New-Font 38 "Bold"
  $body = New-Font 23 "Regular"
  $kicker = New-Font 21 "Bold"
  Draw-Text $g $scene.Title $title $palette.ink 64 152 606 128 "Near" "Near" 2
  Draw-Text $g $scene.Copy $body $palette.body 66 298 536 116 "Near" "Near" 4
  Draw-CompactBullets $g $scene.Bullets 66 450 520 $scene.Accent
  Fill-RoundedRect $g 680 176 540 396 24 $palette.panelStrong $palette.line 1
  if ($scene.ChartType -eq "line") {
    Draw-LineChart $g $scene.ChartData 722 278 456 216 $scene.ChartTitle $scene.Accent
  } else {
    Draw-Bars $g $scene.ChartData 722 278 456 216 $scene.ChartTitle
  }
  Draw-Text $g $scene.Source $kicker $palette.muted 680 600 540 34 "Center"
  $title.Dispose()
  $body.Dispose()
  $kicker.Dispose()
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

function Get-AudioDuration([string]$path) {
  $raw = & ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $path
  return [double]::Parse($raw.Trim(), [System.Globalization.CultureInfo]::InvariantCulture)
}

function Render-SlideClip([string]$slidePath, [string]$clipPath, [double]$duration, [int]$width, [int]$height, [string]$motion) {
  $fps = 30
  $frames = [Math]::Max(60, [Math]::Ceiling($duration * $fps))
  $fadeOutStart = [Math]::Max(0.1, $duration - 0.24).ToString([System.Globalization.CultureInfo]::InvariantCulture)
  $durationText = $duration.ToString([System.Globalization.CultureInfo]::InvariantCulture)
  $progress = "on/$frames"
  $xExpr = "iw/2-(iw/zoom/2)"
  $yExpr = "ih/2-(ih/zoom/2)"
  if ($motion -eq "right") {
    $xExpr = "(iw-iw/zoom)*$progress"
  } elseif ($motion -eq "left") {
    $xExpr = "(iw-iw/zoom)*(1-$progress)"
  } elseif ($motion -eq "up") {
    $yExpr = "(ih-ih/zoom)*(1-$progress)"
  } elseif ($motion -eq "down") {
    $yExpr = "(ih-ih/zoom)*$progress"
  }
  $vf = "zoompan=z='min(1.055,1+0.055*$progress)':x='$xExpr':y='$yExpr':d=${frames}:s=${width}x${height}:fps=${fps},fade=t=in:st=0:d=0.16,fade=t=out:st=${fadeOutStart}:d=0.22,format=yuv420p"
  & ffmpeg -y -hide_banner -loglevel error -loop 1 -i $slidePath -vf $vf -t $durationText -frames:v $frames -an -c:v libx264 -preset veryfast -crf 19 -pix_fmt yuv420p $clipPath
  if ($LASTEXITCODE -ne 0) { throw "ffmpeg failed creating clip $clipPath" }
}

function Join-ClipsWithAudio([string[]]$clips, [string]$audioPath, [string]$outputPath) {
  $concatPath = Join-Path (Split-Path $outputPath -Parent) (([System.IO.Path]::GetFileNameWithoutExtension($outputPath)) + ".concat.txt")
  $lines = New-Object System.Collections.Generic.List[string]
  foreach ($clip in $clips) {
    $safe = $clip.Replace("\", "/").Replace("'", "'\''")
    $lines.Add("file '$safe'")
  }
  $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
  [System.IO.File]::WriteAllLines($concatPath, [string[]]$lines, $utf8NoBom)
  & ffmpeg -y -hide_banner -loglevel error -f concat -safe 0 -i $concatPath -i $audioPath -map 0:v -map 1:a -c:v copy -af "apad=pad_dur=0.9" -shortest -c:a aac -b:a 128k $outputPath
  if ($LASTEXITCODE -ne 0) { throw "ffmpeg failed joining $outputPath" }
}

function New-ChartItem([string]$label, [double]$value, [string]$display, [string]$color = "") {
  return [PSCustomObject]@{ Label = $label; Value = $value; Display = $display; Color = $color }
}

function Get-ProSpecs {
  return @(
    [PSCustomObject]@{
      Number = 1
      Title = "The Fed Did Not Blink"
      Category = "FED WATCH"
      Eye = "PAUSE IS NOT PIVOT"
      Deck = "A hold can still be a restrictive message when inflation is above target."
      BigMetric = "3.50-3.75%"
      BigMetricLabel = "target range stayed put"
      Accent = $palette.teal
      Picture = "fed"
      ChartType = "line"
      ChartTitle = "Fed rate backdrop"
      ChartLead = "The market wanted relief. The statement gave patience."
      ChartRead = "Solid activity plus elevated inflation gives the Fed permission to wait."
      ChartData = @(
        (New-ChartItem "Mar" 3.625 "3.625%" $palette.teal),
        (New-ChartItem "Apr" 3.625 "3.625%" $palette.teal),
        (New-ChartItem "May" 3.625 "3.625%" $palette.teal),
        (New-ChartItem "Jun" 3.625 "hold" $palette.red)
      )
      Context = "This is the nuance quick recaps miss: a pause can remove urgency without creating an all-clear."
      Bullets = @("Inflation still above the 2 percent goal.", "Solid activity means no rescue cut pressure.", "High-growth valuation stays rate-sensitive.")
      BottomLine = "The hold was not the gift markets wanted."
      FinalRead = "The signal is not 'cuts are here.' The signal is: inflation has to prove it."
      Watch = @("Next inflation print", "Fed language around risk", "Rate-sensitive growth stocks")
      Source = "Source: Federal Reserve, June 17 FOMC statement"
      Narration = "The Fed did not blink. The target range stayed at 3.50 to 3.75 percent, but the real message was patience. The statement still described solid activity, stable jobs, and inflation above the 2 percent goal. That combination does not force rescue cuts. It lets the Fed wait. For markets, especially long-duration growth stocks, that matters. A pause is not automatically a pivot. This one says: prove inflation is cooling first. Not investment advice."
    },
    [PSCustomObject]@{
      Number = 2
      Title = "The Inflation Number Everyone Missed"
      Category = "INFLATION"
      Eye = "DEMAND DID NOT BREAK"
      Deck = "The awkward part of PCE was not only inflation. Consumers were still spending."
      BigMetric = "+0.7%"
      BigMetricLabel = "income and spending in May"
      Accent = $palette.amber
      Picture = "consumer"
      ChartType = "bar"
      ChartTitle = "May PCE: inflation plus demand"
      ChartLead = "Hot inflation is harder to dismiss when demand still has a pulse."
      ChartRead = "Income and spending both rose 0.7 percent. Real spending still rose after inflation."
      ChartData = @(
        (New-ChartItem "Income" 0.7 "+0.7%" $palette.teal),
        (New-ChartItem "Spend" 0.7 "+0.7%" $palette.amber),
        (New-ChartItem "Real PCE" 0.3 "+0.3%" $palette.olive),
        (New-ChartItem "PCE YoY" 4.1 "+4.1%" $palette.red)
      )
      Context = "The market wants a clean slowdown. The data showed inflation and resilient demand in the same report."
      Bullets = @("Income rose, spending rose, and real PCE rose.", "That does not scream emergency slowdown.", "It keeps rate-cut confidence harder to defend.")
      BottomLine = "Sticky prices plus spending is the uncomfortable mix."
      FinalRead = "Inflation alone is one problem. Inflation with resilient demand is why the Fed can stay patient."
      Watch = @("Core PCE trend", "Real consumer spending", "Next Fed inflation language")
      Source = "Source: BEA Personal Income and Outlays, May 2026"
      Narration = "The market saw the PCE inflation number. The missed part was demand. Personal income rose 0.7 percent, spending rose 0.7 percent, and real PCE still rose after inflation. At the same time, the PCE price index was up 4.1 percent from a year earlier. That is not a clean slowdown story. It is inflation with a consumer that still has a pulse. That is why rate-cut confidence got harder to defend. Not investment advice."
    },
    [PSCustomObject]@{
      Number = 3
      Title = "Core CPI Looked Better. Energy Did Not."
      Category = "CPI SPLIT"
      Eye = "CORE CALMED. ENERGY SPIKED."
      Deck = "Markets can talk core. Households still feel headline inflation."
      BigMetric = "+23.5%"
      BigMetricLabel = "energy CPI over the year"
      Accent = $palette.red
      Picture = "energy"
      ChartType = "bar"
      ChartTitle = "May CPI split"
      ChartLead = "The soft core print came with a much louder energy line."
      ChartRead = "Core looked better, but energy and gasoline are what consumers feel fastest."
      ChartData = @(
        (New-ChartItem "Core YoY" 2.9 "+2.9%" $palette.teal),
        (New-ChartItem "CPI YoY" 4.2 "+4.2%" $palette.amber),
        (New-ChartItem "Gas MoM" 7.0 "+7.0%" $palette.red),
        (New-ChartItem "Energy YoY" 23.5 "+23.5%" $palette.red)
      )
      Context = "Energy volatility matters because it can shape confidence and inflation psychology."
      Bullets = @("Core CPI rose 0.2 percent in May.", "Headline CPI still rose 4.2 percent over the year.", "Energy was the pressure point.")
      BottomLine = "The inflation debate is not over just because core looked calmer."
      FinalRead = "The Fed watches core. Consumers live inside headline inflation."
      Watch = @("Gasoline prices", "Energy pass-through", "Core services")
      Source = "Source: BLS Consumer Price Index, May 2026"
      Narration = "Core CPI looked calmer. Energy did not. May CPI rose 4.2 percent from a year earlier, while core CPI was up 2.9 percent. That looks like progress, until you look at energy. Energy rose 23.5 percent over the year, and gasoline rose 7 percent in the month. Markets like to focus on core, but consumers feel gasoline, utilities, and travel. That is why headline pressure still matters. Not investment advice."
    },
    [PSCustomObject]@{
      Number = 4
      Title = "Jobs Are Not Weak Enough For Rescue Cuts"
      Category = "LABOR"
      Eye = "STABLE JOBS, PATIENT FED"
      Deck = "The jobs report was not hot. It was inconvenient for easy-policy hopes."
      BigMetric = "+172K"
      BigMetricLabel = "payroll gain in May"
      Accent = $palette.olive
      Picture = "jobs"
      ChartType = "bar"
      ChartTitle = "Where the May jobs came from"
      ChartLead = "The labor market was stable enough to keep the waiting game alive."
      ChartRead = "Several sectors added jobs, while financial activities showed a crack."
      ChartData = @(
        (New-ChartItem "Payrolls" 172 "+172K" $palette.olive),
        (New-ChartItem "Leisure" 70 "+70K" $palette.teal),
        (New-ChartItem "Govt." 55 "+55K" $palette.amber),
        (New-ChartItem "Finance" -22 "-22K" $palette.red)
      )
      Context = "Stable labor data can be good for the economy and uncomfortable for rate-cut hopes."
      Bullets = @("Unemployment held at 4.3 percent.", "Payroll growth did not force a panic response.", "The Fed can wait for more inflation evidence.")
      BottomLine = "Good enough jobs can be bad for rescue-cut hopes."
      FinalRead = "This report did not force easier policy. It kept the Fed's patience intact."
      Watch = @("Payroll trend", "Unemployment drift", "Wage growth")
      Source = "Source: BLS Employment Situation, May 2026"
      Narration = "The jobs report was not hot. It was inconvenient. Payrolls rose by 172,000, and unemployment held at 4.3 percent. That is not a boom, but it is not a collapse either. Leisure, local government, and health care added jobs. Financial activities lost jobs. The big market point is simple: stable labor does not force the Fed to rescue risk assets. It keeps the waiting game alive. Not investment advice."
    },
    [PSCustomObject]@{
      Number = 5
      Title = "AI Demand Is Real. The Multiple Is The Question."
      Category = "AI VALUATION"
      Eye = "AI DEMAND IS REAL"
      Deck = "The business story is powerful. The stock question is what investors pay for it."
      BigMetric = '$81.6B'
      BigMetricLabel = "NVIDIA Q1 FY2027 revenue"
      Accent = $palette.teal
      Picture = "ai"
      ChartType = "bar"
      ChartTitle = "AI infrastructure demand"
      ChartLead = "The demand story is not the weak part. Valuation is the harder question."
      ChartRead = "NVIDIA and Micron both point to major AI infrastructure spending."
      ChartData = @(
        (New-ChartItem "NVDA Rev" 81.6 '$81.6B' $palette.teal),
        (New-ChartItem "Data Ctr" 75.2 '$75.2B' $palette.ceramicTeal),
        (New-ChartItem "Growth" 92 "+92%" $palette.olive),
        (New-ChartItem "MU Guide" 50 '$50B' $palette.amber)
      )
      Context = "A great business can still get repriced when rates change what investors are willing to pay."
      Bullets = @("NVIDIA revenue rose 85 percent year over year.", "Data Center revenue rose 92 percent.", "Higher rates still pressure future growth multiples.")
      BottomLine = "The market can believe in AI and still reprice AI stocks."
      FinalRead = "Demand is real. The multiple is where the fight is."
      Watch = @("AI capex commentary", "Gross margin durability", "Rate expectations")
      Source = "Sources: NVIDIA financial reports; Micron Q3 FY2026 results"
      Narration = "AI demand is not the weak part of the story. NVIDIA reported Q1 fiscal 2027 revenue of 81.6 billion dollars, up 85 percent from a year earlier. Data Center revenue was 75.2 billion, up 92 percent. Micron also pointed to huge AI memory demand. The question is valuation. When inflation stays firm and the Fed stays patient, future growth faces a higher discount rate. Demand can be real and the multiple can still be challenged. Not investment advice."
    },
    [PSCustomObject]@{
      Number = 6
      Title = "The Market Is Fighting Three Stories"
      Category = "MARKET MAP"
      Eye = "THREE STORIES COLLIDE"
      Deck = "Inflation is real. Fed patience is real. AI demand is real."
      BigMetric = "3"
      BigMetricLabel = "forces moving the tape"
      Accent = $palette.walnut
      Picture = "market"
      ChartType = "bar"
      ChartTitle = "The collision"
      ChartLead = "The market is not fighting one narrative. It is pricing a collision."
      ChartRead = "Each story is strong enough to matter, but none gives a clean all-clear."
      ChartData = @(
        (New-ChartItem "PCE YoY" 4.1 "+4.1%" $palette.red),
        (New-ChartItem "CPI YoY" 4.2 "+4.2%" $palette.red),
        (New-ChartItem "Fed" 3.625 "hold" $palette.teal),
        (New-ChartItem "AI Rev" 81.6 '$81.6B' $palette.amber)
      )
      Context = "The best question is not which headline wins today. It is how the stories collide."
      Bullets = @("Inflation argues for patience.", "Jobs do not force rescue cuts.", "AI growth keeps risk appetite alive.")
      BottomLine = "The messy feeling is the story."
      FinalRead = "Growth, inflation, and rate pressure can all be true at the same time."
      Watch = @("Inflation", "Fed patience", "AI capex")
      Source = "Sources: BEA, BLS, Federal Reserve, NVIDIA, Micron"
      Narration = "This market is not fighting one story. It is fighting three. Inflation is still too firm. The Fed can wait. AI demand is still powerful. That is why the tape feels messy. Growth is real, inflation is real, and rate pressure is real. The better question is not which story wins today. It is how they collide. Not investment advice."
    },
    [PSCustomObject]@{
      Number = 7
      Title = "The Pause Is Not The Pivot"
      Category = "FED WATCH"
      Eye = "THE HOLD WAS THE MESSAGE"
      Deck = "The Fed held, but the burden of proof stayed on inflation."
      BigMetric = "2%"
      BigMetricLabel = "inflation goal still not met"
      Accent = $palette.teal
      Picture = "fed"
      ChartType = "line"
      ChartTitle = "Pause without pivot"
      ChartLead = "A hold does not automatically mean cuts are next."
      ChartRead = "The June statement kept inflation risk front and center."
      ChartData = @(
        (New-ChartItem "Goal" 2.0 "2%" $palette.olive),
        (New-ChartItem "Core" 2.9 "+2.9%" $palette.amber),
        (New-ChartItem "PCE" 4.1 "+4.1%" $palette.red),
        (New-ChartItem "CPI" 4.2 "+4.2%" $palette.red)
      )
      Context = "Markets often want a hold to mean easier policy. This statement asked for proof."
      Bullets = @("Economic activity was described as solid.", "Inflation remained elevated.", "The Fed can wait instead of chase.")
      BottomLine = "Pause is not pivot."
      FinalRead = "The all-clear did not arrive. The burden of proof stayed with inflation."
      Watch = @("Inflation proof", "FOMC language", "Rate-cut pricing")
      Source = "Sources: Federal Reserve; BLS; BEA"
      Narration = "A Fed pause is not automatically a pivot. The Fed held rates steady, but the statement still said inflation remained elevated relative to the 2 percent goal. It also described economic activity as solid. That is not the language of a central bank rushing to ease. It is the language of a central bank that can wait. Pause is not pivot. That is the signal. Not investment advice."
    },
    [PSCustomObject]@{
      Number = 8
      Title = "Why Tech Felt The Pressure"
      Category = "TECH + RATES"
      Eye = "GROWTH STILL HAS A PRICE"
      Deck = "Great demand does not cancel the math of higher discount rates."
      BigMetric = "RATES"
      BigMetricLabel = "change what future earnings are worth"
      Accent = $palette.amber
      Picture = "market"
      ChartType = "line"
      ChartTitle = "Rate math for future growth"
      ChartLead = "Tech can feel pressure even when the business story is intact."
      ChartRead = "When rates stay firm, future earnings are discounted more heavily today."
      ChartData = @(
        (New-ChartItem "Lower" 100 "100" $palette.teal),
        (New-ChartItem "Mid" 86 "86" $palette.amber),
        (New-ChartItem "Firm" 74 "74" $palette.red),
        (New-ChartItem "Higher" 66 "66" $palette.red)
      )
      Context = "The market is asking what price it should pay for growth, not only whether growth exists."
      Bullets = @("AI demand can be strong.", "Valuation can still compress.", "Rate expectations change the price investors accept.")
      BottomLine = "Strong growth does not erase valuation risk."
      FinalRead = "The question is not just whether AI grows. It is what multiple the market will pay."
      Watch = @("Yields", "Earnings revisions", "AI capex durability")
      Source = "Editorial model based on discount-rate mechanics"
      Narration = "Tech did not need bad news to feel pressure. High-growth stocks are sensitive to the rate backdrop. When investors expect easier policy, future earnings look more valuable today. When inflation stays hot and the Fed stays patient, that math gets harder. So AI demand can be strong and the stocks can still get more volatile. The question is not only: will AI grow? It is: what price should the market pay for that growth? Not investment advice."
    },
    [PSCustomObject]@{
      Number = 9
      Title = "The Energy Trap"
      Category = "ENERGY"
      Eye = "ENERGY IS THE TRAP"
      Deck = "The market can ignore energy for a while. Consumers cannot."
      BigMetric = "+7.0%"
      BigMetricLabel = "gasoline in May"
      Accent = $palette.red
      Picture = "energy"
      ChartType = "bar"
      ChartTitle = "Energy pressure"
      ChartLead = "Core inflation can look calmer while headline pressure gets louder."
      ChartRead = "Energy affects confidence quickly because consumers see it every week."
      ChartData = @(
        (New-ChartItem "Core MoM" 0.2 "+0.2%" $palette.teal),
        (New-ChartItem "Energy MoM" 3.9 "+3.9%" $palette.amber),
        (New-ChartItem "Gas MoM" 7.0 "+7.0%" $palette.red),
        (New-ChartItem "Energy YoY" 23.5 "+23.5%" $palette.red)
      )
      Context = "Energy is volatile, but it can change inflation psychology fast."
      Bullets = @("Core looked better.", "Energy was the loud pressure point.", "Households feel headline inflation.")
      BottomLine = "Energy can keep inflation anxiety alive."
      FinalRead = "Core matters for models. Energy matters for consumers."
      Watch = @("Oil volatility", "Gasoline", "Consumer confidence")
      Source = "Source: BLS Consumer Price Index, May 2026"
      Narration = "The market can ignore energy for a while. Consumers cannot. Core inflation looked calmer in May, but energy rose 3.9 percent for the month and 23.5 percent over the year. Gasoline rose 7 percent in May. That matters because energy inflation hits confidence quickly. It changes how households feel about the economy, and it changes the tone around inflation risk. That is the caveat quick recaps skip. Not investment advice."
    },
    [PSCustomObject]@{
      Number = 10
      Title = "What To Watch Next"
      Category = "WATCHLIST"
      Eye = "THE NEXT SIGNAL MAP"
      Deck = "Do not chase one headline. Watch the variables that can change the story."
      BigMetric = "4"
      BigMetricLabel = "signals before the next narrative"
      Accent = $palette.teal
      Picture = "market"
      ChartType = "bar"
      ChartTitle = "Four-variable watchlist"
      ChartLead = "The next market narrative probably comes from one of these inputs."
      ChartRead = "The setup is inflation, labor stability, AI capex, and energy."
      ChartData = @(
        (New-ChartItem "Inflation" 4.1 "PCE" $palette.red),
        (New-ChartItem "Jobs" 172 "+172K" $palette.olive),
        (New-ChartItem "AI" 81.6 '$81.6B' $palette.teal),
        (New-ChartItem "Energy" 23.5 "+23.5%" $palette.amber)
      )
      Context = "The market story changes when one of these pillars breaks or confirms."
      Bullets = @("Inflation tells you how patient the Fed can be.", "Jobs tell you whether rescue cuts enter the chat.", "AI capex tells you whether growth can keep carrying risk.")
      BottomLine = "This is the checklist before the next market turn."
      FinalRead = "The narrative is not one datapoint. It is the interaction between the four."
      Watch = @("Inflation prints", "Labor data", "AI capex and energy")
      Source = "Sources: BEA, BLS, Federal Reserve, NVIDIA, Micron"
      Narration = "If you want the next market signal, watch four things. First, inflation. If energy cools and core stays contained, markets can breathe. Second, jobs. Stable jobs let the Fed wait. A sharp slowdown changes the story. Third, AI capex commentary. Demand is real, but investors need proof it is durable. Fourth, energy volatility. That is the setup: inflation, Fed patience, labor stability, and AI growth. Not investment advice."
    }
  )
}

function Render-ProShort($spec) {
  $slug = "{0:00}-{1}" -f $spec.Number, (ConvertTo-Slug $spec.Title)
  $videoDir = Join-Path $workPath $slug
  New-Item -ItemType Directory -Force -Path $videoDir | Out-Null

  $sceneNames = @("hook", "chart", "evidence", "bottom")
  $slides = @()
  for ($i = 0; $i -lt $sceneNames.Count; $i++) {
    $slide = Join-Path $videoDir ("scene_{0:00}_{1}.png" -f ($i + 1), $sceneNames[$i])
    New-ProShortSlide $slide $spec $sceneNames[$i]
    $slides += $slide
  }

  $audio = Join-Path $videoDir "voiceover.wav"
  New-Narration $spec.Narration $audio
  $audioDuration = Get-AudioDuration $audio
  $videoDuration = [Math]::Max(30.0, $audioDuration + 1.2)
  $durations = @(
    [Math]::Max(4.2, $videoDuration * 0.14),
    [Math]::Max(8.0, $videoDuration * 0.31),
    [Math]::Max(8.0, $videoDuration * 0.30),
    [Math]::Max(7.0, $videoDuration * 0.25)
  )
  $scale = $videoDuration / (($durations | Measure-Object -Sum).Sum)
  $durations = @($durations | ForEach-Object { $_ * $scale })
  $motions = @("right", "left", "up", "down")
  $clips = @()
  for ($i = 0; $i -lt $slides.Count; $i++) {
    $clip = Join-Path $videoDir ("clip_{0:00}.mp4" -f ($i + 1))
    Render-SlideClip $slides[$i] $clip $durations[$i] 1080 1920 $motions[$i]
    $clips += $clip
  }

  $output = Join-Path $outputPath ($slug + ".mp4")
  Join-ClipsWithAudio $clips $audio $output
  return [PSCustomObject]@{
    type = "short"
    number = $spec.Number
    title = $spec.Title
    style = "professional-editorial"
    file = $output
    duration_sec = [Math]::Round((Get-AudioDuration $output), 1)
  }
}

function Get-LongformScript([string]$markdown) {
  $scriptMatch = [regex]::Match($markdown, "(?ms)^## Script\r?\n\r?\n(?<script>.+?)\r?\n\r?\n## Visual Plan")
  if ($scriptMatch.Success) {
    return ($scriptMatch.Groups["script"].Value.Trim() -replace "\r?\n\r?\n", "`n")
  }
  return $markdown
}

function Get-LongformScenes {
  return @(
    [PSCustomObject]@{
      Section = "THE SETUP"; Title = "The market is fighting three stories"; Copy = "Inflation is still firm, the Fed can wait, and AI demand is still strong enough to keep growth in the conversation."; Accent = $palette.walnut; ChartType = "bar"; ChartTitle = "Three forces"; Source = "Sources: BEA, BLS, Fed, NVIDIA, Micron"; Bullets = @("Inflation", "Fed patience", "AI demand"); ChartData = @((New-ChartItem "PCE" 4.1 "+4.1%" $palette.red), (New-ChartItem "Fed" 3.625 "hold" $palette.teal), (New-ChartItem "AI" 81.6 '$81.6B' $palette.amber))
    },
    [PSCustomObject]@{
      Section = "INFLATION"; Title = "Demand did not give the Fed a clean all-clear"; Copy = "Personal income and spending both rose 0.7 percent in May while PCE inflation remained above target."; Accent = $palette.red; ChartType = "bar"; ChartTitle = "May PCE"; Source = "Source: BEA Personal Income and Outlays"; Bullets = @("Income rose", "Spending rose", "Inflation stayed firm"); ChartData = @((New-ChartItem "Income" 0.7 "+0.7%" $palette.teal), (New-ChartItem "Spend" 0.7 "+0.7%" $palette.amber), (New-ChartItem "Real PCE" 0.3 "+0.3%" $palette.olive), (New-ChartItem "PCE YoY" 4.1 "+4.1%" $palette.red))
    },
    [PSCustomObject]@{
      Section = "CPI"; Title = "Core looked calmer. Energy changed the feel."; Copy = "Energy and gasoline made the headline inflation picture harder to ignore."; Accent = $palette.red; ChartType = "bar"; ChartTitle = "CPI split"; Source = "Source: BLS CPI"; Bullets = @("Core improved", "Headline still hot", "Energy hit confidence"); ChartData = @((New-ChartItem "Core YoY" 2.9 "+2.9%" $palette.teal), (New-ChartItem "CPI YoY" 4.2 "+4.2%" $palette.amber), (New-ChartItem "Gas MoM" 7.0 "+7.0%" $palette.red), (New-ChartItem "Energy YoY" 23.5 "+23.5%" $palette.red))
    },
    [PSCustomObject]@{
      Section = "FED"; Title = "The hold was not the gift markets wanted"; Copy = "The June statement kept inflation risk alive and gave the Fed room to wait."; Accent = $palette.teal; ChartType = "line"; ChartTitle = "Pause, not pivot"; Source = "Source: Federal Reserve"; Bullets = @("Rate range held", "Inflation elevated", "Activity solid"); ChartData = @((New-ChartItem "Mar" 3.625 "3.625%" $palette.teal), (New-ChartItem "Apr" 3.625 "3.625%" $palette.teal), (New-ChartItem "May" 3.625 "3.625%" $palette.teal), (New-ChartItem "Jun" 3.625 "hold" $palette.red))
    },
    [PSCustomObject]@{
      Section = "LABOR"; Title = "Stable jobs keep the waiting game alive"; Copy = "Payroll growth was not spectacular, but it was not weak enough to force rescue cuts."; Accent = $palette.olive; ChartType = "bar"; ChartTitle = "May labor signal"; Source = "Source: BLS Employment Situation"; Bullets = @("Payrolls +172K", "Unemployment 4.3%", "No panic signal"); ChartData = @((New-ChartItem "Payrolls" 172 "+172K" $palette.olive), (New-ChartItem "Leisure" 70 "+70K" $palette.teal), (New-ChartItem "Govt." 55 "+55K" $palette.amber), (New-ChartItem "Finance" -22 "-22K" $palette.red))
    },
    [PSCustomObject]@{
      Section = "AI"; Title = "AI demand is real. Valuation is the fight."; Copy = "NVIDIA and Micron show real infrastructure demand, but rate math still affects the multiple."; Accent = $palette.amber; ChartType = "bar"; ChartTitle = "AI infrastructure"; Source = "Sources: NVIDIA; Micron"; Bullets = @("Demand is real", "Growth is crowded", "Rates still matter"); ChartData = @((New-ChartItem "NVDA Rev" 81.6 '$81.6B' $palette.teal), (New-ChartItem "Data Ctr" 75.2 '$75.2B' $palette.ceramicTeal), (New-ChartItem "Growth" 92 "+92%" $palette.olive), (New-ChartItem "MU Guide" 50 '$50B' $palette.amber))
    },
    [PSCustomObject]@{
      Section = "RATE MATH"; Title = "Great companies can still be repriced"; Copy = "The stock market is not only asking if AI grows. It is asking what price it should pay for that growth."; Accent = $palette.walnut; ChartType = "line"; ChartTitle = "Future growth repricing"; Source = "Editorial model"; Bullets = @("Future profits", "Higher discount rate", "Multiple pressure"); ChartData = @((New-ChartItem "Lower" 100 "100" $palette.teal), (New-ChartItem "Mid" 86 "86" $palette.amber), (New-ChartItem "Firm" 74 "74" $palette.red), (New-ChartItem "Higher" 66 "66" $palette.red))
    },
    [PSCustomObject]@{
      Section = "WATCH NEXT"; Title = "The next signal map"; Copy = "Watch inflation, jobs, AI capex commentary, and energy volatility before accepting the next clean market story."; Accent = $palette.teal; ChartType = "bar"; ChartTitle = "Four variables"; Source = "Sources: BEA, BLS, Fed, NVIDIA, Micron"; Bullets = @("Inflation prints", "Labor stability", "AI capex and energy"); ChartData = @((New-ChartItem "Inflation" 4.1 "PCE" $palette.red), (New-ChartItem "Jobs" 172 "+172K" $palette.olive), (New-ChartItem "AI" 81.6 '$81.6B' $palette.teal), (New-ChartItem "Energy" 23.5 "+23.5%" $palette.amber))
    }
  )
}

function Render-ProLongform([string]$scriptText) {
  $videoDir = Join-Path $workPath "longform-professional"
  New-Item -ItemType Directory -Force -Path $videoDir | Out-Null
  $slides = @()
  $scenes = Get-LongformScenes
  for ($i = 0; $i -lt $scenes.Count; $i++) {
    $slide = Join-Path $videoDir ("scene_{0:00}.png" -f ($i + 1))
    New-ProLongSlide $slide $scenes[$i]
    $slides += $slide
  }
  $audio = Join-Path $videoDir "voiceover.wav"
  New-Narration $scriptText $audio
  $audioDuration = Get-AudioDuration $audio
  $clipDuration = [Math]::Max(8.0, ($audioDuration + 2.0) / $slides.Count)
  $motions = @("right", "left", "up", "down", "right", "left", "up", "down")
  $clips = @()
  for ($i = 0; $i -lt $slides.Count; $i++) {
    $clip = Join-Path $videoDir ("clip_{0:00}.mp4" -f ($i + 1))
    Render-SlideClip $slides[$i] $clip $clipDuration 1280 720 $motions[$i % $motions.Count]
    $clips += $clip
  }
  $output = Join-Path $outputPath "longform-the-market-is-fighting-three-stories.mp4"
  Join-ClipsWithAudio $clips $audio $output
  return [PSCustomObject]@{
    type = "longform"
    title = "The Market Is Fighting Three Stories"
    style = "professional-editorial"
    file = $output
    duration_sec = [Math]::Round((Get-AudioDuration $output), 1)
  }
}

$manifest = New-Object System.Collections.Generic.List[object]
$specs = Get-ProSpecs
foreach ($spec in $specs | Where-Object { $ShortNumbers -contains $_.Number }) {
  Write-Host "Rendering professional short $($spec.Number): $($spec.Title)"
  $manifest.Add((Render-ProShort $spec))
}

if ($RenderLongform) {
  Write-Host "Rendering professional long-form video draft"
  $longMarkdown = Get-Content -Raw (Join-Path $contentPath "youtube-script.md")
  $manifest.Add((Render-ProLongform (Get-LongformScript $longMarkdown)))
}

$manifestPath = Join-Path $outputPath "video_manifest.json"
$manifest | ConvertTo-Json -Depth 8 | Set-Content -Path $manifestPath -Encoding UTF8
Write-Host "Wrote professional video manifest: $manifestPath"
