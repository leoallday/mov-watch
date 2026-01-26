import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mov_watch.app import main
from mov_watch.utils import is_bundled
from mov_watch.updater import check_for_updates

if __name__ == "__main__":
    if is_bundled():
        check_for_updates()
    
    main()
