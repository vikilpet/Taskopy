$URL = "http://127.0.0.1/task?send_to&fullpath="
foreach ($file in $args) {
    # echo ($URL + [uri]::EscapeUriString($file))
    Invoke-WebRequest -Uri ($URL + [uri]::EscapeUriString($file))
    # Invoke-WebRequest -Uri $URL -Method POST `
    #     -ContentType 'application/x-www-form-urlencoded' -Body @{fullpath = $file}
}
# [void][System.Console]::ReadKey($true)
