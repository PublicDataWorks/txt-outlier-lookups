from datetime import datetime

def format_metric_by_audience_segment(metrics):
    metric_report = ''
    for metric in metrics:
        metric_report += f"| - {metric[1].ljust(28)} | {str(metric[2]).ljust(4)} |\n"
    return metric_report.strip() + '\n' if metric_report else ''

def format_conversation_for_report(conversations):
    conversation_report = ''
    for result in conversations:
        conversation_report += f"| - {result[0].ljust(28)} | {str(result[1]).ljust(4)} |\n"
    return conversation_report.strip() + '\n' if conversation_report else ''

def format_lookup_history(metrics):
    lookup_history_report = ''
    for metric in metrics:
        lookup_history_report += f"| {map_status(metric[0]).ljust(28)} | {str(metric[1]).ljust(5)} |\n"
    return lookup_history_report.strip() + '\n' if lookup_history_report else ''

def format_geographic_regions(zipcodes):
    geographic_regions_table = ''
    for result in zipcodes:
        breakpoint()
        geographic_regions_table += f"| {str(result[0]).ljust(28)} | {str(result[1]).ljust(4)} |\n"
    return geographic_regions_table.strip() + '\n' if geographic_regions_table else ''

def to_pascal_case(string):
    return ' '.join(word.capitalize() for word in string.lower().split('_'))

def map_status(raw_status):
    if raw_status == 'OK':
        return 'No Tax Debt'
    else:
        return to_pascal_case(raw_status)

def get_current_date_formatted_for_weekly_report():
      return datetime.now().strftime("%Y-%m-%d")