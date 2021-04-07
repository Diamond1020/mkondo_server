import pandas
import requests

from sqlalchemy import func
from mkondo import db
from media.models import Media, Comment, Album
from users.models import MediaUserHistory, User


class ArtistInsights:
    @classmethod
    def fetch_artist_data(cls, artist_id):
        query = Media.query.filter_by(owner_id=artist_id).with_entities(Media.id, Media.shares, Media.likes)
        data = db.session.query(func.sum(Media.shares), func.sum(Media.likes)).filter_by(owner_id=artist_id).all()
        shares, likes = data[0][0], data[0][1]
        media_ids = [media.id for media in query.all()]
        artist_comments_count = Comment.query.filter(Comment.media_id.in_(media_ids)).count()
        histories = MediaUserHistory.query.filter(MediaUserHistory.media_id.in_(media_ids)).all()
        plays = 0

        for h in histories:
            plays += h.plays

        ip_addresses = list(set([history.user.locality for history in histories]))
        audience = []

        for ip_address in ip_addresses:
            result = requests.get(f'http://api.ipstack.com/{ip_address}?access_key=e17511b1b202682166e46cb188347457').json()
            audience.append({'country': result['country_name'], 'region': result['region_name']})
        
        audience_data = []

        for a in audience:
            b = {'count': 0, 'country': a['country'], 'region': a['region']}

            for c in audience:
                if c['country'] == b['country'] and c['region'] == b['region']:
                    b['count'] += 1
            
            if b in audience_data:
                continue
            else:
                audience_data.append(b)
        
        return dict(
            success=True,
            shares=shares,
            plays=plays,
            likes=likes,
            comments=artist_comments_count,
            audience=audience_data,
        )


class UsersInsights:
    @staticmethod
    def fetch_audio_insights():
        albums = Album.query.all()
        songs = Media.query.filter_by(category='audio').with_entities(Media.id, Media.owner_id).all()
        song_ids = [song.id for song in songs]
        listener_count = MediaUserHistory.query.filter(MediaUserHistory.media_id.in_(song_ids)).with_entities(MediaUserHistory.user_id).distinct().count()
        publisher_count = len(list(set([album.publisher for album in albums])))
        artist_count = len(list(set([song.owner_id for song in songs])))
        total_users = len(User.query.all())

        return dict(
            success=True,
            artists=artist_count,
            publishers=publisher_count,
            listeners=listener_count,
            users=total_users
        )
