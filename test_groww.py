import os
import logging
from dotenv import load_dotenv
from growwapi import GrowwAPI

# Set up clean logging for the terminal
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

def run_diagnostics():
    logger.info("=== GROWW API DIAGNOSTIC TEST ===")
    
    # 1. Load Environment Variables
    load_dotenv()
    api_key = os.getenv("GROWW_API_KEY")
    secret_key = os.getenv("GROWW_SECRET_KEY")

    if not api_key or not secret_key:
        logger.error("❌ ERROR: Could not find GROWW_API_KEY or GROWW_SECRET_KEY in your .env file.")
        logger.info("Please make sure your .env file is in the same folder and the names match exactly.")
        return

    logger.info("✅ Credentials found in .env file.")

    try:
        # 2. Test Authentication (Token Generation)
        logger.info("⏳ Attempting to generate Access Token...")
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=secret_key)
        
        if not access_token:
            logger.error("❌ ERROR: Token generation failed. Check if your API Key and Secret are valid and active on the dashboard.")
            return
            
        logger.info("✅ Access Token successfully generated!")

        # 3. Test Client Initialization
        logger.info("⏳ Initializing Groww Client...")
        client = GrowwAPI(access_token)
        logger.info("✅ Client initialized!")

        # 4. Test Read-Only Data Fetch (Safe test, no money involved)
        logger.info("⏳ Testing data retrieval (Fetching basic user data)...")
        
        # Note: We use a safe, read-only endpoint here. 
        # If get_profile() throws an error, you can swap it to get_holdings_for_user()
        try:
            profile_data = client.get_profile() 
            logger.info("✅ Read-only data fetch successful!")
            logger.info("\n🎉 SUCCESS! Your API is fully connected and ready to use for the bot.")
        except Exception as data_error:
            logger.warning(f"⚠️ Authenticated successfully, but data fetch failed. The SDK might use a different method name. Error: {data_error}")
            logger.info("However, your keys ARE working!")

    except Exception as e:
        logger.error(f"❌ Connection Test Failed: {e}")
        logger.info("Common fixes: Check your internet connection, ensure no extra spaces are in your .env file strings, and verify the keys aren't expired.")

if __name__ == "__main__":
    run_diagnostics()