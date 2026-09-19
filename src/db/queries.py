from mysql.connector import Error
from .connection import get_db_connection
from ..util import checkDictShape

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

def searchUser(email: str) -> dict:
	"""
	Fetches full user record as a dictionary. Returns None if not found.
	"""
	query = "SELECT * FROM users WHERE email = %s LIMIT 1"
	conn = None
	try:
		conn = get_db_connection()
		cursor = conn.cursor(dictionary=True)
		cursor.execute(query, (email.strip().lower(),))
		return {
			"success": True,
			"row": cursor.fetchone()
		}

	except Error as e:
		print(f"[DB ERROR] get_user_by_email: {e}")
		return {
			"success": False,
			"error": e
		};

	finally:
		if conn and conn.is_connected():
			cursor.close()
			conn.close()

#def checkPass(email: str, raw_password: str) -> bool:
#	"""
#	Verifies the user's password against the stored password hash in the database.
#	Returns True if valid, False otherwise.
#	"""
#	# Note: Requires email to find which user's password to compare against
#	query = "SELECT password_hash FROM users WHERE email = %s LIMIT 1"
#	conn = None
#	try:
#		conn = get_db_connection()
#		cursor = conn.cursor()
#		cursor.execute(query, (email.strip().lower(),))
#		result = cursor.fetchone()
#
#		if result:
#			stored_hash = result[0]
#			# Replace with your hashing verification method (e.g., bcrypt / passlib / argon2)
#			# Example using passlib/bcrypt: return pwd_context.verify(raw_password, stored_hash)
#			return stored_hash == raw_password
#		return False
#	except Error as e:
#		print(f"[DB ERROR] checkPass: {e}")
#		return False
#	finally:
#		if conn and conn.is_connected():
#			cursor.close()
#			conn.close()

# -----------------------------------------------

# 1. Insert initial document record when uploaded
def insertDocument(
	user_id,
	document_type,
	file_path,
	status="uploaded"
):
#	Returns:
#		{
#			"success" bool,
#			...
#		}
	query = """
		INSERT INTO documents (user_id, document_type, file_path, status)
		VALUES (%s, %s, %s, %s)
	"""
	conn = None
	try:
		conn = get_db_connection()
		cursor = conn.cursor(dictionary = True)
		cursor.execute(query, (user_id, document_type, file_path, status))
		conn.commit();
		document_id = cursor.lastrowid;
		return {
			"success": True,
			"document_id": document_id
		};
	except Error as e:
		print(f"[DB ERROR] insert_document: {e}")
		if conn:
			conn.rollback()
		return {
			"success": False,
			"error": e
		};
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
	# for inserting docs
	user_id: int,
	document_type: str,
	file_path: str,

	# for inserting screening
	officer_id: int,
	person_id: int = None,
	risk_score: float = None,
	decision: str = ""
) -> dict | None:
	"""
	Atomically inserts document details into `documents` and screening details
	into `screenings` within a single database transaction.
	Returns: {
		"success": bool,
		...
	}
	"""
	doc_query = """
		INSERT INTO documents (user_id, document_type, file_path)
		VALUES (%s, %s, %s)
	"""
	screening_query = """
		INSERT INTO screenings (person_id, document_id, officer_id, risk_score, decision)
		VALUES (%s, %s, %s, %s, %s)
	"""
	conn = None
	try:
		conn=get_db_connection()
		cursor = conn.cursor(dictionary = True)

		# 1. Insert Document
		result: dict = cursor.execute(doc_query, (user_id, document_type, file_path))
		# document_id = cursor.lastrowid
		document_id=result["document_id"];

		# 2. Insert Screening record referencing the new document_id
		result: dict = cursor.execute(screening_query, (person_id, document_id, officer_id, risk_score, decision));
		screening_id = result["screening_id"];

		conn.commit();
		return {
			"success": True,
			"document_id": document_id,
			"screening_id": screening_id
		}
	except Error as e:
		print(f"[DB ERROR] insert_document_and_screening: {e}")
		if conn:
			conn.rollback()
		return {
			"success": False,
			"error": str(e),
		};
	finally:
		if conn and conn.is_connected():
			cursor.close()
			conn.close()

#
#def get_all_audit_logs(limit: int = 50, offset: int = 0) -> list[dict]:
#	"""
#	Fetches audit log records enriched with user name and document details
#	for the Audit History dashboard view.
#	Returns:
#		{
#			"success": bool,
#			...
#		}
#	"""
#	query = """
#		SELECT 
#			u.name AS user_name,
#			u.email AS user_email,
#			al.document_id,
#			d.document_type,
#			al.decision,
#			al.timestamp
#		FROM audit_logs al
#		LEFT JOIN users u ON al.user_id = u.user_id
#		LEFT JOIN documents d ON al.document_id = d.id
#		ORDER BY al.timestamp DESC
#		LIMIT %s OFFSET %s;
#	"""
#	conn = None
#	try:
#		conn = get_db_connection()
#		cursor = conn.cursor(dictionary=True)
#		cursor.execute(query, (limit, offset))
#		return {
#			"success": True,
#			"rows": cursor.fetchall()
#		}
#	except Error as e:
#		print(f"[DB ERROR] get_all_audit_logs: {e}")
#		return {
#			"success": False,
#			"error": e
#		};
#	finally:
#		if conn and conn.is_connected():
#			cursor.close()
#			conn.close()


def getAuditLogsByUser(user_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
	"""
	Fetches audit trail records performed by a specific user.
	Returns: {
		"success": bool,
		...
	}
	"""

	if type(limit) != int or type(offset) != int:
		limit = 20;
		offset = 0;

	query = """
		SELECT 
			d.document_id as doc_id,
			d.document_type as doc_type,
			u.name as user_name,
			al.timestamp as timestamp,
			al.decision as decision
		FROM audit_logs al
		LEFT JOIN users u ON al.user_id = u.user_id
		LEFT JOIN documents d ON al.document_id = d.document_id
		WHERE user_id = %s
		ORDER BY timestamp DESC
		LIMIT %s OFFSET %s;
	"""
	conn = None
	try:
		conn = get_db_connection()
		cursor = conn.cursor(dictionary=True)
		cursor.execute(query, (user_id, limit, offset))
		return {
			"success": True,
			"rows": cursor.fetchall()
		};
	except Error as e:
		print(f"[DB ERROR] get_audit_logs_by_user: {e}")
		return {
			"success": False,
			"error": e
		}
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

def addUserToOrganisation(organization_id: int, organization_user: str, user_id: int) -> dict:
	"""
	Inserts a newly created user into the organisation table.
	"""
	query = """
		INSERT INTO organisation (organization_id, organization_user, user_id)
		VALUES (%s, %s, %s)
	"""
	conn = None
	try:
		conn = get_db_connection()
		cursor = conn.cursor()
		cursor.execute(query, (organization_id, organization_user, user_id))
		conn.commit()
		return {"success": True, "message": "User linked to organization successfully"}
	except Error as e:
		print(f"[DB ERROR] addUserToOrganisation: {e}")
		if conn:
			conn.rollback()
		return {"success": False, "message": f"Database error: {str(e)}"}
	finally:
		if conn and conn.is_connected():
			cursor.close()
			conn.close()

def createOrganization(
	organization_name: str
) -> dict:
	conn = None;
	try:
		conn = get_db_connection();
		cursor = conn.cursor(dictionary = True);

		cursor.execute("insert into organization (organization_name) values (%s)", (organization_name));
		if (cursor.fetchone()):
			return {
				"success": true,
				"message": "Organization successfully created.",
				"details": {
					"organization_name": organization_name
				}
			};
	except Error as e:
		print(f"[DB ERROR] createOrganization: {e}")
		if conn:
			conn.rollback()
		return {"success": False, "message": f"Database error: {str(e)}"}
	finally:
		if conn and conn.is_connected():
			cursor.close()
			conn.close()

def createUser(
	oldUserData: dict,
	newUserData: dict,
	admin_registration: str
) -> dict:

	conn = None;
	cursor = None;
	try:
		conn = get_db_connection();
		cursor = conn.cursor(dictionary=True, buffered=True);

		if (admin_registration):

			# Creating a new admin user (from /register endpoint)
			# --------------------------------------------------

			# Checking if all fields are present in newUserData
			# --------------------------------------------------
			if (not checkDictShape(newUserData, {"email", "password", "name", "organization", "phone"})):
				return {
					"success": False,
					"message": "Could not create user due to missing fields.",
					"details": {
						"newUserData": newUserData
					}
				};
			newUserData["email"] = newUserData["email"].strip().lower();

			# Checking if user already exists with same email and password
			# --------------------------------------------------
			row: dict = cursor.execute("select * from users where user_id = %s and password_hash = %s", (newUserData["email"], newUserData["password"]));

			if (row):
				return {
					"success": False,
					"message": "Could not create user, the user with given email already exists",
					"details": {
						"oldUserData": oldUserData,
						"newUserData": newUserData,
						"admin_registration": admin_registration
					}
				};

#			cursor.execute("describe users");
#			for row in cursor.fetchall():
#				print(row);


			# Creating new organization before creating a new admin user
			# --------------------------------------------------
			cursor.execute("insert into organization (organization_name) values (%s)", (newUserData["organization"], ));
			organization_id: str = cursor.lastrowid;

			# Creating new user
			# --------------------------------------------------
			cursor.execute("insert into users (email, name, password_hash, phone, organization_id, role) values (%s, %s, %s, %s, %s, %s)", (
				newUserData["email"],
				newUserData["name"],
				newUserData["password"],
				newUserData["phone"],
				organization_id,
				"admin"
			));
			user_id: str = cursor.lastrowid;
			conn.commit();

			# Returning final output
			# --------------------------------------------------
			return {
				"success": True,
				"message": "Created user and organization",
				"details": {
					"user_id": user_id,
					"organization_id": organization_id
				}
			};
		else:

			# Creating a new officer
			# --------------------------------------------------

			# Checking the shape of newUserData
			# --------------------------------------------------
			if (not checkDictShape(newUserData, {"email", "password", "name", "phone"})):
				return {
					"success": False,
					"message": "Could not create user due to missing fields.",
					"details": {
						"newUserData": newUserData
					}
				};
			newUserData["email"] = newUserData["email"].strip().lower();

			# Checking the shape of oldUserData
			# --------------------------------------------------
			if (not checkDictShape(oldUserData, {"email", "password"})):
				return {
					"success": False,
					"message": "Could not create officer, due to invalid authorization of admin user.",
					"details": {
						"oldUserData": oldUserData
					}
				};

			# Checking if admin user exists or not
			# --------------------------------------------------
			cursor.execute("select organization_id from users where email = %s and password_hash = %s limit 1", (oldUserData["email"], oldUserData["password"]));
			row: dict = cursor.fetchone();
			if (not row):
				return {
					"success": False,
					"message": "Could not create officer, admin user does not exist.",
					"details": {
						"oldUserData": oldUserData
					}
				}
			organization_id: str = row["organization_id"];

			# Creating user
			# --------------------------------------------------
			result: dict = cursor.execute("insert into users (name, email, phone, password_hash, organization_id, role) values (%s, %s, %s, %s, %s, %s)", (
				newUserData["name"],
				newUserData["email"],
				newUserData["phone"],
				newUserData["password"],
				organization_id,
				"officer"
			));
			user_id: str = cursor.lastrowid;

			conn.commit();

			# Returning final result
			# --------------------------------------------------
			return {
				"success": True,
				"message": "User and organization created",
				"details": {
					"user_id": user_id,
					"organization_id": organization_id
				}
			};

	except Error as e:
		print(f"[DB ERROR] createUser: {e}")
		if conn:
			conn.rollback();
		return {"success": False, "message": "Could not create user or organization.", "details": {
			"oldUserData": oldUserData,
			"newUserData": newUserData,
			"admin_registration": admin_registration
		}}
	finally:
		if conn and conn.is_connected():
			conn.close();
		if cursor:
			cursor.close();
