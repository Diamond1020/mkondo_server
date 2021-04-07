from media.schemas import MediaSchema, GenreSchema
from mkondo import marshmallow
from .models import User, MediaUserHistory, Follower
from marshmallow import fields


class HistorySchema(marshmallow.SQLAlchemySchema):
    media_id = fields.String(attribute='media.media_id')

    class Meta:
        model = MediaUserHistory
        fields = ('plays', 'media_id')

class UserSchema(marshmallow.SQLAlchemySchema):
    favourites = marshmallow.Nested(MediaSchema(dump_only=('media_id',), many=True))
    # history = marshmallow.Nested(HistorySchema(dump_only=('plays',), many=True))
    genres = fields.Pluck(GenreSchema, 'name', many=True)
    instagram_link = fields.String(required=False, allow_none=True)
    facebook_link = fields.String(required=False, allow_none=True)
    twitter_link = fields.String(required=False, allow_none=True)
    youtube_link = fields.String(required=False, allow_none=True)
    admin_id = fields.String(required=False, allow_none=True)
    description = fields.String(required=False, allow_none=True)
    about = fields.String(required=False, allow_none=True)
    avatar_url = fields.String(required=False, allow_none=True)
    cover_url = fields.String(required=False, allow_none=True)
    followers = fields.Pluck('self', 'user_id', many=True)
    following = fields.Pluck('self', 'user_id', many=True)

    class Meta:
        model = User
        fields = (
            'user_id', 'full_name', 'email', 'phone_number', 'password', 'user_type', 'joined', 'last_active', 'about',
            'avatar_url', 'country', 'locality', 'archived', 'favourites', 'publish', 'youtube_link',
            'instagram_link', 'facebook_link', 'twitter_link', 'admin_id', 'followers', 'following', 'description', 'genres', 'cover_url')
        dump_only = ('publish', 'favourites', 'followers', 'following',)
        load_only = ('password',)


class ArtistSchema(marshmallow.SQLAlchemySchema):
    genres = fields.Pluck(GenreSchema, 'name', many=True)
    instagram_url = fields.String(allow_none=True)
    facebook_url = fields.String(allow_none=True)
    twitter_url = fields.String(allow_none=True)
    youtube_url = fields.String(allow_none=True)
    admin_id = fields.String(allow_none=True)
    description = fields.String(allow_none=True)
    

    class Meta:
        model = User
        fields = (
            'user_id', 'full_name', 'email', 'phone_number', 'password', 'user_type', 'joined', 'last_active', 'about',
            'avatar_url', 'country', 'locality', 'archived', 'facebook_link', 'twitter_link', 'instagram_link',
            'youtube_link', 'genres', 'publish', 'description', 'admin_id')
        dump_only = ('publish',)
        load_only = ('password',)
