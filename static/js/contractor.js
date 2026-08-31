const alertContainer = document.getElementById('alertContainer');
const searchModal = new bootstrap.Modal(document.getElementById('searchModal'));
const searchResults = document.getElementById('searchResults');
const contractorForm = document.getElementById('contractorForm');

function showAlert(message, type = 'success') {
    alertContainer.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
}

function getValue(id) {
    return document.getElementById(id).value.trim();
}

function setValue(id, value) {
    const field = document.getElementById(id);
    const cleanValue = value || '';
    if (field && field.tagName === 'SELECT' && cleanValue) {
        const hasOption = Array.from(field.options).some(option => option.value === cleanValue);
        if (!hasOption) {
            field.add(new Option(cleanValue, cleanValue));
        }
    }
    field.value = cleanValue;
}

function isValidEmail(email) {
    return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email);
}

function validateContractorForm() {
    const branch = getValue('branch');
    const workType = getValue('work_type');
    const ledgerName = getValue('ledger_name');
    const address1 = getValue('address1');
    const state = getValue('state');
    const mobile = getValue('mobile');
    const pan = getValue('pan').toUpperCase();
    const email = getValue('email');
    const gstApplicable = getValue('gst_applicable');
    const gstin = getValue('gstin').toUpperCase();

    if (!branch) {
        return 'Branch is required.';
    }
    if (!workType) {
        return 'Work Type is required.';
    }
    if (!ledgerName) {
        return 'Ledger Name is required.';
    }
    if (!address1) {
        return 'Address 1 is required.';
    }
    if (!state) {
        return 'State is required.';
    }
    if (!mobile || !/^\d{10}$/.test(mobile)) {
        return 'Mobile number must be exactly 10 digits.';
    }
    if (!pan || pan.length !== 10) {
        return 'PAN must be exactly 10 characters.';
    }
    if (email && !isValidEmail(email)) {
        return 'Please enter a valid email address.';
    }
    if (gstApplicable === 'Yes' && gstin.length !== 15) {
        return 'GSTIN must be exactly 15 characters when GST Applicable is Yes.';
    }
    return null;
}

function generateContractorCode() {
    const branch = getValue('branch');
    const workType = getValue('work_type');
    const pan = getValue('pan').toUpperCase();

    if (branch.length >= 2 && workType.length >= 2 && pan.length === 10) {
        const code = `${branch.substring(0, 2).toUpperCase()}${workType.substring(0, 2).toUpperCase()}${pan.substring(6)}`;
        setValue('contractor_code', code);
    }
}

function clearForm() {
    contractorForm.reset();
    setValue('contractor_code', '');
}

async function performSearch() {
    const searchBy = getValue('searchBy');
    const searchTerm = getValue('searchTerm');

    if (!searchTerm) {
        searchResults.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted">Please enter a search term.</td>
            </tr>
        `;
        return;
    }

    searchResults.innerHTML = `
        <tr>
            <td colspan="7" class="text-center text-muted">Searching...</td>
        </tr>
    `;

    try {
        const response = await fetch('/search_contractor', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ searchBy, searchTerm })
        });

        if (!response.ok) {
            throw new Error('Search request failed.');
        }

        const records = await response.json();

        if (!records.length) {
            searchResults.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted">No matching contractors found.</td>
                </tr>
            `;
            return;
        }

        searchResults.innerHTML = records.map(record => `
            <tr>
                <td>${record.ContractorCode}</td>
                <td>${record.LedgerName || ''}</td>
                <td>${record.OwnerName || ''}</td>
                <td>${record.MobileNo || ''}</td>
                <td>${record.MainBranch || ''}</td>
                <td>${record.WorkType || ''}</td>
                <td class="text-end">
                    <button type="button" class="btn btn-sm btn-primary select-contractor" data-code="${record.ContractorCode}">Select</button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        searchResults.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-danger">${error.message}</td>
            </tr>
        `;
    }
}

async function loadContractor(contractorCode) {
    try {
        const response = await fetch(`/get_contractor/${encodeURIComponent(contractorCode)}`);
        if (!response.ok) {
            throw new Error('Unable to load contractor details.');
        }
        const contractor = await response.json();

        const mapping = {
            ContractorCode: 'contractor_code',
            MainBranch: 'branch',
            WorkType: 'work_type',
            LedgerCode: 'ledger_code',
            LedgerName: 'ledger_name',
            OwnerName: 'owner_name',
            GroupName: 'group_name',
            MailingName: 'mailing_name',
            Address1: 'address1',
            Address2: 'address2',
            StateName: 'state',
            PinCode: 'pincode',
            ContactPerson: 'contactperson',
            PhoneNo: 'phone',
            MobileNo: 'mobile',
            EmailID: 'email',
            PANNo: 'pan',
            GSTApplicable: 'gst_applicable',
            GSTRegistrationType: 'gst_type',
            GSTIN: 'gstin',
            TDSApplicable: 'tds_applicable',
            DeducteeType: 'deductee_type',
            DeductTDSSameVoucher: 'samevoucher',
            IgnoreSurcharge: 'surcharge',
            AccountNumber: 'accountno',
            IFSCCode: 'ifsc',
            BankName: 'bankname',
            BankRefID: 'bankref',
            BankTransactionType: 'banktype',
            BillwiseApplicable: 'billwise',
            CreditPeriod: 'creditperiod',
            PartyType: 'partytype',
            EcommerceOperator: 'ecommerce',
            CrossUsing: 'crossusing'
        };

        Object.entries(mapping).forEach(([key, fieldId]) => {
            if (contractor[key] !== undefined && document.getElementById(fieldId)) {
                setValue(fieldId, contractor[key]);
            }
        });

        searchModal.hide();
        showAlert('Contractor loaded successfully.', 'success');
    } catch (error) {
        showAlert(error.message, 'danger');
    }
}

async function sendUpdateRequest() {
    const contractorCode = getValue('contractor_code');
    if (!contractorCode) {
        showAlert('Please load a contractor before updating.', 'warning');
        return;
    }

    const error = validateContractorForm();
    if (error) {
        showAlert(error, 'danger');
        return;
    }

    const payload = {
        ContractorCode: contractorCode,
        MainBranch: getValue('branch'),
        WorkType: getValue('work_type'),
        LedgerCode: getValue('ledger_code'),
        LedgerName: getValue('ledger_name'),
        OwnerName: getValue('owner_name'),
        GroupName: getValue('group_name'),
        MailingName: getValue('mailing_name'),
        Address1: getValue('address1'),
        Address2: getValue('address2'),
        StateName: getValue('state'),
        PinCode: getValue('pincode'),
        ContactPerson: getValue('contactperson'),
        PhoneNo: getValue('phone'),
        MobileNo: getValue('mobile'),
        EmailID: getValue('email'),
        PANNo: getValue('pan').toUpperCase(),
        GSTApplicable: getValue('gst_applicable'),
        GSTRegistrationType: getValue('gst_type'),
        GSTIN: getValue('gstin').toUpperCase(),
        TDSApplicable: getValue('tds_applicable'),
        DeducteeType: getValue('deductee_type'),
        DeductTDSSameVoucher: getValue('samevoucher'),
        IgnoreSurcharge: getValue('surcharge'),
        AccountNumber: getValue('accountno'),
        IFSCCode: getValue('ifsc').toUpperCase(),
        BankName: getValue('bankname'),
        BankRefID: getValue('bankref'),
        BankTransactionType: getValue('banktype'),
        BillwiseApplicable: getValue('billwise'),
        CreditPeriod: getValue('creditperiod'),
        PartyType: getValue('partytype'),
        EcommerceOperator: getValue('ecommerce'),
        CrossUsing: getValue('crossusing')
    };

    try {
        const response = await fetch('/update_contractor', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        if (!response.ok || result.status !== 'success') {
            throw new Error(result.message || 'Failed to update contractor.');
        }

        showAlert(result.message, 'success');
    } catch (error) {
        showAlert(error.message, 'danger');
    }
}

async function sendDeleteRequest() {
    const contractorCode = getValue('contractor_code');
    if (!contractorCode) {
        showAlert('Please load a contractor before deleting.', 'warning');
        return;
    }

    if (!confirm('Are you sure you want to delete this contractor?')) {
        return;
    }

    try {
        const response = await fetch('/delete_contractor', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ContractorCode: contractorCode })
        });

        const result = await response.json();
        if (!response.ok || result.status !== 'success') {
            throw new Error(result.message || 'Failed to delete contractor.');
        }

        clearForm();
        showAlert(result.message, 'success');
    } catch (error) {
        showAlert(error.message, 'danger');
    }
}

contractorForm.addEventListener('submit', event => {
    const error = validateContractorForm();
    if (error) {
        event.preventDefault();
        showAlert(error, 'danger');
    }
});

document.getElementById('work_type').addEventListener('change', generateContractorCode);
document.getElementById('pan').addEventListener('input', event => {
    event.target.value = event.target.value.toUpperCase();
    generateContractorCode();
});

document.getElementById('btnNew').addEventListener('click', clearForm);
document.getElementById('btnSearch').addEventListener('click', () => searchModal.show());
document.getElementById('btnRunSearch').addEventListener('click', performSearch);
searchResults.addEventListener('click', event => {
    if (event.target.classList.contains('select-contractor')) {
        const contractorCode = event.target.dataset.code;
        loadContractor(contractorCode);
    }
});
document.getElementById('btnUpdate').addEventListener('click', sendUpdateRequest);
const deleteButton = document.getElementById('btnDelete');
if (deleteButton) {
    deleteButton.addEventListener('click', sendDeleteRequest);
}
