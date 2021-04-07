from mkondo import marshmallow
from .models import Media, Playlist, Album, Comment, Genre
from marshmallow import fields

class MediaSchema(marshmallow.SQLAlchemySchema):
    composer = fields.String(allow_none=True)
    cover_url = fields.String(allow_none=True)
    release_date = fields.String(allow_none=True)
    record_label = fields.String(allow_none=True)
    song_writer = fields.String(allow_none=True)
    movie_director = fields.String(allow_none=True)
    staring = fields.String(allow_none=True)
    starting_date = fields.String(allow_none=True)
    production_company = fields.String(allow_none=True)
    owner_avatar_url = fields.String(allow_none=True)
    album_id = fields.String(attribute='album.album_id', allow_none=True)
    owner_id = fields.String(attribute='owner.user_id')
    owner_name = fields.String(attribute='owner.full_name')
    genres = fields.Pluck('GenreSchema', 'name', many=True)

    class Meta:
        model = Media
        fields = (
            'media_id', 'name', 'description', 'cover_url', 'duration', 'category', 'added', 'edited', 'plays',
            'owner_id',
            'archived', 'likes', 'media_url', 'page_views', 'shares', 'composer', 'release_date', 'song_writer',
            'record_label', 'owner_avatar_url', 'album_id', 'owner_name', 'genres', 'production_company', 'movie_director', 'staring', 'starting_date')
        dump_only = ('owner_name',)


class PlaylistSchema(marshmallow.SQLAlchemySchema):
    songs = marshmallow.Nested(MediaSchema, many=True)
    owner_user_id = fields.String(attribute='owner.user_id')

    class Meta:
        model = Playlist
        fields = ('name', 'owner_id', 'duration', 'created', 'modified', 'songs', 'page_views', 'shares', 'likes', 'playlist_id', 'owner_user_id')
        load_only = ('owner_id',)
        dump_only = ('songs', 'owner_user_id')


class AlbumSchema(marshmallow.SQLAlchemySchema):
    songs = marshmallow.Nested(MediaSchema, many=True)
    release_date = fields.String(allow_none=True)
    record_label = fields.String(allow_none=True)
    publisher = fields.String(allow_none=True)
    country = fields.String(allow_none=True)
    region = fields.String(allow_none=True)
    genres = fields.Pluck('GenreSchema', 'name', many=True)

    class Meta:
        model = Album
        fields = (
            'name', 'description', 'songs', 'plays', 'genres', 'cover_image', 'modified', 'archived', 'created',
            'owner_id',
            'album_id', 'page_views', 'shares', 'likes', 'publisher', 'release_date', 'region', 'country', 'record_label')
        dump_only = ('songs',)
        load_only = ('owner_id',)
        include_fk = True


class CommentSchema(marshmallow.SQLAlchemyAutoSchema):
    commenter_name = fields.String(attribute='user.full_name')
    avatar_user_url = fields.String(attribute='user.avatar_url')
    media_id = fields.String(attribute='media.media_id')
    user_id = fields.String(attribute='user.user_id')

    class Meta:
        model = Comment
        fields = ('value', 'user_id', 'media_id', 'posted', 'modified', 'commenter_name', 'avatar_user_url')
        dump_only = ('commenter_name', 'avatar_user_url')


class GenreSchema(marshmallow.SQLAlchemySchema):
    class Meta:
        model = Genre
        fields = ('name', 'genre_id')
        dump_only = ('genre_id',)
