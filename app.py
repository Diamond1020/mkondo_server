from flask import jsonify
from flask_restful import Api
from marshmallow import ValidationError

from media.models import Media, Playlist, Album, Comment, Genre
from media.resources import (
    MediaListResource,
    MediaResource,
    MediaNewRealseResource,
    PlaylistListResource,
    PlaylistResource,
    AlbumListResource,
    AlbumResource,
    AlbumArchiveResource,
    AlbumArchiveListResource,
    MediaPresignedUrlResource,
    MediaPresignedPostResource,
    CommentListResource,
    CommentResource,
    MediaCommentListResource,
    UserCommentListResource,
    MediaLikResource,
    MediaRatingResource,
    AlbumSharesResource,
    MediaShareResource,
    MediaPageViewsResource,
    AlbumPageViewsResource,
    PlaylistPageViewsResource,
    PopularMediaRecommendationResource,
    SimilarMediaRecommendationResource,
    PlaylistSharesResource,
    UserPlaylistResource,
    SearchResource,
    StatusResource
)
from mkondo import create_app, jwt, db
from notifications.models import Notification
from notifications.resources import NotificationListResource, NotificationOpenedResource
from users.models import User, ResetToken, Follower
from users.resources import (
    UserListResource,
    UserResource,
    UserLoginResource,
    UserArchiveResource,
    ArtistListResource,
    ForgotPasswordResource,
    ResetPasswordResource,
    UserMediaHistoryResource,
    SearchArtistGenreResource,
    UserFavouriteResource, 
    AdminArtistsResource,
    UserFollowerResource,
    ArtistInsightsResource,
    AudioUsersInsightsResource,
    UserMediaResource,
    SimilarArtistsResource, UserSearchResource,
    VistorTokenResource
)


def init_app():
    """
    Register endpoints and other functions.
    """
    app = create_app()
    api = Api(app)

    api.add_resource(UserListResource, '/users')
    api.add_resource(VistorTokenResource, '/users/visitor-token')
    api.add_resource(UserFavouriteResource, '/users/<string:user_id>/favourites')
    api.add_resource(UserCommentListResource, '/users/<string:user_id>/comments')
    api.add_resource(ResetPasswordResource, '/users/password/reset')
    api.add_resource(ForgotPasswordResource, '/users/forgotpassword')
    api.add_resource(UserLoginResource, '/users/authenticate')
    api.add_resource(UserArchiveResource, '/users/<string:user_id>/archive')
    api.add_resource(UserResource, '/users/<string:user_id>')
    api.add_resource(UserMediaHistoryResource, '/users/<string:user_id>/history')
    api.add_resource(UserFollowerResource, '/users/<string:user_id>/followers')
    api.add_resource(UserPlaylistResource, '/users/<string:user_id>/playlists')
    api.add_resource(UserMediaResource, '/users/<string:user_id>/media')
    api.add_resource(MediaListResource, '/media')
    api.add_resource(MediaNewRealseResource, '/media/new-release')
    api.add_resource(MediaCommentListResource, '/media/<string:media_id>/comments')
    api.add_resource(MediaShareResource, '/media/<string:media_id>/shares')
    api.add_resource(MediaPresignedUrlResource, '/media/presigned-get-url')
    api.add_resource(MediaPresignedPostResource, '/media/presigned-post-url')
    api.add_resource(MediaResource, '/media/<string:media_id>')
    api.add_resource(MediaLikResource, '/media/<string:media_id>/like')
    api.add_resource(MediaRatingResource, '/media/<string:media_id>/rating')
    api.add_resource(MediaPageViewsResource, '/media/<string:media_id>/page-views')
    api.add_resource(PopularMediaRecommendationResource, '/media/recommended/<string:user_id>/popular')
    api.add_resource(SimilarMediaRecommendationResource, '/media/recommended/<string:user_id>/similar')
    api.add_resource(PlaylistListResource, '/playlists')
    api.add_resource(PlaylistResource, '/playlists/<string:playlist_id>')
    api.add_resource(PlaylistPageViewsResource, '/playlists/<string:playlist_id>/page-views')
    api.add_resource(PlaylistSharesResource, '/playlists/<string:playlist_id>/shares')
    api.add_resource(AlbumListResource, '/albums')
    api.add_resource(AlbumArchiveListResource, '/albums/archive')
    api.add_resource(AlbumResource, '/albums/<string:album_id>')
    api.add_resource(AlbumPageViewsResource, '/albums/<string:album_id>/page-views')
    api.add_resource(AlbumArchiveResource, '/albums/<string:album_id>/archive')
    api.add_resource(AlbumSharesResource, '/albums/<string:album_id>/shares')
    api.add_resource(ArtistListResource, '/artists')
    api.add_resource(AdminArtistsResource, '/admin/<string:admin_id>/artists')
    api.add_resource(SearchArtistGenreResource, '/artists/genre')
    api.add_resource(ArtistInsightsResource, '/artists/<string:artist_id>/insights')
    api.add_resource(SimilarArtistsResource, '/artists/<string:artist_id>/similar')
    api.add_resource(CommentListResource, '/comments')
    api.add_resource(CommentResource, '/comments/<string:comment_id>')
    api.add_resource(NotificationListResource, '/notifications')
    api.add_resource(NotificationOpenedResource, '/notifications/<string:notification_id>/opened')
    api.add_resource(AudioUsersInsightsResource, '/insights/audio/users')
    api.add_resource(SearchResource, '/search')
    api.add_resource(StatusResource, '/status')
    api.add_resource(UserSearchResource, '/search/users')

    @jwt.user_claims_loader
    def add_claims_to_access_token(user):
        return {'user_type': user.user_type}

    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return user.user_id

    @app.errorhandler(ValidationError)
    def handle_marshmallow_error(error):
        return jsonify(error.messages), 400

    @app.shell_context_processor
    def make_shell_context():
        return dict(
            db=db,
            User=User,
            Media=Media,
            Playlist=Playlist,
            Album=Album,
            Comment=Comment,
            Notification=Notification,
            Genre=Genre,
            ResetToken=ResetToken,
            Follower=Follower
        )

    return app
