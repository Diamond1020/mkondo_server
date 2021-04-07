import uuid
from datetime import datetime

from mkondo import db


notification_user_table = db.Table(
    'notification_user',
    db.Column('notification_id', db.ForeignKey('notifications.id', ondelete='CASCADE'), nullable=False),
    db.Column('user_id', db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
)


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    message = db.Column(db.Text, nullable=False)
    opened = db.Column(db.Integer, nullable=False, default=0)
    dispatcher = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    users = db.relationship('User', secondary=notification_user_table)

    def __init__(self, message, dispatcher):
        self.message = message
        self.dispatcher = dispatcher
        self.notification_id = uuid.uuid4()

    @classmethod
    def fetch_all(cls):
        """
        Fetch all notifications from the database
        """
        return cls.query.all()

    def save(self):
        """
        Save current notification
        """
        db.session.add(self)
        db.session.commit()
