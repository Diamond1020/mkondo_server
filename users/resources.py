import logging
import os
import uuid
from datetime import timedelta

from flask import render_template
from flask_cors import cross_origin
from flask_jwt_extended import create_access_token, decode_token
from flask_restful import Resource, reqparse, request
from marshmallow.fields import Boolean
from sqlalchemy.sql import or_

from media.models import Media, Genre
from media.schemas import MediaSchema
from mkondo import sendgrid, argon_2, pagination
from mkondo.security import authorized_users
from mkondo.tasks import send_mail
from .models import User, ResetToken, MediaUserHistory, Follower
from .schemas import UserSchema, ArtistSchema
from users.insights import ArtistInsights, UsersInsights

user_schema = UserSchema()
users_schema = UserSchema(many=True)
artist_schema = ArtistSchema()
artists_schema = ArtistSchema(many=True)
media_schema = MediaSchema()
media_list_schema = MediaSchema(many=True)

class UserListResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('full_name', type=str, required=True)
    parser.add_argument('email', type=str, required=True)
    parser.add_argument('phone_number', type=str, required=True)
    parser.add_argument('user_type', type=str, required=True, choices=('creator', 'user', 'admin'),
                        help='Missing required parameter in the JSON body, choices are creator or user')
    parser.add_argument('country', type=str, required=True)
    parser.add_argument('password', type=str, required=True)
    parser.add_argument('avatar_url', type=str, required=False, nullable=True)
    parser.add_argument('cover_url', type=str, required=False, nullable=True)
    parser.add_argument('about', type=str, required=False, nullable=True)
    parser.add_argument('admin_id', type=str, required=False, nullable=True)
    parser.add_argument('facebook_link', type=str, required=False, nullable=True)
    parser.add_argument('twitter_link', type=str, required=False, nullable=True)
    parser.add_argument('instagram_link', type=str, required=False, nullable=True)
    parser.add_argument('youtube_link', type=str, required=False, nullable=True)
    parser.add_argument('description', type=str, required=False, nullable=True)


    @staticmethod
    @cross_origin(origin='*', headers=['Content- Type', 'Authorization'])
    def post():
        json_data = UserListResource.parser.parse_args()

        if User.fetch_by_email(json_data['email']):
            return {
                       'success': False,
                       'message': f"A user with the email address '{json_data['email']}' already exists."
                   }, 400

        if User.fetch_by_phone_number(json_data['phone_number']):
            return {
                       'success': False,
                       'message': f"A user with the phone number '{json_data['phone_number']}' already exists."
                   }, 400
        
        json_data['locality'] = request.remote_addr

        user_data = user_schema.load(json_data)
        user = User(**user_data)

        try:
            user.save()
        except:
            return {
                       'success': False,
                       'message': 'Something went wrong while attempting to save the user data'
                   }, 500

        try:
            email_html = render_template('emails/welcome.html', full_name=user.full_name)
            email_from = os.environ.get('SENDGRID_DEFAULT_FROM')
            data = {}
            data['to'] = user.email.lower()
            data['subject'] = 'Welcome To Mkondo'
            data['html_content'] = email_html
            send_mail.apply_async(kwargs=data)
        except Exception as e:
            logging.error(e)
            print('Something went wrong while sending the welcome email.')

        access_token = create_access_token(user, fresh=True, expires_delta=timedelta(weeks=12.0))

        return {
                   'success': True,
                   'access_token': access_token,
                   'user': user_schema.dump(user)
               }, 200

    @staticmethod
    @authorized_users(['SA'])
    def get():
        user_type_arg = request.args.get('type')

        if user_type_arg:
            users = User.fetch_all_by_type(user_type_arg)
        else:
            users = User.fetch_all()

        if len(users) == 0:
            return {
                       'success': False,
                       'message': 'Users not found.'
                   }, 404

        return {
            'success': True,
            'users': pagination.paginate(User.query.filter_by(archived=False), users_schema, True)
        }


class UserResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('full_name', type=str, required=True)
    parser.add_argument('email', type=str, required=True)
    parser.add_argument('phone_number', type=str, required=True)
    parser.add_argument('user_type', type=str, required=True, choices=('creator', 'user', 'admin'),
                        help='Missing required parameter in the JSON body, choices are creator or user')
    parser.add_argument('password', type=str, required=False)
    parser.add_argument('avatar_url', type=str, required=False, nullable=True)
    parser.add_argument('cover_url', type=str, required=False, nullable=True)
    parser.add_argument('about', type=str, required=False, nullable=True)
    parser.add_argument('admin_id', type=str, required=False, nullable=True)
    parser.add_argument('facebook_link', type=str, required=False, nullable=True)
    parser.add_argument('twitter_link', type=str, required=False, nullable=True)
    parser.add_argument('instagram_link', type=str, required=False, nullable=True)
    parser.add_argument('youtube_link', type=str, required=False, nullable=True)
    parser.add_argument('description', type=str, required=False, nullable=True)
    parser.add_argument('genres', action='append', required=False, nullable=True)
    parser.add_argument('publish', type=bool, required=False)

    @staticmethod
    @authorized_users(['SA', 'A', 'U', 'C'])
    def get(user_id):
        user = User.fetch_by_id(user_id)

        if not user:
            return {
                       'success': False,
                       'message': 'User not found'
                   }, 404

        return {
            'success': True,
            'user': user_schema.dump(user)
        }

    @staticmethod
    @authorized_users(['SA'])
    def delete(user_id):
        user = User.fetch_by_id(user_id)

        if not user:
            return {
                       'success': False,
                       'message': 'User not found'
                   }, 404

        user.delete()

        return {
                   'success': True,
                   'message': 'User deleted successfully.'
               }, 204

    @staticmethod
    @authorized_users(['SA', 'A', 'C', 'U'])
    def put(user_id):
        json_data = UserResource.parser.parse_args()

        user = User.fetch_by_id(user_id)

        if not user:
            return {
                       'success': False,
                       'message': 'User not found'
                   }, 404

        user_with_similar_email = User.fetch_by_email(json_data['email'])

        if user_with_similar_email and user_with_similar_email.user_id != user.user_id:
            return {
                       'success': False,
                       'message': f"A user with the email adress '{json_data['email']}' already exists."
                   }, 400

        user_with_similar_phone_number = User.fetch_by_phone_number(json_data['phone_number'])

        if user_with_similar_phone_number and user_with_similar_phone_number.user_id != user.user_id:
            return {
                       'success': False,
                       'message': f"A user with the phone number '{json_data['phone_number']}' already exists."
                   }, 400

        user.full_name = json_data['full_name']
        user.email = json_data['email']
        user.phone_number = json_data['phone_number']
        user.user_type = json_data['user_type']
        user.avatar_url = json_data['avatar_url']
        user.cover_url = json_data['cover_url']
        user.about = json_data['about']
        user.description = json_data['description']

        if json_data['publish']:
            user.publish = json_data['publish']
        
        if json_data['password']:
            user.password = argon_2.generate_password_hash(json_data['password'])
        
        if json_data['youtube_link']:
            user.youtube_link = json_data['youtube_link']
        
        if json_data['twitter_link']:
            user.twitter_link = json_data['twitter_link']
        
        if json_data['instagram_link']:
            user.instagram_link = json_data['instagram_link']
        
        if json_data['facebook_link']:
            user.facebook_link = json_data['facebook_link']
        
        if json_data['genres']:
            genres = []

            for genre in json_data['genres']:
                g = Genre.get_or_create(genre)
                genres.append(g)
                user.genres = genres
        
        try:
            user.save()
        except:
            return {
                       'success': False,
                       'message': 'Something went wront while attempting to update user data.'
                   }, 500

        return {
                   'success': True,
                   'message': 'User updated successfully.'
               }, 200


class VistorTokenResource(Resource):
    @staticmethod
    def get():
        class Visitor:
            def __init__(self, user_id, user_type):
                self.user_id = user_id
                self.user_type = user_type
        
        v_id = uuid.uuid4()
        
        user = Visitor(v_id, 'visitor')

        token = create_access_token(user, expires_delta=timedelta(days=1))

        return {'token': token}, 200


class UserLoginResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('username', required=True)
    parser.add_argument('password', required=True)

    @staticmethod
    def post():
        json_data = UserLoginResource.parser.parse_args()

        user = User.fetch_by_username(json_data['username'])

        if not user:
            return {
                       'success': False,
                       'message': f"User with username '{json_data['username']}' not found."
                   }, 404

        if not argon_2.check_password_hash(user.password, json_data['password']):
            return {
                       'success': False,
                       'message': 'username and password do not match.'
                   }, 400

        access_token = create_access_token(user, fresh=True, expires_delta=timedelta(weeks=12.0))

        return {
                   'success': True,
                   'access_token': access_token,
                   'user': user_schema.dump(user)
               }, 200


class UserFavouriteResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('media_id', required=True, type=str)

    @staticmethod
    def post(user_id):
        json_data = UserFavouriteResource.parser.parse_args()
        user = User.fetch_by_id(user_id)

        if not user:
            return {
                       'success': False,
                       'message': 'User not found'
                   }, 404

        media = Media.fetch_by_id(json_data['media_id'])

        if not media:
            return {
                       'success': False,
                       'message': 'Media not found'
                   }, 404

        if media in user.favourites:
            pass
        else:
            user.favourites.append(media)

            try:
                user.save()
            except:
                return {
                           'success': False,
                           'message': 'There was an error updating user favourites'
                       }, 500

        return {
                   'success': True,
                   'message': 'Media added to user favourites'
               }, 200

    @staticmethod
    def delete(user_id):
        json_data = UserFavouriteResource.parser.parse_args()
        user = User.fetch_by_id(user_id)

        if not user:
            return {
                       'success': False,
                       'message': 'User not found'
                   }, 404

        media = Media.fetch_by_id(json_data['media_id'])

        if not media:
            return {
                       'success': False,
                       'message': 'Media not found'
                   }, 404

        if media not in user.favourites:
            pass
        else:
            user.favourites.remove(media)

            try:
                user.save()
            except:
                return {
                           'success': False,
                           'message': 'There was an error updating user favourites'
                       }, 500

        return {
                   'success': True,
                   'message': 'Media removed from user favourites'
               }, 204


class ForgotPasswordResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('email', type=str, required=True)

    @staticmethod
    def post():
        json_data = ForgotPasswordResource.parser.parse_args()

        user = User.fetch_by_email(json_data['email'])

        if not user:
            return {
                       'success': False,
                       'message': 'The email provided does not exist'
                   }, 400

        # Deactivate active tokens of this user if any and give them a new one.
        ResetToken.deactivate_reset_tokens(user.id)
        reset_token = create_access_token(user, expires_delta=timedelta(minutes=15.0))
        db_reset_token = ResetToken(reset_token, user.id)
        db_reset_token.save()

        forgot_password_html = render_template('emails/reset_password.html', full_name=user.full_name,
                                               url=request.host_url + "reset-password?token=" + reset_token)

        try:
            mail.send_mail(user.email.lower(), 'Reset Your Password', forgot_password_html)
        except Exception as e:
            logging.error(e)

        return {
                   'success': True
               }, 200


class ResetPasswordResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('reset_token', required=True, type=str)
    parser.add_argument('password', required=True, type=str)

    @staticmethod
    def post():
        json_data = ResetPasswordResource.parser.parse_args()

        # Check first if the token is still valid.
        if not ResetToken.token_is_valid(json_data['reset_token']):
            return {
                       'success': False,
                       'message': 'Token is not valid'
                   }, 400

        user_id = decode_token(json_data['reset_token'])['identity']

        user = User.fetch_by_id(user_id)
        user.password = argon_2.generate_password_hash(json_data['password'])

        try:
            user.save()
        except:
            return {
                       'success': False,
                       'message': 'Something went wrong while updating the password.'
                   }, 500

        try:
            sendgrid.send_email(user.email, 'Password Reset Successful',
                                html='<p>Your password was updated successfully</p>')
        except Exception as e:
            logging.error(e)

        access_token = create_access_token(user, fresh=True, expires_delta=timedelta(weeks=12.0))
        return {
                   'success': True,
                   'access_token': access_token,
                   'user': user_schema.dump(user)
               }, 200


class UserArchiveResource(Resource):
    @staticmethod
    @authorized_users(['SA'])
    def put(user_id):
        user = User.fetch_by_id(user_id)

        if not user:
            return {
                       'success': False,
                       'message': 'User not found'
                   }, 404

        current_archive_status = user.archived
        user.archived = not current_archive_status

        try:
            user.save()
        except:
            return {
                       'success': False,
                       'message': 'An error occured while updating archive status'
                   }, 500

        return {
                   'success': True,
                   'message': 'User archive state updated successfully'
               }, 200


class UserArchiveListResource(Resource):
    @staticmethod
    @authorized_users(['SA'])
    def get():
        users = User.fetch_archived()

        if len(users) == 0:
            return {
                       'success': False,
                       'message': 'No archived users found'
                   }, 404

        return {
                   'success': True,
                   'users': users_schema.dump(users)
               }, 200


class ArtistListResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('full_name', type=str, required=True)
    parser.add_argument('email', type=str, required=True)
    parser.add_argument('phone_number', type=str, required=True)
    parser.add_argument('user_type', type=str, required=False, default='creator')
    parser.add_argument('country', type=str, required=True)
    parser.add_argument('password', type=str, required=True)
    parser.add_argument('avatar_url', type=str, required=False, nullable=True)
    parser.add_argument('about', type=str, required=False, nullable=True)
    parser.add_argument('admin_id', type=str, required=False, nullable=True)
    parser.add_argument('facebook_link', type=str, required=False, nullable=True)
    parser.add_argument('twitter_link', type=str, required=False, nullable=True)
    parser.add_argument('instagram_link', type=str, required=False, nullable=True)
    parser.add_argument('youtube_link', type=str, required=False, nullable=True)
    parser.add_argument('description', type=str, required=False, nullable=True)

    @staticmethod
    @authorized_users(['SA'])
    def get():
        artists = User.fetch_artists()

        if len(artists) == 0:
            return {
                       'success': False,
                       'message': 'No artist found'
                   }, 404

        return {
                   'success': True,
                   'artists': artists_schema.dump(artists)
               }, 200

    @staticmethod
    @authorized_users(['SA', 'A'])
    def post():
        json_data = ArtistListResource.parser.parse_args()

        if User.fetch_by_email(json_data['email']):
            return {
                       'success': False,
                       'message': f"A user with the email adress '{json_data['email']}' already exists."
                   }, 400

        if User.fetch_by_phone_number(json_data['phone_number']):
            return {
                       'success': False,
                       'message': f"A user with the phone number '{json_data['phone_number']}' already exists."
                   }, 400

        json_data['locality'] = request.remote_addr
        user_data = artist_schema.load(json_data)
        user = User(**user_data)

        try:
            user.save()
        except:
            return {
                       'success': False,
                       'message': 'Something went wrong while attempting to save the user data'
                   }, 500
        
        reset_token = create_access_token(user, expires_delta=timedelta(minutes=15.0))
        db_reset_token = ResetToken(reset_token, user.id)
        db_reset_token.save()

        email_html = render_template('emails/artist_welcome.html', artist_name=user.full_name,
                                               url=request.host_url + "reset-password?token=" + reset_token)

        try:
            mail.send_email(to_email=user.email, subject='Welcome To Mkondo', html=email_html)
        except Exception as e:
            logging.error(e)

        return {
                   'success': True,
                   'user_id': user.user_id,
                   'message': 'Artist created successfully'
               }, 201


class UserMediaHistoryResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('media_id', required=True, type=str)

    @staticmethod
    def post(user_id):
        json_data = UserMediaHistoryResource.parser.parse_args()
        user = User.fetch_by_id(user_id)

        if not user:
            return {
                       'success': False,
                       'message': 'User not found'
                   }, 404

        media = Media.fetch_by_id(json_data['media_id'])

        if not media:
            return {
                       'success': False,
                       'message': 'Media not found'
                   }, 404

        media.plays = media.plays + 1

        if MediaUserHistory.exists(user.id, media.id):
            MediaUserHistory.increase_plays(user.id, media.id)
        else:
            user_history = MediaUserHistory(user.id, media.id)

            try:
                media.save()
                user_history.save()
            except:
                return {
                           'success': False,
                           'message': 'There was an error adding the media to history'
                       }, 500

        return {
                   'success': True,
                   'message': 'Media added to history'
               }, 200

    @staticmethod
    def get(user_id):
        user = User.fetch_by_id(user_id)

        if not user:
            return {
                       'success': False,
                       'message': 'User not found'
                   }, 404

        media_history = user.history

        if len(media_history) == 0:
            return {
                       'success': False,
                       'message': 'User has no media history'
                   }, 404

        media = [media_schema.dump(x.media) for x in media_history]

        return {
                   'success': True,
                   'media': media
               }, 200


class SearchArtistGenreResource(Resource):
    @staticmethod
    def get():
        genre_name_args = request.args.get('name')

        if genre_name_args:
            artists = []

            genre_name_args = genre_name_args.split(',')

            for genre in genre_name_args:
                artists.extend(User.fetch_artists_by_genre(genre))

            if len(artists) == 0:
                return {
                           'success': False,
                           'message': 'There are no artists in the specified genres genre'
                       }, 404
        else:
            artists = User.fetch_artists()

            if len(artists) == 0:
                return {
                           'success': False,
                           'message': 'There are no artists found'
                       }, 404

        return {
            'success': True,
            'artists': artists_schema.dump(artists)
        }


class AdminArtistsResource(Resource):
    @staticmethod
    def get(admin_id):
        admin = User.fetch_by_id(admin_id)

        if not admin:
            return {
                'success': False,
                'message': f"There is no user with user_id {admin_id}"
            }, 404

        if admin and admin.user_type != 'admin':
            return {
                'success': False,
                'message': f"'{admin_id}' is not an admin"
            }, 400

        artists = User.get_users_under_admin('creator', admin_id)

        if len(artists) == 0:
            return {
                'success': False,
                'message': 'There are no artists unser this admin'
            }, 404

        return {
            'success': True,
            'artists': artists_schema.dump(artists)
        }, 200


class UserFollowerResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('follower_id', type=str, required=True)

    @staticmethod
    def post(user_id):
        user = User.fetch_by_id(user_id)

        if not user:
            return {
                'success': False,
                'message': f"User with user_id '{user_id}' not found"
            }, 404

        json_data = UserFollowerResource.parser.parse_args()
        
        follower = User.fetch_by_id(json_data['follower_id'])

        if not follower:
            return {
                'success': False,
                'message': f"User with user_id '{user_id}' not found"
            }, 404
        
        follow = Follower.get_follow(user.id, follower.id)

        if follow:
            return {
                'success': False,
                'message': f"'{user_id}' is already following '{json_data['follower_id']}'"
            }
        
        follower = Follower(user.id, follower.id)

        try:
            follower.save()
        except:
            return {
                'success': False,
                'message': 'We could not save this follower'
            }, 500
        
        return {
            'success': True,
            'message': 'Follower added successfully'
        }, 201

    @staticmethod
    def delete(user_id):
        user = User.fetch_by_id(user_id)

        if not user:
            return {
                'success': False,
                'message': f"User with user_id '{user_id}' not found"
            }, 404

        json_data = UserFollowerResource.parser.parse_args()
        
        follower = User.fetch_by_id(json_data['follower_id'])

        if not follower:
            return {
                'success': False,
                'message': f"User with user_id '{user_id}' not found"
            }, 404
        
        follow = Follower.get_follow(user.id, follower.id)

        if not follow:
            return {
                'success': False,
                'message': 'The user you are trying to unfollow is not a follower'
            }, 400

        try:
            Follower.delete_follow(follow)
        except:
            return {
                'success': False,
                'message': 'We could not complete the unfollow process'
            }, 500
        
        return {
            'success': True
        }, 204


class ArtistInsightsResource(Resource):
    @staticmethod
    def get(artist_id):
        artist = User.fetch_artist_by_id(artist_id)

        if not artist:
            return {
                'success': False,
                'message': 'There is no artist with the provided id'
            }, 404

        return ArtistInsights.fetch_artist_data(artist.id)


class AudioUsersInsightsResource(Resource):
    @staticmethod
    def get():
        return UsersInsights.fetch_audio_insights()


class UserMediaResource(Resource):
    @staticmethod
    def get(user_id):
        user = User.fetch_by_id(user_id)

        if not user:
            return {
                'success': False,
                'message': 'User not found'
            }, 404

        query = Media.query.filter_by(owner_id=user.id, archived=False)

        if len(query.all()) == 0:
            return {
                'success': False,
                'message': 'User has no media'
            }, 404
        
        return {
            'success': True,
            'media': pagination.paginate(query, media_list_schema, True)
        }


class SimilarArtistsResource(Resource):
    @staticmethod
    def get(artist_id):
        artist = User.fetch_artist_by_id(artist_id)

        if not artist:
            return {
                'success': False,
                'message': 'Artist not found'
            }, 404
        
        artist_genres = artist.genres
        artists = User.query.filter_by(user_type='creator').filter(User.id != artist.id).filter()
        
        similar_artists = []

        for artist in artists:
            if len(similar_artists) == 10:
                break
            if len(artist.genres) == 0:
                continue
            if artist.genres == artist_genres:
                similar_artists.append(artist)
            elif len(artist_genres) < len(artist.genres):
                g = artist.genres
                genres = artist.genres[0:len(artist_genres)]
                if genres == artist_genres:
                    similar_artists.append(artist)
                elif lambda artist_genres, g: any(i in g for i in artist_genres)(artist_genres, g):
                    similar_artists.append(artist)
            elif len(artist.genres) < len(artist_genres):
                g = artist.genres
                genres = artist_genres[0:len(artist.genres)]
                if genres == artist.genres:
                    similar_artists.append(artist)
                elif lambda g, artist_genres: any(i in artist_genres for i in g)(g, artist_genres):
                    similar_artists.append(artist)

        if len(similar_artists) == 0:
            return {
                'success': False,
                'message': 'Similar artists not found.'
            }, 404
        
        return {
            'success': True,
            'artists': artists_schema.dump(similar_artists)
        }, 200


class UserSearchResource(Resource):
    parser = reqparse.RequestParser(trim=True)
    parser.add_argument('query', type=str, required=False, location='args')
    parser.add_argument('user_type', type=str, required=False, location='args')

    @staticmethod
    def get():
        args = UserSearchResource.parser.parse_args()

        if not args['query']:
            users = User.query.limit(15).all()
        else:
            users = User.search(args['query'], limit=15, user_type=args['user_type'])

        if len(users) == 0:
            return {'success': False, 'message': 'no users found.'}, 404
        
        return {'success': True, 'users': users_schema.dump(users)}, 200
