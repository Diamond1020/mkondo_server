from flask_restful import Resource, reqparse

from .models import Notification
from .schemas import NotificationSchema
from users.models import User

notifications_schema = NotificationSchema(many=True)
notification_schema = NotificationSchema()


class NotificationListResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('dispatcher', type=str, required=True)
    parser.add_argument('message', type=str, required=True)

    @staticmethod
    def get():
        notifications = Notification.fetch_all()

        if len(notifications) == 0:
            return {
                'success': False,
                'message': 'No notification found'
            }, 404

        return {
            'success': True,
            'notifications': notifications
        }, 200

    @staticmethod
    def post():
        json_data = NotificationListResource.parser.parser_args()

        dispatcher = User.fetch_by_id(json_data['dispatcher'])

        if not dispatcher:
            return {
                'success': False,
                'message': f"Dispatcher with user_id {json_data['dispatcher']} not found"
            }, 404

        notification_data = notification_schema.load(json_data)
        notification = Notification(**notification_data)

        try:
            notification.save()
        except:
            return {
                'success': False,
                'message': 'There was an error issuing the notification'
            }, 500

        return {
            'success': True,
            'message': 'Notification created successfully'
        }, 201


class NotificationOpenedResource(Resource):
    @staticmethod
    def post(notification_id):
        notification = Notification.fetch_by_id(notification_id)

        if not notification:
            return {
                'success': False,
                'message': 'Notification not found'
            }, 404

        notification.count = notification.count + 1

        notification.save()

        return {
            'success': True,
            'message': 'Notifcation opened count increased'
        }, 201

    @staticmethod
    def get(notification_id):
        notification = Notification.fetch_by_id(notification_id)

        if not notification:
            return {
                'success': False,
                'message': 'Notification not found'
            }, 404

        return {
            'success': True,
            'count': notification.opened
        }
