from typing import Any

from django.db import models
from django.utils.timezone import now as timezone_now

from zerver.models.realms import Realm
from zerver.models.users import UserProfile


class SavedReply(models.Model):
    MAX_TITLE_LENGTH = 30

    realm = models.ForeignKey(Realm, on_delete=models.CASCADE)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=MAX_TITLE_LENGTH)
    content = models.TextField()
    date_created = models.DateTimeField(default=timezone_now)

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "date_created": int(self.date_created.timestamp()),
        }
