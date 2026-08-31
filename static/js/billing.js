const alertContainer = document.getElementById('alertContainer');
const billingForm = document.getElementById('billingForm');
const billingIdField = document.getElementById('billing_id');
const originalUniqueKeyField = document.getElementById('original_unique_key');
const originalContractorCodeField = document.getElementById('original_contractor_code');
const originalBillNoField = document.getElementById('original_bill_no');
const billingSearchModal = new bootstrap.Modal(document.getElementById('billingSearchModal'));
const billingSearchResults = document.getElementById('billingSearchResults');
const billingPermissions = window.billingPermissions || { canEditBillingTracking: false };
let currentContractor = null;

function showAlert(message, type = 'success') {
    alertContainer.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
}

function getValue(id) {
    const el = document.getElementById(id);
    return el ? el.value.trim() : '';
}

function setValue(id, value) {
    const el = document.getElementById(id);
    if (el) {
        el.value = value != null ? value : '';
    }
}

// Contractor Code + Bill No form the unique key. Once an existing record is
// loaded they are frozen, so Update can never move a row to a different key.
function setKeyFieldsLocked(locked) {
    ['contractor_code', 'bill_no'].forEach(function (id) {
        const el = document.getElementById(id);
        if (el) {
            el.readOnly = locked;
            el.classList.toggle('bg-body-secondary', locked);
            el.title = locked
                ? 'Contractor Code and Bill No cannot be changed on an existing entry. Use New to add a different bill.'
                : '';
        }
    });
    const fetchBtn = document.getElementById('btnFetchContractor');
    if (fetchBtn) { fetchBtn.disabled = locked; }
}

function money(value) {
    return Number(value || 0).toFixed(2);
}

function isYesValue(value) {
    return ['yes', 'true', '1'].includes(String(value ?? '').trim().toLowerCase());
}

function calculateTaxes() {
    const billAmount = Number(getValue('bill_amount'));
    if (Number.isNaN(billAmount) || billAmount <= 0) {
        setValue('tds', '');
        setValue('ewt', '');
        setValue('gst', '');
        setValue('payable_amount', '');
        return;
    }

    const panNumber = getValue('pan_number').toUpperCase();
    const tdsRate = panNumber.includes('F') ? 0.02 : 0.01;
    const tds = billAmount * tdsRate;
    const ewt = billAmount * 0.01;
    const gst = currentContractor && isYesValue(currentContractor.GSTApplicable) ? billAmount * 0.18 : 0;

    setValue('tds', money(tds));
    setValue('ewt', money(ewt));
    setValue('gst', money(gst));
    setValue('payable_amount', money(billAmount - (tds + ewt + gst)));
}

function validateBillingForm() {
    const contractorCode = getValue('contractor_code');
    const agencyName = getValue('agency_name');
    const contactNo = getValue('contractor_contact');
    const billNo = getValue('bill_no');
    const billDate = getValue('bill_date');
    const billAmount = getValue('bill_amount');

    if (!contractorCode) {
        return 'Contractor Code is required.';
    }
    if (!agencyName) {
        return 'Contractor Agency Name is required.';
    }
    if (!contactNo) {
        return 'Contractor Contact No is required.';
    }
    if (!/^[0-9]+$/.test(contactNo)) {
        return 'Contractor Contact No must contain only digits.';
    }
    if (!billNo) {
        return 'Bill No / Deb Remarks is required.';
    }
    if (!billDate) {
        return 'Bill Date is required.';
    }
    if (!billAmount || Number.isNaN(Number(billAmount))) {
        return 'Bill Amount must be a valid number.';
    }
    return null;
}

function clearBillingForm() {
    const branchName = getValue('branch_name');
    const contractorLocation = getValue('contractor_location');
    billingForm.reset();
    billingIdField.value = '';
    originalUniqueKeyField.value = '';
    originalContractorCodeField.value = '';
    originalBillNoField.value = '';
    currentContractor = null;
    setKeyFieldsLocked(false);
    setValue('branch_name', branchName);
    setValue('contractor_location', contractorLocation);
}

function buildBillingPayload() {
    return {
        BillingID: billingIdField.value || null,
        OriginalUniquekey: originalUniqueKeyField.value || `${getValue('contractor_code')}_${getValue('bill_no')}`,
        OriginalContractorCode: originalContractorCodeField.value || getValue('contractor_code'),
        OriginalBillNoDebRemarks: originalBillNoField.value || getValue('bill_no'),
        BranchName: getValue('branch_name'),
        ContractorLocation: getValue('contractor_location'),
        ContractorCode: getValue('contractor_code'),
        ContractorAgencyName: getValue('agency_name'),
        ContractorEmailID: getValue('contractor_email'),
        ContractorContactNo: getValue('contractor_contact'),
        OwnerName: getValue('owner_name'),
        LONumberCrRemarks: getValue('lo_number'),
        SiteProjectName: getValue('site_project'),
        VoucherType: getValue('voucher_type'),
        WorkOrderNo: getValue('work_order_no'),
        WorkOrderDate: getValue('work_order_date'),
        TCVValue: getValue('tcv_value'),
        BillSentDate: getValue('bill_sent_date'),
        BillNoDebRemarks: getValue('bill_no'),
        BillDate: getValue('bill_date'),
        BillAmount: getValue('bill_amount'),
        BillStage: getValue('bill_stage'),
        BillRecdDate: getValue('bill_recd_date'),
        ProjectPayment: getValue('project_payment'),
        ZohoDoc: getValue('zoho_doc'),
        TallyName: getValue('tally_name'),
        InstRemarks: getValue('inst_remarks'),
        BillGivenHOD: getValue('bill_given_hod'),
        BillRecdFromHOD: getValue('bill_recd_hod'),
        BillSubmittedToAcctDate: getValue('bill_submitted_acct_date'),
        AccountNumber: getValue('account_number'),
        BankName: getValue('bank_name'),
        IFSCCode: getValue('ifsc_code'),
        PANNumber: getValue('pan_number'),
        TDS: getValue('tds'),
        EWT: getValue('ewt'),
        GST: getValue('gst'),
        PayableAmount: getValue('payable_amount'),
        PaymentDate: getValue('payment_date'),
        UTRNumber: getValue('utr_number'),
        StatusInfo: getValue('status_info'),
        AcctRemarks: getValue('acct_remarks')
    };
}

function populateBillingForm(data) {
    if (!data) return;

    billingIdField.value = data.BillingID || '';
    originalUniqueKeyField.value = data.Uniquekey || '';
    originalContractorCodeField.value = data.ContractorCode || '';
    originalBillNoField.value = data.BillNoDebRemarks || '';
    setKeyFieldsLocked(true);
    setValue('branch_name', data.BranchName);
    setValue('contractor_location', data.ContractorLocation || '');
    setValue('contractor_code', data.ContractorCode);
    setValue('agency_name', data.ContractorAgencyName);
    setValue('contractor_email', data.ContractorEmailID);
    setValue('contractor_contact', data.ContractorContactNo);
    setValue('owner_name', data.OwnerName);
    setValue('lo_number', data.LONumberCrRemarks);
    setValue('site_project', data.SiteProjectName);
    setValue('voucher_type', data.VoucherType);
    setValue('work_order_no', data.WorkOrderNo);
    setValue('work_order_date', data.WorkOrderDate);
    setValue('tcv_value', data.TCVValue);
    setValue('bill_sent_date', data.BillSentDate);
    setValue('bill_no', data.BillNoDebRemarks);
    setValue('bill_date', data.BillDate);
    setValue('bill_amount', data.BillAmount);
    setValue('bill_stage', data.BillStage);
    setValue('bill_recd_date', data.BillRecdDate);
    setValue('project_payment', data.ProjectPayment);
    setValue('zoho_doc', data.ZohoDoc);
    setValue('tally_name', data.TallyName);
    setValue('inst_remarks', data.InstRemarks);
    setValue('bill_given_hod', data.BillGivenHOD);
    setValue('bill_recd_hod', data.BillRecdFromHOD);
    setValue('bill_submitted_acct_date', data.BillSubmittedToAcctDate);
    setValue('account_number', data.AccountNumber);
    setValue('bank_name', data.BankName);
    setValue('ifsc_code', data.IFSCCode);
    setValue('pan_number', data.PANNumber);
    setValue('tds', data.TDS);
    setValue('ewt', data.EWT);
    setValue('gst', data.GST);
    setValue('payable_amount', data.PayableAmount);
    setValue('payment_date', data.PaymentDate);
    setValue('utr_number', data.UTRNumber);
    setValue('status_info', data.StatusInfo);
    setValue('acct_remarks', data.AcctRemarks);
}

async function performBillingSearch() {
    const searchTerm = getValue('billingSearchTerm').toUpperCase();

    if (!searchTerm) {
        billingSearchResults.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted">Please enter a unique key.</td>
            </tr>
        `;
        return;
    }

    billingSearchResults.innerHTML = `
        <tr>
            <td colspan="7" class="text-center text-muted">Searching...</td>
        </tr>
    `;

    try {
        const response = await fetch('/search_billing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ searchTerm })
        });

        if (!response.ok) {
            throw new Error('Search request failed.');
        }

        const records = await response.json();
        if (!records.length) {
            billingSearchResults.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted">No billing entries found.</td>
                </tr>
            `;
            return;
        }

        billingSearchResults.innerHTML = records.map(record => `
            <tr>
                <td>${record.Uniquekey || ''}</td>
                <td>${record.ContractorCode || ''}</td>
                <td>${record.ContractorAgencyName || ''}</td>
                <td>${record.BillNoDebRemarks || ''}</td>
                <td>${record.BillDate || ''}</td>
                <td>${record.BillAmount != null ? record.BillAmount : ''}</td>
                <td class="text-end">
                    <button type="button" class="btn btn-sm btn-primary select-billing" data-id="${record.BillingID}">Select</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        billingSearchResults.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-danger">${error.message}</td>
            </tr>
        `;
    }
}

async function loadBillingEntry(billingId) {
    try {
        const response = await fetch(`/get_billing/${encodeURIComponent(billingId)}`);
        if (!response.ok) {
            throw new Error('Unable to load billing entry.');
        }

        const data = await response.json();
        populateBillingForm(data);
        billingSearchModal.hide();
        await loadContractorByCode();
        showAlert('Billing entry loaded successfully.', 'success');
    } catch (error) {
        showAlert(error.message, 'danger');
    }
}

async function loadContractorByCode() {
    const code = getValue('contractor_code').toUpperCase();
    if (!code) {
        showAlert('Please enter a contractor code.', 'warning');
        return;
    }
    setValue('contractor_code', code);
    try {
        const resp = await fetch(`/get_contractor?code=${encodeURIComponent(code)}`);
        if (!resp.ok) {
            showAlert('No contractor found for the provided code.', 'warning');
            return;
        }
        const c = await resp.json();
        currentContractor = c;
        setValue('contractor_location', c.MainBranch || '');
        setValue('contractor_code', c.ContractorCode || getValue('contractor_code'));
        setValue('agency_name', c.LedgerName || getValue('agency_name'));
        setValue('contractor_email', c.EmailID || getValue('contractor_email'));
        setValue('contractor_contact', c.MobileNo || getValue('contractor_contact'));
        setValue('owner_name', c.OwnerName || getValue('owner_name'));
        setValue('account_number', c.AccountNumber || getValue('account_number'));
        setValue('bank_name', c.BankName || getValue('bank_name'));
        setValue('ifsc_code', c.IFSCCode || getValue('ifsc_code'));
        setValue('pan_number', c.PANNo || getValue('pan_number'));
        calculateTaxes();
        showAlert('Contractor fields autofilled from master.', 'info');
    } catch (error) {
        showAlert('Failed to fetch contractor details: ' + error.message, 'danger');
    }
}

// Autofill contractor fields when contractor code is entered
document.getElementById('contractor_code').addEventListener('blur', function () {
    if (getValue('contractor_code')) {
        loadContractorByCode();
    }
});

document.getElementById('contractor_code').addEventListener('keydown', function (event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        loadContractorByCode();
    }
});

document.getElementById('btnFetchContractor').addEventListener('click', function () {
    loadContractorByCode();
});

document.getElementById('bill_amount').addEventListener('input', calculateTaxes);

async function updateBilling() {
    const billingId = billingIdField.value;
    if (!billingId) {
        showAlert('Please select an existing billing entry before updating.', 'warning');
        return;
    }

    const error = validateBillingForm();
    if (error) {
        showAlert(error, 'danger');
        return;
    }

    const payload = buildBillingPayload();

    try {
        const response = await fetch('/update_billing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.message || 'Billing update failed.');
        }

        showAlert(result.message || 'Billing entry updated successfully.', 'success');
    } catch (error) {
        showAlert(error.message, 'danger');
    }
}

async function deleteBilling() {
    const billingId = billingIdField.value;
    if (!billingId) {
        showAlert('Please select a billing entry to delete.', 'warning');
        return;
    }

    if (!confirm('Are you sure you want to delete this billing entry?')) {
        return;
    }

    try {
        const response = await fetch('/delete_billing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ BillingID: billingId })
        });

        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.message || 'Delete request failed.');
        }

        clearBillingForm();
        showAlert(result.message || 'Billing entry deleted successfully.', 'success');
    } catch (error) {
        showAlert(error.message, 'danger');
    }
}

billingForm.addEventListener('submit', function (event) {
    const error = validateBillingForm();
    if (error) {
        event.preventDefault();
        showAlert(error, 'danger');
    }
});

document.getElementById('btnNew').addEventListener('click', function () {
    clearBillingForm();
    showAlert('Billing form cleared. Ready for new entry.', 'info');
});

document.getElementById('btnUpdate').addEventListener('click', function () {
    updateBilling();
});

// Delete is not rendered for branch logins, so bind only when it exists.
const btnDelete = document.getElementById('btnDelete');
if (btnDelete) {
    btnDelete.addEventListener('click', function () {
        deleteBilling();
    });
}

document.getElementById('btnSearchBilling').addEventListener('click', function () {
    setValue('billingSearchTerm', getValue('contractor_code'));
    billingSearchModal.show();
});

document.getElementById('btnRunBillingSearch').addEventListener('click', performBillingSearch);

document.getElementById('billingSearchTerm').addEventListener('keydown', function (event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        performBillingSearch();
    }
});

billingSearchResults.addEventListener('click', function (event) {
    if (event.target.classList.contains('select-billing')) {
        loadBillingEntry(event.target.dataset.id);
    }
});
