
import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Load env
load_dotenv()

# Add path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import app, db, User

# Import payment models definition
from payment_module import create_payment_models

# Initialize Payment Models
payment_models = create_payment_models(db)
CreditLedger = payment_models['CreditLedger']

# Initialize Supabase Admin Client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("Error: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    sys.exit(1)

supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

EMAIL = "lewis@tsaftech.com" # Target user email

def grant_credits():
    with app.app_context():
        # Ensure tables exist
        db.create_all()
        
        # 1. Get User from Supabase
        print(f"Fetching user {EMAIL} from Supabase...")
        try:
            # List users to find the one with the email
            # supabase-py admin.list_users() might not be straightforward in all versions, 
            # but auth.admin.list_users() is standard for gotrue-py which underlies it.
            # Let's try listing users.
            
            # Using list_users with a filter if possible, or iterating.
            # Page defaults to 1, per_page defaults to 50.
            response = supabase_admin.auth.admin.list_users() 
            target_user = None
            # Check if response is a list or an object with users attribute
            users_list = response.users if hasattr(response, 'users') else response
            for user in users_list:
                if user.email == EMAIL:
                    target_user = user
                    break
            
            if not target_user:
                print(f"User {EMAIL} not found in Supabase Auth.")
                return

            print(f"Found Supabase User: {target_user.id}")
            
            # 2. Sync User to Local DB
            local_user = User.query.get(target_user.id)
            if not local_user:
                print(f"User not found in local DB. Creating...")
                local_user = User(
                    id=target_user.id,
                    email=target_user.email,
                    username=target_user.email.split('@')[0], # Default username
                    created_at=datetime.now() # Fallback to now to simplify debugging for this step, or handle parsing better
                )
                db.session.add(local_user)
                db.session.commit()
                print("Local User created.")
            else:
                print("Local User already exists.")

            # 3. Grant Credits
            # Check existing credits
            existing_ledger = CreditLedger.query.filter_by(
                user_id=target_user.id,
                service_type='stock_analysis',
                source='admin_grant'
            ).first()

            if existing_ledger:
                print(f"User already has admin_grant credits: {existing_ledger.amount_remaining}")
                # Optional: Add more? For now just skip
            else:
                print("Granting 1000 credits...")
                new_ledger = CreditLedger(
                    user_id=target_user.id,
                    service_type='stock_analysis',
                    source='admin_grant',
                    amount_initial=1000,
                    amount_remaining=1000,
                    expires_at=None # Never expires
                )
                db.session.add(new_ledger)
                db.session.commit()
                print("Credits granted successfully.")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    from datetime import datetime
    grant_credits()
