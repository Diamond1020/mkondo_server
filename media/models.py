import uuid
from datetime import datetime
from users.models import User
from mkondo import db
from sqlalchemy import or_, desc

playlist_song_table = db.Table('playlist_song',
                               db.Column('playlist_id', db.ForeignKey('playlists.id'), nullable=False),
                               db.Column('song_id', db.ForeignKey('media.id'), nullable=False)
                               )

genre_media_table = db.Table(
    'genre_media',
    db.Column('genre_id', db.Integer, db.ForeignKey('genres.id'), nullable=False),
    db.Column('media_id', db.Integer, db.ForeignKey('media.id'), nullable=False)
)

genre_album_table = db.Table(
    'genre_album',
    db.Column('genre_id', db.Integer, db.ForeignKey('genres.id'), nullable=False),
    db.Column('album_id', db.Integer, db.ForeignKey('albums.id'), nullable=False)
)


class Media(db.Model):
    __tablename__ = 'media'

    id = db.Column(db.Integer, primary_key=True)
    media_id = db.Column(db.String(50), nullable=False, unique=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    cover_url = db.Column(db.Text, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    edited = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    plays = db.Column(db.Float, nullable=False, default=0.0)
    composer = db.Column(db.String, nullable=True)
    song_writer = db.Column(db.String, nullable=True)
    record_label = db.Column(db.String, nullable=True)
    release_date = db.Column(db.DateTime, nullable=True)
    movie_director = db.Column(db.String, nullable=True)
    staring = db.Column(db.String, nullable=True)
    production_company = db.Column(db.String, nullable=True)
    starting_date = db.Column(db.DateTime, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    archived = db.Column(db.Boolean, nullable=False, default=False)
    likes = db.Column(db.Integer, nullable=False, default=0)
    shares = db.Column(db.Integer, nullable=False, default=0)
    page_views = db.Column(db.Integer, nullable=False, default=0)
    media_url = db.Column(db.Text, nullable=False)
    owner_avatar_url = db.Column(db.Text, nullable=True)
    album_id = db.Column(db.Integer, db.ForeignKey('albums.id'), nullable=True)
    album = db.relationship('Album', back_populates='songs')
    genres = db.relationship('Genre', secondary=genre_media_table, backref='media')
    owner = db.relationship('User')

    def __init__(self, name, description, cover_url, duration, category, owner_id, media_url, record_label=None,
                 release_date=None, composer=None, song_writer=None, owner_avatar_url=None, album_id=None, genres=None, movie_director=None, staring=None, production_company=None, starting_date=None):
        self.media_id = uuid.uuid4()
        self.name = name
        self.description = description
        self.cover_url = cover_url
        self.duration = duration
        self.category = category
        self.owner_id = owner_id
        self.media_url = media_url

        if movie_director:
            self.movie_director = movie_director

        if staring:
            self.staring = staring

        if production_company:
            self.production_company = production_company
        
        if starting_date:
            self.starting_date = starting_date
        
        if album_id:
            self.album_id = album_id

        if song_writer:
            self.song_writer = song_writer

        if record_label:
            self.record_label = record_label

        if composer:
            self.composer = composer

        if release_date:
            self.release_date = release_date
        
        if owner_avatar_url:
            self.owner_avatar_url = owner_avatar_url
        
        if genres:
            for genre in genres:
                self.genres.append(Genre.get_or_create(genre['name']))

    def __repr__(self):
        """
        Represent a media instance by the media name.
        """
        return self.name

    @classmethod
    def fetch_all(cls):
        """
        Fetch all media files from storage.
        """
        return cls.query.all()

    @classmethod
    def fetch_latest_release(cls, amount, category):
        """
        Return latest release by amount.
        """
        return cls.query.filter_by(category=category).order_by(desc(cls.added)).limit(amount).all()

    @classmethod
    def get_media_by_user_id(cls, user_id):
        """
        Return all media belonging to a user
        """
        return cls.query.filter_by(owner_id=user_id)

    @classmethod
    def fetch_by_id(cls, media_id):
        """
        Fetch a single media object by it's id
        """
        return cls.query.filter_by(media_id=media_id).first()
    
    @classmethod
    def fetch_by_ids(cls, ids):
        """
        Fetch for media by multiple ids
        """
        return cls.query.filter(cls.media_id.in_(ids)).all()

    def save(self):
        """
        Save the current media object to the database.
        """
        db.session.add(self)
        db.session.commit()
    
    @classmethod
    def search(cls, query, limit=10):
        """
        Search media by query
        """
        return cls.query.filter((cls.name.ilike(f'%{query}%')) | (cls.description.ilike(f'%{query}%'))).limit(limit).all()

    def delete(self):
        """
        Delete a single media object permanently.
        """
        db.session.delete(self)
        db.session.commit()


class Playlist(db.Model):
    __tablename__ = 'playlists'

    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(255), nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    modified = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    duration = db.Column(db.Integer, nullable=False, default=0)
    likes = db.Column(db.Integer, nullable=False, default=0)
    shares = db.Column(db.Integer, nullable=False, default=0)
    page_views = db.Column(db.Integer, nullable=False, default=0)
    songs = db.relationship('Media', secondary=playlist_song_table)
    owner = db.relationship('User', backref='playlists')

    def __init__(self, name, owner_id):
        self.name = name
        self.owner_id = owner_id
        self.playlist_id = uuid.uuid4()

    def save(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def fetch_by_id(cls, playlist_id):
        """
        Fetch a playlist by id
        """
        return cls.query.filter_by(playlist_id=playlist_id).first()

    @classmethod
    def has_song(cls, song_id):
        """
        Checks and returns True if a song is in the playlist
        """
        songs = cls.query.filter(cls.songs.any(media_id=song_id)).all()

        if len(songs) < 1:
            return False
        else:
            return True

    @classmethod
    def fetch_playlists_by_user_id(cls, user_id):
        return cls.query.filter_by(owner_id=user_id).all()

    def save(self):
        """
        Save current playlist to the database.
        """
        db.session.add(self)
        db.session.commit()


class Album(db.Model):
    __tablename__ = 'albums'

    id = db.Column(db.Integer, primary_key=True)
    album_id = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(255), nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    modified = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    plays = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.Text, nullable=True)
    cover_image = db.Column(db.Text, nullable=True)
    archived = db.Column(db.Boolean, default=False)
    likes = db.Column(db.Integer, nullable=False, default=0)
    shares = db.Column(db.Integer, nullable=False, default=0)
    page_views = db.Column(db.Integer, nullable=False, default=0)
    publisher = db.Column(db.String, nullable=True)
    region = db.Column(db.String, nullable=True)
    country = db.Column(db.String, nullable=True)
    record_label = db.Column(db.String, nullable=True)
    release_date = db.Column(db.DateTime, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    songs = db.relationship('Media', back_populates='album')
    genres = db.relationship('Genre', secondary=genre_album_table, backref='albums')


    def __init__(self, name, owner_id, publisher=None, region=None, country=None, record_label=None, release_date=None, genres=None):
        self.name = name
        self.owner_id = owner_id
        self.album_id = uuid.uuid4()
        
        if region:
            self.region = region
        
        if country:
            self.country = country
        
        if record_label:
            self.record_label = record_label
        
        if publisher:
            self.publisher = publisher
        
        if release_date:
            self.release_date = release_date
        
        if genres:
            for genre in genres:
                self.genres.append(Genre.get_or_create(genre['name']))

    def __repr__(self):
        return self.name

    @classmethod
    def fetch_all(cls):
        """
        Fetch all albums that are not archived from the database
        """
        return cls.query.filter_by(archived=False).all()
    
    @classmethod
    def search(cls, query, limit=10):
        """
        Search media by query
        """
        return cls.query.filter((cls.name.ilike(f'%{query}%')) | (cls.description.ilike(f'%{query}%'))).limit(limit).all()

    def save(self):
        """
        Save the current album to the database.
        """
        db.session.add(self)
        db.session.commit()

    @classmethod
    def fetch_by_id(cls, album_id):
        """
        Fetch an album by it's id
        """
        return cls.query.filter_by(album_id=album_id).first()

    @classmethod
    def fetch_archived(cls):
        """
        Fetch all archived albums
        """
        return cls.query.filter_by(archived=True).all()

    def delete(self):
        """
        Delete current album
        """
        db.session.delete(self)
        db.session.commit()


class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.String(50), unique=True)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    value = db.Column(db.Text, nullable=False)
    posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    modified = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived = db.Column(db.Boolean, nullable=False, default=False)
    media = db.relationship('Media', backref='comments')
    user = db.relationship('User', backref='comments')

    def __init__(self, value, media_id, user_id):
        self.value = value
        self.media_id = media_id
        self.user_id = user_id
        self.comment_id = uuid.uuid4()

    @classmethod
    def fetch_all(cls):
        """
        Fetch all comments from the database
        """
        return cls.query.all()

    def save(self):
        """
        Save the current comment to the database
        """
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """
        Delete current comment from the database.
        """
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def fetch_by_id(cls, comment_id):
        """
        Fetch a comment by comment_id
        """
        return cls.query.filter_by(comment_id=comment_id).first()


class Genre(db.Model):
    __tablename__ = 'genres'

    id = db.Column(db.Integer, primary_key=True)
    genre_id = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String, nullable=False, unique=True)

    def __init__(self, name):
        self.genre_id = uuid.uuid4()
        self.name = name.lower()
    
    def save(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_or_create(cls, name):
        """
        Gets a genre or creates one if it does not exist.
        """
        genre = cls.query.filter_by(name=name.lower()).first()

        if not genre:
            genre = cls(name.lower())
            genre.save()
        
        return genre
