$dll = "C:\Users\13157\Desktop\work\blasphemy-edgeai\project-egde_cnn_vad\max78000\e7_power\_lib\ATK_UT70DLL.dll"
$a = [Reflection.Assembly]::Load([IO.File]::ReadAllBytes($dll))
foreach ($n in @('CVDataModel','Frequency','Parameter')) {
  $t = $a.GetTypes() | Where-Object { $_.Name -eq $n } | Select-Object -First 1
  if ($t) {
    Write-Output "=== $n ==="
    if ($t.IsEnum) { [Enum]::GetNames($t) | ForEach-Object { "  $_ = " + [int]([Enum]::Parse($t,$_)) } }
    else { $t.GetProperties() | ForEach-Object { "  $($_.PropertyType.Name) $($_.Name)" }; $t.GetFields() | ForEach-Object { "  field $($_.FieldType.Name) $($_.Name)" } }
  }
}
