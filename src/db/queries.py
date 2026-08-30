from mysql.connector import Error
from .connection import get_db_connection
import bcrypt


# Author: Saadat Ali ----------------------------
def testQuery():
	query: str = "SELECT * FROM documents";
	conn = None;
	try:
		conn = get_db_connection();
		cursor = conn.cursor();
		cursor.execute(query, ());
		result = cursor.fetchone();
		return result;
	except Error as e:
		print(f"DB Error: {e}");
		return None;
	finally:
		if conn and conn.is_connected():
			cursor.close();
			conn.close();

def searchUser(email: str) -> dict | None:
    """
    Fetches full user record as a dictionary. Returns None if not found.
    """
    query = "SELECT user_id, name, email, password_hash, role FROM users WHERE email = %s LIMIT 1"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, (email.strip().lower(),))
        return cursor.fetchone()
    except Error as e:
        print(f"[DB ERROR] get_user_by_email: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def checkPass(email: str, raw_password: str) -> bool:
    """
    Verifies the user's password against the stored password hash in the database.
    Returns True if valid, False otherwise.
    """
    # Note: Requires email to find which user's password to compare against
    query = "SELECT password_hash FROM users WHERE email = %s LIMIT 1"
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, (email.strip().lower(),))
        result = cursor.fetchone()

        if result:
            stored_hash = result[0]
            # Replace with your hashing verification method (e.g., bcrypt / passlib / argon2)
            # Example using passlib/bcrypt: return pwd_context.verify(raw_password, stored_hash)
            return stored_hash == raw_password
        return False
    except Error as e:
        print(f"[DB ERROR] checkPass: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# -----------------------------------------------

# 1. Insert initial document record when uploaded
def insert_document(uploaded_by, document_type, file_path, person_id=None, status="PENDING"):
    query = """
        INSERT INTO documents (person_id, uploaded_by, document_type, file_path, status)
        VALUES (%s, %s, %s, %s, %s)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, (person_id, uploaded_by, document_type, file_path, status))
        conn.commit()
        doc_id = cursor.lastrowid
        return doc_id
    except Error as e:
        print(f"[DB ERROR] insert_document: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


# 2. Check if a document number is in the blacklist
def check_blacklist(document_number):
    query = """
        SELECT id, document_number, reason, status 
        FROM blacklist 
        WHERE document_number = %s AND status = 'ACTIVE'
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, (document_number,))
        result = cursor.fetchone()
        return result  # Returns dict if found, None otherwise
    except Error as e:
        print(f"[DB ERROR] check_blacklist: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


# 3. Store extracted OCR data
def insert_extracted_data(document_id, extracted_dict):
    query = """
        INSERT INTO extracted_data (
            document_id, name, passport_number, nationality, 
            dob, gender, expiry_date, visa_number, visa_type
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, (
            document_id,
            extracted_dict.get("name"),
            extracted_dict.get("passport_number"),
            extracted_dict.get("nationality"),
            extracted_dict.get("dob"),
            extracted_dict.get("gender"),
            extracted_dict.get("expiry_date"),
            extracted_dict.get("visa_number"),
            extracted_dict.get("visa_type")
        ))
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"[DB ERROR] insert_extracted_data: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


# 4. Store verification scores and risk score
def insert_verification_results(document_id, ocr_score, validation_score, tampering_score, face_match_score, risk_score, final_status):
    query = """
        INSERT INTO verification_results (
            document_id, ocr_score, validation_score, 
            tampering_score, face_match_score, risk_score, final_status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, (
            document_id, ocr_score, validation_score,
            tampering_score, face_match_score, risk_score, final_status
        ))
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"[DB ERROR] insert_verification_results: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


# 5. Log officer's screening decision
def insert_screening_log(document_id, officer_id, action, decision):
    query = """
        INSERT INTO screening_logs (document_id, officer_id, action, decision)
        VALUES (%s, %s, %s, %s)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, (document_id, officer_id, action, decision))
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"[DB ERROR] insert_screening_log: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def get_dashboard_metrics() -> dict:
    """
    Fetches real-time summary statistics, risk distribution, daily screening volume,
    and recent records directly from the `screenings` table.
    """
    conn = None
    dashboard_data = {
        "summary": {
            "total": 0,
            "verified": 0,
            "rejected": 0,
            "suspicious": 0,
            "verification_rate": 0.0,
            "rejection_rate": 0.0,
            "suspicious_rate": 0.0
        },
        "risk_distribution": {
            "low_risk": 0,
            "rejected": 0,
            "medium_risk": 0
        },
        "screening_activity": [],
        "recent_screenings": []
    }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Summary Cards & Risk Breakdown
        summary_query = """
            SELECT 
                COUNT(*) AS total,
                COUNT(CASE WHEN LOWER(decision) = 'verified' THEN 1 END) AS verified,
                COUNT(CASE WHEN LOWER(decision) = 'rejected' THEN 1 END) AS rejected,
                COUNT(CASE WHEN LOWER(decision) IN ('suspicious', 'manual_review') THEN 1 END) AS suspicious
            FROM screenings;
        """
        cursor.execute(summary_query)
        stats = cursor.fetchone()
        
        if stats:
            total = stats.get("total") or 0
            verified = stats.get("verified") or 0
            rejected = stats.get("rejected") or 0
            suspicious = stats.get("suspicious") or 0

            dashboard_data["summary"] = {
                "total": total,
                "verified": verified,
                "rejected": rejected,
                "suspicious": suspicious,
                "verification_rate": round((verified / total * 100), 1) if total > 0 else 0.0,
                "rejection_rate": round((rejected / total * 100), 1) if total > 0 else 0.0,
                "suspicious_rate": round((suspicious / total * 100), 1) if total > 0 else 0.0
            }
            dashboard_data["risk_distribution"] = {
                "low_risk": verified,
                "rejected": rejected,
                "medium_risk": suspicious
            }

        # 2. Daily Screening Activity (Last 6-7 days trend for the line chart)
        activity_query = """
            SELECT 
                DATE(screening_time) AS date,
                DATE_FORMAT(screening_time, '%d %b') AS label,
                COUNT(*) AS volume
            FROM screenings
            WHERE screening_time >= CURDATE() - INTERVAL 6 DAY
            GROUP BY DATE(screening_time), DATE_FORMAT(screening_time, '%d %b')
            ORDER BY DATE(screening_time) ASC;
        """
        cursor.execute(activity_query)
        dashboard_data["screening_activity"] = cursor.fetchall()

        # 3. Recent Screenings List (Top 10 latest records)
        recent_query = """
            SELECT 
                s.screening_id,
                s.person_id,
                s.document_id,
                s.officer_id,
                s.risk_score,
                s.decision,
                s.screening_time,
                d.document_type,
                ed.name AS applicant_name,
                ed.passport_number
            FROM screenings s
            LEFT JOIN documents d ON s.document_id = d.id
            LEFT JOIN extracted_data ed ON s.document_id = ed.document_id
            ORDER BY s.screening_time DESC
            LIMIT 10;
        """
        cursor.execute(recent_query)
        dashboard_data["recent_screenings"] = cursor.fetchall()

        return dashboard_data

    except Error as e:
        print(f"[DB ERROR] get_dashboard_metrics: {e}")
        return dashboard_data
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def insert_screening(person_id: int, document_id: int, officer_id: int, risk_score: float = None, decision: str = "verified") -> int | None:
    """
    Inserts a record into the screenings table matching the schema attributes:
    (person_id, document_id, officer_id, risk_score, decision)
    Returns the generated screening_id on success, or None on failure.
    """
    query = """
        INSERT INTO screenings (person_id, document_id, officer_id, risk_score, decision)
        VALUES (%s, %s, %s, %s, %s)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, (person_id, document_id, officer_id, risk_score, decision))
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"[DB ERROR] insert_screening: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def insert_document_and_screening(
    uploaded_by: int,
    document_type: str,
    file_path: str,
    officer_id: int,
    person_id: int = None,
    risk_score: float = None,
    decision: str = "verified",
    status: str = "PENDING"
) -> dict | None:
    """
    Atomically inserts document details into `documents` and screening details
    into `screenings` within a single database transaction.
    """
    doc_query = """
        INSERT INTO documents (person_id, uploaded_by, document_type, file_path, status)
        VALUES (%s, %s, %s, %s, %s)
    """
    screening_query = """
        INSERT INTO screenings (person_id, document_id, officer_id, risk_score, decision)
        VALUES (%s, %s, %s, %s, %s)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Insert Document
        cursor.execute(doc_query, (person_id, uploaded_by, document_type, file_path, status))
        document_id = cursor.lastrowid

        # 2. Insert Screening record referencing the new document_id
        cursor.execute(screening_query, (person_id, document_id, officer_id, risk_score, decision))
        screening_id = cursor.lastrowid

        conn.commit()
        return {
            "document_id": document_id,
            "screening_id": screening_id
        }
    except Error as e:
        print(f"[DB ERROR] insert_document_and_screening: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


            def get_all_audit_logs(limit: int = 50, offset: int = 0) -> list[dict]:
    """
    Fetches audit log records enriched with user name and document details
    for the Audit History dashboard view.
    """
    query = """
        SELECT 
            al.log_id,
            al.user_id,
            u.name AS user_name,
            u.email AS user_email,
            al.document_id,
            d.document_type,
            al.action,
            al.decision,
            al.timestamp
        FROM audit_logs al
        LEFT JOIN users u ON al.user_id = u.user_id
        LEFT JOIN documents d ON al.document_id = d.id
        ORDER BY al.timestamp DESC
        LIMIT %s OFFSET %s;
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, (limit, offset))
        return cursor.fetchall()
    except Error as e:
        print(f"[DB ERROR] get_all_audit_logs: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def get_audit_logs_by_user(user_id: int, limit: int = 20) -> list[dict]:
    """
    Fetches audit trail records performed by a specific user.
    """
    query = """
        SELECT 
            log_id,
            user_id,
            document_id,
            action,
            decision,
            timestamp
        FROM audit_logs
        WHERE user_id = %s
        ORDER BY timestamp DESC
        LIMIT %s;
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, (user_id, limit))
        return cursor.fetchall()
    except Error as e:
        print(f"[DB ERROR] get_audit_logs_by_user: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def insert_audit_log(user_id: int, document_id: int = None, action: str = None, decision: str = None) -> int | None:
    """
    Inserts a new event into the audit_logs table.
    """
    query = """
        INSERT INTO audit_logs (user_id, document_id, action, decision)
        VALUES (%s, %s, %s, %s)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, (user_id, document_id, action, decision))
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print(f"[DB ERROR] insert_audit_log: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()



            def register_user(name: str, email: str, raw_password: str, role: str = "officer") -> dict:
    """
    Registers a new user in the users table.
    Returns a dict with success status and user_id/message.
    """
    cleaned_email = email.strip().lower()

    # 1. Check if email already exists
    if searchUser(cleaned_email):
        return {"success": False, "message": "Email already registered"}

    # 2. Hash the plain password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(raw_password.encode('utf-8'), salt).decode('utf-8')

    # 3. Insert new user record
    query = """
        INSERT INTO users (name, email, password_hash, role)
        VALUES (%s, %s, %s, %s)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, (name.strip(), cleaned_email, hashed_password, role))
        conn.commit()
        user_id = cursor.lastrowid
        return {"success": True, "user_id": user_id, "message": "User registered successfully"}
    except Error as e:
        print(f"[DB ERROR] register_user: {e}")
        if conn:
            conn.rollback()
        return {"success": False, "message": f"Database error: {str(e)}"}
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()