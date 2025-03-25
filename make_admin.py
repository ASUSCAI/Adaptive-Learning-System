from database.engine import DatabaseEngine
from database.models import User
from shared import db

def make_user_admin(email):
    # Get the user by email
    user = db.query(User).filter_by(email=email).first()
    
    if not user:
        print(f"User with email {email} not found.")
        return False
    
    # Make the user an admin
    user.is_admin = True
    db.add(user)
    print(f"User {user.name} ({user.email}) is now an admin.")
    return True

if __name__ == "__main__":
    # Get the email from command line argument or prompt
    import sys
    if len(sys.argv) > 1:
        email = sys.argv[1]
    else:
        email = input("Enter the email of the user to make admin: ")
    
    make_user_admin(email) 