# app/queries/weekly_queries.py

from sqlalchemy.sql import text

from .config import (
    IMPACT_LABEL_IDS,
    BROADCAST_SOURCE_PHONE_NUMBER,
)

GET_WEEKLY_UNSUBSCRIBE_BY_AUDIENCE_SEGMENT = text("""
    SELECT 
    bsms.audience_segment_id,
    asg.name as audience_segment_name,
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

GET_WEEKLY_BROADCAST_SENT = text("""
    SELECT *
    FROM public.broadcast_sent_message_status
    WHERE 
    is_second = False
    AND
    created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
    AND 
    created_at < DATE_TRUNC('week', CURRENT_DATE) 
""")

GET_WEEKLY_BROADCAST_STARTERS = text("""
    SELECT COUNT(*) AS COUNT
    FROM BROADCAST_SENT_MESSAGE_STATUS
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
    SELECT COUNT(*) AS count
    FROM public.broadcast_sent_message_status
    WHERE 
    twilio_sent_status = 'undelivered' 
    AND
    created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
    AND 
    created_at < DATE_TRUNC('week', CURRENT_DATE) 
""")

GET_WEEKLY_TEXT_INS = text(f"""
    SELECT COUNT(DISTINCT from_field) AS count
    FROM public.twilio_messages
    WHERE 
        is_broadcast_reply = false
        AND from_field != '{BROADCAST_SOURCE_PHONE_NUMBER}'
        AND created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
        AND created_at < DATE_TRUNC('week', CURRENT_DATE) 
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

GET_WEEKLY_REPLIES_BY_AUDIENCE_SEGMENT = text("""
    SELECT bsms.audience_segment_id, asg.name as audience_segment_name, COUNT(distinct tm.id) as count
    FROM public.twilio_messages tm 
    LEFT JOIN public.broadcast_sent_message_status bsms 
    ON tm.reply_to_broadcast = bsms.broadcast_id
    LEFT JOIN public.audience_segments asg 
    ON bsms.audience_segment_id = asg.id
    WHERE tm.is_broadcast_reply = true and tm.from_field = bsms.recipient_phone_number
    GROUP BY bsms.audience_segment_id, asg.name
""")

GET_WEEKLY_REPORTER_CONVERSATION = lambda reporter_label_ids: text(f"""
    SELECT COUNT(distinct cl.conversation_id) as count
    FROM public.conversations_labels cl 
    JOIN public.labels l ON cl.label_id = l.id
    WHERE cl.label_id IN ({reporter_label_ids})
    AND
    cl.created_at >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week'  
    AND 
    cl.created_at < DATE_TRUNC('week', CURRENT_DATE)
""")

GET_WEEKLY_DATA_LOOKUP = text("""
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
