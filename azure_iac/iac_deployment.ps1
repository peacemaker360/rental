az account clear
az login --use-device-code

# Variablen definieren
$resourceGroup = "rg-test2"
$location = "switzerlandnorth"
$templateFile = ".\azure_iac\template.json"
$parametersFile = ".\azure_iac\parameters.json"

# Ressourcengruppe erstellen
az group create --name $resourceGroup --location $location

# ARM Template deployen
$deployment = $(az deployment group create `
    --name IaC_depolyment `
    --resource-group $resourceGroup `
    --template-file $templateFile `
    --parameters @$parametersFile)

$deployment = az deployment group show -g $resourceGroup -n IaC_depolyment -o json

$d = ConvertFrom-Json ($deployment | Out-String)
if ($d.properties.parameters.isInitialDeployment.value) {
  Write-host "Init password: $($d.properties.outputs.initDBADMPW)"
}

Write-Host -ForegroundColor Cyan "ℹ️ NOTE: The depolyment might still be in progress.`n  After you check the status in the Azure Portal, make sure to configure GitHub Actions accordingly (setup CI/CD Pipeline)."

Write-Host -ForegroundColor Cyan "ℹ️ NOTE: If this is an intial deployment, consider resetting the db admin password!"
az mysql flexible-server update --resource-group $resourceGroup --name $(Read-Host -Prompt "Server Name") --admin-password $([System.Net.NetworkCredential]::new("", (Read-Host -Prompt "New passowrd" -AsSecureString)).Password)

Write-Host -ForegroundColor Green "Success!"
Write-Host -ForegroundColor Cyan "Dont forget to configure SECRET_KEY and DB password in the web app settings."
