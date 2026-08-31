IF OBJECT_ID('dbo.AdBillingMaster', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.AdBillingMaster', 'Uniquekey') IS NULL
    BEGIN
        ALTER TABLE dbo.AdBillingMaster ADD Uniquekey NVARCHAR(300) NULL;
    END

    UPDATE dbo.AdBillingMaster
    SET Uniquekey = LTRIM(RTRIM(ISNULL(ContractorCode, ''))) + '_' + LTRIM(RTRIM(ISNULL(BillNoDebRemarks, '')))
    WHERE Uniquekey IS NULL OR LTRIM(RTRIM(Uniquekey)) = '';

    IF EXISTS (
        SELECT 1
        FROM dbo.AdBillingMaster
        GROUP BY LTRIM(RTRIM(Uniquekey))
        HAVING COUNT(*) > 1
    )
    BEGIN
        RAISERROR('Duplicate Uniquekey values exist in AdBillingMaster. Remove duplicates before creating the unique index.', 16, 1);
        RETURN;
    END

    IF EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE object_id = OBJECT_ID('dbo.AdBillingMaster')
          AND name = 'UX_AdBillingMaster_ContractorCode_BillNoDebRemarks'
    )
    BEGIN
        DROP INDEX UX_AdBillingMaster_ContractorCode_BillNoDebRemarks ON dbo.AdBillingMaster;
    END

    ALTER TABLE dbo.AdBillingMaster ALTER COLUMN Uniquekey NVARCHAR(300) NOT NULL;

    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE object_id = OBJECT_ID('dbo.AdBillingMaster')
          AND name = 'UX_AdBillingMaster_Uniquekey'
    )
    BEGIN
        CREATE UNIQUE INDEX UX_AdBillingMaster_Uniquekey
        ON dbo.AdBillingMaster (Uniquekey);
    END
END
