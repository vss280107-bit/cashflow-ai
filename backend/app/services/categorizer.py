"""Rule-based transaction categorizer (keyword matching). Swap for an ML classifier later."""

EXPENSE_RULES = {
    "rent": ["rent", "landlord", "pg ", "hostel fee"],
    "food": ["swiggy", "zomato", "restaurant", "cafe", "starbucks", "dominos", "mcdonald", "kfc", "grocery",
             "bigbasket", "blinkit", "zepto", "instamart", "dmart", "lunch", "dinner", "breakfast", "chai",
             "coffee", "canteen", "mess", "snacks", "food"],
    "transport": ["uber", "ola", "rapido", "metro", "fuel", "petrol", "diesel", "irctc", "redbus", "cab",
                  "auto", "bus pass", "train", "parking"],
    "bills": ["electricity", "bescom", "water bill", "gas", "broadband", "wifi", "airtel", "jio", "recharge",
              "internet", "bill", "emi", "insurance", "mobile"],
    "entertainment": ["netflix", "spotify", "prime", "hotstar", "youtube", "movie", "bookmyshow", "pvr",
                      "steam", "game", "concert", "subscription"],
    "shopping": ["amazon", "flipkart", "myntra", "ajio", "nykaa", "decathlon", "mall", "shopping", "clothes",
                 "shoes", "gadget", "laptop", "phone"],
    "education": ["course", "udemy", "coursera", "tuition", "college", "fees", "book", "exam", "stationery",
                  "certification"],
    "health": ["pharmacy", "apollo", "medical", "hospital", "clinic", "doctor", "gym", "cult", "medicine"],
    "travel": ["hotel", "oyo", "makemytrip", "airbnb", "goibibo", "flight", "indigo", "trip", "vacation"],
}
INCOME_RULES = {
    "salary": ["salary", "stipend", "payroll", "wages"],
    "freelance": ["freelance", "client", "project payment", "invoice", "gig"],
    "other income": ["refund", "interest", "cashback", "gift", "pocket money", "allowance", "dividend"],
}

EXPENSE_CATEGORIES = [*EXPENSE_RULES.keys(), "other"]
INCOME_CATEGORIES = [*INCOME_RULES.keys(), "other income"]


def categorize(description: str, txn_type: str) -> str:
    text = f" {(description or '').lower()} "
    rules = INCOME_RULES if txn_type == "income" else EXPENSE_RULES
    for category, words in rules.items():
        if any(w in text for w in words):
            return category
    return "other income" if txn_type == "income" else "other"
