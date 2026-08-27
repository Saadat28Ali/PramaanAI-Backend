from hashlib import new;

def hashIt(s: str, algo = "sha256") -> str:
	hash_obj = new(algo);
	hash_obj.update(s.encode("utf-8"));
	return hash_obj.hexdigest();
