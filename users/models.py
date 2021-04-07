import uuid
from datetime import datetime

import pandas
import numpy
from sklearn.model_selection import train_test_split

from mkondo import db, argon_2

media_user_favourites_table = db.Table(
    'media_user_favourites',
    db.Column('media_id', db.ForeignKey('media.id'), nullable=False),
    db.Column('user_id', db.ForeignKey('users.id'), nullable=False)
)


class MediaUserHistory(db.Model):
    __tablename__ = 'media_user_history'
    __table_args__ = (
        db.PrimaryKeyConstraint('user_id', 'media_id'),
    )
    user_id = db.Column(db.ForeignKey('users.id'), nullable=False)
    media_id = db.Column(db.ForeignKey('media.id'), nullable=False)
    plays = db.Column(db.Integer, nullable=False, default=1)
    user = db.relationship('User', back_populates='history')
    media = db.relationship('Media')

    def __init__(self, user_id, media_id):
        self.media_id = media_id
        self.user_id = user_id
        self.plays = 1

    @classmethod
    def exists(cls, user_id, media_id):
        if cls.query.filter_by(user_id=user_id, media_id=media_id).first():
            return True
        return False

    @classmethod
    def increase_plays(cls, user_id, media_id):
        user_media_history = cls.query.filter_by(user_id=user_id, media_id=media_id).first()
        user_media_history.plays = user_media_history.plays + 1
        db.session.add(user_media_history)
        db.session.commit()

    @classmethod
    def get_train_data(cls):
        user_history_data = pandas.read_sql_table(cls.__tablename__, con=db.engine)
        media_data = pandas.read_sql_table('media', con=db.engine, columns=['id', 'media_id', 'plays'])

        media_df = pandas.merge(user_history_data, media_data, left_on='media_id', right_on='id', how='left')
        media_grouped = media_df.groupby(['media_id_y']).agg({'plays_x': 'count'}).reset_index()
        grouped_sum = media_grouped['plays_x'].sum()
        media_grouped['percentage'] = media_grouped['plays_x'].div(grouped_sum) * 100
        media_grouped.sort_values(['plays_x', 'media_id_y'], ascending=[0, 1])
        users = media_df['user_id'].unique()
        media = media_df['media_id_x'].unique()
        train_data, test_data = train_test_split(media_df, test_size=0.20, random_state=0)

        return train_data

    def save(self):
        db.session.add(self)
        db.session.commit()


genre_user_table = db.Table(
    'genre_user',
    db.Column('genre_id', db.Integer, db.ForeignKey('genres.id'), nullable=False),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), nullable=False)
)


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False, unique=True, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    phone_number = db.Column(db.String(50), nullable=False, unique=True, index=True)
    password = db.Column(db.String(128), nullable=False)
    user_type = db.Column(db.String(50), nullable=False)
    joined = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    country = db.Column(db.String(50), nullable=False, default='TZ')
    locality = db.Column(db.String(50), nullable=False)
    avatar_url = db.Column(db.Text, nullable=True)
    cover_url = db.Column(db.Text, nullable=True)
    about = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    facebook_link = db.Column(db.Text, nullable=True)
    instagram_link = db.Column(db.Text, nullable=True)
    twitter_link = db.Column(db.Text, nullable=True)
    youtube_link = db.Column(db.Text, nullable=True)
    admin_id = db.Column(db.String(50), nullable=True)
    publish = db.Column(db.Boolean, default=True, nullable=False)
    archived = db.Column(db.Boolean, nullable=False, default=False)
    albums = db.relationship('Album', backref='owner', cascade="all, delete")
    favourites = db.relationship('Media', secondary=media_user_favourites_table, cascade="all, delete")
    history = db.relationship('MediaUserHistory', back_populates='user')
    genres = db.relationship('Genre', secondary=genre_user_table, backref='users')

    def __init__(self, full_name, email, phone_number, password, user_type, locality, country='TZ', instagram_link=None,
                 facebook_link=None, youtube_link=None, twitter_link=None, avatar_url=None, description=None, admin_id=None, about=None, cover_url=None):
        """
        Create a new user.
        """
        self.user_id = uuid.uuid4()
        self.full_name = full_name.lower().title()
        self.email = email.lower()
        self.password = argon_2.generate_password_hash(password)
        self.country = country
        self.locality = locality
        self.user_type = user_type
        self.phone_number = phone_number

        if user_type != 'user':
            self.publish = False

        if youtube_link:
            self.youtube_link = youtube_link

        if instagram_link:
            self.instagram_link = instagram_link

        if twitter_link:
            self.twitter_link = twitter_link

        if facebook_link:
            self.facebook_link = facebook_link

        if avatar_url:
            self.avatar_url = avatar_url
        
        if description:
            self.description = description
        
        if admin_id:
            self.admin_id = admin_id
        
        if about:
            self.about = about
        
        if cover_url:
            self.cover_url = cover_url

    def __repr__(self):
        """
        Represent the user instance by email address.
        """
        return self.email

    @classmethod
    def fetch_by_email(cls, email):
        """
        Fetch a single user by their email address.
        """
        return cls.query.filter_by(email=email).first()
    
    @property
    def followers(self):
        followers = Follower.query.with_entities(Follower.follower_id).filter_by(user_id=self.id).all()
        return self.query.filter(User.id.in_(followers)).all()
    
    @property
    def following(self):
        followers = Follower.query.with_entities(Follower.user_id).filter_by(follower_id=self.id).all()
        return self.query.filter(User.id.in_(followers)).all()


    @classmethod
    def fetch_by_phone_number(cls, phone_number):
        """
        Fetch a single user by their phone number.
        """
        return cls.query.filter_by(phone_number=phone_number).first()
    
    @classmethod
    def search(cls, query, user_type=None, limit=10):
        """
        Search media by query
        """

        if user_type:
            return cls.query.filter((cls.full_name.ilike(f'%{query}%')) | (cls.description.ilike(f'%{query}%'))).filter_by(user_type=user_type).limit(limit).all()

        return cls.query.filter((cls.full_name.ilike(f'%{query}%')) | (cls.description.ilike(f'%{query}%'))).limit(limit).all()

    @classmethod
    def fetch_all(cls):
        """
        Fetch all users from the database.
        """
        return cls.query.filter_by(archived=False).all()

    @classmethod
    def fetch_all_by_type(cls, user_type):
        """
        Fetch all non archived users by type.
        """
        return cls.query.filter_by(archived=False, user_type=user_type).all()
    
    @classmethod
    def get_users_under_admin(cls, user_type, admin_id):
        return cls.query.filter_by(user_type=user_type, admin_id=admin_id).all()

    @classmethod
    def fetch_artists_by_genre(cls, genre):
        """
        Retrun all artists who who belong to the specified genre.
        """
        return cls.query.filter(user_type='creator').filter(cls.genres.any(name=genre.lower())).all()

    @classmethod
    def fetch_by_id(cls, user_id):
        """
        Fetch a single user by their user id.
        """
        return cls.query.filter_by(user_id=user_id).first()
    
    @classmethod
    def fetch_artist_by_id(cls, user_id):
        """
        Fetch an artist by user id
        """
        return cls.query.filter_by(user_id=user_id, user_type='creator').first()

    @classmethod
    def fetch_by_username(cls, username):
        """
        Fetch a single user by either their phone number
        or email address as their username.
        """
        return cls.query.filter((cls.email == username) | (cls.phone_number == username)).first()

    @classmethod
    def fetch_artists(cls):
        """
        Return all users who are creators/artists.
        """
        return cls.query.filter_by(archived=False, user_type='creator').all()

    def delete(self):
        """
        Delete the current user from the database.
        """
        db.session.delete(self)
        db.session.commit()

    def save(self):
        """
        Save the current user to the database.
        """
        db.session.add(self)
        db.session.commit()


class ResetToken(db.Model):
    __tablename__ = 'reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.Text, nullable=False)
    is_valid = db.Column(db.Boolean, default=True, nullable=False)

    def __init__(self, token, user_id):
        self.user_id = user_id
        self.token = token

    def add_token(self):
        """
        Save token to database.
        """
        db.session.add(self)
        db.session.commit()

    @classmethod
    def deactivate_reset_tokens(cls, user_id):
        """
        Deactivate all reset tokens for a given user.
        """
        valid_tokens = cls.query.filter_by(user_id=user_id, is_valid=True).all()

        for token in valid_tokens:
            token.is_valid = False
            db.session.add(token)

        db.session.commit()

    @classmethod
    def token_is_valid(cls, token):
        """
        Check if token is valid.
        """
        db_token = cls.query.filter_by(token=token).first()

        if db_token.is_valid:
            return True

        return False


class Follower(db.Model):
    __tablename__ = 'user_followers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __init__(self, user_id, follower_id):
        self.user_id = user_id
        self.follower_id = follower_id
    
    @classmethod
    def get_follow(cls, user_id, follower_id):
        return cls.query.filter_by(user_id=user_id, follower_id=follower_id).first()
    
    @classmethod
    def delete_follow(cls, follow):
        """
        Deletes a follower instance.
        """
        db.session.delete(follow)
        db.session.commit()

    def save(self):
        """
        Save this instance to the database.
        """
        db.session.add(self)
        db.session.commit()
