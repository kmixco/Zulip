
from typing import Text, List

import pytz

def get_all_timezones():
    # type: () -> List[Text]
    return sorted(pytz.all_timezones)
