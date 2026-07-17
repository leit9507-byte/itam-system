param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$Username = "admin",
  [string]$Password = "admin",
  [string]$ReportOutput = ""
)

$ErrorActionPreference = "Stop"

function U {
  param([string]$Base64)
  return [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($Base64))
}

$StatusRepairing = U "57u05L+u5Lit"
$StatusFinished = U "5bey5a6M5oiQ"
$ScopeAll = U "5YWo6YOo"
$StatusInProgress = U "6L+b6KGM5Lit"
$ResultNormal = U "5q2j5bi4"
$StatusPendingDisposal = U "5b6F5aSE572u"
$StatusDisposed = U "5bey5aSE572u"

function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok {
  param([string]$Message)
  Write-Host "OK  $Message" -ForegroundColor Green
}

function Assert-True {
  param(
    [bool]$Condition,
    [string]$Message
  )
  if (-not $Condition) {
    throw "Acceptance failed: $Message"
  }
  Write-Ok $Message
}

function Assert-Equal {
  param(
    [object]$Actual,
    [object]$Expected,
    [string]$Message
  )
  if ("$Actual" -ne "$Expected") {
    throw "Acceptance failed: $Message. Expected: $Expected, actual: $Actual"
  }
  Write-Ok "$Message`: $Expected"
}

function Convert-ToJsonBody {
  param([object]$Body)
  return ($Body | ConvertTo-Json -Depth 30)
}

function Invoke-ItamApi {
  param(
    [ValidateSet("GET", "POST", "PUT", "DELETE")]
    [string]$Method,
    [string]$Path,
    [object]$Body = $null,
    [switch]$Raw
  )

  $headers = @{}
  if ($script:Token) {
    $headers.Authorization = "Bearer $script:Token"
  }

  $uri = "$ApiBaseUrl$Path"
  if ($Raw) {
    return Invoke-WebRequest -Method $Method -Uri $uri -Headers $headers -UseBasicParsing
  }

  $requestArgs = @{
    Method = $Method
    Uri = $uri
    Headers = $headers
    UseBasicParsing = $true
  }
  if ($null -eq $Body) {
    $response = Invoke-WebRequest @requestArgs
  } else {
    $requestArgs.ContentType = "application/json; charset=utf-8"
    $requestArgs.Body = Convert-ToJsonBody $Body
    $response = Invoke-WebRequest @requestArgs
  }

  $stream = $response.RawContentStream
  if ($stream.CanSeek) {
    $stream.Position = 0
  }
  $reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::UTF8)
  $text = $reader.ReadToEnd()
  if ([string]::IsNullOrWhiteSpace($text)) {
    return $null
  }
  return $text | ConvertFrom-Json
}

function Escape-QueryValue {
  param([string]$Value)
  return [System.Uri]::EscapeDataString($Value)
}

function Get-AssetById {
  param([string]$AssetId)
  $result = Invoke-ItamApi -Method GET -Path "/asset/list?keyword=$(Escape-QueryValue $AssetId)&page_size=0"
  $asset = @($result.list | Where-Object { $_.asset_id -eq $AssetId })[0]
  if (-not $asset) {
    throw "Acceptance failed: asset not found: $AssetId"
  }
  return $asset
}

Write-Step "Check backend health"
$health = Invoke-RestMethod -Method GET -Uri "$ApiBaseUrl/"
Assert-Equal $health.ok $true "Backend health check"

Write-Step "Login and acquire JWT"
$login = Invoke-ItamApi -Method POST -Path "/auth/login" -Body @{
  username = $Username
  password = $Password
  provider = "local"
}
$script:Token = $login.access_token
Assert-True ([string]::IsNullOrWhiteSpace($script:Token) -eq $false) "JWT token acquired"

$stamp = Get-Date -Format "yyyyMMddHHmmss"
$purchaseNo = "E2E-PO-$stamp"
$approvalNo = "E2E-OA-$stamp"
$sn = "E2E-SN-$stamp"
$today = Get-Date -Format "yyyy-MM-dd"

Write-Step "Purchase inbound: create purchase order"
$purchase = Invoke-ItamApi -Method POST -Path "/purchase/create" -Body @{
  purchase_no = $purchaseNo
  company = "E2E Acceptance Company"
  approval_no = $approvalNo
  supplier_name = "E2E Acceptance Supplier"
  purchase_reason = "E2E business acceptance"
  total_amount = 68000
  status = "pending_acceptance"
  items = @(
    @{
      name = "E2E High Value Laptop"
      category = "Laptop"
      brand = "Lenovo"
      model = "E2E-X1"
      quantity = 1
      unit_price = 68000
      retirement_years = 5
      purchase_reason = "E2E business acceptance"
      location = "E2E Warehouse"
      dept_id = "IT"
    }
  )
}
Assert-Equal $purchase.purchase_no $purchaseNo "Purchase number persisted"
Assert-Equal $purchase.status "pending_acceptance" "Purchase initial status"
$itemId = $purchase.items[0].id
Assert-True ($itemId -gt 0) "Purchase item generated"

Write-Step "Purchase inbound: accept and generate asset"
$acceptPath = "/purchase/accept?purchase_no=$(Escape-QueryValue $purchaseNo)"
$acceptResult = Invoke-ItamApi -Method POST -Path $acceptPath -Body @{
  operator = "E2E Receiver"
  acceptances = @(
    @{
      item_id = $itemId
      assets = @(
        @{
          sn = $sn
          name = "E2E High Value Laptop"
          brand = "Lenovo"
          model = "E2E-X1"
          category = "Laptop"
          spec = "32G/1TB"
          location = "E2E Warehouse"
          dept_id = "IT"
          company = "E2E Acceptance Company"
          purchase_price = 68000
          purchase_date = "${today}T00:00:00"
          purchase_approval_no = $approvalNo
          purchase_supplier_name = "E2E Acceptance Supplier"
          warranty_months = 36
        }
      )
    }
  )
}
Assert-Equal $acceptResult.purchase.status "received" "Purchase accepted status"
Assert-True (@($acceptResult.assets).Count -eq 1) "One asset generated by acceptance"
$assetId = $acceptResult.assets[0].asset_id
$asset = Get-AssetById $assetId
Assert-Equal $asset.status "in_stock" "Asset status after purchase acceptance"
Assert-Equal $asset.sn $sn "Asset SN persisted"

Write-Step "Outbound: assign asset to a user"
$outbound = Invoke-ItamApi -Method POST -Path "/asset/$assetId/status" -Body @{
  to_status = "in_use"
  owner_user_id = "U-ADMIN"
  dept_id = "IT"
  location = "E2E Desk A-01"
  remark = "E2E outbound"
}
Assert-Equal $outbound.status "in_use" "Asset status after outbound"
Assert-Equal $outbound.owner_user_id "U-ADMIN" "Asset owner assigned"

Write-Step "Repair: create repair order and verify asset status"
$repair = Invoke-ItamApi -Method POST -Path "/repair/create" -Body @{
  asset_id = $assetId
  repair_time = "${today}T00:00:00"
  fault_reason = "E2E screen flicker"
  repair_cost = 800
  vendor = "E2E Repair Vendor"
  operator = "E2E Asset Admin"
  remark = "E2E repair acceptance"
}
Assert-Equal $repair.status $StatusRepairing "Repair order status"
$asset = Get-AssetById $assetId
Assert-Equal $asset.status "repair" "Asset status after repair creation"

Write-Step "Repair: finish repair and return to stock"
$repairFinish = Invoke-ItamApi -Method POST -Path "/repair/$($repair.id)/finish" -Body @{
  finish_time = "${today}T00:00:00"
  next_status = "in_stock"
  operator = "E2E Asset Admin"
  remark = "E2E repair finished"
}
Assert-Equal $repairFinish.status $StatusFinished "Repair finished status"
$asset = Get-AssetById $assetId
Assert-Equal $asset.status "in_stock" "Asset status after repair finish"

Write-Step "Stocktake: create, start, submit item, finish"
$stocktake = Invoke-ItamApi -Method POST -Path "/stocktake/tasks" -Body @{
  name = "E2E Stocktake $stamp"
  scope = $ScopeAll
  target = ""
  owner = "E2E Checker"
}
Assert-True (@($stocktake.items | Where-Object { $_.asset_id -eq $assetId }).Count -eq 1) "Stocktake task includes the asset"

$stocktakeStarted = Invoke-ItamApi -Method POST -Path "/stocktake/tasks/$($stocktake.id)/start"
Assert-Equal $stocktakeStarted.status $StatusInProgress "Stocktake started status"

$stocktakeItem = Invoke-ItamApi -Method POST -Path "/stocktake/tasks/$($stocktake.id)/items/$assetId" -Body @{
  actual_location = "E2E Warehouse"
  result = $ResultNormal
  checker = "E2E Checker"
  remark = "E2E stocktake acceptance"
}
Assert-Equal $stocktakeItem.result $ResultNormal "Stocktake item result"

$stocktakeFinished = Invoke-ItamApi -Method POST -Path "/stocktake/tasks/$($stocktake.id)/finish"
Assert-Equal $stocktakeFinished.status $StatusFinished "Stocktake finished status"

Write-Step "Scrap: submit request and register disposal"
$scrap = Invoke-ItamApi -Method POST -Path "/scrap/$assetId/create" -Body @{
  applicant = "E2E Asset Admin"
  reason = "E2E scrap acceptance"
  estimated_residual_value = 100
}
Assert-Equal $scrap.status $StatusPendingDisposal "Scrap request initial status"
$asset = Get-AssetById $assetId
Assert-Equal $asset.status "pending_scrap" "Asset status after scrap request"

$scrapDisposed = Invoke-ItamApi -Method POST -Path "/scrap/$($scrap.id)/dispose" -Body @{
  retirement_date = "${today}T00:00:00"
  retirement_approval_no = "E2E-SC-$stamp"
  disposal_method = "报废"
  final_residual_value = 100
  disposal_remark = "E2E disposal registration"
}
Assert-Equal $scrapDisposed.status $StatusDisposed "Scrap disposed status"
$asset = Get-AssetById $assetId
Assert-Equal $asset.status "disposed" "Asset status after disposal registration"

Write-Step "Audit report: run audit and download HTML"
$audit = Invoke-ItamApi -Method POST -Path "/audit/run" -Body @{ users = @() }
Assert-True ($audit.total_assets -ge 1) "Audit returns total asset count"
Assert-True ($null -ne $audit.risk_score) "Audit returns risk score"

if ([string]::IsNullOrWhiteSpace($ReportOutput)) {
  $ReportOutput = Join-Path (Resolve-Path ".") "artifacts\e2e-audit-report-$stamp.html"
}
$reportDir = Split-Path -Parent $ReportOutput
if (-not (Test-Path $reportDir)) {
  New-Item -ItemType Directory -Path $reportDir | Out-Null
}
$reportResponse = Invoke-ItamApi -Method GET -Path "/audit/report" -Raw
$reportStream = $reportResponse.RawContentStream
if ($reportStream.CanSeek) {
  $reportStream.Position = 0
}
$memory = New-Object System.IO.MemoryStream
$reportStream.CopyTo($memory)
[System.IO.File]::WriteAllBytes($ReportOutput, $memory.ToArray())
Assert-True ((Test-Path $ReportOutput) -and ((Get-Item $ReportOutput).Length -gt 0)) "Audit report downloaded to $ReportOutput"

Write-Host ""
Write-Host "E2E acceptance passed" -ForegroundColor Green
Write-Host "Purchase: $purchaseNo"
Write-Host "Asset: $assetId"
Write-Host "Repair: $($repair.repair_no)"
Write-Host "Stocktake: $($stocktake.id)"
Write-Host "Scrap: $($scrap.request_no)"
Write-Host "Audit report: $ReportOutput"
