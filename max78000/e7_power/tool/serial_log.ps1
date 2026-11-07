param(
    [string]$Port = "COM3",
    [int]$Seconds = 3540
)
$log = "C:\Users\13157\Desktop\work\blasphemy-edgeai\project-egde_cnn_vad\energy_test\serial_1h.log"

$sp = New-Object System.IO.Ports.SerialPort($Port, 115200, "None", 8, "One")
$sp.ReadTimeout = 200
$ok = $false
for ($try = 1; $try -le 15; $try++) {
    try { $sp.Open(); $ok = $true; break }
    catch { Write-Output "open attempt $try failed: $($_.Exception.Message)"; Start-Sleep -Milliseconds 1000 }
}
if (-not $ok) { Write-Output "FATAL: cannot open $Port"; exit 2 }

$out = New-Object System.IO.StreamWriter($log, $false, (New-Object System.Text.UTF8Encoding($false)))
$out.AutoFlush = $true
$out.WriteLine("# t_ms<TAB>line   port=$Port baud=115200   start=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
Write-Output "opened $Port, logging $Seconds s -> $log"

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$carry = ""
$count = 0
$errs = 0
while ($sw.Elapsed.TotalSeconds -lt $Seconds) {
    Start-Sleep -Milliseconds 200
    try {
        $n = $sp.BytesToRead
        if ($n -gt 0) {
            $buf = New-Object byte[] $n
            [void]$sp.Read($buf, 0, $n)
            $txt = $carry + [System.Text.Encoding]::ASCII.GetString($buf)
            $parts = $txt -split "`n"
            $carry = $parts[-1]
            $ms = [long]$sw.Elapsed.TotalMilliseconds
            for ($k = 0; $k -lt $parts.Count - 1; $k++) {
                $line = $parts[$k].Trim()
                if ($line -ne "") { $out.WriteLine("$ms`t$line"); $count++ }
            }
        }
    } catch { $errs++ }
}
$out.WriteLine("# total_lines=$count errors=$errs elapsed_s=$([math]::Round($sw.Elapsed.TotalSeconds,1))")
$out.Close()
$sp.Close()
Write-Output "done: lines=$count errors=$errs -> $log"
