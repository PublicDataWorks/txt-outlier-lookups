# tests/factories.py
import factory
from factory.faker import Faker
from factory.alchemy import SQLAlchemyModelFactory
from datetime import datetime
import uuid
from models import Comments, User, TwilioMessage, Author, CommentsMentions, Conversation


class ConversationFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Conversation
        sqlalchemy_session_persistence = 'commit'

    id = factory.LazyFunction(uuid.uuid4)
    created_at = factory.LazyFunction(datetime.now)
    messages_count = 0
    drafts_count = 0
    send_later_messages_count = 0
    attachments_count = 0
    tasks_count = 0
    completed_tasks_count = 0
    web_url = factory.Faker('url')
    app_url = factory.Faker('url')


class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = 'commit'

    id = factory.LazyFunction(uuid.uuid4)
    name = Faker('name')
    email = Faker('email')
    avatar_url = Faker('url')


class CommentsFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Comments
        sqlalchemy_session_persistence = 'commit'

    id = factory.LazyFunction(uuid.uuid4)
    conversation_id = factory.LazyAttribute(lambda obj: obj.conversation.id)
    created_at = factory.LazyFunction(datetime.now)
    body = Faker('text', max_nb_chars=100)
    user_id = factory.LazyAttribute(lambda obj: obj.user.id)
    is_task = False
    attachment = None


class TwilioMessageFactory(SQLAlchemyModelFactory):
    class Meta:
        model = TwilioMessage
        sqlalchemy_session_persistence = 'commit'

    id = factory.LazyFunction(uuid.uuid4)
    preview = Faker('text', max_nb_chars=50)
    type = 'sms'
    delivered_at = factory.LazyFunction(datetime.now)
    references = factory.List([factory.Faker('text') for _ in range(1)])
    from_field = Faker('phone_number')
    to_field = Faker('phone_number')
    is_broadcast_reply = False
    reply_to_broadcast = None


class AuthorFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Author
        sqlalchemy_session_persistence = 'commit'

    phone_number = Faker('phone_number')
    name = Faker('name')
    unsubscribed = False
    email = Faker('email')
    zipcode = Faker('zipcode')


class CommentsMentionsFactory(SQLAlchemyModelFactory):
    class Meta:
        model = CommentsMentions
        sqlalchemy_session_persistence = 'commit'

    id = factory.Sequence(lambda n: n)
    comment_id = factory.LazyAttribute(lambda obj: obj.comment.id)
    user_id = factory.LazyAttribute(lambda obj: obj.user.id)
