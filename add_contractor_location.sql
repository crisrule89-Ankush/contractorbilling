-- Contractor Location: the contractor's own location (their MainBranch in
-- Contractor Master), mapped from the Contractor Code.
-- This is distinct from BranchName, which is the branch the work was done for
-- and the branch the billing must reflect in.
IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'AdBillingMaster' AND COLUMN_NAME = 'ContractorLocation'
)
BEGIN
    ALTER TABLE dbo.AdBillingMaster ADD ContractorLocation NVARCHAR(100) NULL;
END

IF EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'AdBillingMaster' AND COLUMN_NAME = 'UpdatedByBranch'
)
BEGIN
    ALTER TABLE dbo.AdBillingMaster DROP COLUMN UpdatedByBranch;
END
