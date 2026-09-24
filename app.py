from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import csv
import os
from io import BytesIO, StringIO
import re
import uuid
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, session, flash, jsonify, Response, send_file, url_for
from werkzeug.utils import secure_filename
from database import get_connection, close_tracked_connections

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY must be set in the environment or .env file.")


@app.teardown_appcontext
def _close_db_connections(exc):
    """Close any DB connection a request left open, even if it raised."""
    close_tracked_connections(exc)


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EXCEL_ILLEGAL_CHAR_REGEX = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]")
UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
DEFAULT_APP_SETTINGS = {
    "brand_name": "Escon Management System",
    "company_name": "Escon Elevators India Pvt. Ltd.",
    "main_image_url": "",
    "login_image_url": "",
    "font_family": "Segoe UI",
    "base_font_size": "16",
    "primary_color": "#003366",
    "secondary_color": "#0B5394",
    "accent_color": "#0b65c9",
    "text_color": "#172033",
    "page_background": "#f4f6f9",
    "card_background": "#ffffff"
}

ALLOWED_SEARCH_COLUMNS = {
    "ContractorCode": "ContractorCode",
    "LedgerName": "LedgerName",
    "OwnerName": "OwnerName",
    "PANNo": "PANNo",
    "MobileNo": "MobileNo"
}

# Billing permissions.  These names are database column names (the SQL column
# is BranchName, although it is displayed to users as "Branch Name").
BRANCH_ALLOWED_FIELDS = [
    "BranchName", "ContractorCode", "ContractorAgencyName",
    "ContractorEmailID", "ContractorContactNo", "OwnerName",
    "LONumberCrRemarks", "SiteProjectName", "VoucherType", "WorkOrderNo",
    "WorkOrderDate", "TCVValue", "BillSentDate", "BillNoDebRemarks",
    "BillDate", "BillAmount", "BillStage"
]

# User-specific billing update permissions
SANDESH_ALLOWED_FIELDS = [
    "BranchName",
    "ContractorLocation",
    "BillRecdDate",
    "ProjectPayment",
    "ZohoDoc",
    "TallyName",
    "InstRemarks",
    "BillGivenHOD",
    "BillRecdFromHOD",
    "BillSubmittedToAcctDate"
]

UDAY_ALLOWED_FIELDS = [
    "AccountNumber",
    "BankName",
    "IFSCCode",
    "PANNumber",
    "TDS",
    "EWT",
    "GST",
    "PayableAmount",
    "PaymentDate",
    "UTRNumber",
    "StatusInfo",
    "AcctRemarks"
]

H007_ONLY_FIELDS = SANDESH_ALLOWED_FIELDS + UDAY_ALLOWED_FIELDS

FORM_FIELDS = {
    "contractor": {
        "title": "Contractor Master",
        "fields": {
            "ContractorCode": "Contractor Code",
            "MainBranch": "Main Branch",
            "WorkType": "Work Type",
            "LedgerName": "Ledger Name",
            "LedgerCode": "Ledger Code",
            "OwnerName": "Owner Name",
            "GroupName": "Group Name",
            "MailingName": "Mailing Name",
            "Address1": "Address 1",
            "Address2": "Address 2",
            "StateName": "State",
            "PinCode": "Pin Code",
            "ContactPerson": "Contact Person",
            "PhoneNo": "Phone No",
            "MobileNo": "Mobile No",
            "EmailID": "Email ID",
            "PANNo": "PAN No",
            "GSTApplicable": "GST Applicable",
            "GSTRegistrationType": "GST Registration Type",
            "GSTIN": "GSTIN/UIN",
            "TDSApplicable": "TDS Applicable",
            "DeducteeType": "Deductee Type",
            "DeductTDSSameVoucher": "Deduct TDS in Same Voucher",
            "IgnoreSurcharge": "Ignore Surcharge Exemption",
            "AccountNumber": "Account Number",
            "IFSCCode": "IFSC Code",
            "BankName": "Bank Name",
            "BankRefID": "Bank Ref ID",
            "BankTransactionType": "Bank Transaction Type",
            "BillwiseApplicable": "Billwise Applicable",
            "CreditPeriod": "Credit Period",
            "PartyType": "Party Type",
            "EcommerceOperator": "E-Commerce Operator",
            "CrossUsing": "Cross Using"
        }
    },
    "billing": {
        "title": "Billing Schedule",
        "fields": {
            "BranchName": "Branch Name",
            "ContractorLocation": "Contractor Location",
            "ContractorCode": "Contractor Code",
            "ContractorAgencyName": "Contractor Agency Name",
            "ContractorEmailID": "Contractor Email ID",
            "ContractorContactNo": "Contractor Contact No",
            "OwnerName": "Owner Name",
            "LONumberCrRemarks": "LO Number / Cr Remarks",
            "SiteProjectName": "Site Name / Project Name",
            "VoucherType": "Voucher Type",
            "WorkOrderNo": "Work Order No",
            "WorkOrderDate": "Work Order Date",
            "TCVValue": "TCV Value",
            "BillSentDate": "Bill Sent Date",
            "BillNoDebRemarks": "Bill No / Deb Remarks",
            "BillDate": "Bill Date",
            "BillAmount": "Bill Amount",
            "BillStage": "Bill Stage",
            "BillRecdDate": "Bill Recd Date",
            "ProjectPayment": "Project Payment",
            "ZohoDoc": "Zoho doc",
            "TallyName": "Tally Name",
            "InstRemarks": "Inst Remarks",
            "BillGivenHOD": "Bill Given HOD",
            "BillRecdFromHOD": "Bill Recd From HOD",
            "BillSubmittedToAcctDate": "Bill Submitted to Acct Date",
            "AccountNumber": "Account Number",
            "BankName": "Bank Name",
            "IFSCCode": "IFSC Code",
            "PANNumber": "PAN Number",
            "TDS": "TDS",
            "EWT": "EWT",
            "GST": "GST",
            "PayableAmount": "Payable Amount",
            "PaymentDate": "Payment Date",
            "UTRNumber": "UTR Number",
            "StatusInfo": "Status Info",
            "AcctRemarks": "Acct Remarks"
        }
    }
}

REQUIRED_FORM_FIELDS = {
    "contractor": {
        "MainBranch",
        "WorkType",
        "LedgerName",
        "Address1",
        "StateName",
        "MobileNo",
        "PANNo"
    },
    "billing": set()
}

FORM_TABLES = {
    "contractor": "ADContractorMaster",
    "billing": "AdBillingMaster"
}

BULK_UPLOAD_CONFIG = {
    "contractor": {
        "title": "Contractor Master",
        "table": "ADContractorMaster",
        "filename": "contractor_master_upload_template"
    },
    "billing": {
        "title": "Billing Schedule",
        "table": "AdBillingMaster",
        "filename": "billing_schedule_upload_template"
    }
}


def validate_email(email):
    return EMAIL_REGEX.match(email) is not None


def row_unique_key(row):
    """Read the unique key off a result row.

    The SQL column is ``UniqueKey``; the application spells it ``Uniquekey``
    throughout. SQL Server does not care, but attribute access on a result row
    is case-sensitive, so read it defensively.
    """
    return getattr(row, "UniqueKey", None) or getattr(row, "Uniquekey", None)


def text_value(value):
    """Trim a payload value. JSON nulls arrive as None, so .strip() is unsafe."""
    return (value or "").strip()


def to_bit(value):
    return 1 if str(value).strip().lower() in ("yes", "true", "1") else 0


def is_h007_user(username=None):
    return (username or session.get("username", "")).strip().lower() == "h007"


def normalize_login_value(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def is_admin_user():
    return (session.get("role") or "").strip().lower() == "admin"


def is_sandesh_or_uday_user():
    return normalize_login_value(session.get("username")) in {"sandesh", "uday"}


def is_billing_admin_user():
    """Full billing rights require admin role and cannot override named owners."""
    return is_admin_user() and not is_sandesh_or_uday_user()


def get_allowed_billing_update_fields(username=None):
    current_user = (username or session.get("username") or "").strip()
    normalized_user = normalize_login_value(current_user)
    if normalized_user == "sandesh":
        return set(SANDESH_ALLOWED_FIELDS)
    if normalized_user == "uday":
        return set(UDAY_ALLOWED_FIELDS)
    # Full access belongs to the admin role only. Sandesh/Uday restrictions
    # above deliberately win even if their UserLogin role was set to admin.
    if is_billing_admin_user():
        return set(FORM_FIELDS["billing"]["fields"].keys())
    # Every other branch login may maintain the operational billing fields.
    return set(BRANCH_ALLOWED_FIELDS)


def can_edit_billing_tracking_fields():
    return bool(get_allowed_billing_update_fields())


def can_bulk_upload_masters():
    allowed_values = {"h007", "headoffice"}
    return (
        is_admin_user()
        or normalize_login_value(session.get("username")) in allowed_values
        or normalize_login_value(session.get("role")) in allowed_values
        or normalize_login_value(session.get("branch")) in allowed_values
    )


def can_bulk_update_billing():
    """Any authenticated login may use the branch-scoped billing uploader."""
    return bool(session.get("username"))


def can_bulk_upload_all_branches():
    """Billing owners and full admins may work with records across branches."""
    return is_sandesh_or_uday_user() or is_billing_admin_user()


def get_billing_bulk_allowed_fields():
    """Return fields that the current user may supply in a billing upload."""
    normalized_user = normalize_login_value(session.get("username"))
    if normalized_user == "sandesh":
        return set(SANDESH_ALLOWED_FIELDS)
    if normalized_user == "uday":
        return set(UDAY_ALLOWED_FIELDS)
    if is_billing_admin_user():
        return None  # Admin may use every ordinary, writable table column.
    return set(BRANCH_ALLOWED_FIELDS)


def get_billing_bulk_columns(table_columns=None):
    """Columns exposed in the billing bulk template for the current login.

    The two key columns are always present because they identify a row; they
    are not permission to modify those columns on an existing billing entry.
    """
    key_columns = ["ContractorCode", "BillNoDebRemarks"]
    allowed_fields = get_billing_bulk_allowed_fields()
    available_columns = set(table_columns) if table_columns is not None else None
    if allowed_fields is None:
        result = key_columns + [
            field for field in FORM_FIELDS["billing"]["fields"]
            if field not in key_columns
        ]
    else:
        result = key_columns + [
            field for field in FORM_FIELDS["billing"]["fields"]
            if field in allowed_fields and field not in key_columns
        ]
    return [field for field in result if available_columns is None or field in available_columns]


def require_billing_bulk_upload_redirect(target="/billing"):
    if not can_bulk_update_billing():
        flash("Please log in to use billing bulk upload.", "danger")
        return redirect(target)
    return None


def can_edit_contractor_branch():
    return can_bulk_upload_masters()


def can_admin_manage_records():
    return is_admin_user()


def can_save_billing():
    """Branch users create operational bills; Sandesh/Uday update their stages only."""
    if "username" not in session:
        return False
    return normalize_login_value(session.get("username")) not in {"sandesh", "uday"}


def can_delete_billing():
    """Deleting billing records stays with admin / head office only."""
    return not is_sandesh_or_uday_user() and (is_billing_admin_user() or is_head_office_user())


def can_select_billing_branch():
    """Admin, head office, and Sandesh may select a billing branch."""
    return (
        is_billing_admin_user()
        or is_head_office_user()
        or normalize_login_value(session.get("username")) == "sandesh"
    )


def require_billing_edit_json():
    # Updating an existing bill is intentionally broader than creating one:
    # Sandesh and Uday may update their assigned columns but may not create a
    # new billing record.
    if "username" not in session or not can_edit_billing_tracking_fields():
        return jsonify({"status": "error", "message": "Please log in again."}), 401
    return None


def require_billing_delete_json():
    if not can_delete_billing():
        return jsonify({"status": "error", "message": "Only admin or head office can delete records."}), 403
    return None


def require_admin_json():
    # Download permission must not grant record-maintenance permission.
    if not is_admin_user():
        return jsonify({"status": "error", "message": "Only admin login can modify records."}), 403
    return None


def require_admin_redirect(target):
    if not is_admin_user():
        flash("Only admin login can modify records.", "danger")
        return redirect(target)
    return None


def require_bulk_upload_redirect(target="/dashboard"):
    if not can_bulk_upload_masters():
        flash("Only admin or headoffice login can upload bulk entries.", "danger")
        return redirect(target)
    return None


def ensure_app_settings_table(cursor):
    cursor.execute(
        """
        IF OBJECT_ID('dbo.AppSettings', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.AppSettings (
                SettingName NVARCHAR(100) NOT NULL PRIMARY KEY,
                SettingValue NVARCHAR(MAX) NULL,
                ModifiedBy NVARCHAR(100) NULL,
                ModifiedDate DATETIME NULL
            )
        END
        """
    )


def get_app_settings():
    settings = dict(DEFAULT_APP_SETTINGS)
    conn = get_connection()
    cursor = conn.cursor()
    ensure_app_settings_table(cursor)
    cursor.execute("SELECT SettingName, SettingValue FROM AppSettings")
    for row in cursor.fetchall():
        if row.SettingName in settings:
            settings[row.SettingName] = row.SettingValue or ""
    cursor.close()
    conn.close()
    return settings


def save_app_setting(cursor, name, value):
    cursor.execute(
        """
        MERGE dbo.AppSettings AS target
        USING (SELECT ? AS SettingName) AS source
        ON target.SettingName = source.SettingName
        WHEN MATCHED THEN
            UPDATE SET SettingValue = ?, ModifiedBy = ?, ModifiedDate = ?
        WHEN NOT MATCHED THEN
            INSERT (SettingName, SettingValue, ModifiedBy, ModifiedDate)
            VALUES (?, ?, ?, ?);
        """,
        (
            name,
            value,
            session.get("username"),
            datetime.now(),
            name,
            value,
            session.get("username"),
            datetime.now()
        )
    )


def allowed_image_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def normalize_hex_color(value, fallback):
    value = (value or "").strip()
    if re.match(r"^#[0-9A-Fa-f]{6}$", value):
        return value
    return fallback


def normalize_font_size(value, fallback="16"):
    try:
        size = int(str(value or "").strip())
    except ValueError:
        return fallback
    if 12 <= size <= 24:
        return str(size)
    return fallback


@app.context_processor
def inject_app_settings():
    try:
        return {"app_settings": get_app_settings()}
    except Exception:
        return {"app_settings": dict(DEFAULT_APP_SETTINGS)}


def ensure_form_field_config_table(cursor):
    cursor.execute(
        """
        IF OBJECT_ID('dbo.FormFieldConfig', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.FormFieldConfig (
                FormName NVARCHAR(50) NOT NULL,
                FieldName NVARCHAR(100) NOT NULL,
                IsVisible BIT NOT NULL CONSTRAINT DF_FormFieldConfig_IsVisible DEFAULT 1,
                ModifiedBy NVARCHAR(100) NULL,
                ModifiedDate DATETIME NULL,
                CONSTRAINT PK_FormFieldConfig PRIMARY KEY (FormName, FieldName)
            )
        END
        """
    )
    cursor.execute(
        """
        IF COL_LENGTH('dbo.FormFieldConfig', 'FieldLabel') IS NULL
            ALTER TABLE dbo.FormFieldConfig ADD FieldLabel NVARCHAR(150) NULL
        """
    )
    cursor.execute(
        """
        IF COL_LENGTH('dbo.FormFieldConfig', 'IsCustom') IS NULL
            ALTER TABLE dbo.FormFieldConfig ADD IsCustom BIT NOT NULL CONSTRAINT DF_FormFieldConfig_IsCustom DEFAULT 0
        """
    )
    cursor.execute(
        """
        IF COL_LENGTH('dbo.FormFieldConfig', 'FieldType') IS NULL
            ALTER TABLE dbo.FormFieldConfig ADD FieldType NVARCHAR(30) NULL
        """
    )
    cursor.execute(
        """
        IF COL_LENGTH('dbo.FormFieldConfig', 'FieldOptions') IS NULL
            ALTER TABLE dbo.FormFieldConfig ADD FieldOptions NVARCHAR(MAX) NULL
        """
    )


DEFAULT_FIELD_TYPES = {
    "EmailID": "email",
    "ContractorEmailID": "email",
    "WorkOrderDate": "date",
    "BillSentDate": "date",
    "BillDate": "date",
    "BillRecdDate": "date",
    "BillSubmittedToAcctDate": "date",
    "PaymentDate": "date",
    "TCVValue": "number",
    "BillAmount": "number",
    "PayableAmount": "number",
    "CreditPeriod": "number"
}

FIELD_TYPE_OPTIONS = {
    "text": "Open Box",
    "textarea": "Large Open Box",
    "dropdown": "Dropdown",
    "number": "Number",
    "date": "Date",
    "email": "Email"
}


def default_field_type(field_name):
    return DEFAULT_FIELD_TYPES.get(field_name, "text")


def is_required_form_field(form_name, field_name):
    return field_name in REQUIRED_FORM_FIELDS.get(form_name, set())


def get_effective_required_fields(form_name):
    visibility = get_form_field_visibility(form_name)
    return {
        field_name
        for field_name in REQUIRED_FORM_FIELDS.get(form_name, set())
        if visibility.get(field_name, True)
    }


def get_form_field_configs(form_name, visible_only=False, custom_only=False):
    base_fields = {} if custom_only else dict(FORM_FIELDS.get(form_name, {}).get("fields", {}))
    configs = {
        field_name: {
            "label": label,
            "type": default_field_type(field_name),
            "options": "",
            "visible": True,
            "custom": False,
            "required": is_required_form_field(form_name, field_name)
        }
        for field_name, label in base_fields.items()
    }

    conn = get_connection()
    cursor = conn.cursor()
    ensure_form_field_config_table(cursor)
    cursor.execute(
        """
        SELECT FieldName, FieldLabel, IsVisible, IsCustom, FieldType, FieldOptions
        FROM FormFieldConfig
        WHERE FormName = ?
        ORDER BY COALESCE(FieldLabel, FieldName)
        """,
        (form_name,)
    )
    for row in cursor.fetchall():
        if custom_only and not row.IsCustom:
            continue
        if row.FieldName not in configs:
            if not row.IsCustom:
                continue
            configs[row.FieldName] = {
                "label": row.FieldName,
                "type": "text",
                "options": "",
                "visible": True,
                "custom": True,
                "required": False
            }

        configs[row.FieldName]["label"] = row.FieldLabel or configs[row.FieldName]["label"]
        configs[row.FieldName]["visible"] = bool(row.IsVisible)
        configs[row.FieldName]["custom"] = bool(row.IsCustom)
        configs[row.FieldName]["type"] = row.FieldType or configs[row.FieldName]["type"]
        configs[row.FieldName]["options"] = row.FieldOptions or ""

    cursor.close()
    conn.close()

    if visible_only:
        configs = {field: config for field, config in configs.items() if config["visible"]}
    return configs


def get_form_field_settings(form_name):
    """Field type overrides the form pages apply to their built-in fields.

    Only fields an admin has explicitly given a type in Field Manager are
    returned. Rows written by a visibility save carry no FieldType, and must
    not disturb controls the page renders deliberately (such as the
    permission-driven Branch Name selector).
    """
    settings = {}
    conn = get_connection()
    cursor = conn.cursor()
    ensure_form_field_config_table(cursor)
    cursor.execute(
        """
        SELECT FieldName, FieldType, FieldOptions
        FROM FormFieldConfig
        WHERE FormName = ? AND FieldType IS NOT NULL AND LTRIM(RTRIM(FieldType)) <> ''
        """,
        (form_name,)
    )
    for row in cursor.fetchall():
        options = [
            option.strip()
            for chunk in (row.FieldOptions or "").splitlines()
            for option in chunk.split(",")
            if option.strip()
        ]
        settings[row.FieldName] = {"type": row.FieldType, "options": options}
    cursor.close()
    conn.close()
    return settings


def get_custom_form_fields(form_name, visible_only=False):
    return {
        field_name: config["label"]
        for field_name, config in get_form_field_configs(form_name, visible_only=visible_only, custom_only=True).items()
    }


def get_configurable_form_fields(form_name):
    return {field_name: config["label"] for field_name, config in get_form_field_configs(form_name).items()}


def get_form_field_visibility(form_name):
    fields = get_configurable_form_fields(form_name)
    visibility = {field: True for field in fields}
    if not fields:
        return visibility

    conn = get_connection()
    cursor = conn.cursor()
    ensure_form_field_config_table(cursor)
    cursor.execute(
        "SELECT FieldName, IsVisible FROM FormFieldConfig WHERE FormName = ?",
        (form_name,)
    )
    for row in cursor.fetchall():
        if row.FieldName in visibility:
            visibility[row.FieldName] = bool(row.IsVisible)
    cursor.close()
    conn.close()
    return visibility


def get_hidden_form_fields(form_name):
    return [field for field, visible in get_form_field_visibility(form_name).items() if not visible]


def save_form_field_visibility(form_name, visible_fields):
    allowed_fields = get_configurable_form_fields(form_name)
    conn = get_connection()
    cursor = conn.cursor()
    ensure_form_field_config_table(cursor)

    for field_name, field_label in allowed_fields.items():
        is_visible = 1 if field_name in visible_fields else 0
        cursor.execute(
            """
            UPDATE FormFieldConfig
            SET IsVisible = ?, ModifiedBy = ?, ModifiedDate = ?
            WHERE FormName = ? AND FieldName = ?
            """,
            (is_visible, session.get("username"), datetime.now(), form_name, field_name)
        )
        if cursor.rowcount == 0:
            cursor.execute(
                """
                INSERT INTO FormFieldConfig (FormName, FieldName, FieldLabel, IsVisible, IsCustom, FieldType, FieldOptions, ModifiedBy, ModifiedDate)
                VALUES (?, ?, ?, ?, 0, ?, '', ?, ?)
                """,
                (form_name, field_name, field_label, is_visible, default_field_type(field_name), session.get("username"), datetime.now())
            )

    conn.commit()
    cursor.close()
    conn.close()


def normalize_custom_field_name(label):
    words = re.findall(r"[A-Za-z0-9]+", label or "")
    if not words:
        return None
    column_name = "Extra_" + "_".join(words)
    return column_name[:100]


def bracket_identifier(identifier):
    return f"[{identifier.replace(']', ']]')}]"


def normalize_field_type(field_type):
    return field_type if field_type in FIELD_TYPE_OPTIONS else "text"


def normalize_field_options(field_options):
    options = []
    for raw_option in re.split(r"[\r\n,]+", field_options or ""):
        option = raw_option.strip()
        if option and option not in options:
            options.append(option)
    return "\n".join(options)


def add_custom_form_field(form_name, field_label, field_type="text", field_options=""):
    if form_name not in FORM_TABLES:
        return "Invalid form selected."

    field_label = (field_label or "").strip()
    if len(field_label) < 2:
        return "Field label is required."

    field_type = normalize_field_type(field_type)
    field_options = normalize_field_options(field_options) if field_type == "dropdown" else ""
    column_name = normalize_custom_field_name(field_label)
    if not column_name:
        return "Please enter a valid field label."

    table_name = FORM_TABLES[form_name]
    conn = get_connection()
    cursor = conn.cursor()
    ensure_form_field_config_table(cursor)

    base_column = column_name
    suffix = 1
    while True:
        cursor.execute(
            "SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID(?) AND name = ?",
            (f"dbo.{table_name}", column_name)
        )
        exists_in_table = cursor.fetchone() is not None
        cursor.execute(
            "SELECT 1 FROM FormFieldConfig WHERE FormName = ? AND FieldName = ?",
            (form_name, column_name)
        )
        exists_in_config = cursor.fetchone() is not None
        if not exists_in_table and not exists_in_config:
            break
        suffix += 1
        column_name = f"{base_column}_{suffix}"

    cursor.execute(
        f"ALTER TABLE dbo.{bracket_identifier(table_name)} ADD {bracket_identifier(column_name)} NVARCHAR(255) NULL"
    )
    cursor.execute(
        """
        INSERT INTO FormFieldConfig (FormName, FieldName, FieldLabel, IsVisible, IsCustom, FieldType, FieldOptions, ModifiedBy, ModifiedDate)
        VALUES (?, ?, ?, 1, 1, ?, ?, ?, ?)
        """,
        (form_name, column_name, field_label, field_type, field_options, session.get("username"), datetime.now())
    )
    conn.commit()
    cursor.close()
    conn.close()
    return None


def collect_custom_values(source, form_name):
    return {
        field_name: (source.get(field_name, "") or "").strip()
        for field_name in get_custom_form_fields(form_name).keys()
    }


def add_custom_values_to_dict(data, row, form_name):
    for field_name in get_custom_form_fields(form_name).keys():
        data[field_name] = getattr(row, field_name, None) if row else None


def update_form_field_settings(form_name, field_name, field_label, field_type, field_options, is_visible):
    if field_name not in get_configurable_form_fields(form_name):
        return "Invalid field selected."

    field_label = (field_label or "").strip()
    if len(field_label) < 2:
        return "Field label is required."

    field_type = normalize_field_type(field_type)
    field_options = normalize_field_options(field_options) if field_type == "dropdown" else ""
    conn = get_connection()
    cursor = conn.cursor()
    ensure_form_field_config_table(cursor)
    cursor.execute(
        """
        UPDATE FormFieldConfig
        SET FieldLabel = ?, FieldType = ?, FieldOptions = ?, IsVisible = ?, ModifiedBy = ?, ModifiedDate = ?
        WHERE FormName = ? AND FieldName = ?
        """,
        (field_label, field_type, field_options, 1 if is_visible else 0, session.get("username"), datetime.now(), form_name, field_name)
    )
    if cursor.rowcount == 0:
        cursor.execute(
            """
            INSERT INTO FormFieldConfig (FormName, FieldName, FieldLabel, IsVisible, IsCustom, FieldType, FieldOptions, ModifiedBy, ModifiedDate)
            VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)
            """,
            (form_name, field_name, field_label, 1 if is_visible else 0, field_type, field_options, session.get("username"), datetime.now())
        )
    conn.commit()
    cursor.close()
    conn.close()
    return None


def delete_custom_form_field(form_name, field_name):
    if form_name not in FORM_TABLES:
        return "Invalid form selected."

    configs = get_form_field_configs(form_name)
    field_config = configs.get(field_name)
    if not field_config:
        return "Invalid field selected."
    if not field_config.get("custom"):
        return "Only extra fields can be deleted. Standard form fields can be hidden or renamed."

    table_name = FORM_TABLES[form_name]
    conn = get_connection()
    cursor = conn.cursor()
    ensure_form_field_config_table(cursor)
    cursor.execute(
        "DELETE FROM FormFieldConfig WHERE FormName = ? AND FieldName = ? AND IsCustom = 1",
        (form_name, field_name)
    )
    cursor.execute(
        f"ALTER TABLE dbo.{bracket_identifier(table_name)} DROP COLUMN {bracket_identifier(field_name)}"
    )
    conn.commit()
    cursor.close()
    conn.close()
    return None


def format_money(value):
    return str(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def parse_decimal(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def is_yes_value(value):
    return str(value).strip().lower() in ("yes", "true", "1")


def apply_contractor_master_fields(billing_data, contractor):
    # BranchName is the branch the work was done for and must NOT be overwritten
    # by the contractor's home branch - a Mumbai contractor working on a Kochi
    # site has to bill to Kochi. The contractor's own location goes in
    # ContractorLocation instead.
    billing_data["ContractorLocation"] = contractor.MainBranch or billing_data.get("ContractorLocation")
    billing_data["ContractorCode"] = contractor.ContractorCode or billing_data.get("ContractorCode")
    billing_data["ContractorAgencyName"] = contractor.LedgerName or billing_data.get("ContractorAgencyName")
    billing_data["ContractorEmailID"] = contractor.EmailID or billing_data.get("ContractorEmailID")
    billing_data["ContractorContactNo"] = contractor.MobileNo or billing_data.get("ContractorContactNo")
    billing_data["OwnerName"] = contractor.OwnerName or billing_data.get("OwnerName")
    billing_data["AccountNumber"] = contractor.AccountNumber or billing_data.get("AccountNumber")
    billing_data["BankName"] = contractor.BankName or billing_data.get("BankName")
    billing_data["IFSCCode"] = contractor.IFSCCode or billing_data.get("IFSCCode")
    billing_data["PANNumber"] = contractor.PANNo or billing_data.get("PANNumber")


def calculate_billing_amounts(billing_data, contractor=None):
    bill_amount = parse_decimal(billing_data.get("BillAmount"))
    if bill_amount is None:
        return

    pan_number = (billing_data.get("PANNumber") or "").upper()
    tds_rate = Decimal("0.02") if "F" in pan_number else Decimal("0.01")
    tds_amount = bill_amount * tds_rate
    ewt_amount = bill_amount * Decimal("0.01")

    gst_applicable = False
    if contractor is not None and hasattr(contractor, "GSTApplicable"):
        gst_applicable = is_yes_value(contractor.GSTApplicable)
    gst_amount = bill_amount * Decimal("0.18") if gst_applicable else Decimal("0.00")

    billing_data["TDS"] = format_money(tds_amount)
    billing_data["EWT"] = format_money(ewt_amount)
    billing_data["GST"] = format_money(gst_amount)

    payable_amount = bill_amount - (tds_amount + ewt_amount + gst_amount)
    billing_data["PayableAmount"] = format_money(payable_amount)


def clear_h007_only_fields(billing_data):
    for field in H007_ONLY_FIELDS:
        billing_data[field] = None


def preserve_h007_only_fields(billing_data, existing):
    for field in H007_ONLY_FIELDS:
        if hasattr(existing, field):
            billing_data[field] = getattr(existing, field)


def validate_contractor_data(data):
    required = get_effective_required_fields("contractor")
    for field in required:
        if not data.get(field):
            return f"{field} is required."

    if data.get("MobileNo") and (not data["MobileNo"].isdigit() or len(data["MobileNo"]) != 10):
        return "Mobile number must be exactly 10 digits."

    if data.get("PANNo") and len(data["PANNo"]) != 10:
        return "PAN must be exactly 10 characters."

    if data.get("EmailID") and not validate_email(data["EmailID"]):
        return "Please enter a valid email address."

    if is_yes_value(data.get("GSTApplicable", "No")):
        if not data.get("GSTIN"):
            return "GSTIN is required when GST Applicable is Yes."
        if len(data["GSTIN"]) != 15:
            return "GSTIN must be exactly 15 characters when GST Applicable is Yes."

    return None


def contractor_code_exists(code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ContractorID FROM AdContractorMaster WHERE LTRIM(RTRIM(ContractorCode)) = ?", ((code or "").strip(),))
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return exists


def pan_exists(pan, exclude_code=None):
    conn = get_connection()
    cursor = conn.cursor()
    if exclude_code:
        cursor.execute("SELECT ContractorID FROM AdContractorMaster WHERE PANNo = ? AND ContractorCode <> ?", (pan, exclude_code))
    else:
        cursor.execute("SELECT ContractorID FROM AdContractorMaster WHERE PANNo = ?", (pan,))
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return exists


def fetch_contractor_by_code(cursor, code):
    clean_code = (code or "").strip()
    if not clean_code:
        return None
    cursor.execute(
        "SELECT TOP 1 * FROM AdContractorMaster WHERE LTRIM(RTRIM(ContractorCode)) = ?",
        (clean_code,)
    )
    return cursor.fetchone()


def generate_contractor_code(branch, work_type, pan):
    branch_part = branch[:2].upper() if branch else "XX"
    work_type_part = work_type[:2].upper() if work_type else "XX"
    pan_part = pan[-4:].upper() if pan and len(pan) >= 4 else "0000"
    base_code = f"{branch_part}{work_type_part}{pan_part}"
    contractor_code = base_code
    suffix = 1
    while contractor_code_exists(contractor_code):
        contractor_code = f"{base_code}{suffix:03d}"
        suffix += 1
    return contractor_code


def get_contractor_dict(row):
    if not row:
        return None
    def yes_no(value):
        return "Yes" if bool(value) else "No"

    data = {
        "ContractorCode": row.ContractorCode,
        "MainBranch": row.MainBranch,
        "WorkType": row.WorkType,
        "LedgerName": row.LedgerName,
        "OwnerName": row.OwnerName,
        "LedgerCode": row.LedgerCode,
        "GroupName": row.GroupName,
        "MailingName": row.MailingName,
        "Address1": row.Address1,
        "Address2": row.Address2,
        "StateName": row.StateName,
        "PinCode": row.PinCode,
        "ContactPerson": row.ContactPerson,
        "PhoneNo": row.PhoneNo,
        "MobileNo": row.MobileNo,
        "EmailID": row.EmailID,
        "PANNo": row.PANNo,
        "GSTApplicable": yes_no(row.GSTApplicable),
        "GSTRegistrationType": row.GSTRegistrationType,
        "GSTIN": row.GSTIN,
        "TDSApplicable": yes_no(row.TDSApplicable),
        "DeducteeType": row.DeducteeType,
        "DeductTDSSameVoucher": yes_no(row.DeductTDSSameVoucher),
        "IgnoreSurcharge": yes_no(row.IgnoreSurcharge),
        "AccountNumber": row.AccountNumber,
        "IFSCCode": row.IFSCCode,
        "BankName": row.BankName,
        "BankRefID": row.BankRefID,
        "BankTransactionType": row.BankTransactionType,
        "BillwiseApplicable": yes_no(row.BillwiseApplicable),
        "CreditPeriod": row.CreditPeriod,
        "PartyType": row.PartyType,
        "EcommerceOperator": yes_no(row.EcommerceOperator),
        "CrossUsing": row.CrossUsing
    }
    add_custom_values_to_dict(data, row, "contractor")
    return data


def validate_billing_data(data):
    required = get_effective_required_fields("billing")
    for field in required:
        if not data.get(field):
            return f"{field} is required."

    if data.get("ContractorContactNo") and not data["ContractorContactNo"].isdigit():
        return "Contractor Contact No must contain only digits."

    if data.get("BillAmount"):
        try:
            float(data["BillAmount"])
        except ValueError:
            return "Bill Amount must be a valid number."

    return None


def make_billing_unique_key(contractor_code, bill_no_deb_remarks):
    contractor_code = (contractor_code or "").strip()
    bill_no_deb_remarks = (bill_no_deb_remarks or "").strip()
    if not contractor_code or not bill_no_deb_remarks:
        return ""
    return f"{contractor_code}_{bill_no_deb_remarks}"


def format_billing_date(value):
    """Return a date safely whether the database driver gives text or a date."""
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def get_billing_dict(row):
    def format_value(value):
        if value is None:
            return None
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, (float, int)):
            return float(value)
        return value

    if not row:
        return None
    data = {
        "BillingID": row.BillingID,
        "Uniquekey": row_unique_key(row),
        "BranchName": row.BranchName,
        "ContractorLocation": getattr(row, "ContractorLocation", None),
        "ContractorCode": row.ContractorCode,
        "ContractorAgencyName": row.ContractorAgencyName,
        "ContractorEmailID": row.ContractorEmailID,
        "ContractorContactNo": row.ContractorContactNo,
        "OwnerName": row.OwnerName,
        "LONumberCrRemarks": row.LONumberCrRemarks,
        "SiteProjectName": row.SiteProjectName,
        "VoucherType": row.VoucherType,
        "WorkOrderNo": row.WorkOrderNo,
        "WorkOrderDate": format_value(row.WorkOrderDate),
        "TCVValue": format_value(row.TCVValue),
        "BillSentDate": format_value(row.BillSentDate),
        "BillNoDebRemarks": row.BillNoDebRemarks,
        "BillDate": format_value(row.BillDate),
        "BillAmount": format_value(row.BillAmount),
        "BillStage": row.BillStage,
        "BillRecdDate": format_value(row.BillRecdDate),
        "ProjectPayment": row.ProjectPayment,
        "ZohoDoc": row.ZohoDoc,
        "TallyName": row.TallyName,
        "InstRemarks": row.InstRemarks,
        "BillGivenHOD": row.BillGivenHOD,
        "BillRecdFromHOD": row.BillRecdFromHOD,
        "BillSubmittedToAcctDate": format_value(row.BillSubmittedToAcctDate),
        "AccountNumber": row.AccountNumber,
        "BankName": row.BankName,
        "IFSCCode": row.IFSCCode,
        "PANNumber": row.PANNumber,
        "TDS": row.TDS,
        "EWT": row.EWT,
        "GST": row.GST,
        "PayableAmount": format_value(row.PayableAmount),
        "PaymentDate": format_value(row.PaymentDate),
        "UTRNumber": row.UTRNumber,
        "StatusInfo": row.StatusInfo,
        "AcctRemarks": row.AcctRemarks
    }
    add_custom_values_to_dict(data, row, "billing")
    return data


EXPORT_CONFIG = {
    "contractors": {
        "table": "AdContractorMaster",
        "branch_column": "MainBranch",
        "filename": "contractor_database"
    },
    "billing": {
        "table": "AdBillingMaster",
        "branch_column": "BranchName",
        "filename": "billing_database"
    }
}


def fetch_export_rows(category, branch_filter=None):
    config = EXPORT_CONFIG[category]
    query = f"SELECT * FROM {config['table']}"
    params = []
    conditions = []

    # This is the authorization boundary for downloads. Sandesh and Uday,
    # like admin/head office, may download both masters across every branch.
    # Every other login remains branch-scoped.
    if not can_export_all_branches():
        conditions.append(f"LTRIM(RTRIM({config['branch_column']})) = ?")
        params.append((session.get("branch") or "").strip())

    # Users with all-branch export access may narrow the report to one branch.
    branch_filter = (branch_filter or "").strip()
    if branch_filter and can_export_all_branches():
        conditions.append(f"LTRIM(RTRIM({config['branch_column']})) = ?")
        params.append(branch_filter)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += f" ORDER BY {config['branch_column']}"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    cursor.close()
    conn.close()
    return columns, rows


def clean_export_value(value):
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str):
        return EXCEL_ILLEGAL_CHAR_REGEX.sub("", value)
    return value


def get_branch_options():
    branches = []
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT LTRIM(RTRIM(Branch_Name)) AS BranchName
        FROM UserLogin
        WHERE Branch_Name IS NOT NULL
          AND LTRIM(RTRIM(Branch_Name)) <> ''
        ORDER BY LTRIM(RTRIM(Branch_Name))
        """
    )
    for row in cursor.fetchall():
        if row.BranchName not in branches:
            branches.append(row.BranchName)
    cursor.close()
    conn.close()
    current_branch = (session.get("branch") or "").strip()
    if current_branch and current_branch not in branches:
        branches.insert(0, current_branch)
    return branches


def is_head_office_user():
    allowed_values = {"h007", "headoffice"}
    return (
        normalize_login_value(session.get("username")) in allowed_values
        or normalize_login_value(session.get("role")) in allowed_values
        or normalize_login_value(session.get("branch")) in allowed_values
    )


def can_export_all_branches():
    """Users authorised to download both masters across every branch."""
    export_users = {"sandesh", "uday"}
    login_designations = {
        normalize_login_value(session.get("username")),
        normalize_login_value(session.get("role")),
        normalize_login_value(session.get("branch")),
    }
    return (
        is_admin_user()
        or is_head_office_user()
        # UserLogin may identify the person through User_Name, Role, or
        # Branch_Name. Any explicit Sandesh/Uday designation gets download-
        # only all-branch access.
        or bool(login_designations & export_users)
    )


def get_dashboard_stats():
    stats = {
        "scope_label": "Your Branch",
        "total_contractors": 0,
        "total_bills": 0,
        "branch_rows": [],
        "contractor_rows": []
    }

    conn = get_connection()
    cursor = conn.cursor()
    show_all_branches = is_admin_user() or is_head_office_user()
    branch = (session.get("branch") or "").strip()

    try:
        if show_all_branches:
            stats["scope_label"] = "All Branches"
            cursor.execute("SELECT COUNT(*) AS TotalCount FROM AdContractorMaster")
            stats["total_contractors"] = cursor.fetchone().TotalCount or 0
            cursor.execute("SELECT COUNT(*) AS TotalCount FROM AdBillingMaster")
            stats["total_bills"] = cursor.fetchone().TotalCount or 0

            # Contractors per branch
            cursor.execute(
                """
                SELECT LTRIM(RTRIM(MainBranch)) AS Branch, COUNT(*) AS Contractors
                FROM AdContractorMaster
                WHERE MainBranch IS NOT NULL AND LTRIM(RTRIM(MainBranch)) <> ''
                GROUP BY LTRIM(RTRIM(MainBranch))
                """
            )
            contractors_by_branch = {row.Branch: (row.Contractors or 0) for row in cursor.fetchall()}

            # Bills per branch
            cursor.execute(
                """
                SELECT LTRIM(RTRIM(BranchName)) AS Branch, COUNT(*) AS Bills
                FROM AdBillingMaster
                WHERE BranchName IS NOT NULL AND LTRIM(RTRIM(BranchName)) <> ''
                GROUP BY LTRIM(RTRIM(BranchName))
                """
            )
            bills_by_branch = {row.Branch: (row.Bills or 0) for row in cursor.fetchall()}

            all_branches = sorted(set(list(contractors_by_branch.keys()) + list(bills_by_branch.keys())))
            stats["branch_rows"] = [
                {"branch": b, "contractors": contractors_by_branch.get(b, 0), "bills": bills_by_branch.get(b, 0)}
                for b in all_branches
            ]

            # Top contractors overall with bill counts
            cursor.execute(
                """
                SELECT c.ContractorCode AS ContractorCode, c.LedgerName AS Agency, COUNT(b.ContractorCode) AS Bills
                FROM AdContractorMaster c
                LEFT JOIN AdBillingMaster b ON c.ContractorCode = b.ContractorCode
                GROUP BY c.ContractorCode, c.LedgerName
                ORDER BY Bills DESC
                """
            )
            stats["contractor_rows"] = [
                {"contractor_code": row.ContractorCode or "", "agency": row.Agency or "", "bills": row.Bills or 0}
                for row in cursor.fetchall()
            ]

        else:
            # Branch-specific summary
            cursor.execute(
                """
                SELECT COUNT(*) AS TotalCount
                FROM AdContractorMaster
                WHERE LTRIM(RTRIM(MainBranch)) = ?
                """,
                (branch,)
            )
            stats["total_contractors"] = cursor.fetchone().TotalCount or 0

            cursor.execute(
                """
                SELECT COUNT(*) AS TotalCount
                FROM AdBillingMaster
                WHERE LTRIM(RTRIM(BranchName)) = ?
                """,
                (branch,)
            )
            stats["total_bills"] = cursor.fetchone().TotalCount or 0

            # Contractors in this branch with their bill counts
            cursor.execute(
                """
                SELECT c.ContractorCode AS ContractorCode, c.LedgerName AS Agency, COUNT(b.ContractorCode) AS Bills
                FROM AdContractorMaster c
                LEFT JOIN AdBillingMaster b ON c.ContractorCode = b.ContractorCode AND LTRIM(RTRIM(b.BranchName)) = ?
                WHERE LTRIM(RTRIM(c.MainBranch)) = ?
                GROUP BY c.ContractorCode, c.LedgerName
                ORDER BY Bills DESC
                """,
                (branch, branch)
            )
            stats["contractor_rows"] = [
                {"contractor_code": row.ContractorCode or "", "agency": row.Agency or "", "bills": row.Bills or 0}
                for row in cursor.fetchall()
            ]
    finally:
        cursor.close()
        conn.close()

    return stats


def make_csv_response(columns, rows, filename):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([clean_export_value(getattr(row, column, "")) for column in columns])

    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}.csv"}
    )


def make_excel_response(columns, rows, filename):
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet.append(columns)
    for row in rows:
        sheet.append([clean_export_value(getattr(row, column, "")) for column in columns])

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=f"{filename}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def get_table_column_metadata(cursor, table_name):
    cursor.execute(
        """
        SELECT c.name AS ColumnName,
               t.name AS DataType,
               c.is_identity AS IsIdentity,
               c.is_computed AS IsComputed
        FROM sys.columns c
        JOIN sys.types t ON c.user_type_id = t.user_type_id
        WHERE c.object_id = OBJECT_ID(?)
        ORDER BY c.column_id
        """,
        (f"dbo.{table_name}",)
    )
    return {
        row.ColumnName: {
            "data_type": row.DataType,
            "is_identity": bool(row.IsIdentity),
            "is_computed": bool(row.IsComputed)
        }
        for row in cursor.fetchall()
    }


def get_bulk_upload_columns(cursor, form_name):
    table_name = BULK_UPLOAD_CONFIG[form_name]["table"]
    metadata = get_table_column_metadata(cursor, table_name)
    return [
        column
        for column, details in metadata.items()
        if not details["is_identity"] and not details["is_computed"]
    ], metadata


def normalize_upload_header(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def get_bulk_header_aliases(form_name, columns):
    labels = FORM_FIELDS.get(form_name, {}).get("fields", {})
    aliases = {}
    for column in columns:
        aliases[normalize_upload_header(column)] = column
        if column in labels:
            aliases[normalize_upload_header(labels[column])] = column
    return aliases


def read_bulk_upload_rows(file_storage):
    filename = secure_filename(file_storage.filename or "")
    extension = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    if extension not in {"csv", "xlsx"}:
        raise ValueError("Please upload a CSV or XLSX file.")

    if extension == "csv":
        raw = file_storage.read()
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            content = raw.decode("latin-1")
        return list(csv.reader(StringIO(content)))

    from openpyxl import load_workbook

    workbook = load_workbook(file_storage, data_only=True)
    sheet = workbook.active
    return [[cell for cell in row] for row in sheet.iter_rows(values_only=True)]


def convert_bulk_value(value, data_type):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None

    data_type = (data_type or "").lower()
    if data_type == "bit":
        return to_bit(value)
    if data_type in {"int", "bigint", "smallint", "tinyint"}:
        return int(Decimal(str(value).replace(",", "")))
    if data_type in {"decimal", "numeric", "money", "smallmoney", "float", "real"}:
        try:
            return Decimal(str(value).replace(",", ""))
        except InvalidOperation:
            raise ValueError(f"{value} is not a valid number.")
    if data_type in {"date", "datetime", "datetime2", "smalldatetime"}:
        if hasattr(value, "date"):
            return value
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(str(value), fmt)
            except ValueError:
                continue
        raise ValueError(f"{value} is not a valid date.")

    return str(value).strip()


def build_bulk_records(form_name, raw_rows, columns, metadata):
    header_row = next((row for row in raw_rows if any(cell not in (None, "") for cell in row)), None)
    if not header_row:
        raise ValueError("The uploaded file is empty.")

    aliases = get_bulk_header_aliases(form_name, columns)
    mapped_headers = []
    unknown_headers = []
    for header in header_row:
        if header in (None, ""):
            mapped_headers.append(None)
            continue
        mapped = aliases.get(normalize_upload_header(header))
        mapped_headers.append(mapped)
        if not mapped:
            unknown_headers.append(str(header).strip())

    if unknown_headers:
        raise ValueError("Unknown header(s): " + ", ".join(unknown_headers))

    records = []
    start_index = raw_rows.index(header_row) + 1
    for row_number, row in enumerate(raw_rows[start_index:], start=start_index + 1):
        if not any(cell not in (None, "") for cell in row):
            continue
        record = {}
        for index, column in enumerate(mapped_headers):
            if not column:
                continue
            value = row[index] if index < len(row) else None
            try:
                record[column] = convert_bulk_value(value, metadata[column]["data_type"])
            except ValueError as exc:
                raise ValueError(f"Row {row_number}, {column}: {exc}")
        records.append((row_number, record))

    if not records:
        raise ValueError("No data rows were found below the header.")
    return records


def prepare_bulk_record(form_name, record):
    now = datetime.now()
    username = session.get("username", "")
    for field in ("CreatedBy", "ModifiedBy"):
        if not record.get(field):
            record[field] = username
    for field in ("CreatedDate", "ModifiedDate"):
        if not record.get(field):
            record[field] = now

    if form_name == "contractor":
        if record.get("PANNo"):
            record["PANNo"] = str(record["PANNo"]).strip().upper()
        if record.get("GSTIN"):
            record["GSTIN"] = str(record["GSTIN"]).strip().upper()
        if record.get("IFSCCode"):
            record["IFSCCode"] = str(record["IFSCCode"]).strip().upper()

    if form_name == "billing":
        if record.get("IFSCCode"):
            record["IFSCCode"] = str(record["IFSCCode"]).strip().upper()
        if record.get("PANNumber"):
            record["PANNumber"] = str(record["PANNumber"]).strip().upper()


def validate_bulk_record(cursor, form_name, row_number, record):
    if form_name == "contractor":
        contractor_code = str(record.get("ContractorCode") or "").strip()
        if not contractor_code:
            return f"Row {row_number}: ContractorCode is required for Contractor Master upload."
        cursor.execute(
            "SELECT ContractorID FROM ADContractorMaster WHERE LTRIM(RTRIM(ContractorCode)) = ?",
            (contractor_code,)
        )
        if cursor.fetchone():
            return f"Row {row_number}: Contractor Code already exists."

    if form_name == "billing":
        unique_key = str(record.get("UniqueKey") or record.get("Uniquekey") or "").strip()
        if not unique_key:
            return f"Row {row_number}: UniqueKey is required for Billing Schedule upload."
        error = validate_billing_data(record)
        if error:
            return f"Row {row_number}: {error}"
        cursor.execute(
            "SELECT BillingID FROM AdBillingMaster WHERE LTRIM(RTRIM(UniqueKey)) = ?",
            (unique_key,)
        )
        if cursor.fetchone():
            return f"Row {row_number}: Billing UniqueKey already exists."

    return None


def insert_bulk_records(form_name, records):
    table_name = BULK_UPLOAD_CONFIG[form_name]["table"]
    conn = get_connection()
    cursor = conn.cursor()
    try:
        columns, metadata = get_bulk_upload_columns(cursor, form_name)
        allowed_columns = set(columns)
        inserted = 0
        seen_contractor_codes = set()
        seen_billing_keys = set()

        for row_number, record in records:
            prepare_bulk_record(form_name, record)
            record = {column: value for column, value in record.items() if column in allowed_columns}
            if form_name == "contractor":
                contractor_code = str(record.get("ContractorCode") or "").strip().lower()
                if contractor_code and contractor_code in seen_contractor_codes:
                    conn.rollback()
                    return inserted, f"Row {row_number}: Contractor Code is duplicated in the uploaded file."
                seen_contractor_codes.add(contractor_code)
            if form_name == "billing":
                billing_key = str(record.get("UniqueKey") or record.get("Uniquekey") or "").strip().lower()
                if billing_key and billing_key in seen_billing_keys:
                    conn.rollback()
                    return inserted, f"Row {row_number}: Billing UniqueKey is duplicated in the uploaded file."
                seen_billing_keys.add(billing_key)
            error = validate_bulk_record(cursor, form_name, row_number, record)
            if error:
                conn.rollback()
                return inserted, error

            insert_columns = [column for column in columns if column in record]
            insert_values = [record[column] for column in insert_columns]
            cursor.execute(
                "INSERT INTO {table} ({columns}) VALUES ({placeholders})".format(
                    table=table_name,
                    columns=", ".join(bracket_identifier(column) for column in insert_columns),
                    placeholders=", ".join(["?"] * len(insert_columns))
                ),
                insert_values
            )
            inserted += 1

        conn.commit()
        return inserted, None
    except Exception as exc:
        conn.rollback()
        return 0, str(exc)
    finally:
        cursor.close()
        conn.close()


def build_billing_bulk_records(raw_rows, columns, metadata):
    """Read a role-specific billing file and reject columns outside its scope."""
    records = build_bulk_records("billing", raw_rows, columns, metadata)
    permitted_columns = set(get_billing_bulk_columns(columns))
    for row_number, record in records:
        forbidden = set(record) - permitted_columns
        if forbidden:
            raise ValueError(
                f"Row {row_number}: this login cannot upload "
                + ", ".join(sorted(forbidden)) + "."
            )
        for key_column in ("ContractorCode", "BillNoDebRemarks"):
            if not str(record.get(key_column) or "").strip():
                raise ValueError(f"Row {row_number}: {key_column} is required.")
        uploaded_branch = str(record.get("BranchName") or "").strip()
        user_branch = str(session.get("branch") or "").strip()
        all_branches = can_bulk_upload_all_branches()
        if not all_branches and uploaded_branch and uploaded_branch.casefold() != user_branch.casefold():
            raise ValueError(f"Row {row_number}: billing uploads are limited to your branch ({user_branch}).")
        if not all_branches and "BranchName" in permitted_columns:
            record["BranchName"] = user_branch
    return records


def prepare_billing_bulk_new_record(cursor, record):
    """Populate system-owned fields and contractor details for a new bill."""
    contractor_code = str(record.get("ContractorCode") or "").strip()
    contractor = fetch_contractor_by_code(cursor, contractor_code)
    if not contractor:
        return None, f"Contractor Code '{contractor_code}' was not found in Contractor Master."

    record = dict(record)
    record["ContractorCode"] = contractor_code
    record["BillNoDebRemarks"] = str(record.get("BillNoDebRemarks") or "").strip()
    apply_contractor_master_fields(record, contractor)
    # Ordinary branch logins stay within their own branch. Billing owners and
    # admins may create a record for the branch listed in their upload.
    if not can_bulk_upload_all_branches() or not str(record.get("BranchName") or "").strip():
        record["BranchName"] = (session.get("branch") or "").strip()
    branch_login_name = (session.get("username") or "").strip()
    upload_time = datetime.now()
    record["ContractorLocation"] = branch_login_name
    # Keep the key's spelling identical to the SQL column name. The bulk
    # insert matches record keys to table metadata with case-sensitive Python
    # comparisons, even though the SQL Server identifiers are case-insensitive.
    record["UniqueKey"] = make_billing_unique_key(
        record["ContractorCode"], record["BillNoDebRemarks"]
    )
    record["CreatedBy"] = branch_login_name
    record["CreatedDate"] = upload_time
    record["ModifiedBy"] = branch_login_name
    record["ModifiedDate"] = upload_time
    prepare_bulk_record("billing", record)
    return record, None


def process_billing_bulk_upload(records):
    """Insert new rows or update an existing key's permitted fields."""
    allowed_fields = get_billing_bulk_allowed_fields()
    all_branches = can_bulk_upload_all_branches()
    conn = get_connection()
    cursor = conn.cursor()
    summary = {"saved": 0, "updated": 0, "skipped": []}
    try:
        table_columns, _ = get_bulk_upload_columns(cursor, "billing")
        uploaded_keys = set()

        for row_number, uploaded_record in records:
            contractor_code = str(uploaded_record.get("ContractorCode") or "").strip()
            bill_no = str(uploaded_record.get("BillNoDebRemarks") or "").strip()
            unique_key = make_billing_unique_key(contractor_code, bill_no)
            key = unique_key.casefold()
            if key in uploaded_keys:
                summary["skipped"].append(f"Row {row_number}: duplicate ContractorCode + BillNo in this file.")
                continue
            uploaded_keys.add(key)

            cursor.execute(
                """
                SELECT BillingID, BranchName FROM AdBillingMaster
                WHERE LTRIM(RTRIM(UniqueKey)) = ?
                """,
                (unique_key,)
            )
            existing = cursor.fetchone()
            if existing:
                existing_branch = str(getattr(existing, "BranchName", "") or "").strip()
                user_branch = str(session.get("branch") or "").strip()
                if not all_branches and existing_branch.casefold() != user_branch.casefold():
                    summary["skipped"].append(
                        f"Row {row_number}: matching billing entry belongs to another branch."
                    )
                    continue

                update_columns = [
                    column for column in uploaded_record
                    if column in table_columns
                    and column not in {
                        "BillingID", "ContractorCode", "BillNoDebRemarks", "UniqueKey",
                        "CreatedBy", "CreatedDate", "ModifiedBy", "ModifiedDate"
                    }
                    and (allowed_fields is None or column in allowed_fields)
                    and uploaded_record[column] is not None
                ]
                if not update_columns:
                    summary["skipped"].append(
                        f"Row {row_number}: no permitted nonblank values to update for UniqueKey '{unique_key}'."
                    )
                    continue

                update_time = datetime.now()
                update_columns.extend(["ModifiedBy", "ModifiedDate"])
                update_values = [uploaded_record[column] for column in update_columns[:-2]]
                update_values.extend([
                    (session.get("username") or "").strip(), update_time, existing.BillingID
                ])
                cursor.execute(
                    "UPDATE AdBillingMaster SET {assignments} WHERE BillingID = ?".format(
                        assignments=", ".join(f"{bracket_identifier(column)} = ?" for column in update_columns)
                    ),
                    update_values
                )
                summary["updated"] += 1
                continue

            record, error = prepare_billing_bulk_new_record(cursor, uploaded_record)
            if error:
                summary["skipped"].append(f"Row {row_number}: {error}")
                continue
            validation_error = validate_billing_data(record)
            if validation_error:
                summary["skipped"].append(f"Row {row_number}: {validation_error}")
                continue

            insert_columns = [column for column in table_columns if column in record]
            cursor.execute(
                "INSERT INTO AdBillingMaster ({columns}) VALUES ({placeholders})".format(
                    columns=", ".join(bracket_identifier(column) for column in insert_columns),
                    placeholders=", ".join(["?"] * len(insert_columns))
                ),
                [record[column] for column in insert_columns]
            )
            summary["saved"] += 1

        conn.commit()
        return summary
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# -----------------------------
# Login Page
# -----------------------------
@app.route("/")
def home():
    return render_template("login.html")


@app.route("/health")
def health_check():
    """Lightweight Render health endpoint that does not require a DB query."""
    return jsonify({"status": "ok"})


# -----------------------------
# Login Authentication
# -----------------------------
@app.route("/login", methods=["POST"])
def login():

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        flash("Username and password are required.", "danger")
        return redirect("/")

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT User_Name, Branch_Name, Role FROM UserLogin WHERE User_Name = ? AND User_Password = ?",
            (username, password)
        )

        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session["username"] = user[0]
            session["branch"] = user[1]
            session["role"] = user[2] or ""
            return redirect("/dashboard")

        flash("Invalid Username or Password", "danger")
        return redirect("/")

    except Exception as exc:
        flash(str(exc), "danger")
        return redirect("/")


# -----------------------------
# Dashboard
# -----------------------------
@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect("/")

    dashboard_stats = get_dashboard_stats()
    return render_template(
        "dashboard.html",
        username=session["username"],
        branch=session["branch"],
        is_admin=is_admin_user(),
        can_bulk_upload=can_bulk_upload_masters(),
        dashboard_stats=dashboard_stats,
        show_branch_summary=is_admin_user() or is_head_office_user()
    )


@app.route("/bulk_upload", methods=["GET", "POST"])
def bulk_upload():
    if "username" not in session:
        return redirect("/")
    access_response = require_bulk_upload_redirect("/dashboard")
    if access_response:
        return access_response

    # Billing Schedule has its own role-specific uploader on /billing.  Keep
    # this legacy screen limited to Contractor Master so head-office access
    # here cannot bypass the billing upload permissions.
    uploadable_configs = {"contractor": BULK_UPLOAD_CONFIG["contractor"]}
    active_tab = request.form.get("form_name") or request.args.get("form_name") or "contractor"
    if active_tab not in uploadable_configs:
        active_tab = "contractor"

    if request.method == "POST":
        form_name = request.form.get("form_name", "").strip()
        upload_file = request.files.get("upload_file")
        if form_name not in uploadable_configs:
            flash("Invalid upload tab selected.", "danger")
            return redirect("/bulk_upload")
        if not upload_file or not upload_file.filename:
            flash("Please choose a CSV or XLSX file to upload.", "danger")
            return redirect(url_for("bulk_upload", form_name=form_name))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            columns, metadata = get_bulk_upload_columns(cursor, form_name)
            cursor.close()
            conn.close()

            raw_rows = read_bulk_upload_rows(upload_file)
            records = build_bulk_records(form_name, raw_rows, columns, metadata)
            inserted, error = insert_bulk_records(form_name, records)
            if error:
                flash(error, "danger")
            else:
                flash(f"{inserted} {BULK_UPLOAD_CONFIG[form_name]['title']} record(s) uploaded successfully.", "success")
        except Exception as exc:
            flash(str(exc), "danger")
        return redirect(url_for("bulk_upload", form_name=form_name))

    upload_configs = {}
    try:
        conn = get_connection()
        cursor = conn.cursor()
        for form_name, config in uploadable_configs.items():
            columns, _ = get_bulk_upload_columns(cursor, form_name)
            upload_configs[form_name] = {**config, "columns": columns}
        cursor.close()
        conn.close()
    except Exception as exc:
        flash(str(exc), "danger")
        upload_configs = uploadable_configs

    return render_template(
        "bulk_upload.html",
        username=session["username"],
        branch=session["branch"],
        upload_configs=upload_configs,
        active_tab=active_tab
    )


@app.route("/bulk_upload/template/<form_name>")
def bulk_upload_template(form_name):
    if "username" not in session:
        return redirect("/")
    # Preserve old bookmarks and downloaded-template links while ensuring
    # Billing Schedule always uses the populated, role-specific template.
    if form_name == "billing":
        return redirect(url_for("billing_bulk_upload_template"))
    access_response = require_bulk_upload_redirect("/dashboard")
    if access_response:
        return access_response
    if form_name != "contractor":
        return jsonify({"status": "error", "message": "Invalid template request."}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()
        columns, _ = get_bulk_upload_columns(cursor, form_name)
        cursor.close()
        conn.close()

        from openpyxl import Workbook

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = BULK_UPLOAD_CONFIG[form_name]["title"][:31]
        sheet.append(columns)
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name=f"{BULK_UPLOAD_CONFIG[form_name]['filename']}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/export/<category>/<file_format>")
def export_data(category, file_format):
    if "username" not in session:
        return redirect("/")

    if category not in EXPORT_CONFIG or file_format not in ("csv", "xlsx"):
        return jsonify({"status": "error", "message": "Invalid export request."}), 400

    try:
        branch_filter = request.args.get("branch_name", "").strip()
        columns, rows = fetch_export_rows(category, branch_filter)
        filename = EXPORT_CONFIG[category]["filename"]
        if branch_filter and can_export_all_branches():
            tag = re.sub(r"[^A-Za-z0-9]+", "_", branch_filter).strip("_")
            if tag:
                filename = f"{filename}_{tag}"
        if not can_export_all_branches():
            branch_part = re.sub(r"[^A-Za-z0-9]+", "_", session.get("branch", "").strip()).strip("_")
            if branch_part:
                filename = f"{filename}_{branch_part}"

        if file_format == "csv":
            return make_csv_response(columns, rows, filename)
        return make_excel_response(columns, rows, filename)
    except Exception as exc:
        app.logger.exception("Export failed")
        return jsonify({"status": "error", "message": str(exc)}), 500


# -----------------------------
# Reports
# -----------------------------
@app.route("/reports")
def reports():
    if "username" not in session:
        return redirect("/")

    return render_template(
        "reports.html",
        username=session["username"],
        branch=session["branch"],
        is_admin=is_admin_user(),
        can_export_all_branches=can_export_all_branches(),
        branch_options=get_branch_options()
    )


@app.route("/field_manager", methods=["GET", "POST"])
def field_manager():
    if "username" not in session:
        return redirect("/")
    admin_response = require_admin_redirect("/dashboard")
    if admin_response:
        return admin_response

    if request.method == "POST":
        action = request.form.get("action", "save_visibility")
        form_name = request.form.get("form_name", "").strip()
        if form_name not in FORM_FIELDS:
            flash("Invalid form selected.", "danger")
            return redirect("/field_manager")

        if action == "add_field":
            error = add_custom_form_field(
                form_name,
                request.form.get("field_label", ""),
                request.form.get("field_type", "text"),
                request.form.get("field_options", "")
            )
            if error:
                flash(error, "danger")
            else:
                flash(f"New field added to {FORM_FIELDS[form_name]['title']}.", "success")
        elif action == "edit_field":
            error = update_form_field_settings(
                form_name,
                request.form.get("field_name", ""),
                request.form.get("field_label", ""),
                request.form.get("field_type", "text"),
                request.form.get("field_options", ""),
                request.form.get("is_visible") == "1"
            )
            if error:
                flash(error, "danger")
            else:
                flash("Field updated successfully.", "success")
        elif action == "delete_field":
            error = delete_custom_form_field(
                form_name,
                request.form.get("field_name", "")
            )
            if error:
                flash(error, "danger")
            else:
                flash("Extra field deleted successfully.", "success")
        else:
            visible_fields = set(request.form.getlist(f"{form_name}_fields"))
            save_form_field_visibility(form_name, visible_fields)
            flash(f"{FORM_FIELDS[form_name]['title']} fields updated successfully.", "success")
        return redirect("/field_manager")

    form_configs = {}
    for form_name, config in FORM_FIELDS.items():
        form_configs[form_name] = {
            "title": config["title"],
            "fields": get_configurable_form_fields(form_name),
            "field_configs": get_form_field_configs(form_name),
            "custom_fields": get_custom_form_fields(form_name),
            "visibility": get_form_field_visibility(form_name)
        }

    return render_template(
        "field_manager.html",
        username=session["username"],
        branch=session["branch"],
        form_configs=form_configs,
        field_type_options=FIELD_TYPE_OPTIONS
    )


# -----------------------------
# Contractor Master
# -----------------------------
@app.route("/contractor")
def contractor():

    if "username" not in session:
        return redirect("/")

    return render_template(
        "contractor.html",
        username=session["username"],
        branch=session["branch"],
        is_admin=is_admin_user(),
        can_edit_branch=can_edit_contractor_branch(),
        branch_options=get_branch_options(),
        field_configs=get_form_field_configs("contractor", visible_only=True),
        hidden_fields=get_hidden_form_fields("contractor"),
        custom_fields=get_custom_form_fields("contractor", visible_only=True),
        field_settings=get_form_field_settings("contractor")
    )


@app.route("/branding_settings", methods=["GET", "POST"])
def branding_settings():
    if "username" not in session:
        return redirect("/")
    admin_response = require_admin_redirect("/dashboard")
    if admin_response:
        return admin_response

    if request.method == "POST":
        brand_name = request.form.get("brand_name", "").strip()
        company_name = request.form.get("company_name", "").strip()
        image_file = request.files.get("main_image")
        login_image_file = request.files.get("login_image")
        font_family = request.form.get("font_family", "").strip() or DEFAULT_APP_SETTINGS["font_family"]
        base_font_size = normalize_font_size(request.form.get("base_font_size"), DEFAULT_APP_SETTINGS["base_font_size"])
        primary_color = normalize_hex_color(request.form.get("primary_color"), DEFAULT_APP_SETTINGS["primary_color"])
        secondary_color = normalize_hex_color(request.form.get("secondary_color"), DEFAULT_APP_SETTINGS["secondary_color"])
        accent_color = normalize_hex_color(request.form.get("accent_color"), DEFAULT_APP_SETTINGS["accent_color"])
        text_color = normalize_hex_color(request.form.get("text_color"), DEFAULT_APP_SETTINGS["text_color"])
        page_background = normalize_hex_color(request.form.get("page_background"), DEFAULT_APP_SETTINGS["page_background"])
        card_background = normalize_hex_color(request.form.get("card_background"), DEFAULT_APP_SETTINGS["card_background"])

        if not brand_name:
            flash("Display name is required.", "danger")
            return redirect("/branding_settings")
        if not company_name:
            flash("Company name is required.", "danger")
            return redirect("/branding_settings")

        try:
            # Read the existing settings BEFORE opening the write connection.
            # get_app_settings() opens its own connection, so calling it after the
            # MERGEs below made a second session wait on the uncommitted locks this
            # request still held - the request deadlocked against itself.
            existing_settings = get_app_settings()

            conn = get_connection()
            cursor = conn.cursor()
            ensure_app_settings_table(cursor)
            save_app_setting(cursor, "brand_name", brand_name)
            save_app_setting(cursor, "company_name", company_name)
            save_app_setting(cursor, "font_family", font_family)
            save_app_setting(cursor, "base_font_size", base_font_size)
            save_app_setting(cursor, "primary_color", primary_color)
            save_app_setting(cursor, "secondary_color", secondary_color)
            save_app_setting(cursor, "accent_color", accent_color)
            save_app_setting(cursor, "text_color", text_color)
            save_app_setting(cursor, "page_background", page_background)
            save_app_setting(cursor, "card_background", card_background)

            remove_main_image = request.form.get("remove_main_image") == "1"
            remove_login_image = request.form.get("remove_login_image") == "1"

            if image_file and image_file.filename:
                if not allowed_image_file(image_file.filename):
                    cursor.close()
                    conn.close()
                    flash("Please upload a PNG, JPG, JPEG, GIF, or WEBP image.", "danger")
                    return redirect("/branding_settings")

                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                original_name = secure_filename(image_file.filename)
                extension = original_name.rsplit(".", 1)[1].lower()
                filename = f"main_page_{uuid.uuid4().hex}.{extension}"
                image_path = os.path.join(UPLOAD_FOLDER, filename)
                image_file.save(image_path)
                save_app_setting(cursor, "main_image_url", url_for("static", filename=f"uploads/{filename}"))
            elif remove_main_image:
                if existing_settings.get("main_image_url"):
                    main_filename = os.path.basename(existing_settings.get("main_image_url"))
                    main_path = os.path.join(UPLOAD_FOLDER, main_filename)
                    if os.path.exists(main_path):
                        try:
                            os.remove(main_path)
                        except OSError:
                            pass
                save_app_setting(cursor, "main_image_url", "")

            if login_image_file and login_image_file.filename:
                if not allowed_image_file(login_image_file.filename):
                    cursor.close()
                    conn.close()
                    flash("Please upload a PNG, JPG, JPEG, GIF, or WEBP image.", "danger")
                    return redirect("/branding_settings")

                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                original_name = secure_filename(login_image_file.filename)
                extension = original_name.rsplit(".", 1)[1].lower()
                filename = f"login_page_{uuid.uuid4().hex}.{extension}"
                image_path = os.path.join(UPLOAD_FOLDER, filename)
                login_image_file.save(image_path)
                save_app_setting(cursor, "login_image_url", url_for("static", filename=f"uploads/{filename}"))
            elif remove_login_image:
                if existing_settings.get("login_image_url"):
                    login_filename = os.path.basename(existing_settings.get("login_image_url"))
                    login_path = os.path.join(UPLOAD_FOLDER, login_filename)
                    if os.path.exists(login_path):
                        try:
                            os.remove(login_path)
                        except OSError:
                            pass
                save_app_setting(cursor, "login_image_url", "")

            conn.commit()
            cursor.close()
            conn.close()
            flash("Branding settings updated successfully.", "success")
            return redirect("/branding_settings")
        except Exception as exc:
            flash(str(exc), "danger")
            return redirect("/branding_settings")

    return render_template(
        "branding_settings.html",
        username=session["username"],
        branch=session["branch"],
        settings=get_app_settings()
    )


# -----------------------------
# Billing Schedule
# -----------------------------
@app.route("/billing")
def billing():

    if "username" not in session:
        return redirect("/")

    allowed_billing_fields = get_allowed_billing_update_fields()
    return render_template(
        "billing.html",
        username=session["username"],
        branch=session["branch"],
        branch_options=get_branch_options(),
        is_h007=is_h007_user(),
        can_edit_billing_tracking=can_edit_billing_tracking_fields(),
        allowed_billing_fields=allowed_billing_fields,
        is_admin=is_admin_user(),
        can_save_billing=can_save_billing(),
        can_delete_billing=can_delete_billing(),
        can_select_branch=can_select_billing_branch(),
        can_bulk_update_billing=can_bulk_update_billing(),
        hidden_fields=get_hidden_form_fields("billing"),
        custom_fields=get_custom_form_fields("billing", visible_only=True),
        field_settings=get_form_field_settings("billing")
    )


@app.route("/billing/bulk-upload", methods=["GET", "POST"])
def billing_bulk_upload():
    if "username" not in session:
        return redirect("/")
    access_response = require_billing_bulk_upload_redirect()
    if access_response:
        return access_response

    if request.method == "POST":
        upload_file = request.files.get("upload_file")
        if not upload_file or not upload_file.filename:
            flash("Please choose a CSV or XLSX file to upload.", "danger")
        else:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                all_columns, metadata = get_bulk_upload_columns(cursor, "billing")
                cursor.close()
                conn.close()

                records = build_billing_bulk_records(
                    read_bulk_upload_rows(upload_file), all_columns, metadata
                )
                summary = process_billing_bulk_upload(records)
                message = (
                    f"{summary['saved']} new billing record(s) saved and "
                    f"{summary['updated']} existing billing record(s) updated; "
                    f"{len(summary['skipped'])} row(s) skipped."
                )
                if summary["skipped"]:
                    message += " Skipped: " + " | ".join(summary["skipped"])
                    flash(message, "warning")
                else:
                    flash(message, "success")
            except Exception as exc:
                flash(str(exc), "danger")
        return redirect("/billing/bulk-upload")

    try:
        conn = get_connection()
        cursor = conn.cursor()
        table_columns, _ = get_bulk_upload_columns(cursor, "billing")
        cursor.close()
        conn.close()
    except Exception as exc:
        flash(str(exc), "danger")
        return redirect("/billing")

    return render_template(
        "billing_bulk_upload.html",
        username=session["username"],
        branch=session.get("branch", ""),
        columns=get_billing_bulk_columns(table_columns),
        all_branches=can_bulk_upload_all_branches(),
        is_admin=is_admin_user()
    )


@app.route("/billing/bulk-upload/template")
def billing_bulk_upload_template():
    if "username" not in session:
        return redirect("/")
    access_response = require_billing_bulk_upload_redirect()
    if access_response:
        return access_response

    try:
        conn = get_connection()
        cursor = conn.cursor()
        table_columns, _ = get_bulk_upload_columns(cursor, "billing")
        cursor.close()
        conn.close()
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500

    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Billing Schedule"
    columns = get_billing_bulk_columns(table_columns)
    sheet.append(columns)
    cursor = conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if can_bulk_upload_all_branches():
            cursor.execute("SELECT * FROM AdBillingMaster ORDER BY BillingID")
        else:
            cursor.execute(
                """
                SELECT * FROM AdBillingMaster
                WHERE LTRIM(RTRIM(BranchName)) = ?
                ORDER BY BillingID
                """,
                ((session.get("branch") or "").strip(),)
            )
        for row in cursor.fetchall():
            sheet.append([clean_export_value(getattr(row, column, None)) for column in columns])
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    sheet.freeze_panes = "A2"
    for cell in sheet[1]:
        cell.font = cell.font.copy(bold=True)
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="billing_schedule_upload_template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# -----------------------------
# Billing CRUD Endpoints
@app.route("/save_billing", methods=["POST"])
def save_billing():
    if not can_save_billing():
        flash("This login can update its assigned billing fields but cannot create a new billing entry.", "danger")
        return redirect("/")

    billing_data = {
        "BranchName": request.form.get("BranchName", "").strip(),
        "ContractorLocation": request.form.get("ContractorLocation", "").strip(),
        "ContractorCode": request.form.get("ContractorCode", "").strip(),
        "ContractorAgencyName": request.form.get("ContractorAgencyName", "").strip(),
        "ContractorEmailID": request.form.get("ContractorEmailID", "").strip(),
        "ContractorContactNo": request.form.get("ContractorContactNo", "").strip(),
        "OwnerName": request.form.get("OwnerName", "").strip(),
        "LONumberCrRemarks": request.form.get("LONumberCrRemarks", "").strip(),
        "SiteProjectName": request.form.get("SiteProjectName", "").strip(),
        "VoucherType": request.form.get("VoucherType", "").strip(),
        "WorkOrderNo": request.form.get("WorkOrderNo", "").strip(),
        "WorkOrderDate": request.form.get("WorkOrderDate", "") or None,
        "TCVValue": request.form.get("TCVValue", "") or None,
        "BillSentDate": request.form.get("BillSentDate", "") or None,
        "BillNoDebRemarks": request.form.get("BillNoDebRemarks", "").strip(),
        "BillDate": request.form.get("BillDate", "") or None,
        "BillAmount": request.form.get("BillAmount", "") or None,
        "BillStage": request.form.get("BillStage", "").strip(),
        "BillRecdDate": request.form.get("BillRecdDate", "") or None,
        "ProjectPayment": request.form.get("ProjectPayment", "").strip(),
        "ZohoDoc": request.form.get("ZohoDoc", "").strip(),
        "TallyName": request.form.get("TallyName", "").strip(),
        "InstRemarks": request.form.get("InstRemarks", "").strip(),
        "BillGivenHOD": request.form.get("BillGivenHOD", "").strip(),
        "BillRecdFromHOD": request.form.get("BillRecdFromHOD", "").strip(),
        "BillSubmittedToAcctDate": request.form.get("BillSubmittedToAcctDate", "") or None,
        "AccountNumber": request.form.get("AccountNumber", "").strip(),
        "BankName": request.form.get("BankName", "").strip(),
        "IFSCCode": request.form.get("IFSCCode", "").strip().upper(),
        "PANNumber": request.form.get("PANNumber", "").strip().upper(),
        "TDS": request.form.get("TDS", "").strip(),
        "EWT": request.form.get("EWT", "").strip(),
        "GST": request.form.get("GST", "").strip(),
        "PayableAmount": request.form.get("PayableAmount", "") or None,
        "PaymentDate": request.form.get("PaymentDate", "") or None,
        "UTRNumber": request.form.get("UTRNumber", "").strip(),
        "StatusInfo": request.form.get("StatusInfo", "").strip(),
        "AcctRemarks": request.form.get("AcctRemarks", "").strip(),
        "CreatedBy": session["username"],
        "CreatedDate": datetime.now(),
        "ModifiedBy": session["username"],
        "ModifiedDate": datetime.now()
    }
    custom_billing_data = collect_custom_values(request.form, "billing")

    # Never trust disabled/read-only browser controls: discard values that this
    # login is not permitted to create.  Admin/head office retain every field.
    allowed_fields = get_allowed_billing_update_fields()
    for field_name in FORM_FIELDS["billing"]["fields"]:
        if field_name not in allowed_fields:
            billing_data[field_name] = None

    # A branch login must always create the bill in its own branch, regardless
    # of a value altered in the browser request.
    if not can_select_billing_branch():
        billing_data["BranchName"] = (session.get("branch") or "").strip()

    try:
        conn = get_connection()
        cursor = conn.cursor()

        contractor = fetch_contractor_by_code(cursor, billing_data.get("ContractorCode"))
        if not contractor:
            cursor.close()
            conn.close()
            flash("Contractor Code was not found in Contractor Master.", "danger")
            return redirect("/billing")

        apply_contractor_master_fields(billing_data, contractor)

        calculate_billing_amounts(billing_data, contractor)
        billing_data["Uniquekey"] = make_billing_unique_key(
            billing_data.get("ContractorCode"),
            billing_data.get("BillNoDebRemarks")
        )

        error = validate_billing_data(billing_data)
        if error:
            cursor.close()
            conn.close()
            flash(error, "danger")
            return redirect("/billing")

        cursor.execute(
            """
            SELECT BillingID
            FROM AdBillingMaster
            WHERE LTRIM(RTRIM(Uniquekey)) = ?
            """,
            (billing_data.get("Uniquekey"),)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            flash("A billing entry with this unique key already exists.", "warning")
            return redirect("/billing")

        insert_columns = [
            "Uniquekey",
            "BranchName", "ContractorLocation", "ContractorCode", "ContractorAgencyName", "ContractorEmailID",
            "ContractorContactNo", "OwnerName", "LONumberCrRemarks", "SiteProjectName",
            "VoucherType", "WorkOrderNo", "WorkOrderDate", "TCVValue", "BillSentDate",
            "BillNoDebRemarks", "BillDate", "BillAmount", "BillStage", "BillRecdDate",
            "ProjectPayment", "ZohoDoc", "TallyName", "InstRemarks", "BillGivenHOD",
            "BillRecdFromHOD", "BillSubmittedToAcctDate", "AccountNumber", "BankName",
            "IFSCCode", "PANNumber", "TDS", "EWT", "GST", "PayableAmount", "PaymentDate",
            "UTRNumber", "StatusInfo", "AcctRemarks", "CreatedBy", "CreatedDate",
            "ModifiedBy", "ModifiedDate"
        ]
        insert_values = [billing_data[column] for column in insert_columns]
        for column, value in custom_billing_data.items():
            insert_columns.append(column)
            insert_values.append(value)

        cursor.execute(
            "INSERT INTO AdBillingMaster ({columns}) VALUES ({placeholders})".format(
                columns=", ".join(bracket_identifier(column) for column in insert_columns),
                placeholders=", ".join(["?"] * len(insert_columns))
            ),
            insert_values
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Billing entry saved successfully.", "success")
        return redirect("/billing")
    except Exception as exc:
        if (
            "UX_AdBillingMaster_Uniquekey" in str(exc)
            or "UX_AdBillingMaster_ContractorCode_BillNoDebRemarks" in str(exc)
        ):
            flash("A billing entry with this unique key already exists.", "warning")
            return redirect("/billing")
        flash(str(exc), "danger")
        return redirect("/billing")


@app.route("/search_billing", methods=["POST"])
def search_billing():
    if "username" not in session:
        return jsonify([]), 401

    payload = request.get_json(silent=True) or {}
    search_term = text_value(payload.get("searchTerm"))

    query = (
        "SELECT BillingID, Uniquekey, ContractorCode, ContractorAgencyName, "
        "BillNoDebRemarks, BillDate, BillAmount FROM AdBillingMaster "
        "WHERE LTRIM(RTRIM(Uniquekey)) LIKE ?"
    )
    params = [f"%{search_term}%"]

    query += " ORDER BY BillingID"

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        results = [
            {
                "BillingID": row.BillingID,
                "Uniquekey": row_unique_key(row),
                "ContractorCode": row.ContractorCode,
                "ContractorAgencyName": row.ContractorAgencyName,
                "BillNoDebRemarks": row.BillNoDebRemarks,
                "BillDate": format_billing_date(row.BillDate),
                "BillAmount": float(row.BillAmount) if row.BillAmount is not None else None
            }
            for row in rows
        ]
        return jsonify(results)
    except Exception as exc:
        app.logger.exception("Billing search failed")
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/get_billing/<int:billing_id>")
def get_billing(billing_id):
    if "username" not in session:
        return jsonify({}), 401

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM AdBillingMaster WHERE BillingID = ?", (billing_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        billing = get_billing_dict(row)
        if not billing:
            return jsonify({}), 404
        return jsonify(billing)
    except Exception as exc:
        app.logger.exception("Failed to fetch billing %s", billing_id)
        return jsonify({"message": str(exc)}), 500


@app.route("/update_billing", methods=["POST"])
def update_billing():
    edit_response = require_billing_edit_json()
    if edit_response:
        return edit_response

    payload = request.get_json(silent=True) or {}
    allowed_fields = get_allowed_billing_update_fields()
    if not allowed_fields:
        return jsonify({"status": "error", "message": "Not authorized to update billing fields."}), 403

    allowed_key_fields = {"BillingID", "ContractorCode", "BillNoDebRemarks", "OriginalUniquekey", "Uniquekey", "OriginalContractorCode", "OriginalBillNoDebRemarks"}
    filtered_payload = {
        key: value
        for key, value in payload.items()
        if key in allowed_key_fields or key in allowed_fields
    }
    payload = filtered_payload

    billing_id = payload.get("BillingID")
    original_unique_key = (payload.get("OriginalUniquekey") or payload.get("Uniquekey") or "").strip()
    original_contractor_code = (payload.get("OriginalContractorCode") or payload.get("ContractorCode") or "").strip()
    original_bill_no = (payload.get("OriginalBillNoDebRemarks") or payload.get("BillNoDebRemarks") or "").strip()

    billing_data = {
        "BranchName": text_value(payload.get("BranchName")),
        "ContractorLocation": text_value(payload.get("ContractorLocation")),
        "ContractorCode": text_value(payload.get("ContractorCode")),
        "ContractorAgencyName": text_value(payload.get("ContractorAgencyName")),
        "ContractorEmailID": text_value(payload.get("ContractorEmailID")),
        "ContractorContactNo": text_value(payload.get("ContractorContactNo")),
        "OwnerName": text_value(payload.get("OwnerName")),
        "LONumberCrRemarks": text_value(payload.get("LONumberCrRemarks")),
        "SiteProjectName": text_value(payload.get("SiteProjectName")),
        "VoucherType": text_value(payload.get("VoucherType")),
        "WorkOrderNo": text_value(payload.get("WorkOrderNo")),
        "WorkOrderDate": payload.get("WorkOrderDate", "") or None,
        "TCVValue": payload.get("TCVValue", "") or None,
        "BillSentDate": payload.get("BillSentDate", "") or None,
        "BillNoDebRemarks": text_value(payload.get("BillNoDebRemarks")),
        "BillDate": payload.get("BillDate", "") or None,
        "BillAmount": payload.get("BillAmount", "") or None,
        "BillStage": text_value(payload.get("BillStage")),
        "BillRecdDate": payload.get("BillRecdDate", "") or None,
        "ProjectPayment": text_value(payload.get("ProjectPayment")),
        "ZohoDoc": text_value(payload.get("ZohoDoc")),
        "TallyName": text_value(payload.get("TallyName")),
        "InstRemarks": text_value(payload.get("InstRemarks")),
        "BillGivenHOD": text_value(payload.get("BillGivenHOD")),
        "BillRecdFromHOD": text_value(payload.get("BillRecdFromHOD")),
        "BillSubmittedToAcctDate": payload.get("BillSubmittedToAcctDate", "") or None,
        "AccountNumber": text_value(payload.get("AccountNumber")),
        "BankName": text_value(payload.get("BankName")),
        "IFSCCode": text_value(payload.get("IFSCCode")).upper(),
        "PANNumber": text_value(payload.get("PANNumber")).upper(),
        "TDS": text_value(payload.get("TDS")),
        "EWT": text_value(payload.get("EWT")),
        "GST": text_value(payload.get("GST")),
        "PayableAmount": payload.get("PayableAmount", "") or None,
        "PaymentDate": payload.get("PaymentDate", "") or None,
        "UTRNumber": text_value(payload.get("UTRNumber")),
        "StatusInfo": text_value(payload.get("StatusInfo")),
        "AcctRemarks": text_value(payload.get("AcctRemarks")),
        "ModifiedBy": session["username"],
        "ModifiedDate": datetime.now()
    }

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Update always targets an existing row found by its unique key. It must
        # never create a row - that is Save's job.
        if not original_unique_key:
            original_unique_key = make_billing_unique_key(original_contractor_code, original_bill_no)
        cursor.execute(
            """
            SELECT * FROM AdBillingMaster
            WHERE LTRIM(RTRIM(Uniquekey)) = ?
            """,
            (original_unique_key,)
        )
        existing = cursor.fetchone()
        if not existing:
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "No billing entry found with the provided unique key."}), 404

        billing_id = existing.BillingID

        stored_code = (existing.ContractorCode or "").strip()
        stored_bill_no = (existing.BillNoDebRemarks or "").strip()

        # Custom fields have no Sandesh/Uday assignment, so only admin may
        # change them. This prevents an injected JSON property bypassing the
        # standard-field permission map.
        custom_billing_data = collect_custom_values(payload, "billing") if is_billing_admin_user() else {}

        contractor = fetch_contractor_by_code(cursor, billing_data.get("ContractorCode"))
        if not contractor:
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "Contractor Code was not found in Contractor Master."}), 400

        # The contractor lookup above validates the code.  Do not overwrite
        # fields from the submitted record here: an update must preserve the
        # authorised values entered by the user (including Uday's bank values)
        # rather than silently replacing them from Contractor Master.

        allowed_fields = get_allowed_billing_update_fields()
        if not allowed_fields:
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "Not authorized to update billing fields."}), 403

        protected_fields = set(FORM_FIELDS["billing"]["fields"].keys()) - allowed_fields
        protected_fields.discard("ContractorCode")
        protected_fields.discard("BillNoDebRemarks")
        protected_fields.discard("Uniquekey")
        for field_name in protected_fields:
            if hasattr(existing, field_name):
                billing_data[field_name] = getattr(existing, field_name)

        if not can_edit_billing_tracking_fields():
            preserve_h007_only_fields(billing_data, existing)

        if "BillAmount" in allowed_fields:
            calculate_billing_amounts(billing_data, contractor)
        # Users with permission to edit the operational fields may also change
        # either component of the unique key.  The duplicate check below keeps
        # the database constraint intact.  Other logins keep the stored key.
        if "ContractorCode" not in allowed_fields:
            billing_data["ContractorCode"] = stored_code
        if "BillNoDebRemarks" not in allowed_fields:
            billing_data["BillNoDebRemarks"] = stored_bill_no
        billing_data["Uniquekey"] = make_billing_unique_key(
            billing_data["ContractorCode"], billing_data["BillNoDebRemarks"]
        )

        error = validate_billing_data(billing_data)
        if error:
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": error}), 400

        cursor.execute(
            """
            SELECT BillingID
            FROM AdBillingMaster
            WHERE LTRIM(RTRIM(Uniquekey)) = ?
              AND BillingID <> ?
            """,
            (billing_data.get("Uniquekey"), billing_id)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "A billing entry with this unique key already exists."}), 409

        update_columns = ["Uniquekey", "ModifiedBy", "ModifiedDate"]
        update_values = [billing_data["Uniquekey"], session["username"], datetime.now()]

        all_billing_columns = [
            "BranchName", "ContractorLocation", "ContractorCode", "ContractorAgencyName", "ContractorEmailID",
            "ContractorContactNo", "OwnerName", "LONumberCrRemarks", "SiteProjectName",
            "VoucherType", "WorkOrderNo", "WorkOrderDate", "TCVValue", "BillSentDate",
            "BillNoDebRemarks", "BillDate", "BillAmount", "BillStage", "BillRecdDate",
            "ProjectPayment", "ZohoDoc", "TallyName", "InstRemarks", "BillGivenHOD",
            "BillRecdFromHOD", "BillSubmittedToAcctDate", "AccountNumber", "BankName",
            "IFSCCode", "PANNumber", "TDS", "EWT", "GST", "PayableAmount", "PaymentDate",
            "UTRNumber", "StatusInfo", "AcctRemarks"
        ]
        for column in all_billing_columns:
            # Missing JSON properties mean "leave the SQL value unchanged".
            # This is the key guard against a restricted user's update turning
            # unrelated columns into NULL/blank values.
            if column in allowed_fields and column in payload and column in billing_data:
                update_columns.append(column)
                update_values.append(billing_data[column])

        for column, value in custom_billing_data.items():
            if is_billing_admin_user() and column in payload:
                update_columns.append(column)
                update_values.append(value)
        update_values.append(billing_id)

        cursor.execute(
            "UPDATE AdBillingMaster SET {assignments} WHERE BillingID = ?".format(
                assignments=", ".join(f"{bracket_identifier(column)} = ?" for column in update_columns)
            ),
            update_values
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": "Billing entry updated successfully."})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/delete_billing", methods=["POST"])
def delete_billing():
    if "username" not in session:
        return jsonify({"status": "error", "message": "Session expired."}), 401
    delete_response = require_billing_delete_json()
    if delete_response:
        return delete_response

    payload = request.get_json(silent=True) or {}
    billing_id = payload.get("BillingID")
    if not billing_id:
        return jsonify({"status": "error", "message": "Billing ID is required."}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM AdBillingMaster WHERE BillingID = ?", (billing_id,))
        conn.commit()
        rowcount = cursor.rowcount
        cursor.close()
        conn.close()

        if rowcount == 0:
            return jsonify({"status": "error", "message": "No billing entry found with the provided ID."}), 404

        return jsonify({"status": "success", "message": "Billing entry deleted successfully."})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


# -----------------------------
# Save Contractor
# -----------------------------
@app.route("/save_contractor", methods=["POST"])
def save_contractor():
    if "username" not in session:
        return redirect("/")
    admin_response = require_admin_redirect("/contractor")
    if admin_response:
        return admin_response

    contractor_data = {
        "MainBranch": request.form.get("MainBranch", "").strip(),
        "WorkType": request.form.get("WorkType", "").strip(),
        "LedgerName": request.form.get("LedgerName", "").strip(),
        "OwnerName": request.form.get("OwnerName", "").strip(),
        "LedgerCode": request.form.get("LedgerCode", "").strip(),
        "GroupName": request.form.get("GroupName", "").strip(),
        "MailingName": request.form.get("MailingName", "").strip(),
        "Address1": request.form.get("Address1", "").strip(),
        "Address2": request.form.get("Address2", "").strip(),
        "StateName": request.form.get("StateName", "").strip(),
        "PinCode": request.form.get("PinCode", "").strip(),
        "ContactPerson": request.form.get("ContactPerson", "").strip(),
        "PhoneNo": request.form.get("PhoneNo", "").strip(),
        "MobileNo": request.form.get("MobileNo", "").strip(),
        "EmailID": request.form.get("EmailID", "").strip(),
        "PANNo": request.form.get("PANNo", "").strip().upper(),
        "GSTApplicable": to_bit(request.form.get("GSTApplicable", "No")),
        "GSTRegistrationType": request.form.get("GSTRegistrationType", "").strip(),
        "GSTIN": request.form.get("GSTIN", "").strip().upper(),
        "TDSApplicable": to_bit(request.form.get("TDSApplicable", "No")),
        "DeducteeType": request.form.get("DeducteeType", "").strip(),
        "DeductTDSSameVoucher": to_bit(request.form.get("DeductTDSSameVoucher", "No")),
        "IgnoreSurcharge": to_bit(request.form.get("IgnoreSurcharge", "No")),
        "AccountNumber": request.form.get("AccountNumber", "").strip(),
        "IFSCCode": request.form.get("IFSCCode", "").strip().upper(),
        "BankName": request.form.get("BankName", "").strip(),
        "BankRefID": request.form.get("BankRefID", "").strip(),
        "BankTransactionType": request.form.get("BankTransactionType", "").strip(),
        "BillwiseApplicable": to_bit(request.form.get("BillwiseApplicable", "Yes")),
        "CreditPeriod": request.form.get("CreditPeriod", "").strip(),
        "PartyType": request.form.get("PartyType", "").strip(),
        "EcommerceOperator": to_bit(request.form.get("EcommerceOperator", "No")),
        "CrossUsing": request.form.get("CrossUsing", "").strip(),
        "CreatedBy": session["username"],
        "CreatedDate": datetime.now(),
        "ModifiedBy": session["username"],
        "ModifiedDate": datetime.now()
    }
    if not can_edit_contractor_branch():
        contractor_data["MainBranch"] = (session.get("branch") or "").strip()
    custom_contractor_data = collect_custom_values(request.form, "contractor")

    error = validate_contractor_data(contractor_data)
    if error:
        flash(error, "danger")
        return redirect("/contractor")

    if contractor_data.get("PANNo") and pan_exists(contractor_data["PANNo"]):
        flash("PAN already exists. Contractor cannot be saved.", "warning")
        return redirect("/contractor")

    try:
        contractor_code = generate_contractor_code(
            contractor_data["MainBranch"],
            contractor_data["WorkType"],
            contractor_data["PANNo"]
        )

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT ContractorID FROM AdContractorMaster WHERE LTRIM(RTRIM(ContractorCode)) = ?",
            (contractor_code,)
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            flash("Contractor Code already exists. Duplicate contractor cannot be saved.", "warning")
            return redirect("/contractor")

        params_list = [
            contractor_code,
            contractor_data["MainBranch"],
            contractor_data["WorkType"],
            contractor_data["LedgerName"],
            contractor_data["OwnerName"],
            contractor_data["LedgerCode"],
            contractor_data["GroupName"],
            contractor_data["MailingName"],
            contractor_data["Address1"],
            contractor_data["Address2"],
            contractor_data["StateName"],
            contractor_data["PinCode"],
            contractor_data["ContactPerson"],
            contractor_data["PhoneNo"],
            contractor_data["MobileNo"],
            contractor_data["EmailID"],
            contractor_data["PANNo"],
            contractor_data["GSTApplicable"],
            contractor_data["GSTRegistrationType"],
            contractor_data["GSTIN"],
            contractor_data["TDSApplicable"],
            contractor_data["DeducteeType"],
            contractor_data["DeductTDSSameVoucher"],
            contractor_data["IgnoreSurcharge"],
            contractor_data["AccountNumber"],
            contractor_data["IFSCCode"],
            contractor_data["BankName"],
            contractor_data["BankRefID"],
            contractor_data["BankTransactionType"],
            contractor_data["BillwiseApplicable"],
            contractor_data["CreditPeriod"],
            contractor_data["PartyType"],
            contractor_data["EcommerceOperator"],
            contractor_data["CrossUsing"],
            contractor_data["CreatedBy"],
            contractor_data["CreatedDate"],
            contractor_data["ModifiedBy"],
            contractor_data["ModifiedDate"]
        ]
        for _, value in custom_contractor_data.items():
            params_list.append(value)

        custom_columns = list(custom_contractor_data.keys())
        sql = """
            INSERT INTO AdContractorMaster (
                ContractorCode, MainBranch, WorkType, LedgerName, OwnerName,
                LedgerCode, GroupName, MailingName, Address1, Address2,
                StateName, PinCode, ContactPerson, PhoneNo, MobileNo,
                EmailID, PANNo, GSTApplicable, GSTRegistrationType, GSTIN,
                TDSApplicable, DeducteeType, DeductTDSSameVoucher, IgnoreSurcharge,
                AccountNumber, IFSCCode, BankName, BankRefID, BankTransactionType,
                BillwiseApplicable, CreditPeriod, PartyType, EcommerceOperator,
                CrossUsing, CreatedBy, CreatedDate, ModifiedBy, ModifiedDate
                {custom_columns}
            ) VALUES ({placeholders})
        """.format(
            custom_columns=(", " + ", ".join(bracket_identifier(column) for column in custom_columns)) if custom_columns else "",
            placeholders=", ".join(["?"] * len(params_list))
        )

        cursor.execute(sql, params_list)
        conn.commit()
        cursor.close()
        conn.close()

        flash(f"Contractor saved successfully with code {contractor_code}.", "success")
        return redirect("/contractor")
    except Exception as exc:
        flash(str(exc), "danger")
        return redirect("/contractor")


@app.route("/search_contractor", methods=["POST"])
def search_contractor():
    if "username" not in session:
        return jsonify([]), 401

    payload = request.get_json(silent=True) or {}
    search_by = ALLOWED_SEARCH_COLUMNS.get(payload.get("searchBy", "ContractorCode"), "ContractorCode")
    search_term = text_value(payload.get("searchTerm"))

    query = f"SELECT ContractorCode, LedgerName, OwnerName, MobileNo, MainBranch, WorkType FROM AdContractorMaster WHERE {search_by} LIKE ? ORDER BY ContractorCode"
    params = [f"%{search_term}%"]

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        results = [
            {
                "ContractorCode": row.ContractorCode,
                "LedgerName": row.LedgerName,
                "OwnerName": row.OwnerName,
                "MobileNo": row.MobileNo,
                "MainBranch": row.MainBranch,
                "WorkType": row.WorkType
            }
            for row in rows
        ]
        return jsonify(results)
    except Exception:
        return jsonify([]), 500


@app.route("/get_contractor")
@app.route("/get_contractor/<path:code>")
def get_contractor(code=None):
    if "username" not in session:
        return jsonify({}), 401

    code = (code or request.args.get("code", "")).strip()
    if not code:
        return jsonify({}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()
        row = fetch_contractor_by_code(cursor, code)
        cursor.close()
        conn.close()

        contractor = get_contractor_dict(row)
        if not contractor:
            return jsonify({}), 404
        return jsonify(contractor)
    except Exception as exc:
        app.logger.exception("Failed to fetch contractor %s", code)
        return jsonify({"message": str(exc)}), 500


@app.route("/update_contractor", methods=["POST"])
def update_contractor():
    if "username" not in session:
        return jsonify({"status": "error", "message": "Session expired."}), 401
    admin_response = require_admin_json()
    if admin_response:
        return admin_response

    payload = request.get_json(silent=True) or {}
    contractor_code = text_value(payload.get("ContractorCode"))
    if not contractor_code:
        return jsonify({"status": "error", "message": "Contractor Code is required."}), 400

    contractor_data = {
        "MainBranch": text_value(payload.get("MainBranch")),
        "WorkType": text_value(payload.get("WorkType")),
        "LedgerName": text_value(payload.get("LedgerName")),
        "OwnerName": text_value(payload.get("OwnerName")),
        "LedgerCode": text_value(payload.get("LedgerCode")),
        "GroupName": text_value(payload.get("GroupName")),
        "MailingName": text_value(payload.get("MailingName")),
        "Address1": text_value(payload.get("Address1")),
        "Address2": text_value(payload.get("Address2")),
        "StateName": text_value(payload.get("StateName")),
        "PinCode": text_value(payload.get("PinCode")),
        "ContactPerson": text_value(payload.get("ContactPerson")),
        "PhoneNo": text_value(payload.get("PhoneNo")),
        "MobileNo": text_value(payload.get("MobileNo")),
        "EmailID": text_value(payload.get("EmailID")),
        "PANNo": text_value(payload.get("PANNo")).upper(),
        "GSTApplicable": to_bit(payload.get("GSTApplicable", "No")),
        "GSTRegistrationType": text_value(payload.get("GSTRegistrationType")),
        "GSTIN": text_value(payload.get("GSTIN")).upper(),
        "TDSApplicable": to_bit(payload.get("TDSApplicable", "No")),
        "DeducteeType": text_value(payload.get("DeducteeType")),
        "DeductTDSSameVoucher": to_bit(payload.get("DeductTDSSameVoucher", "No")),
        "IgnoreSurcharge": to_bit(payload.get("IgnoreSurcharge", "No")),
        "AccountNumber": text_value(payload.get("AccountNumber")),
        "IFSCCode": text_value(payload.get("IFSCCode")).upper(),
        "BankName": text_value(payload.get("BankName")),
        "BankRefID": text_value(payload.get("BankRefID")),
        "BankTransactionType": text_value(payload.get("BankTransactionType")),
        "BillwiseApplicable": to_bit(payload.get("BillwiseApplicable", "Yes")),
        "CreditPeriod": text_value(payload.get("CreditPeriod")),
        "PartyType": text_value(payload.get("PartyType")),
        "EcommerceOperator": to_bit(payload.get("EcommerceOperator", "No")),
        "CrossUsing": text_value(payload.get("CrossUsing")),
        "ModifiedBy": session["username"],
        "ModifiedDate": datetime.now()
    }

    error = validate_contractor_data(contractor_data)
    if error:
        return jsonify({"status": "error", "message": error}), 400

    if pan_exists(contractor_data["PANNo"], exclude_code=contractor_code):
        return jsonify({"status": "error", "message": "PAN already exists for another contractor."}), 409

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE AdContractorMaster SET
                MainBranch = ?,
                WorkType = ?,
                LedgerName = ?,
                OwnerName = ?,
                LedgerCode = ?,
                GroupName = ?,
                MailingName = ?,
                Address1 = ?,
                Address2 = ?,
                StateName = ?,
                PinCode = ?,
                ContactPerson = ?,
                PhoneNo = ?,
                MobileNo = ?,
                EmailID = ?,
                PANNo = ?,
                GSTApplicable = ?,
                GSTRegistrationType = ?,
                GSTIN = ?,
                TDSApplicable = ?,
                DeducteeType = ?,
                DeductTDSSameVoucher = ?,
                IgnoreSurcharge = ?,
                AccountNumber = ?,
                IFSCCode = ?,
                BankName = ?,
                BankRefID = ?,
                BankTransactionType = ?,
                BillwiseApplicable = ?,
                CreditPeriod = ?,
                PartyType = ?,
                EcommerceOperator = ?,
                CrossUsing = ?,
                ModifiedBy = ?,
                ModifiedDate = ?
            WHERE ContractorCode = ?
            """,
            (
                contractor_data["MainBranch"],
                contractor_data["WorkType"],
                contractor_data["LedgerName"],
                contractor_data["OwnerName"],
                contractor_data["LedgerCode"],
                contractor_data["GroupName"],
                contractor_data["MailingName"],
                contractor_data["Address1"],
                contractor_data["Address2"],
                contractor_data["StateName"],
                contractor_data["PinCode"],
                contractor_data["ContactPerson"],
                contractor_data["PhoneNo"],
                contractor_data["MobileNo"],
                contractor_data["EmailID"],
                contractor_data["PANNo"],
                contractor_data["GSTApplicable"],
                contractor_data["GSTRegistrationType"],
                contractor_data["GSTIN"],
                contractor_data["TDSApplicable"],
                contractor_data["DeducteeType"],
                contractor_data["DeductTDSSameVoucher"],
                contractor_data["IgnoreSurcharge"],
                contractor_data["AccountNumber"],
                contractor_data["IFSCCode"],
                contractor_data["BankName"],
                contractor_data["BankRefID"],
                contractor_data["BankTransactionType"],
                contractor_data["BillwiseApplicable"],
                contractor_data["CreditPeriod"],
                contractor_data["PartyType"],
                contractor_data["EcommerceOperator"],
                contractor_data["CrossUsing"],
                contractor_data["ModifiedBy"],
                contractor_data["ModifiedDate"],
                contractor_code
            )
        )
        conn.commit()
        rowcount = cursor.rowcount
        cursor.close()
        conn.close()

        if rowcount == 0:
            return jsonify({"status": "error", "message": "No active contractor found with the provided code."}), 404

        return jsonify({"status": "success", "message": "Contractor updated successfully."})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/delete_contractor", methods=["POST"])
def delete_contractor():
    if "username" not in session:
        return jsonify({"status": "error", "message": "Session expired."}), 401
    admin_response = require_admin_json()
    if admin_response:
        return admin_response

    payload = request.get_json(silent=True) or {}
    contractor_code = text_value(payload.get("ContractorCode"))
    if not contractor_code:
        return jsonify({"status": "error", "message": "Contractor Code is required."}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM AdContractorMaster WHERE ContractorCode = ?",
            (contractor_code,)
        )
        conn.commit()
        rowcount = cursor.rowcount
        cursor.close()
        conn.close()

        if rowcount == 0:
            return jsonify({"status": "error", "message": "No contractor found with the provided code."}), 404

        return jsonify({"status": "success", "message": "Contractor deleted successfully."})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


# -----------------------------
# Logout
# -----------------------------
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# -----------------------------
# Run Application
# -----------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
