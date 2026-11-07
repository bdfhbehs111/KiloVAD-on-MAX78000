$dll = "C:\Users\13157\Desktop\work\blasphemy-edgeai\project-egde_cnn_vad\max78000\e7_power\_lib\ATK_UT70DLL.dll"
function Show($a, $how) {
    Write-Output "=== LOADED via $how : $($a.FullName)"
    Write-Output "=== REFERENCED ==="
    $a.GetReferencedAssemblies() | ForEach-Object { "  $($_.Name) $($_.Version)" }
    Write-Output "=== TYPES ==="
    $a.GetTypes() | ForEach-Object { "  $($_.FullName)" } | Sort-Object
    $t = $a.GetTypes() | Where-Object { $_.Name -eq 'ATKUT70' } | Select-Object -First 1
    if ($t) {
        Write-Output "=== ATKUT70 (ns=$($t.Namespace)) ==="
        $t.GetMembers([Reflection.BindingFlags]'Public,Instance,Static,DeclaredOnly') | ForEach-Object { "  $($_.MemberType)  $($_.ToString())" } | Sort-Object
    }
}
$a = $null
try { $a = [Reflection.Assembly]::LoadFrom($dll); Show $a "LoadFrom" }
catch {
    Write-Output "LoadFrom failed: $($_.Exception.InnerException.Message)"
    try { $a = [Reflection.Assembly]::Load([IO.File]::ReadAllBytes($dll)); Show $a "Load(bytes)" }
    catch { Write-Output "Load(bytes) failed: $($_.Exception.InnerException.Message)" }
}
