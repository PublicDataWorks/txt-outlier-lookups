import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .config import DATABASE_URL, IMPACT_LABEL_IDS, REPORTER_LABEL_IDS, BROADCAST_SOURCE_PHONE_NUMBER
from .utils import (
    format_metric_by_audience_segment,
    format_conversation_for_report,
    format_lookup_history,
    get_current_date_formatted_for_weekly_report,
    format_geographic_regions,
)
from libs.MissiveAPI import MissiveAPI

class AnalyticsService:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_weekly_unsubscribe_by_audience_segment(self, session):
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

    def get_weekly_broadcast_sent(self, session):
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

    def get_weekly_failed_message(self, session):
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

    def get_weekly_text_ins(self, session):
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

    def get_weekly_impact_conversations(self, session):
        impact_label_ids = ', '.join(f"'{id}'" for id in IMPACT_LABEL_IDS)
        query = text(f"""
            SELECT l.name as label_name, COUNT(*) as count
            FROM public.conversations_labels cl 
            JOIN public.labels l ON cl.label_id = l.id
            WHERE label_id IN ({impact_label_ids})
            AND
            cl.created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
            AND 
            cl.created_at < DATE_TRUNC('week', CURRENT_DATE) 
            GROUP BY l.name;
        """)
        return session.execute(query).fetchall()

    def get_weekly_replies_by_audience_segment(self, session):
        query = text("""
            SELECT bsms.audience_segment_id, asg.name, COUNT(distinct tm.id) as count
            FROM public.twilio_messages tm 
            LEFT JOIN public.broadcast_sent_message_status bsms 
            ON tm.reply_to_broadcast = bsms.broadcast_id
            LEFT JOIN public.audience_segments asg 
            ON bsms.audience_segment_id = asg.id
            WHERE tm.is_broadcast_reply = true and tm.from_field = bsms.recipient_phone_number
            GROUP BY bsms.audience_segment_id, asg.name
        """)
        return session.execute(query).fetchall()

    def get_weekly_reporter_conversation(self, session):
        reporter_label_ids = ', '.join(f"'{id}'" for id in REPORTER_LABEL_IDS)
        query = text(f"""
            SELECT l.name as label_name, COUNT(*) as count
            FROM public.conversations_labels cl 
            JOIN public.labels l ON cl.label_id = l.id
            WHERE label_id IN ({reporter_label_ids})
            GROUP BY l.name;
        """)
        return session.execute(query).fetchall()

    def get_weekly_data_look_up(self, session):
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
            ) AS combined_statuses
            GROUP BY 
                status
            ORDER BY 
                status;
        """)
        return session.execute(query).fetchall()

    def get_weekly_top_zip_code(self, session):
        query = text ("""
        SELECT zip_code, COUNT(*) AS count
        FROM "lookup_history"
        WHERE
        created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
        AND 
        created_at < DATE_TRUNC('week', CURRENT_DATE) 
        GROUP BY zip_code
        ORDER BY count DESC
        LIMIT 5;
    """)
        return session.execute(query).fetchall()

    def fetch_data(self):
        with self.Session() as session:
            # Fetch all the data here synchronously
            unsubscribed_messages = self.get_weekly_unsubscribe_by_audience_segment(session)
            broadcasts = self.get_weekly_broadcast_sent(session)
            failed_messages = self.get_weekly_failed_message(session)
            text_ins = self.get_weekly_text_ins(session)
            impact_conversations = self.get_weekly_impact_conversations(session)
            replies = self.get_weekly_replies_by_audience_segment(session)
            report_conversations = self.get_weekly_reporter_conversation(session)
            lookup_history = self.get_weekly_data_look_up(session)
            zip_codes = self.get_weekly_top_zip_code(session)
        
        return (
            unsubscribed_messages,
            broadcasts,
            failed_messages,
            text_ins,
            impact_conversations,
            replies,
            report_conversations,
            lookup_history,
            zip_codes
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
            lookup_history,
            zip_codes
        ) = self.fetch_data()
       
        # weekly_report_conversation_id = os.getenv('MISSIVE_WEEKLY_REPORT_CONVERSATION_ID')
        total_unsubscribed_messages = sum(int(conversation[1]) for conversation in unsubscribed_messages) if unsubscribed_messages else 0
        total_replies = sum(int(conversation[2]) for conversation in replies) if replies else 0
        total_report_conversations = sum(int(conversation[1]) for conversation in report_conversations) if report_conversations else 0

        intro = f"# Weekly Summary Report ({get_current_date_formatted_for_weekly_report()})"

        major_themes = (
            "## Summary of Major Themes/Topics\n"
            "- **User Satisfaction**: Significant number of users expressed satisfaction with the resources provided.\n"
            "- **Problem Addressed**: Numerous reports of problems addressed successfully.\n"
            "- **Crisis Averted**: Notable increase in crisis averted scenarios.\n"
            "- **Property Status Inquiries**: Frequent inquiries about property status, particularly regarding tax debt and compliance issues.\n"
            "- **Accountability Initiatives**: Positive feedback on accountability initiatives, with some users highlighting persistent issues.\n"
        )

        conversation_metrics = (
            "### Conversation Metrics\n"
            "| Metric                         | Count |\n"
            "|------------------------------- |-------|\n"
            f"| Conversation Starters Sent     | {broadcasts[0]} |\n"
            f"| Broadcast replies              | {total_replies}  |\n"
            f"| Text-ins                       | {text_ins[0]} |\n"
            f"| Reporter conversations         | {total_report_conversations} |\n"
            f"| Failed Deliveries              | {failed_messages[0]} |\n"
            f"| Unsubscribes                   | {total_unsubscribed_messages} |\n"
        )

        lookup_history_section = ''
        formatted_lookup_history = format_lookup_history(lookup_history)
        if formatted_lookup_history.strip():
            lookup_history_section = (
                "### Data Lookups by Property Status\n"
                "| Status                         | Count |\n"
                "|------------------------------- |-------|\n"
                f"{formatted_lookup_history}"
            )

        impact_conversations_section = format_conversation_for_report(impact_conversations)
        conversation_outcomes = ''
        if impact_conversations_section.strip():
            conversation_outcomes = (
                "### Conversation Outcomes\n"
                "| Outcome                         | Count |\n"
                "|-------------------------------  |-------|\n"
                f"{impact_conversations_section}"
            )

        zip_code_section = format_geographic_regions(zip_codes)
        geographic_regions = ''
        if zip_code_section.strip():
            geographic_regions = (
                "### Data Lookups by Geographic Regions (Top 5 ZIP Codes)\n"
                "| **ZIP Code** | **Count** |\n"
                "|--------------|-------|\n"
                f"{zip_code_section}"
            )

        replies_by_audience_segment = format_metric_by_audience_segment(replies)
        broadcast_replies = ''
        if replies_by_audience_segment.strip():
            broadcast_replies = (
                "### Broadcast Replies by Audience Segment\n"
                "| Segment                         | Count |\n"
                "|-------------------------------  |-------|\n"
                f"{replies_by_audience_segment}"
            )

        unsubscribed_by_audience_segment = format_metric_by_audience_segment(unsubscribed_messages)
        unsubscribe_section = ''
        if unsubscribed_by_audience_segment.strip():
            unsubscribe_section = (
                "### Unsubscribes by Audience Segment\n"
                "| Segment                         | Count |\n"
                "|-------------------------------  |-------|\n"
                f"{unsubscribed_by_audience_segment}"
            )

        markdown_report = [intro, major_themes, conversation_metrics]
        
        if lookup_history_section:
            markdown_report.append(lookup_history_section)
        if geographic_regions:
            markdown_report.append(geographic_regions)
        if conversation_outcomes:
            markdown_report.append(conversation_outcomes)
        if broadcast_replies:
            markdown_report.append(broadcast_replies)
        if unsubscribe_section:
            markdown_report.append(unsubscribe_section)

        missive_client = MissiveAPI()
        missive_client.send_post_sync(markdown_report, conversation_id= os.getenv('MISSIVE_WEEKLY_REPORT_CONVERSATION_ID'))
        
