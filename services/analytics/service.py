import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import datetime

from configs.database import Session
from .config import (
    DATABASE_URL,
    IMPACT_LABEL_IDS,
    REPORTER_LABEL_IDS,
)
from .utils import (
    process_conversation_metrics,
    process_conversation_outcomes,
    process_audience_segment_related_data,
    process_lookup_history,
    generate_geographic_region_markdown,
    generate_data_by_audience_segment_markdown,
    generate_conversation_outcomes_markdown,
    generate_lookup_history_markdown,
    generate_intro_section,
    generate_major_themes_section,
    generate_conversation_metrics_section,
    FetchDataResult,
    generate_broadcast_info_section,
)
from .queries import (
    GET_WEEKLY_UNSUBSCRIBE_BY_AUDIENCE_SEGMENT,
    GET_WEEKLY_BROADCAST_SENT,
    GET_WEEKLY_FAILED_MESSAGE,
    GET_WEEKLY_TEXT_INS,
    GET_WEEKLY_IMPACT_CONVERSATIONS,
    GET_WEEKLY_REPLIES_BY_AUDIENCE_SEGMENT,
    GET_WEEKLY_REPORTER_CONVERSATION,
    GET_WEEKLY_DATA_LOOKUP,
    GET_WEEKLY_TOP_ZIP_CODE,
    GET_WEEKLY_MESSAGES_HISTORY,
)
from collections import defaultdict
from libs.MissiveAPI import MissiveAPI
from models import WeeklyReport

load_dotenv(override=True)


class AnalyticsService:
    def __init__(self):
        self.Session = Session()


    def get_weekly_unsubscribe_by_audience_segment(self, session):
        return session.execute(GET_WEEKLY_UNSUBSCRIBE_BY_AUDIENCE_SEGMENT).fetchall()

    def get_weekly_broadcast_sent(self, session):
        return session.execute(GET_WEEKLY_BROADCAST_SENT).fetchall()

    def get_weekly_messages_history(self, session, broadcast_sent):
        broadcast_messages = []
        for broadcast in broadcast_sent:
            broadcast_messages.append(broadcast["first_message"])
            broadcast_messages.append(broadcast["second_message"])

        if broadcast_messages:
            placeholders = ', '.join([f':msg{i + 1}' for i in range(len(broadcast_messages))])
            not_in_clause = f"AND preview NOT IN ({placeholders})"
            params = {f'msg{i + 1}': msg for i, msg in enumerate(broadcast_messages)}
        else:
            not_in_clause = ""
            params = {}

        query = text(GET_WEEKLY_MESSAGES_HISTORY + "\n" + not_in_clause).bindparams(**params)

        messages = session.execute(query).fetchall()

        grouped_messages = defaultdict(list)
        for message in messages:
            refs = message["references"]
            preview = message["preview"]
            grouped_messages[refs[0]].append(preview)

        return grouped_messages

    def get_weekly_failed_message(self, session):
        return session.execute(GET_WEEKLY_FAILED_MESSAGE).fetchone()

    def get_weekly_text_ins(self, session):
        return session.execute(GET_WEEKLY_TEXT_INS).fetchone()

    def get_weekly_impact_conversations(self, session):
        impact_label_ids = ", ".join(f"'{id}'" for id in IMPACT_LABEL_IDS)
        return session.execute(GET_WEEKLY_IMPACT_CONVERSATIONS(impact_label_ids)).fetchall()

    def get_weekly_replies_by_audience_segment(self, session):
        return session.execute(GET_WEEKLY_REPLIES_BY_AUDIENCE_SEGMENT).fetchall()

    def get_weekly_reporter_conversation(self, session):
        reporter_label_ids = ", ".join(f"'{id}'" for id in REPORTER_LABEL_IDS)
        return session.execute(GET_WEEKLY_REPORTER_CONVERSATION(reporter_label_ids)).fetchall()

    def get_weekly_data_look_up(self, session):
        return session.execute(GET_WEEKLY_DATA_LOOKUP).fetchall()

    def get_weekly_top_zip_code(self, session):
        return session.execute(GET_WEEKLY_TOP_ZIP_CODE).fetchall()

    def fetch_data(self):
        with self.Session as session:
            # Fetch all the data here synchronously
            unsubscribed_messages = self.get_weekly_unsubscribe_by_audience_segment(session)
            broadcasts = self.get_weekly_broadcast_sent(session)
            messages_history = self.get_weekly_messages_history(session, broadcasts)
            failed_deliveries = self.get_weekly_failed_message(session)
            text_ins = self.get_weekly_text_ins(session)
            impact_conversations = self.get_weekly_impact_conversations(session)
            replies = self.get_weekly_replies_by_audience_segment(session)
            report_conversations = self.get_weekly_reporter_conversation(session)
            lookup_history = self.get_weekly_data_look_up(session)
            zip_codes = self.get_weekly_top_zip_code(session)

        return FetchDataResult(
            unsubscribed_messages,
            broadcasts,
            messages_history,
            failed_deliveries,
            text_ins,
            impact_conversations,
            replies,
            report_conversations,
            lookup_history,
            zip_codes,
        )

    def insert_weekly_report(self,
                             session,
                             current_date,
                             conversation_metrics,
                             conversation_outcomes,
                             property_statuses,
                             broadcast_replies,
                             unsubscribes,
                             ):
        new_report = WeeklyReport(
            created_at=current_date,
            conversation_starters_sent=conversation_metrics["conversation_starters_sent"],
            broadcast_replies=conversation_metrics["broadcast_replies"],
            text_ins=conversation_metrics["text_ins"],
            reporter_conversations=conversation_metrics["reporter_conversations"],
            failed_deliveries=conversation_metrics["failed_deliveries"],
            unsubscribes=conversation_metrics["unsubscribes"],
            user_satisfaction=conversation_outcomes["user satisfaction"],
            problem_addressed=conversation_outcomes["problem addressed"],
            crisis_averted=conversation_outcomes["crisis averted"],
            accountability_gap=conversation_outcomes["accountability gap"],
            source=conversation_outcomes["source"],
            unsatisfied=conversation_outcomes["unsatisfied"],
            future_keyword=conversation_outcomes["future keyword"],
            status_registered=property_statuses["REGISTERED"],
            status_unregistered=property_statuses["UNREGISTERED"],
            status_tax_debt=property_statuses["TAX_DEBT"],
            status_no_tax_debt=property_statuses["NO_TAX_DEBT"],
            status_compliant=property_statuses["COMPLIANT"],
            status_foreclosed=property_statuses["FORECLOSED"],
            replies_total=sum(broadcast_replies.values()),
            replies_proactive=broadcast_replies["Proactive"],
            replies_receptive=broadcast_replies["Receptive"],
            replies_connected=broadcast_replies["Connected"],
            replies_passive=broadcast_replies["Passive"],
            replies_inactive=broadcast_replies["Inactive"],
            unsubscribes_total=sum(unsubscribes.values()),
            unsubscribes_proactive=unsubscribes["Proactive"],
            unsubscribes_receptive=unsubscribes["Receptive"],
            unsubscribes_connected=unsubscribes["Connected"],
            unsubscribes_passive=unsubscribes["Passive"],
            unsubscribes_inactive=unsubscribes["Inactive"],
        )
        session.add(new_report)
        session.commit()

    def send_weekly_report(self):
        # Fetch the data synchronously
        data = self.fetch_data()

        conversation_metrics = process_conversation_metrics(data)
        property_statuses = process_lookup_history(data["lookup_history"])
        conversations_outcomes = process_conversation_outcomes(data["impact_conversations"])
        replies_by_audience_segment = process_audience_segment_related_data(data["replies"])
        unsubscribes_by_audience_segment = process_audience_segment_related_data(
            data["unsubscribed_messages"]
        )

        intro_section = generate_intro_section()
        broadcast_and_summary_section = generate_broadcast_info_section(data["broadcasts"])
        major_themes_section = generate_major_themes_section(data["messages_history"])
        zip_code_section = generate_geographic_region_markdown(data["zip_codes"])
        conversation_metrics_section = generate_conversation_metrics_section(conversation_metrics)
        lookup_history_section = generate_lookup_history_markdown(property_statuses)
        conversation_outcomes_section = generate_conversation_outcomes_markdown(
            conversations_outcomes
        )
        replies_by_audience_segment_section = generate_data_by_audience_segment_markdown(
            replies_by_audience_segment
        )
        unsubscribe_by_audience_segment_section = generate_data_by_audience_segment_markdown(
            unsubscribes_by_audience_segment
        )

        markdown_report = [
            intro_section,
            major_themes_section,
            broadcast_and_summary_section,
            conversation_metrics_section,
        ]

        if lookup_history_section:
            markdown_report.append(lookup_history_section)
        if zip_code_section:
            markdown_report.append(zip_code_section)
        if conversation_outcomes_section:
            markdown_report.append(conversation_outcomes_section)
        if replies_by_audience_segment_section:
            markdown_report.append(replies_by_audience_segment_section)
        if unsubscribe_by_audience_segment_section:
            markdown_report.append(unsubscribe_by_audience_segment_section)

        missive_client = MissiveAPI()
        missive_client.send_post_sync(
            markdown_report, conversation_id=os.getenv("MISSIVE_WEEKLY_REPORT_CONVERSATION_ID")
        )

        with self.Session() as session:
            self.insert_weekly_report(
                session,
                datetime.datetime.now().isoformat(),
                conversation_metrics,
                conversations_outcomes,
                property_statuses,
                replies_by_audience_segment,
                unsubscribes_by_audience_segment,
            )
