$password = "riofuturo2026"
$securePassword = ConvertTo-SecureString $password -AsPlainText -Force

# Para comandos SSH
function Invoke-SSHCommand {
    param([string]$Command)
    
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "ssh"
    $psi.Arguments = "debian@167.114.114.51 `"$Command`""
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    
    $process = [System.Diagnostics.Process]::Start($psi)
    $process.StandardInput.WriteLine($password)
    $process.StandardInput.Close()
    
    $output = $process.StandardOutput.ReadToEnd()
    $error = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    
    return @{
        Output = $output
        Error = $error
        ExitCode = $process.ExitCode
    }
}
