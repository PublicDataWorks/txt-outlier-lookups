import datetime
from collections import defaultdict

from dotenv import load_dotenv
from sqlalchemy import text

from configs.database import Session
from libs.MissiveAPI import MissiveAPI
from models import WeeklyReport
from services.analytics.config import IMPACT_LABEL_IDS
from services.analytics.queries import (
    GET_WEEKLY_TOTAL_UNSUBSCRIBES,
    GET_WEEKLY_FAILED_MESSAGE,
    GET_WEEKLY_TEXT_INS,
    GET_WEEKLY_IMPACT_CONVERSATIONS,
    GET_WEEKLY_TOTAL_REPLIES,
    GET_WEEKLY_REPORTER_CONVERSATION,
    GET_WEEKLY_DATA_LOOKUP,
    GET_WEEKLY_TOP_ZIP_CODE,
    GET_WEEKLY_MESSAGES_HISTORY,
    GET_WEEKLY_BROADCAST_CONTENT,
    GET_WEEKLY_BROADCAST_STARTERS
)
from services.analytics.utils import (
    process_conversation_metrics,
    process_conversation_outcomes,
    process_lookup_history,
    generate_geographic_region_markdown,
    generate_conversation_outcomes_markdown,
    generate_lookup_history_markdown,
    generate_intro_section,
    generate_conversation_metrics_section,
    format_weekly_report_data,
    calculate_percentage_change,
    FetchDataResult,
    generate_broadcast_info_section, get_conversation_id, generate_major_themes_section,
)

load_dotenv(override=True)


class AnalyticsService:
    def __init__(self):
        self.Session = Session()

    def get_weekly_total_unsubscribes(self, session):
        return session.execute(GET_WEEKLY_TOTAL_UNSUBSCRIBES).fetchall()

    def get_weekly_broadcast_sent(self, session):
        return session.execute(GET_WEEKLY_BROADCAST_CONTENT).fetchall()

    def get_broadcasts_starters(self, session, broadcast_sent):
        if not broadcast_sent:
            return []
        broadcast_ids = [broadcast["id"] for broadcast in broadcast_sent]
        return session.execute(GET_WEEKLY_BROADCAST_STARTERS, {'ids': tuple(broadcast_ids)}).fetchall()

    def get_weekly_messages_history(self, session, broadcast_sent):
        broadcast_messages = set()
        for broadcast in broadcast_sent:
            broadcast_messages.add(broadcast["first_message"])
            broadcast_messages.add(broadcast["second_message"])

        like_conditions = []
        params = {}

        for i, msg in enumerate(broadcast_messages):
            param_name = f'msg{i + 1}'
            like_conditions.append(f"preview NOT LIKE :{param_name}")
            params[param_name] = f"%{msg[:100]}%"

        if like_conditions:
            not_like_clause = f"AND ({' AND '.join(like_conditions)})"
        else:
            not_like_clause = ""

        query = text(GET_WEEKLY_MESSAGES_HISTORY + "\n" + not_like_clause).bindparams(**params)

        messages = session.execute(query).fetchall()

        grouped_messages = defaultdict(list)
        for message in messages:
            refs = message["references"]
            grouped_messages[refs[0]].append({
                "preview": message["preview"],
                "from_field": message["from_field"],
                "to_field": message["to_field"],
                "sender_name": message["name"],
                "sender_email": message["email"]
            })

        return grouped_messages

    def get_weekly_failed_message(self, session):
        return session.execute(GET_WEEKLY_FAILED_MESSAGE).fetchone()

    def get_weekly_text_ins(self, session):
        return session.execute(GET_WEEKLY_TEXT_INS).fetchone()

    def get_weekly_impact_conversations(self, session):
        impact_label_ids = ", ".join(f"'{id}'" for id in IMPACT_LABEL_IDS)
        return session.execute(GET_WEEKLY_IMPACT_CONVERSATIONS(impact_label_ids)).fetchall()

    def get_weekly_total_replies(self, session):
        return session.execute(GET_WEEKLY_TOTAL_REPLIES).fetchall()

    def get_weekly_reporter_conversation(self, session):
        return session.execute(GET_WEEKLY_REPORTER_CONVERSATION).fetchall()

    def get_weekly_data_look_up(self, session):
        return session.execute(GET_WEEKLY_DATA_LOOKUP).fetchall()

    def get_weekly_top_zip_code(self, session):
        return session.execute(GET_WEEKLY_TOP_ZIP_CODE).fetchall()

    def get_broadcasts_content(self, session):
        return session.execute(GET_WEEKLY_BROADCAST_CONTENT).fetchall()

    def fetch_data_last_week(self):
        # Calculate the date of the last Monday
        today = datetime.date.today()
        last_monday = today - datetime.timedelta(days=today.weekday() + 7)

        # Calculate the end date of the last Sunday
        last_sunday = last_monday + datetime.timedelta(days=6)

        # Convert to datetime for database query purposes
        last_monday_start = datetime.datetime.combine(last_monday, datetime.time.min)
        last_sunday_end = datetime.datetime.combine(last_sunday, datetime.time.max)

        with self.Session as session:
            # Fetch data for the given week
            data = (
                session.query(WeeklyReport)
                .filter(
                    WeeklyReport.created_at >= last_monday_start,
                    WeeklyReport.created_at <= last_sunday_end,
                )
                .first()
            )

        return format_weekly_report_data(data)

    def fetch_data(self):
        with self.Session as session:
            # Fetch all the data here synchronously
            unsubscribed_messages = self.get_weekly_total_unsubscribes(session)
            broadcasts = self.get_weekly_broadcast_sent(session)
            broadcast_starters = self.get_broadcasts_starters(session, broadcasts)
            messages_history = self.get_weekly_messages_history(session, broadcasts)
            failed_deliveries = self.get_weekly_failed_message(session)
            text_ins = self.get_weekly_text_ins(session)
            impact_conversations = self.get_weekly_impact_conversations(session)
            replies = self.get_weekly_total_replies(session)
            report_conversations = self.get_weekly_reporter_conversation(session)
            lookup_history = self.get_weekly_data_look_up(session)
            zip_codes = self.get_weekly_top_zip_code(session)
            broadcasts_content = self.get_broadcasts_content(session)

        return FetchDataResult(
            unsubscribed_messages,
            broadcasts,
            broadcast_starters,
            messages_history,
            failed_deliveries,
            text_ins,
            impact_conversations,
            replies,
            report_conversations,
            lookup_history,
            zip_codes,
            broadcasts_content
        )

    def insert_weekly_report(
        self,
        session,
        current_date,
        conversation_metrics,
        conversation_outcomes,
        property_statuses,
        total_broadcast_replies,
        total_unsubscribes,
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
            replies_total=total_broadcast_replies,
            unsubscribes_total=total_unsubscribes,
        )
        session.add(new_report)
        session.commit()

    def send_weekly_report(self):
        # Fetch the data synchronously
        data = self.fetch_data()
        last_week_data = self.fetch_data_last_week()
        last_4_week_data = self.fetch_average_data_last_4_weeks()

        conversation_metrics = process_conversation_metrics(data)
        property_statuses = process_lookup_history(data["lookup_history"])
        conversations_outcomes = process_conversation_outcomes(data["impact_conversations"])

        intro_section = generate_intro_section()
        broadcast_and_summary_section = generate_broadcast_info_section(data["broadcasts_content"])
        major_themes_section = generate_major_themes_section(data["messages_history"])
        zip_code_section = generate_geographic_region_markdown(data["zip_codes"])

        conversation_metrics_section = generate_conversation_metrics_section(
            conversation_metrics,
            calculate_percentage_change(
                last_week_data["conversation_metrics"], conversation_metrics
            ),
            calculate_percentage_change(
                last_4_week_data["conversation_metrics"], conversation_metrics
            ),
        )
        lookup_history_section = generate_lookup_history_markdown(
            property_statuses,
            calculate_percentage_change(last_week_data["lookup_history"], property_statuses),
            calculate_percentage_change(last_4_week_data["lookup_history"], property_statuses),
        )
        conversation_outcomes_section = generate_conversation_outcomes_markdown(
            conversations_outcomes,
            calculate_percentage_change(
                last_week_data["conversation_outcomes"], conversations_outcomes
            ),
            calculate_percentage_change(
                last_4_week_data["conversation_outcomes"], conversations_outcomes
            ),
        )
        markdown_report = [intro_section]

        if major_themes_section:
            markdown_report.append(major_themes_section)
        if broadcast_and_summary_section:
            markdown_report.append(broadcast_and_summary_section)
        if conversation_metrics_section:
            markdown_report.append(conversation_metrics_section)
        if lookup_history_section:
            markdown_report.append(lookup_history_section)
        if zip_code_section:
            markdown_report.append(zip_code_section)
        if conversation_outcomes_section:
            markdown_report.append(conversation_outcomes_section)

        conversation_id = get_conversation_id(self.Session)
        missive_client = MissiveAPI()
        missive_client.send_post_sync(markdown_report, conversation_id=conversation_id)
        with self.Session as session:
            self.insert_weekly_report(
                session,
                datetime.datetime.now().isoformat(),
                conversation_metrics,
                conversations_outcomes,
                property_statuses,
                data["replies"][0][0],
                data["unsubscribed_messages"][0][0],
            )

    def fetch_average_data_last_4_weeks(self):
        # Calculate the start date for 4 weeks ago
        today = datetime.date.today()
        start_date = today - datetime.timedelta(days=today.weekday() + 28)

        # Calculate the end date of the last Sunday
        end_date = today - datetime.timedelta(days=today.weekday() + 1)

        # Convert to datetime for database query purposes
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)

        query = text("""
            SELECT 
                AVG(conversation_starters_sent) AS conversation_starters_sent,
                AVG(broadcast_replies) AS broadcast_replies,
                AVG(text_ins) AS text_ins,
                AVG(reporter_conversations) AS reporter_conversations,
                AVG(failed_deliveries) AS failed_deliveries,
                AVG(unsubscribes) AS unsubscribes,
                AVG(user_satisfaction) AS user_satisfaction,
                AVG(problem_addressed) AS problem_addressed,
                AVG(crisis_averted) AS crisis_averted,
                AVG(accountability_gap) AS accountability_gap,
                AVG(source) AS source,
                AVG(unsatisfied) AS unsatisfied,
                AVG(future_keyword) AS future_keyword,
                AVG(status_registered) AS status_registered,
                AVG(status_unregistered) AS status_unregistered,
                AVG(status_tax_debt) AS status_tax_debt,
                AVG(status_no_tax_debt) AS status_no_tax_debt,
                AVG(status_compliant) AS status_compliant,
                AVG(status_foreclosed) AS status_foreclosed,
                AVG(replies_proactive) AS replies_proactive,
                AVG(replies_receptive) AS replies_receptive,
                AVG(replies_connected) AS replies_connected,
                AVG(replies_passive) AS replies_passive,
                AVG(replies_inactive) AS replies_inactive,
                AVG(unsubscribes_proactive) AS unsubscribes_proactive,
                AVG(unsubscribes_receptive) AS unsubscribes_receptive,
                AVG(unsubscribes_connected) AS unsubscribes_connected,
                AVG(unsubscribes_passive) AS unsubscribes_passive,
                AVG(unsubscribes_inactive) AS unsubscribes_inactive
            FROM weekly_reports
            WHERE created_at >= :start_date AND created_at <= :end_date
        """)

        with self.Session as session:
            result = session.execute(
                query, {"start_date": start_datetime, "end_date": end_datetime}
            ).fetchone()

            if not result:
                return None

        return format_weekly_report_data(result)
