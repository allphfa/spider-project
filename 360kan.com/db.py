from mongoengine import *


class VideoNumber(EmbeddedDocument):
    name = StringField()
    link = StringField()


class VideoInfo(EmbeddedDocument):
    meta = {
        'strict': False,
        "collection": "videoinfo",
    }
    name = StringField()
    links = ListField(EmbeddedDocumentField(VideoNumber), defaulf=[])


class Video(Document):
    meta = {
        'strict': False,
        "collection": "video",
    }
    cid = StringField(unique=True)
    topcls_name = StringField()
    subcls_name = ListField(StringField(), default=[])
    title = StringField()
    score = StringField()

    pic = StringField()  
    year = StringField()
    area = StringField()
    director = ListField(StringField(), default=[])
    actor = ListField(StringField(), default=[])
    desc = StringField()
    update_to = StringField()
    all_num = StringField()

    update_time = StringField()

    videos = ListField(EmbeddedDocumentField(VideoInfo), default=[])


connect(db='videos_cms', host='127.0.0.1', port=27017, username='root', password='123456')
