import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL, IMPACT_LABEL_IDS, REPORTER_LABEL_IDS, BROADCAST_SOURCE_PHONE_NUMBER
from utils import (
    format_metric_by_audience_segment,
    format_conversation_for_report,
    format_lookup_history,
    map_status,
    to_pascal_case
)

class AnalyticsService:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)

    def fetch_data(self):
        with self.Session() as session:
            # Fetch all the data here synchronously
            unsubscribed_messages = self.get_weekly_unsubscribe_by_audience_segment(session)
            broadcasts = self.get_weekly_broadcast_sent(session)
            failed_messages = self.get_weekly_failed_message(session)
            text_ins = self.get_weekly_text_ins(session)
            impact_conversations = self.get_weekly_impact_conversations(session)
            replies = self.get_weekly_replies_by_audience_segment(session)
            report_conversations = self.get_weekly_report_conversations(session)
            lookup_history = self.get_weekly_data_lookup(session)
        
        return (
            unsubscribed_messages,
            broadcasts,
            failed_messages,
            text_ins,
            impact_conversations,
            replies,
            report_conversations,
            lookup_history
        )
    
    def send_weekly_report(self):
        # Fetch the data synchronously
        (
            unsubscribed_messages,
            broadcasts,
            failed_messages,
            text_ins,
            impact_conversations,
            replies,
            report_conversations,
            lookup_history
        ) = self.fetch_data()
        
        # weekly_report_conversation_id = os.getenv('MISSIVE_WEEKLY_REPORT_CONVERSATION_ID')
        total_unsubscribed_messages = sum(int(conversation['count']) for conversation in unsubscribed_messages)
        total_replies = sum(int(conversation['count']) for conversation in replies)
        total_report_conversations = sum(int(conversation['count']) for conversation in report_conversations)

        intro = f"# Weekly Summary Report ({self.get_current_date_formatted_for_weekly_report()})"

        major_themes = """
        ## Summary of Major Themes/Topics
        - **User Satisfaction**: Significant number of users expressed satisfaction with the resources provided.
        - **Problem Addressed**: Numerous reports of problems addressed successfully.
        - **Crisis Averted**: Notable increase in crisis averted scenarios.
        - **Property Status Inquiries**: Frequent inquiries about property status, particularly regarding tax debt and compliance issues.
        - **Accountability Initiatives**: Positive feedback on accountability initiatives, with some users highlighting persistent issues.
        """

        conversation_metrics = f"""### Conversation Metrics
        | Metric                         | Count |
        |------------------------------- |-------|
        | Conversation Starters Sent     | {broadcasts['count']} |
        | Broadcast replies              | {total_replies}  |
        | Text-ins                       | {text_ins['count']} |
        | Reporter conversations         | {total_report_conversations} |
        | Failed Deliveries              | {failed_messages['count']} |
        | Unsubscribes                   | {total_unsubscribed_messages} |
        """

        lookup_history_section = ''
        formatted_lookup_history = format_lookup_history(lookup_history)
        if formatted_lookup_history.strip():
            lookup_history_section = f"""### Data Lookups by Property Status
        | Status                         | Count |
        |------------------------------- |-------| 
        {formatted_lookup_history}"""

        impact_conversations_section = format_conversation_for_report(impact_conversations)
        conversation_outcomes = ''
        if impact_conversations_section.strip():
            conversation_outcomes = f"""### Conversation Outcomes
        | Outcome                         | Count |
        |-------------------------------  |-------| 
        {impact_conversations_section}"""

        replies_by_audience_segment = format_metric_by_audience_segment(replies)
        broadcast_replies = ''
        if replies_by_audience_segment.strip():
            broadcast_replies = f"""### Broadcast Replies by Audience Segment
        | Segment                         | Count |
        |-------------------------------  |-------| 
        {replies_by_audience_segment}"""

        unsubscribed_by_audience_segment = format_metric_by_audience_segment(unsubscribed_messages)
        unsubscribe_section = ''
        if unsubscribed_by_audience_segment.strip():
            unsubscribe_section = f"""### Unsubcribes by Audience Segment
        | Segment                         | Count |
        |-------------------------------  |-------|
        {unsubscribed_by_audience_segment}"""

        markdown_report = [intro, major_themes, conversation_metrics]
        
        if lookup_history_section:
            markdown_report.append(lookup_history_section)
        if conversation_outcomes:
            markdown_report.append(conversation_outcomes)
        if broadcast_replies:
            markdown_report.append(broadcast_replies)
        if unsubscribe_section:
            markdown_report.append(unsubscribe_section)
        return markdown_report
    
    def select_weekly_unsubscribe_broadcast_message_status(self):
        with self.Session() as session:
            query = text("""
                SELECT 
                bsms.audience_segment_id,
                asg.name,
                COUNT(*) AS count
                FROM 
                  public.unsubscribed_messages um 
                LEFT JOIN 
                  public.broadcast_sent_message_status bsms 
                ON 
                  um.reply_to = bsms.id
                LEFT JOIN public.audience_segments asg 
                ON bsms.audience_segment_id = asg.id
                WHERE
                um.created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
                AND 
                um.created_at < DATE_TRUNC('week', CURRENT_DATE) 
                GROUP BY bsms.audience_segment_id, asg.name
            """)
            return session.execute(query).fetchall()

    def select_weekly_broadcast_sent(self):
        with self.Session() as session:
            query = text("""
                SELECT COUNT(*) AS count
                FROM public.broadcast_sent_message_status
                WHERE 
                is_second = False
                AND
                created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
                AND 
                created_at < DATE_TRUNC('week', CURRENT_DATE) 
            """)
            return session.execute(query).fetchone()

    def select_weekly_failed_message(self):
        with self.Session() as session:
            query = text("""
                SELECT COUNT(*) AS count
                FROM public.broadcast_sent_message_status
                WHERE 
                twilio_sent_status = 'failed' 
                AND
                created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
                AND 
                created_at < DATE_TRUNC('week', CURRENT_DATE) 
            """)
            return session.execute(query).fetchone()

    def select_weekly_text_ins(self):
        with self.Session() as session:
            query = text(f"""
                SELECT COUNT(*) AS count
                FROM public.twilio_messages
                WHERE 
                is_broadcast_reply = false
                AND 
                from_field != '{BROADCAST_SOURCE_PHONE_NUMBER}'
                AND
                created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
                AND 
                created_at < DATE_TRUNC('week', CURRENT_DATE) 
            """)
            return session.execute(query).fetchone()

    def select_weekly_impact_conversations(self):
        impact_label_ids = ', '.join(f"'{id}'" for id in IMPACT_LABEL_IDS)
        with self.Session() as session:
            query = text(f"""
                SELECT l.name as label_name, COUNT(*) as count
                FROM public.conversations_labels cl 
                JOIN public.labels l ON cl.label_id = l.id
                WHERE label_id IN ({impact_label_ids})
                GROUP BY l.name;
            """)
            return session.execute(query).fetchall()

    def select_weekly_replies_broken_by_audience_segment(self):
        with self.Session() as session:
            query = text("""
                SELECT bsms.audience_segment_id, asg.name, COUNT(distinct tm.id) as count
                FROM public.twilio_messages tm 
                LEFT JOIN public.broadcast_sent_message_status bsms 
                ON tm.reply_to_broadcast = bsms.broadcast_id
                LEFT JOIN public.audience_segments asg 
                ON bsms.audience_segment_id = asg.id
                WHERE tm.is_broadcast_reply = true and tm.from_field = bsms.recipient_phone_number
                AND
                tm.created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
                AND 
                tm.created_at < DATE_TRUNC('week', CURRENT_DATE) 
                GROUP BY bsms.audience_segment_id, asg.name
            """)
            return session.execute(query).fetchall()

    def select_weekly_reporter_conversation(self):
        reporter_label_ids = ', '.join(f"'{id}'" for id in REPORTER_LABEL_IDS)
        with self.Session() as session:
            query = text(f"""
                SELECT l.name as label_name, COUNT(*) as count
                FROM public.conversations_labels cl 
                JOIN public.labels l ON cl.label_id = l.id
                WHERE label_id IN ({reporter_label_ids})
                AND
                cl.created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
                AND 
                cl.created_at < DATE_TRUNC('week', CURRENT_DATE) 
                GROUP BY l.name;
            """)
            return session.execute(query).fetchall()

    def select_weekly_data_look_up(self):
        with self.Session() as session:
            query = text("""
                SELECT 
                    status,
                    COUNT(*) AS count
                FROM (
                    SELECT 
                        rental_status AS status
                    FROM 
                        lookup_history
                    WHERE
                    created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
                    AND 
                    created_at < DATE_TRUNC('week', CURRENT_DATE) 
                    UNION ALL
                    SELECT 
                        tax_status AS status
                    FROM 
                        lookup_history
                    WHERE
                        created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
                        AND 
                        created_at < DATE_TRUNC('week', CURRENT_DATE) 
                ) AS combined_statuses
                GROUP BY 
                    status
                ORDER BY 
                    status;
            """)
            return session.execute(query).fetchall()