ROLES = {
    "ceo":       {"name": "Aditi Rao",   "title": "Chief Executive Officer", "region": None,          "hideFinance": False},
    "finance":   {"name": "Karan Mehta", "title": "Finance Manager",         "region": None,          "hideFinance": False},
    "marketing": {"name": "Simran Kaur", "title": "Marketing Manager",       "region": None,          "hideFinance": True},
    "regional":  {"name": "Rohan Nair",  "title": "Regional Manager — South","region": "South India", "hideFinance": True},
}

def get_role(role_key: str) -> dict:
    return ROLES.get(role_key, ROLES["ceo"])
