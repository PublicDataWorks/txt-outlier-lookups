# tests/services/test_common.py
from unittest.mock import patch

from services.common import get_conversation_data
from tests.factories import (
    ConversationFactory,
    UserFactory,
    CommentsFactory,
    CommentsMentionsFactory,
    TwilioMessageFactory,
    AuthorFactory
)


class TestGetConversationData:
    def test_get_conversation_data_success(self, db_session, setup_factories):
        # Arrange
        conversation = ConversationFactory()
        conversation_id = str(conversation.id)
        query_phone = '+1234567890'
        system_phone = '+9876543210'

        # Create authors first
        AuthorFactory(
            phone_number=query_phone,
            email='test@example.com',
            zipcode='12345'
        )
        AuthorFactory(
            phone_number=system_phone
        )

        # Create test users
        user1 = UserFactory()
        user2 = UserFactory()

        # Create test comments
        comment1 = CommentsFactory(
            conversation_id=conversation.id,
            user_id=user1.id,
            body="Test comment 1"
        )
        comment2 = CommentsFactory(
            conversation_id=conversation.id,
            user_id=user2.id,
            body="Test comment 2"
        )

        # Create mentions
        CommentsMentionsFactory(
            comment_id=str(comment1.id),
            user_id=str(user2.id)
        )

        # Create messages after authors exist
        TwilioMessageFactory(
            from_field=query_phone,
            to_field=system_phone,
            preview="Test message 1"
        )
        TwilioMessageFactory(
            from_field=system_phone,
            to_field=query_phone,
            preview="Test message 2"
        )

        with patch('services.common.get_conversation_data_with_cache') as mock_cache, \
                patch('services.common.get_template_content_by_name') as mock_template, \
                patch.dict('os.environ', {'PHONE_NUMBER': system_phone}):
            mock_cache.return_value = {'summary': 'Test summary'}
            mock_template.side_effect = lambda x: f'Mock {x}'
            # Act
            result = get_conversation_data(conversation_id, query_phone)

            # Assert
            assert result is not None
            assert result['messages_title'] == 'Mock messages_title'
            assert result['comments_title'] == 'Mock comments_title'
            assert result['outcome_title'] == 'Mock outcome_title'
