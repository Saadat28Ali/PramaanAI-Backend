from mysql.connector import Error
from .connection import get_db_connection

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
