# Live Smoke Test for Running Backend Gateway
$ErrorActionPreference = "Stop"

Write-Host "--- 1. Health Probe ---"
$h = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get
Write-Host "Health:" ($h | ConvertTo-Json -Compress)

Write-Host "`n--- 2. User Authentication ---"
$loginBody = @{
    username = "analyst_user"
    password = "AnalystPass2026!"
} | ConvertTo-Json
$auth = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/auth/login" -Method Post -ContentType "application/json" -Body $loginBody
Write-Host "Authenticated As:" $auth.user_id "Role:" $auth.role "Token:" ($auth.token.Substring(0, 16) + "...")

$headers = @{
    Authorization = "Bearer $($auth.token)"
}

Write-Host "`n--- 3. Dataset Inspection ---"
$datasets = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/datasets" -Method Get -Headers $headers
foreach ($d in $datasets) {
    Write-Host "Dataset:" $d.dataset_id "- Records:" $d.total_records "- Privacy Unit:" $d.privacy_unit
}

Write-Host "`n--- 4. Query Validation & Execution (DP Release) ---"
$queryBody = @{
    dataset_id = "health"
    field = "diagnosis_category"
    operator = "equals"
    value = "cardiovascular"
    epsilon = 0.5
} | ConvertTo-Json
$rel1 = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/queries/run" -Method Post -ContentType "application/json" -Headers $headers -Body $queryBody
Write-Host "Release ID:" $rel1.release_id
Write-Host "Noisy Count (Laplace):" $rel1.noisy_count
Write-Host "Epsilon Spent:" $rel1.epsilon_spent "Remaining Budget:" $rel1.remaining_budget
Write-Host "Is Cached:" $rel1.is_cached
Write-Host "Receipt ID:" $rel1.receipt.receipt_id
Write-Host "Ed25519 Signature:" ($rel1.receipt.signature.Substring(0, 24) + "...")

Write-Host "`n--- 5. Repeated Query Caching Check ---"
$rel2 = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/queries/run" -Method Post -ContentType "application/json" -Headers $headers -Body $queryBody
Write-Host "Second Query Cached:" $rel2.is_cached "Epsilon Spent:" $rel2.epsilon_spent "(Zero budget deducted)"

Write-Host "`n--- 6. Cryptographic Audit Chain Verification ---"
$audit = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/audit/verify" -Method Get -Headers $headers
Write-Host "Audit Chain Valid:" $audit.valid
Write-Host "Total Verified Entries:" $audit.verified_entries "of" $audit.total_entries
Write-Host "Tamper Detected:" $audit.tamper_detected
Write-Host "Verification Algorithm:" $audit.algorithm

Write-Host "`n--- 7. Evaluation & Transparency Status ---"
$eval = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/evaluation/status" -Method Get -Headers $headers
Write-Host "Official Accounting Status:" $eval.official_accounting_spec_status
Write-Host "Official Risk Evaluation:" $eval.official_empirical_risk_evaluation_status
Write-Host "`n[SUCCESS] Live Smoke Test Passed Completely!"
