$dll = "C:\Users\13157\Downloads\7、【正点原子】UT70 USB测试仪\中文版（国内）\1，UT70 USB测试仪上位机软件\DLL文档\x64\ATK_UT70DLL.dll"
Write-Output "PSVersion: $($PSVersionTable.PSVersion)"
try {
    $a = [Reflection.Assembly]::LoadFrom($dll)
    Write-Output "=== LOADED ==="
    Write-Output "FullName: $($a.FullName)"
    Write-Output "=== TYPES ==="
    $a.GetTypes() | ForEach-Object { $_.FullName } | Sort-Object
    $t = $a.GetTypes() | Where-Object { $_.Name -eq 'ATKUT70' } | Select-Object -First 1
    if ($t) {
        Write-Output "=== ATKUT70 MEMBERS (ns=$($t.Namespace)) ==="
        $t.GetMembers([Reflection.BindingFlags]'Public,Instance,Static,DeclaredOnly') |
            ForEach-Object { "  $($_.MemberType)  $($_.ToString())" } | Sort-Object
    }
    $c = $a.GetTypes() | Where-Object { $_.Name -eq 'CVDataModel' } | Select-Object -First 1
    if ($c) {
        Write-Output "=== CVDataModel ==="
        $c.GetProperties() | ForEach-Object { "  $($_.PropertyType.Name) $($_.Name)" }
    }
} catch {
    Write-Output "FAILED: $($_.Exception.GetType().Name): $($_.Exception.Message)"
    if ($_.Exception.InnerException) { Write-Output "  inner: $($_.Exception.InnerException.Message)" }
}
