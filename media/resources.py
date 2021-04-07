import os
import uuid

import logging
import dotenv
from flask import request
from flask_restful import Resource, reqparse
from sqlalchemy import exc
from botocore.exceptions import ClientError
from werkzeug.datastructures import FileStorage

import vimeo
from mkondo.s3 import client
from .schemas import MediaSchema, PlaylistSchema, AlbumSchema, CommentSchema
from .models import Media, Playlist, Album, Comment
from users.models import User, MediaUserHistory
from users.schemas import UserSchema
from mkondo.security import authorized_users
from .recommender import PopularityRecommender, SimilarityRecommender
from mkondo.tasks import send_mail

dotenv.load_dotenv()

media_schema = MediaSchema()
media_list_schema = MediaSchema(many=True)
playlist_schema = PlaylistSchema()
playlists_schema = PlaylistSchema(many=True)
album_schema = AlbumSchema()
albums_schema = AlbumSchema(many=True)
comment_schema = CommentSchema()
comments_schema = CommentSchema(many=True)
users_schema = UserSchema(many=True)

UPLOADS_FOLDER = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'uploads')
# logging.basicConfig(filename='myapp.log', level=logging.DEBUG)

class MediaListResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('name', type=str, required=True, location=['form', 'json'])
    parser.add_argument('description', type=str, required=True, location=['form', 'json'])
    parser.add_argument('cover_url', type=str, required=True, location=['form', 'json'])
    parser.add_argument('duration', type=int, required=True, location=['form', 'json'])
    parser.add_argument('category', type=str, required=True, choices=('audio', 'video', 'movie'), location=['form', 'json'])
    parser.add_argument('album_id', type=str, required=False, location=['form', 'json'])
    parser.add_argument('cover_url', type=str, required=True, location=['form', 'json'])
    parser.add_argument('duration', type=int, required=True, location=['form', 'json'])
    parser.add_argument('media_url', type=str, required=True, location=['form', 'json'])
    parser.add_argument('release_date', type=str, required=False, location=['form', 'json'])
    parser.add_argument('composer', type=str, required=False, location=['form', 'json'])
    parser.add_argument('record_label', type=str, required=False, location=['form', 'json'])
    parser.add_argument('song_writer', type=str, required=False, location=['form', 'json'])
    parser.add_argument('owner_avatar_url', type=str, required=False, location=['form', 'json'])
    parser.add_argument('movie_director', type=str, required=False, location=['form', 'json'])
    parser.add_argument('staring', type=str, required=False, location=['form', 'json'])
    parser.add_argument('production_company', type=str, required=False, location=['form', 'json'])
    parser.add_argument('genres', action='append', required=False, nullable=True, location=['form', 'json'])
    parser.add_argument('owner_id', type=str, required=True, location=['form', 'json'])
    parser.add_argument('starting_date', type=str, required=False, location=['form', 'json'])
    parser.add_argument('file', type=FileStorage, required=False, location=['files', 'form'])
    @staticmethod
    @authorized_users(['SA'])
    def get():
        media = Media.fetch_all()

        return {
                   'success': True,
                   'media': media_list_schema.dump(media)
               }, 200

    @staticmethod
    @authorized_users(['SA', 'A', 'C'])
    def post():
        json_data = MediaListResource.parser.parse_args()

        owner = User.fetch_by_id(json_data['owner_id'])
        logging.info(json_data['owner_id'])

        if not owner:
            return {'success':False, 'message': 'Owner not found'}, 404

        if json_data['category'] == 'video' or json_data['category'] == 'movie':
            if not os.path.exists(UPLOADS_FOLDER):
                os.mkdir(UPLOADS_FOLDER)
            logging.info("Loging dict ---> {0}".format(json_data['file'].filename))
            
            video_file = os.path.join(UPLOADS_FOLDER, json_data['file'].filename)
            json_data['file'].save(video_file)

            try:
                client = vimeo.VimeoClient(
                    token=os.environ.get('VIMEO_TOKEN'),
                    key=os.environ.get('VIMEO_KEY'),
                    secret=os.environ.get('VIMEO_SECRET')
                )

                uri = client.upload(video_file, data={
                    'name': json_data['name'],
                    'description': json_data['description']
                })
                json_data['media_url'] = 'https://vimeo.com/' + str(uri).split('/')[-1]
            except Exception as e:
                logging.error(e)
                return {'success': False, 'message': 'Video upload failed.'}, 500
            finally:
                if os.path.exists(video_file):
                    os.remove(video_file)

        if 'file' in json_data:
            del json_data['file']

        album = None
        # extension = os.path.splitext(json_data['file'].filename)[1]

        json_data['owner_id'] = str(owner.id)
        media_data = media_schema.load(json_data)

        if json_data['album_id']:
            album = Album.fetch_by_id(json_data['album_id'])
            media_data['album_id'] = album.id

            if not album:
                return {
                    'success': False,
                    'message': 'Album not found'
                }, 404


        media_data['owner_id'] = int(media_data['owner']['user_id'])
        del media_data['owner']
        del media_data['album']
        media = Media(**media_data)

        try:
            media.save()
        except exc.SQLAlchemyError as e:
            logging.error(e)
            return {
                       'success': False,
                       'message': 'We encountered an error while attempting to save the media.'
                   }, 500
        """
        try:
            data = {}
            data['subject'] = f'{owner.full_name} just uploaded {media.name}'
            data['html_content'] = f'<h1>{media.name}</h1>'
            for follower in owner.followers:
                data['to'] = follower.email
                send_mail.apply_async(kwargs=data)
        except Exception as e:
            logging.error(e)
        """
        return {
            'success': True,
            'media_id': media.media_id,
            'message': 'Media added successfully.'
        }, 201

class MediaResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('name', type=str, required=True)
    parser.add_argument('description', type=str, required=True)
    parser.add_argument('cover_url', type=str, required=True)
    parser.add_argument('duration', type=int, required=True)
    parser.add_argument('category', type=str, required=True, choices=('audio', 'video'),
                        help=('Missing required parameter in the JSON body, choices are audio or video'))
    parser.add_argument('owner_id', type=str, required=True)
    parser.add_argument('owner_avatar_url', type=str, required=False)
    parser.add_argument('album_id', type=str, required=False)

    @staticmethod
    @authorized_users(['SA', 'A', 'C', 'U', 'V'])
    def get(media_id):
        media = Media.fetch_by_id(media_id)

        if not media:
            return {
                       'success': False,
                       'message': 'Media not found.'
                   }, 404

        return {
                   'success': True,
                   'media': media_schema.dump(media)
               }, 200

    @staticmethod
    @authorized_users(['SA', 'A', 'C'])
    def delete(media_id):
        media = Media.fetch_by_id(media_id)

        if not media:
            return {
                       'success': False,
                       'message': 'Media not found.'
                   }, 404

        media.delete()

        return {
                   'success': True,
                   'message': 'Media deleted successfully'
               }, 204

    @staticmethod
    @authorized_users(['SA', 'A', 'C'])
    def put(media_id):
        json_data = MediaResource.parser.parse_args()

        media = Media.fetch_by_id(media_id)

        if not media:
            return {
                       'success': False,
                       'message': 'Media not found.'
                   }, 404

        media.name = json_data['name']
        media.description = json_data['description']
        media.cover_url = json_data['cover_url']
        media.duration = json_data['duration']
        media.category = json_data['category']
        media.owner_avatar_url = json_data['owner_avatar_url']

        if json_data['album_id']:
            album = Album.fetch_by_id(json_data['album_id'])

            if not album:
                return {
                    'success': False,
                    'message': 'Album does not exist'
                }
            
            media.album_id = album.id

        try:
            media.save()
        except:
            return {
                       'success': False,
                       'message': 'Something went wrong while update media data.'
                   }, 500

        return {
                   'success': True,
                   'message': 'Media updated successfully'
               }, 200


class PopularMediaRecommendationResource(Resource):
    @staticmethod
    def get(user_id):
        train_data = MediaUserHistory.get_train_data()
        popularity_recommender = PopularityRecommender()
        popularity_recommender.create(train_data, 'user_id', 'media_id_y')
        recommendations = popularity_recommender.recommend(user_id)
        media = Media.fetch_by_ids(list(recommendations['media_id_y']))

        if len(media) == 0:
            return {
                'success': False,
                'message': 'There is no media to recommend'
            }, 404
        
        return {
            'success': True,
            'media': media_list_schema.dump(media)
        }, 200

class SimilarMediaRecommendationResource(Resource):
    @staticmethod
    def get(user_id):
        train_data = MediaUserHistory.get_train_data()
        is_model = SimilarityRecommender()
        is_model.create(train_data, 'user_id', 'media_id_y')
        user_media = is_model.get_user_media(user_id)

        if len(user_media) == 0:
            return {
                'success': False,
                'message': 'The current user has no songs for training the item similarity based recommendation model.'
            }, 404

        recommended = is_model.recommend(user_id)
        media = Media.fetch_by_ids(list(recommended['media_id_y']))

        return {
            'success': True,
            'media': media_list_schema.dump(media)
        }, 200

class MediaNewRealseResource(Resource):
    @staticmethod
    @authorized_users(['SA', 'A', 'C', 'U', 'V'])
    def get():
        category = request.args.get('category', 'audio')
        amount = request.args.get('amount', 10)
        media = Media.fetch_latest_release(amount=amount, category=category)

        return {
                   'success': True,
                   'media': media_list_schema.dump(media)
               }, 200


class PlaylistListResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('name', type=str, required=True)
    parser.add_argument('owner_id', type=str, required=True)

    @staticmethod
    @authorized_users(['SA', 'A', 'C', 'U'])
    def post():
        json_data = PlaylistListResource.parser.parse_args()

        owner = User.fetch_by_id(json_data['owner_id'])

        if not owner:
            return {
                       'success': False,
                       'message': f"Owner with id '{json_data['owner_id']}' was not found."
                   }, 404

        json_data['owner_id'] = owner.id

        playlist_data = playlist_schema.load(json_data)
        playlist = Playlist(**playlist_data)

        try:
            playlist.save()
        except:
            return {
                       'success': False,
                       'message': 'Something went wrong while creating the playlist'
                   }, 500

        return {
                   'success': True,
                   'message': 'Playlist created successfully',
                   'playlist_id': playlist.playlist_id
               }, 201


class PlaylistResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('owner_id', type=str, required=True)
    parser.add_argument('song_id', type=str, required=True)

    @staticmethod
    @authorized_users(['SA', 'A', 'C', 'U'])
    def put(playlist_id):
        json_data = PlaylistResource.parser.parse_args()

        playlist = Playlist.fetch_by_id(playlist_id)

        user = User.fetch_by_id(json_data['owner_id'])

        if not user:
            return {
                'success': False,
                'message': 'Owner not found'
            }, 404
        
        if user.id != playlist.owner_id:
            return {
                'success': False,
                'message': 'You are not the owner of this playlist'
            }, 403

        if not playlist:
            return {
                       'success': False,
                       'message': 'playlist not found'
                   }, 404

        song = Media.fetch_by_id(json_data['song_id'])

        if not song:
            return {
                       'success': False,
                       'message': 'Song does not exist'
                   }, 404

        if song in playlist.songs:
            playlist.songs.remove(song)
            playlist.duration = playlist.duration - song.duration
        else:
            playlist.songs.append(song)
            playlist.duration = playlist.duration + song.duration

        try:
            playlist.save()
        except:
            return {
                       'success': False,
                       'message': 'Something went wrong while updatating the playlist'
                   }, 500

        return {
                   'success': True,
                   'messages': 'Playlist updated successfully.'
               }, 200

    @staticmethod
    # @authorized_users(['SA', 'A', 'C', 'U'])
    def get(playlist_id):
        playlist = Playlist.fetch_by_id(playlist_id)

        if not playlist:
            return {
                       'success': False,
                       'message': 'playlist not found'
                   }, 404

        return {
                   'success': True,
                   'playlist': playlist_schema.dump(playlist)
               }, 200


class PlaylistSharesResource(Resource):
    @staticmethod
    def post(playlist_id):
        playlist = Playlist.fetch_by_id(playlist_id)

        if not playlist:
            return {
                       'success': False,
                       'message': 'playlist not found'
                   }, 404

        playlist.shares = playlist.shares + 1

        try:
            playlist.save()
        except:
            return {
                       'success': False,
                       'message': 'Something went wrong while updatating the playlist shares'
                   }, 500

        return {
            'success': True,
            'message': 'playlist shares updated'
        }


class UserPlaylistResource(Resource):
    @staticmethod
    def get(user_id):
        user = User.fetch_by_id(user_id)

        if not user:
            return {
                       'success': False,
                       'message': 'User not found'
                   }, 404

        playlists = Playlist.fetch_playlists_by_user_id(user.id)

        if len(playlists) == 0:
            return {
                'success': False,
                'message': 'User has no playlists'
            }, 404
        
        return {
            'success': True,
            'playlists': playlists_schema.dump(playlists)
        }, 200


class AlbumListResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('name', required=True, type=str)
    parser.add_argument('owner_id', required=True, type=str)
    parser.add_argument('region', required=False, type=str)
    parser.add_argument('country', required=False, type=str)
    parser.add_argument('publisher', required=False, type=str)
    parser.add_argument('release_date', type=str, required=False)
    parser.add_argument('record_label', type=str, required=False)
    parser.add_argument('genres', action='append', required=False, nullable=True)

    @staticmethod
    @authorized_users(['SA'])
    def get():
        albums = Album.fetch_all()

        if len(albums) == 0:
            return {
                       'success': False,
                       'message': 'No albums found'
                   }, 404

        return {
            'success': True,
            'albums': albums_schema.dump(albums)
        }

    @staticmethod
    @authorized_users(['SA', 'A', 'C'])
    def post():
        json_data = AlbumListResource.parser.parse_args()

        owner = User.fetch_by_id(json_data['owner_id'])

        if not owner:
            return {
                       'success': False,
                       'message': 'owner not found'
                   }, 404

        json_data['owner_id'] = owner.id
        album_data = album_schema.load(json_data)
        album = Album(**album_data)

        try:
            album.save()
        except:
            return {
                       'success': False,
                       'message': 'An error occured while attempting to create the album'
                   }, 500

        return {
                   'success': True,
                   'message': 'Album created successfully',
                   'album_id': album.album_id
               }, 201


class AlbumResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('name', required=True, type=str)
    parser.add_argument('description', required=True, type=str)
    parser.add_argument('cover_image', required=True, type=str)
    parser.add_argument('genre', required=True, type=str)
    parser.add_argument('region', required=False, type=str)
    parser.add_argument('country', required=False, type=str)
    parser.add_argument('publisher', required=False, type=str)
    parser.add_argument('release_date', type=str, required=False)
    parser.add_argument('record_label', type=str, required=False)

    @staticmethod
    @authorized_users(['SA', 'A', 'C', 'U'])
    def get(album_id):
        album = Album.fetch_by_id(album_id)

        if not album:
            return {
                       'success': False,
                       'message': 'Album not found'
                   }, 404

        return {
            'success': True,
            'album': album_schema.dump(album)
        }

    @staticmethod
    @authorized_users(['SA'])
    def delete(album_id):
        album = Album.fetch_by_id(album_id)

        if not album:
            return {
                       'success': False,
                       'message': 'Album not found'
                   }, 404

        album.delete()

        return {
                   'success': True,
                   'message': 'Album deleted'
               }, 204

    @staticmethod
    @authorized_users(['SA', 'A', 'C'])
    def put(album_id):
        json_data = AlbumResource.parser.parse_args()

        album = Album.fetch_by_id(album_id)

        if not album:
            return {
                       'success': False,
                       'message': 'Album not found'
                   }, 404

        album.name = json_data['name']
        album.cover_image = json_data['cover_image']
        album.description = json_data['description']
        album.genre = json_data['genre']
        album.publisher = json_data['publisher']
        album.region = json_data['region']
        album.country = json_data['country']
        album.release_date = json_data['release_date']
        album.record_label = json_data['record_label']

        try:
            album.save()
        except:
            return {
                       'success': False,
                       'message': 'There was an error updating album details'
                   }, 500

        return {
                   'success': True,
                   'message': 'Album updated successfully'
               }, 200


class AlbumArchiveListResource(Resource):
    @staticmethod
    @authorized_users(['SA'])
    def get():
        albums = Album.fetch_archived()

        if len(albums) == 0:
            return {
                       'success': False,
                       'message': 'Archived albums not found'
                   }, 404

        return {
                   'success': True,
                   'albums': albums_schema.dump(albums)
               }, 200


class AlbumArchiveResource(Resource):
    @staticmethod
    @authorized_users(['SA'])
    def put(album_id):
        album = Album.fetch_by_id(album_id)

        if not album:
            return {
                       'success': False,
                       'message': 'Album not found'
                   }, 404

        current_archive_status = album.archived
        album.archived = not current_archive_status

        try:
            album.save()
        except:
            return {
                       'success': False,
                       'message': 'There was an error updating the arhive status of this album'
                   }, 500

        return {
                   'success': True,
                   'message': 'Album archive state updated successfully'
               }, 200


class MediaPresignedUrlResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('file_name', required=True)

    @staticmethod
    @authorized_users(['SA', 'A', 'C', 'U', 'V'])
    def get():
        json_data = MediaPresignedUrlResource.parser.parse_args()

        try:
            response = client.generate_presigned_url(ClientMethod='get_object',
                                                     Params={'Bucket': 'mkondo.co', 'Key': json_data['file_name']},
                                                     ExpiresIn=300)
        except:
            return {
                       'success': False,
                       'message': 'Something went wrong'
                   }, 500

        return {
                   'success': True,
                   'response': response
               }, 200


class MediaPresignedPostResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('file_name', required=True)

    @staticmethod
    @authorized_users(['SA', 'A', 'C', 'U', 'V'])
    def get():
        json_data = MediaPresignedPostResource.parser.parse_args()

        try:
            response = client.generate_presigned_post('mkondo.co', json_data['file_name'], ExpiresIn=300)
        except ClientError as e:
            return {
                       'success': False,
                       'messsage': 'Something went wrong'
                   }, 500

        return {
                   'success': True,
                   'response': response
               }, 200


class CommentListResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('media_id', required=True, type=str)
    parser.add_argument('user_id', required=True, type=str)
    parser.add_argument('value', required=True, type=str)

    @staticmethod
    # @authorized_users(['SA'])
    def get():
        comments = Comment.fetch_all()

        if len(comments) == 0:
            return {
                       'success': False,
                       'message': 'No comment found'
                   }, 404

        return {
                   'success': True,
                   'comments': comments_schema.dump(comments)
               }, 200

    @staticmethod
    @authorized_users(['SA', 'A', 'C', 'U'])
    def post():
        json_data = CommentListResource.parser.parse_args()


        media = Media.fetch_by_id(json_data['media_id'])

        if not media:
            return {
                       'success': False,
                       'message': 'Media not found'
                   }, 404

        user = User.fetch_by_id(json_data['user_id'])

        if not user:
            return {
                       'success': False,
                       'message': 'User not found'
                   }, 404

        comment_data = comment_schema.load(json_data)
        comment_data['user_id'] = user.id
        comment_data['media_id'] = media.id
        del comment_data['media']
        del comment_data['user']
        comment = Comment(**comment_data)
        
        try:
            comment.save()
        except Exception as e:
            logging.error(e)
            return {
                       'success': False,
                       'message': 'We encountered an error while attempting to save the comment'
                   }, 500

        return {
                   'success': True,
                   'message': 'Comment added successfully'
               }, 201


class CommentResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('value', required=True, type=str)

    @staticmethod
    @authorized_users(['SA', 'A', 'C', 'U'])
    def get(comment_id):
        comment = Comment.fetch_by_id()

        if not comment:
            return {
                       'success': False,
                       'message': 'Comment not found'
                   }, 404

        return {
                   'success': True,
                   'comment': comment_schema.dump(comment)
               }, 200

    @staticmethod
    @authorized_users(['SA', 'A', 'C', 'U'])
    def put(comment_id):
        json_data = CommentResource.parser.parse_args()

        comment = Comment.fetch_by_id(comment_id)

        if not comment:
            return {
                       'success': False,
                       'message': 'Comment not found'
                   }, 404

        comment.value = json_data['value']

        try:
            comment.save()
        except:
            return {
                       'success': False,
                       'message': 'Error encountered while attempting to update the comment'
                   }, 500

        return {
                   'success': True,
                   'message': 'Comment updated successfully'
               }, 200

    @staticmethod
    @authorized_users(['SA'])
    def delete(comment_id):
        comment = Comment.fetch_by_id(comment_id)

        if not comment:
            return {
                       'success': False,
                       'message': 'Comment not found'
                   }, 404

        try:
            comment.delete()
        except:
            return {
                       'success': False,
                       'message': 'There was an error deleting the comment'
                   }, 500

        return {
                   'success': True,
                   'message': 'Comment delteted successfully'
               }, 204


class MediaCommentListResource(Resource):
    @staticmethod
    @authorized_users(['SA', 'A', 'C', 'U'])
    def get(media_id):
        media = Media.fetch_by_id(media_id)

        if not media:
            return {
                'success': False,
                'message': 'Media not found'
            }

        comments = media.comments

        if len(comments) == 0:
            return {
                       'success': False,
                       'message': 'No comments for this media was found'
                   }, 404

        return {
                   'success': True,
                   'comments': comments_schema.dump(comments)
               }, 200


class UserCommentListResource(Resource):
    @staticmethod
    @authorized_users(['SA'])
    def get(user_id):
        user = User.fetch_by_id(user_id)

        if not user:
            return {
                       'success': False,
                       'message': 'User not found'
                   }, 404

        comments = user.comments

        if len(comments) == 0:
            return {
                       'success': False,
                       'message': 'No comment for this user was found'
                   }, 404

        return {
                   'success': True,
                   'comments': comments_schema.dump(comments)
               }, 200


class MediaLikResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('media_id', type=str, required=True)

    @staticmethod
    @authorized_users(['SA', 'A', 'C', 'U'])
    def post(media_id):
        media = Media.fetch_by_id(media_id)

        if not media:
            return {
                       'success': False,
                       'message': 'media not found'
                   }, 404

        media.likes = media.likes + 1

        try:
            media.save()
        except:
            return {
                       'success': False,
                       'message': 'Likes could not be updated'
                   }, 500

        return {
                   'success': True,
                   'message': 'Media likes updated'
               }, 200


class MediaRatingResource(Resource):
    parser = reqparse.RequestParser(trim=True, bundle_errors=True)
    parser.add_argument('plays', type=int, required=True)

    @staticmethod
    def post(media_id):
        json_data = MediaRatingResource.parser.parse_args()
        
        media = Media.fetch_by_id(media_id)

        if not media:
            return {
                       'success': False,
                       'message': 'media not found'
                   }, 404

        media.plays = media.plays + json_data['plays']

        try:
            media.save()
        except:
            return {
                       'success': False,
                       'message': 'Plays could not be updated'
                   }, 500

        return {
                   'success': True,
                   'message': 'Plays updated success fully'
               }, 201


class AlbumSharesResource(Resource):
    @staticmethod
    def post(album_id):
        album = Album.fetch_by_id(album_id)

        if not album:
            return {
                       'success': False,
                       'message': 'Album not found'
                   }, 404

        album.shares = album.shares + 1

        try:
            album.save()
        except:
            return {
                       'success': True,
                       'message': 'There was an issue updating the album shares'
                   }, 500

        return {
                   'success': True,
                   'message': 'Album shares updated successfully'
               }, 201


class MediaShareResource(Resource):
    @staticmethod
    def post(media_id):
        media = Media.fetch_by_id(media_id)

        if not media:
            return {
                       'success': False,
                       'message': 'Media not found'
                   }, 404

        media.shares = media.shares + 1

        try:
            media.save()
        except:
            return {
                       'success': False,
                       'message': 'There was an error updating the number of shares'
                   }, 500

        return {
                   'success': True,
                   'message': 'Media shares updated successfully'
               }, 201


class MediaPageViewsResource(Resource):
    @staticmethod
    def post(media_id):
        media = Media.fetch_by_id(media_id)

        if not media:
            return {
                       'success': False,
                       'message': 'Media not found'
                   }, 404

        media.page_views = media.page_views + 1

        try:
            media.save()
        except:
            return {
                       'success': False,
                       'message': 'There was an error updating the number of page views'
                   }, 500

        return {
                   'success': True,
                   'message': 'Media page views updated successfully'
               }, 201


class AlbumPageViewsResource(Resource):
    @staticmethod
    def post(album_id):
        album = Album.fetch_by_id(album_id)

        if not album:
            return {
                       'success': False,
                       'message': 'Album not found'
                   }, 404

        album.page_views = album.page_views + 1

        try:
            album.save()
        except:
            return {
                       'success': True,
                       'message': 'There was an issue updating the album page views'
                   }, 500

        return {
                   'success': True,
                   'message': 'Album page views updated successfully'
               }, 201


class PlaylistPageViewsResource(Resource):
    @staticmethod
    def post(playlist_id):
        playlist = Playlist.fetch_by_id(playlist_id)

        if not playlist:
            return {
                       'success': False,
                       'message': 'playlist not found'
                   }, 404

        playlist.page_views = playlist.page_views + 1

        try:
            playlist.save()
        except:
            return {
                       'success': False,
                       'message': 'Something went wrong while updatating the playlist page views'
                   }, 500

        return {
            'success': True,
            'message': 'playlist page views updated'
        }

class StatusResource(Resource):
    parser =reqparse.RequestParser(trim=True)
    parser.add_argument('user-type', required=False, location='args')

    @staticmethod
    def get():
        json_data = SearchResource.parser.parse_args()
        return {
            'success': True,
            'result': json_data['user_type']
        }, 200

class SearchResource(Resource):
    parser =reqparse.RequestParser(trim=True)
    parser.add_argument('user_type', required=False, location='args')

    @staticmethod
    def get():
        json_data = SearchResource.parser.parse_args()

        query = request.args['query']
        
        media_list = Media.search(query)
        user_list = User.search(query, user_type=json_data['user_type'])
        album_list = Album.search(query)

        if len(album_list) == 0 and len(user_list) == 0 and len(media_list) == 0:
            return {
                'success': False,
                'message': 'Not match was found'
            }, 404

        return {
            'success': True,
            'users': users_schema.dump(user_list),
            'media': media_list_schema.dump(media_list),
            'albums': albums_schema.dump(album_list),
        }, 200
