from mkondo import marshmallow
from .models import Notification
from users.schemas import UserSchema


class NotificationSchema(marshmallow.SQLAlchemySchema):
    users = marshmallow.Nested(UserSchema(dump_only=('user_id',), many=True))

    class Meta:
        model = Notification
        fields = ('message', 'users', 'opened', 'date')
