from sqlalchemy.sql import text

from services.analytics.config import (
    IMPACT_LABEL_IDS,
    BROADCAST_SOURCE_PHONE_NUMBER,
    AUTOMATED_SENDER_IDS,
)

GET_WEEKLY_TOTAL_UNSUBSCRIBES = text("""
    SELECT COUNT(DISTINCT bsms.recipient_phone_number) AS count
    FROM public.unsubscribed_messages um 
    INNER JOIN public.message_statuses bsms 
        ON um.reply_to = bsms.id
    WHERE um.created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'
""")

GET_WEEKLY_BROADCAST_SENT = text("""
    SELECT *
    FROM public.message_statuses
    WHERE 
    is_second = False
    AND
    created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
    AND 
    created_at < DATE_TRUNC('week', CURRENT_DATE) 
""")

GET_WEEKLY_BROADCAST_STARTERS = text("""
    SELECT COUNT(distinct recipient_phone_number) AS COUNT
    FROM MESSAGE_STATUSES
    WHERE BROADCAST_ID IN :ids
        AND IS_SECOND = FALSE;
""")

GET_WEEKLY_MESSAGES_HISTORY = """
    SELECT tm.*, u.name, u.email
    FROM public.twilio_messages tm LEFT JOIN public.users u on tm.sender_id = u.id
    WHERE 
    tm.created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'
    AND 
    tm.created_at < DATE_TRUNC('week', CURRENT_DATE)
"""

GET_WEEKLY_FAILED_MESSAGE = text("""
    SELECT COUNT(DISTINCT recipient_phone_number) AS count
    FROM public.message_statuses
    WHERE twilio_sent_status IN ('undelivered', 'failed') 
        AND is_second = FALSE
        AND created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'   
""")

GET_WEEKLY_TEXT_INS = text(f"""
    SELECT COUNT(DISTINCT from_field) AS count
    FROM public.twilio_messages
    WHERE is_reply = false
        AND from_field != '{BROADCAST_SOURCE_PHONE_NUMBER}'
        AND created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'
""")

impact_label_ids = ", ".join(f"'{id}'" for id in IMPACT_LABEL_IDS)
GET_WEEKLY_IMPACT_CONVERSATIONS = lambda impact_label_ids: text(f"""
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

GET_WEEKLY_TOTAL_REPLIES = text("""
    SELECT COUNT(DISTINCT tm.from_field) as count
    FROM public.twilio_messages tm 
    LEFT JOIN public.message_statuses bsms 
        ON tm.reply_to_broadcast = bsms.broadcast_id 
        AND tm.from_field = bsms.recipient_phone_number
    WHERE tm.reply_to_broadcast IS NOT NULL
        AND tm.created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'
""")

GET_WEEKLY_REPORTER_CONVERSATION = text(f"""
    WITH previous_texters AS (
        SELECT DISTINCT from_field as phone_number
        FROM twilio_messages
        WHERE is_reply = false
            AND from_field != '{BROADCAST_SOURCE_PHONE_NUMBER}'
            AND created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'
    )
    SELECT COUNT(DISTINCT tm.to_field)
    FROM twilio_messages tm 
    WHERE tm.sender_id IS NOT NULL
        AND tm.sender_id NOT IN ({AUTOMATED_SENDER_IDS})
        AND tm.from_field = '{BROADCAST_SOURCE_PHONE_NUMBER}'
        AND tm.created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'
        AND tm.to_field NOT IN (
            SELECT phone_number 
            FROM previous_texters
        )
""")

GET_WEEKLY_DATA_LOOKUP = text("""
    SELECT status, COUNT(*) AS count
    FROM (
        SELECT rental_status AS status
        FROM lookup_history
        WHERE
            created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
        AND 
            created_at < DATE_TRUNC('week', CURRENT_DATE) 
        UNION ALL
        SELECT tax_status AS status
        FROM lookup_history
        WHERE
            created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
        AND 
            created_at < DATE_TRUNC('week', CURRENT_DATE)
    ) AS combined_statuses
    GROUP BY status
    ORDER BY status;
""")

GET_WEEKLY_TOP_ZIP_CODE = text("""
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

GET_WEEKLY_BROADCAST_CONTENT = text("""
   SELECT id, first_message, second_message, run_at
    FROM broadcasts
    WHERE 
    run_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'
    AND 
    run_at < DATE_TRUNC('week', CURRENT_DATE)
    ORDER BY id                                 
""")
