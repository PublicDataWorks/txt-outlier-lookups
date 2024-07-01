import logging
import os
from typing import NamedTuple

from configs.query_engine.weekly_report_trend_summary import generate_report_summary
from models import LookupTemplate

logger = logging.getLogger(__name__)


def format_metric_by_audience_segment(metrics):
    metric_report = ""
    for metric in metrics:
        metric_report += f"| - {metric[1].ljust(28)} | {str(metric[2]).ljust(4)} |\n"
    return metric_report.strip() + "\n" if metric_report else ""


def format_conversation_for_report(conversations):
    conversation_report = ""
    for result in conversations:
        conversation_report += f"| - {result[0].ljust(28)} | {str(result[1]).ljust(4)} |\n"
    return conversation_report.strip() + "\n" if conversation_report else ""


def format_lookup_history(metrics):
    lookup_history_report = ""
    for metric in metrics:
        lookup_history_report += (
            f"| {map_status(metric[0]).ljust(28)} | {str(metric[1]).ljust(5)} |\n"
        )
    return lookup_history_report.strip() + "\n" if lookup_history_report else ""


def format_geographic_regions(zipcodes):
    geographic_regions_table = ""
    for result in zipcodes:
        geographic_regions_table += f"| {str(result[0]).ljust(28)} | {str(result[1]).ljust(4)} |\n"
    return geographic_regions_table.strip() + "\n" if geographic_regions_table else ""


def to_pascal_case(string):
    return " ".join(word.capitalize() for word in string.lower().split("_"))


def map_status(raw_status):
    if raw_status == "OK":
        return "No Tax Debt"
    else:
        return to_pascal_case(raw_status)


def format_broadcast_details(broadcast):
    run_at = broadcast['run_at']
    first_message = broadcast['first_message']
    second_message = broadcast['second_message']
    run_at_formatted = run_at.strftime("%a %b %d, %Y at %I:%M%p ET")

    return f"""
    
*{run_at_formatted}*

_{first_message}_

_{second_message}_

"""


def process_conversation_metrics(data):
    total_broadcasts = (
        len(data["broadcasts"])
        if "broadcasts" in data and data["broadcasts"]
        else 0
    )
    total_text_ins = (
        data["text_ins"]["count"] if isinstance(data["text_ins"], dict) and data["text_ins"] else 0
    )
    failed_deliveries = (
        data["failed_deliveries"]["count"]
        if isinstance(data["failed_deliveries"], dict) and data["failed_deliveries"]
        else 0
    )
    total_unsubscribed_messages = (
        sum(int(conversation["count"]) for conversation in data["unsubscribed_messages"])
        if data["unsubscribed_messages"]
        else 0
    )
    total_replies = (
        sum(int(conversation["count"]) for conversation in data["replies"])
        if data["replies"]
        else 0
    )
    total_report_conversations = (
        sum(int(conversation["count"]) for conversation in data["report_conversations"])
        if data["report_conversations"]
        else 0
    )

    conversation_metrics = {
        "conversation_starters_sent": total_broadcasts,
        "broadcast_replies": total_replies,
        "text_ins": total_text_ins,
        "reporter_conversations": total_report_conversations,
        "unsubscribes": total_unsubscribed_messages,
        "failed_deliveries": failed_deliveries,
    }

    return conversation_metrics


def process_lookup_history(lookup_data):
    # Initialize the status counts
    status_counts = {
        "REGISTERED": 0,
        "UNREGISTERED": 0,
        "TAX_DEBT": 0,
        "NO_TAX_DEBT": 0,
        "COMPLIANT": 0,
        "FORECLOSED": 0,
    }

    # Map the fetched data to status_counts
    for row in lookup_data:
        status = row["status"]
        if status in status_counts:
            count = row["count"]
            status_counts[status] = count

    return status_counts


def process_conversation_outcomes(outcomes):
    outcome_counts = {
        "user satisfaction": 0,
        "problem addressed": 0,
        "unsatisfied": 0,
        "accountability gap": 0,
        "crisis averted": 0,
        "future keyword": 0,
        "source": 0,
    }

    # Map the fetched data to outcome_counts
    for row in outcomes:
        label_name = row["label_name"]
        if label_name in outcome_counts:
            count = row["count"]
            outcome_counts[label_name] = count

    return outcome_counts


def process_audience_segment_related_data(data):
    # Initialize the segment counts
    segment_counts = {"Proactive": 0, "Receptive": 0, "Connected": 0, "Passive": 0, "Inactive": 0}

    # Map the fetched data to segment_counts
    for row in data:
        segment_name = row["audience_segment_name"]
        if segment_name in segment_counts:
            count = row["count"]
            segment_counts[segment_name] = count

    return segment_counts


def generate_geographic_region_markdown(zip_codes):
    zip_code_section = format_geographic_regions(zip_codes)
    if zip_code_section.strip():
        return (
            "### Data Lookups by Geographic Regions (Top 5 ZIP Codes)\n"
            "| **ZIP Code** | **Count** |\n"
            "|--------------|-------|\n"
            f"{zip_code_section}"
        )
    return ""


def generate_lookup_history_markdown(status_counts, percentage_changes, percentage_changes_4_week):
    return (
        "### Data Lookups by Property Status\n"
        "| Status                         | Count |  Change (week) | Change (4-week avg) |\n"
        "|------------------------------- |-------|----------------|---------------------|\n"
        f"| Registered             | {status_counts['REGISTERED']} |   {format_percentage_change(percentage_changes['REGISTERED'])} | {format_percentage_change(percentage_changes_4_week['REGISTERED'])} \n"
        f"| Unregistered            | {status_counts['UNREGISTERED']}  |   {format_percentage_change(percentage_changes['UNREGISTERED'])} | {format_percentage_change(percentage_changes_4_week['UNREGISTERED'])} \n"
        f"| Tax Debt                | {status_counts['TAX_DEBT']} |   {format_percentage_change(percentage_changes['TAX_DEBT'])} | {format_percentage_change(percentage_changes_4_week['TAX_DEBT'])} \n"
        f"| No Tax Debt            | {status_counts['NO_TAX_DEBT']} |   {format_percentage_change(percentage_changes['NO_TAX_DEBT'])} | {format_percentage_change(percentage_changes_4_week['NO_TAX_DEBT'])} \n"
        f"| Compliant               | {status_counts['COMPLIANT']} |   {format_percentage_change(percentage_changes['COMPLIANT'])} | {format_percentage_change(percentage_changes_4_week['COMPLIANT'])} \n"
        f"| Foreclosed              | {status_counts['FORECLOSED']} |   {format_percentage_change(percentage_changes['FORECLOSED'])} | {format_percentage_change(percentage_changes_4_week['FORECLOSED'])} \n"
    )


def generate_conversation_outcomes_markdown(
    outcome_counts, percentage_changes, percentage_changes_4_week
):
    return (
        "### Conversation Outcomes\n"
        "| Outcome                         | Count |  Change (week) | Change (4-week avg) |\n"
        "|-------------------------------  |-------|----------------|---------------------|\n"
        f"| User Satisfaction             | {outcome_counts['user satisfaction']} |   {format_percentage_change(percentage_changes['user satisfaction'])} | {format_percentage_change(percentage_changes_4_week['user satisfaction'])} \n"
        f"| Problem Addressed             | {outcome_counts['problem addressed']}  |   {format_percentage_change(percentage_changes['problem addressed'])} | {format_percentage_change(percentage_changes_4_week['problem addressed'])} \n"
        f"| Crisis Averted                | {outcome_counts['crisis averted']} |   {format_percentage_change(percentage_changes['crisis averted'])} | {format_percentage_change(percentage_changes_4_week['crisis averted'])} \n"
        f"| Accountability Gap            | {outcome_counts['accountability gap']} |   {format_percentage_change(percentage_changes['accountability gap'])} | {format_percentage_change(percentage_changes_4_week['accountability gap'])} \n"
        f"| Source                        | {outcome_counts['source']} |   {format_percentage_change(percentage_changes['source'])} |  {format_percentage_change(percentage_changes_4_week['source'])} \n"
        f"| Unsatisfied                    | {outcome_counts['unsatisfied']} |   {format_percentage_change(percentage_changes['unsatisfied'])} |  {format_percentage_change(percentage_changes_4_week['unsatisfied'])} \n"
        f"| Future Keyword                | {outcome_counts['future keyword']} |   {format_percentage_change(percentage_changes['future keyword'])} | {format_percentage_change(percentage_changes_4_week['future keyword'])} \n"
    )


def generate_data_by_audience_segment_markdown(
    segment_counts, percentage_changes, percentage_changes_4_week
):
    return (
        "### Broadcast Replies by Audience Segment\n"
        "| Segment                         | Count |  Change (week) | Change (4-week avg) |\n"
        "|-------------------------------  |-------|----------------|---------------------|\n"
        f"| Proactive              | {segment_counts['Proactive']}|   {format_percentage_change(percentage_changes['Proactive'])}  | {format_percentage_change(percentage_changes_4_week['Proactive'])}  \n"
        f"| Receptive             | {segment_counts['Receptive']}|   {format_percentage_change(percentage_changes['Receptive'])}   | {format_percentage_change(percentage_changes_4_week['Receptive'])}   \n"
        f"| Connected                | {segment_counts['Connected']}|   {format_percentage_change(percentage_changes['Connected'])}  | {format_percentage_change(percentage_changes_4_week['Connected'])}  \n"
        f"| Passive            | {segment_counts['Passive']}|   {format_percentage_change(percentage_changes['Passive'])}  | {format_percentage_change(percentage_changes_4_week['Passive'])}  \n"
        f"| Inactive                        | {segment_counts['Inactive']}|   {format_percentage_change(percentage_changes['Inactive'])}  | {format_percentage_change(percentage_changes_4_week['Inactive'])}  \n"
    )


def get_current_date_formatted_for_weekly_report():
    # Placeholder function: Replace with the actual implementation
    from datetime import date

    return date.today().strftime("%B %d, %Y")


def generate_intro_section():
    report_date = get_current_date_formatted_for_weekly_report()
    return f"# Weekly Summary Report ({report_date})"


def generate_broadcast_info_section(broadcasts):
    formatted_details = []
    for broadcast in broadcasts:
        formatted_detail = format_broadcast_details(broadcast)
        formatted_details.append(formatted_detail)

    # Combine all formatted details into a single string
    return (
            "### Broadcast messages sent this week\n"
            + '\n'.join(formatted_details)
    )


def generate_major_themes_section(messages_history):
    summary = generate_report_summary(messages_history)

    if messages_history:
        return (
            "## Summary of Major Themes/Topics\n"
            f"{summary}"
        )
    return ""


def generate_conversation_metrics_section(
    conversation_metrics, percentage_changes, percentage_changes_4_week
):
    return (
        "### Conversation Metrics\n"
        "| Metric                         | Count | Change |\n"
        "|------------------------------- |-------|--------|\n"
        f"| Conversation Starters Sent     | {conversation_metrics['conversation_starters_sent']} |   {format_percentage_change(percentage_changes['conversation_starters_sent'])} |   \n"
        f"| Broadcast replies              | {conversation_metrics['broadcast_replies']}  |   {format_percentage_change(percentage_changes['broadcast_replies'])} | {format_percentage_change(percentage_changes_4_week['broadcast_replies'])} |\n"
        f"| Text-ins                       | {conversation_metrics['text_ins']} |   {format_percentage_change(percentage_changes['text_ins'])}| {format_percentage_change(percentage_changes_4_week['text_ins'])} \n"
        f"| Reporter conversations         | {conversation_metrics['reporter_conversations']} |   {format_percentage_change(percentage_changes['reporter_conversations'])}| {format_percentage_change(percentage_changes_4_week['reporter_conversations'])} \n"
        f"| Failed Deliveries              | {conversation_metrics['failed_deliveries']} |   {format_percentage_change(percentage_changes['failed_deliveries'])}| {format_percentage_change(percentage_changes_4_week['failed_deliveries'])} \n"
        f"| Unsubscribes                   | {conversation_metrics['unsubscribes']} |   {format_percentage_change(percentage_changes['unsubscribes'])}| {format_percentage_change(percentage_changes_4_week['unsubscribes'])} \n"
    )


def calculate_percentage_changes(current_data, last_data):
    percentage_changes = {}
    for key in current_data:
        current_value = current_data[key]
        last_value = last_data.get(key, 0)
        if isinstance(current_value, (int, float)) and isinstance(last_value, (int, float)):
            if last_value != 0:
                change = ((current_value - last_value) / last_value) * 100
            else:
                change = 0 if current_value == 0 else 100
            percentage_changes[key] = change
    return percentage_changes


def format_weekly_report_data(report_data):
    formatted_data = {
        "conversation_metrics": {
            "conversation_starters_sent": int(report_data.conversation_starters_sent if report_data else 0),
            "broadcast_replies": int(report_data.broadcast_replies if report_data else 0),
            "text_ins": int(report_data.text_ins if report_data else 0),
            "reporter_conversations": int(report_data.reporter_conversations if report_data else 0),
            "unsubscribes": int(report_data.unsubscribes if report_data else 0),
            "failed_deliveries": int(report_data.failed_deliveries if report_data else 0),
        },
        "lookup_history": {
            "REGISTERED": int(report_data.status_registered if report_data else 0),
            "UNREGISTERED": int(report_data.status_unregistered if report_data else 0),
            "TAX_DEBT": int(report_data.status_tax_debt if report_data else 0),
            "NO_TAX_DEBT": int(report_data.status_no_tax_debt if report_data else 0),
            "COMPLIANT": int(report_data.status_compliant if report_data else 0),
            "FORECLOSED": int(report_data.status_foreclosed if report_data else 0),
        },
        "conversation_outcomes": {
            "user satisfaction": int(report_data.user_satisfaction if report_data else 0),
            "problem addressed": int(report_data.problem_addressed if report_data else 0),
            "unsatisfied": int(report_data.unsatisfied if report_data else 0),
            "accountability gap": int(report_data.accountability_gap if report_data else 0),
            "crisis averted": int(report_data.crisis_averted if report_data else 0),
            "future keyword": int(report_data.future_keyword if report_data else 0),
            "source": int(report_data.source if report_data else 0),
        },
        "unsubscribed_messages": {
            "Proactive": int(report_data.unsubscribes_proactive if report_data else 0),
            "Receptive": int(report_data.unsubscribes_receptive if report_data else 0),
            "Connected": int(report_data.unsubscribes_connected if report_data else 0),
            "Passive": int(report_data.unsubscribes_passive if report_data else 0),
            "Inactive": int(report_data.unsubscribes_inactive if report_data else 0),
        },
        "replies": {
            "Proactive": int(report_data.replies_proactive if report_data else 0),
            "Receptive": int(report_data.replies_receptive if report_data else 0),
            "Connected": int(report_data.replies_connected if report_data else 0),
            "Passive": int(report_data.replies_passive if report_data else 0),
            "Inactive": int(report_data.replies_inactive if report_data else 0),
        },
    }

    return formatted_data


def calculate_percentage_change(old_data, new_data):
    def calculate_change(old, new):
        if old == 0:
            return 100
        try:
            return ((new - old) / old) * 100 if old != 0 else float("inf") if new != 0 else 0
        except ZeroDivisionError:
            return float("inf")

    def recurse_dict(old_dict, new_dict):
        change_dict = {}
        for key in old_dict:
            if isinstance(old_dict[key], dict):
                change_dict[key] = recurse_dict(old_dict[key], new_dict.get(key, {}))
            else:
                old_value = old_dict[key]
                new_value = new_dict.get(key, old_value)
                change_dict[key] = calculate_change(old_value, new_value)
        return change_dict

    return recurse_dict(old_data, new_data)


def format_percentage_change(change):
    if change > 0:
        return f"▲ {change:.2f}%"
    elif change < 0:
        return f"▼ {abs(change):.2f}%"
    else:
        return "~ 0%"


def get_conversation_id(session):
    try:
        lookup_id = session.query(LookupTemplate).filter_by(name="missive_report_conversation_id").first()
        if lookup_id:
            text = lookup_id.content
        else:
            fallback_id = os.getenv("MISSIVE_WEEKLY_REPORT_CONVERSATION_ID")
            if fallback_id:
                text = fallback_id
            else:
                logger.error(f"Error fetching backup MISSIVE_WEEKLY_REPORT_CONVERSATION_ID")
                return None
    except Exception as e:
        logger.error(f"Error fetching MISSIVE_WEEKLY_REPORT_CONVERSATION_ID from database: {e}")
        return None


class FetchDataResult(NamedTuple):
    unsubscribed_messages: any
    broadcasts: any
    messages_history: any
    failed_deliveries: any
    text_ins: any
    impact_conversations: any
    replies: any
    report_conversations: any
    lookup_history: any
    zip_codes: any
    broadcasts_content: any

    def __getitem__(self, key):
        return getattr(self, key)
