import os
import shutil

cache_dir = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'py-yfinance')
print("Cache dir exists:", os.path.exists(cache_dir))
if os.path.exists(cache_dir):
    try:
        shutil.rmtree(cache_dir)
        print("Successfully cleared cache dir!")
    except Exception as e:
        print("Failed to clear cache dir:", e)
