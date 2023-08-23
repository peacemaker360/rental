az account clear
az login --use-device-code

# Variablen definieren
$resourceGroup="rg-test"
$location="switzerlandnorth"
$templateFile=".\azure_iac\template.json"
$parametersFile=".\azure_iac\parameters.json"

# Ressourcengruppe erstellen
az group create --name $resourceGroup --location $location


# ARM Template deployen
az deployment group create `
  --name IaC_depolyment `
  --resource-group $resourceGroup `
  --template-file $templateFile `
  --parameters @$parametersFile
