import os
import time

from flask import jsonify
from loguru import logger
from sqlalchemy import and_, case, func, or_, text
from sqlalchemy.orm import aliased

from configs.cache_template import (
    get_rental_message,
    get_tax_message,
    get_template_content_by_name,
)
from configs.database import Session
from configs.query_engine.text_summary import generate_text_summary
from constants.following_message import FollowingMessageType
from libs.MissiveAPI import MissiveAPI
from models import (
    Author,
    Comments,
    ConversationAssignee,
    ConversationLabel,
    LookupHistory,
    MiWayneDetroit,
    ResidentialRentalRegistrations,
    TwilioMessage,
    User,
)
from utils.address_normalizer import (
    extract_latest_address,
    get_first_valid_normalized_address,
)
from utils.check_property_status import check_property_status
from utils.map_keys_to_result import map_keys_to_result

missive_client = MissiveAPI()


def search_service(query, conversation_id, to_phone, owner_query_engine_without_sunit):
    session = Session()

    # Run query engine to get address
    normalized_address = get_first_valid_normalized_address([query])
    address, sunit = extract_address_information(normalized_address)
    rental_status_case = case(
        (ResidentialRentalRegistrations.lat.isnot(None), "REGISTERED"), else_="UNREGISTERED"
    ).label("rental_status")

    if not address:
        logger.error("Wrong format address", query)
        return handle_wrong_format(conversation_id=conversation_id, to_phone=to_phone)
    else:
        if sunit:
            results = (
                session.query(
                    MiWayneDetroit.address,
                    rental_status_case,
                    MiWayneDetroit.tax_status,
                    MiWayneDetroit.szip5,
                    MiWayneDetroit.tax_due,
                )
                .outerjoin(
                    ResidentialRentalRegistrations,
                    and_(
                        func.ST_DWithin(
                            MiWayneDetroit.wkb_geometry,
                            ResidentialRentalRegistrations.wkb_geometry,
                            0.001,
                        ),
                        func.strict_word_similarity(
                            func.upper(MiWayneDetroit.saddstr),
                            func.upper(ResidentialRentalRegistrations.street_name),
                        )
                        > 0.8,
                        MiWayneDetroit.saddno == ResidentialRentalRegistrations.street_num,
                    ),
                )
                .filter(
                    MiWayneDetroit.address.ilike(f"{address.strip()}%"),
                    or_(
                        MiWayneDetroit.sunit.ilike(f"%{sunit}%"),
                    ),
                )
                .all()
            )
        else:
            results = (
                session.query(
                    MiWayneDetroit.address,
                    rental_status_case,
                    MiWayneDetroit.tax_status,
                    MiWayneDetroit.szip5,
                    MiWayneDetroit.tax_due,
                )
                .outerjoin(
                    ResidentialRentalRegistrations,
                    and_(
                        func.ST_DWithin(
                            MiWayneDetroit.wkb_geometry,
                            ResidentialRentalRegistrations.wkb_geometry,
                            0.001,
                        ),
                        func.strict_word_similarity(
                            func.upper(MiWayneDetroit.saddstr),
                            func.upper(ResidentialRentalRegistrations.street_name),
                        )
                        > 0.8,
                        MiWayneDetroit.saddno == ResidentialRentalRegistrations.street_num,
                    ),
                )
                .filter(
                    MiWayneDetroit.address.ilike(f"{address.strip()}%"),
                )
                .all()
            )

    display_address = address if not sunit else address + " " + sunit
    if not results:
        return handle_no_match(display_address, conversation_id, to_phone)

    address, rental_status, tax_status, zip_code, tax_due = results[0]

    if not tax_status and tax_due and int(tax_due) > 0:
        add_data_lookup_to_db(
            address,
            zip_code,
            "TAX_DEBT",
            rental_status,
        )
    elif not tax_status and tax_due and int(tax_due) > 0 or tax_status == "OK":
        add_data_lookup_to_db(
            address,
            zip_code,
            "NO_TAX_DEBT",
            rental_status,
        )
    else:
        add_data_lookup_to_db(
            address,
            zip_code,
            tax_status,
            rental_status,
        )

    if len(results) > 1:
        return handle_ambiguous(display_address, conversation_id, to_phone)

    # Missive API to adding tags
    query_result = owner_query_engine_without_sunit.query(address)

    if "result" not in query_result.metadata:
        logger.error(query_result)
        return "", 200

    owner_data = map_keys_to_result(query_result.metadata)

    following_message_type = ""
    if "owner" in owner_data:
        if "LAND BANK" in owner_data["owner"].upper():
            following_message_type = FollowingMessageType.LAND_BACK
        elif "UNCONFIRMED" in owner_data["tax_status"].upper():
            following_message_type = FollowingMessageType.UNCONFIRMED_TAX_STATUS
        else:
            following_message_type = FollowingMessageType.DEFAULT

    return handle_match(query_result, conversation_id, to_phone, rental_status, following_message_type)


def more_search_service(conversation_id, to_phone, tax_query_engine, tax_query_engine_without_sunit):
    messages = missive_client.extract_preview_content(conversation_id=conversation_id)
    normalized_address = extract_latest_address(messages, conversation_id, to_phone)
    if not normalized_address:
        logger.error("Couldn't parse address from history messages", messages)
        return (
            jsonify({"message": "Couldn't parse address from history messages"}),
            200,
        )

    address, sunit = extract_address_information(normalized_address)

    if sunit:
        query_result = tax_query_engine.query(str({"address": address, "sunit": sunit}))
    else:
        query_result = tax_query_engine_without_sunit.query(str({"address": {address}}))

    if "result" not in query_result.metadata:
        logger.error(query_result)
        return "", 200

    tax_status, rental_status = check_property_status(query_result)
    process_statuses(tax_status, rental_status, conversation_id, to_phone)


def handle_no_match(query, conversation_id, to_phone):
    # Missive API -> Send SMS template
    content = get_template_content_by_name("no_match")
    if content:
        formatted_content = content.format(address=query)
        missive_client.send_sms_sync(
            formatted_content,
            to_phone,
            conversation_id,
        )
        return {"result": formatted_content}, 200
    else:
        logger.exception("Could not find template no_match")
        return {"result": ""}, 200


def handle_ambiguous(query, conversation_id, to_phone):
    # Missive API -> Send SMS template
    content = get_template_content_by_name("closest_match")
    if content:
        formatted_content = content.format(address=query)
        missive_client.send_sms_sync(
            formatted_content,
            to_phone,
            conversation_id,
        )
        return {"result": formatted_content}, 200
    else:
        logger.exception("Could not find template closest_match")
        return {"result": ""}, 200


def handle_match(
        response,
        conversation_id,
        to_phone,
        rental_status="UNREGISTERED",
        following_message_type="",
):
    response = str(response)
    if rental_status == "REGISTERED":
        response += "It is registered as a residential rental property"

    # Missive API -> Send SMS template
    missive_client.send_sms_sync(
        str(response),
        conversation_id=conversation_id,
        to_phone=to_phone,
        add_label_list=[os.environ.get("MISSIVE_LOOKUP_TAG_ID")],
    )

    time.sleep(2)

    match following_message_type:
        case FollowingMessageType.LAND_BACK:
            following_message = get_template_content_by_name(FollowingMessageType.LAND_BACK)
        case FollowingMessageType.UNCONFIRMED_TAX_STATUS:
            following_message = get_template_content_by_name(FollowingMessageType.UNCONFIRMED_TAX_STATUS)
        case FollowingMessageType.DEFAULT:
            following_message = get_template_content_by_name(FollowingMessageType.DEFAULT)
        case _:
            following_message = ""

    if following_message:
        missive_client.send_sms_sync(
            following_message,
            conversation_id=conversation_id,
            to_phone=to_phone,
            add_label_list=[os.environ.get("MISSIVE_LOOKUP_TAG_ID")],
        )
    # Remove tags
    return {"result": str(response)}, 200


def handle_wrong_format(conversation_id, to_phone):
    content = get_template_content_by_name("wrong_format")
    if content:
        missive_client.send_sms_sync(
            content,
            conversation_id=conversation_id,
            to_phone=to_phone,
        )
        return {"result": content}, 200
    else:
        logger.exception("Could not find template wrong_format")
        return {"result": ""}, 200


def process_statuses(tax_status, rental_status, conversation_id, phone):
    if tax_status and tax_status != "NO_TAX_DEBT":
        missive_client.send_sms_sync(
            get_tax_message(tax_status),
            conversation_id=conversation_id,
            to_phone=phone,
        )
        time.sleep(2)

    if rental_status:
        missive_client.send_sms_sync(
            get_rental_message(rental_status),
            conversation_id=conversation_id,
            to_phone=phone,
        )
        time.sleep(2)

    content = get_template_content_by_name("final")
    if content:
        missive_client.send_sms_sync(
            content,
            conversation_id=conversation_id,
            to_phone=phone,
        )


def extract_address_information(normalized_address):
    address = normalized_address.get("address_line_1", "")
    address_line_2 = normalized_address.get("address_line_2")
    if address_line_2 is not None:
        sunit = " ".join(address_line_2.replace("UNIT", "").replace("#", "").split())
    else:
        sunit = ""

    return address, sunit


def add_data_lookup_to_db(address, zip_code, tax_status, rental_status):
    session = Session()
    try:
        new_data_lookup = LookupHistory(
            address=address, zip_code=zip_code, tax_status=tax_status, rental_status=rental_status
        )
        session.add(new_data_lookup)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_address_information(session, address):
    normalized_address = get_first_valid_normalized_address([address])
    address, sunit = extract_address_information(normalized_address)

    # Define the case statement for rental_status
    rental_status_case = case(
        (ResidentialRentalRegistrations.lat.isnot(None), "IS"), else_="IS NOT"
    ).label("rental_status")

    query = (
        session.query(
            rental_status_case,
            MiWayneDetroit.tax_due,
            MiWayneDetroit.tax_status,
            MiWayneDetroit.szip5,
        )
        .outerjoin(
            ResidentialRentalRegistrations,
            and_(
                func.ST_DWithin(
                    MiWayneDetroit.wkb_geometry,
                    ResidentialRentalRegistrations.wkb_geometry,
                    0.001,
                ),
                func.strict_word_similarity(
                    MiWayneDetroit.address,
                    ResidentialRentalRegistrations.street_num
                    + " "
                    + ResidentialRentalRegistrations.street_name,
                )
                > 0.8,
            ),
        )
        .filter(
            MiWayneDetroit.address.ilike(f"{address.strip()}%"),
            or_(
                MiWayneDetroit.sunit.ilike(f"%{sunit}%"),
                MiWayneDetroit.sunit == "",
                MiWayneDetroit.sunit.is_(None),
            ),
        )
    )

    results = query.all()
    return results


def get_conversation_data(conversation_id, query_phone_number):
    try:
        with Session() as session:
            # Get the query phone number
            phone_number = os.getenv('PHONE_NUMBER')
            if not phone_number:
                return None
            phone_pair_1 = [query_phone_number + phone_number]
            phone_pair_2 = [phone_number + query_phone_number]

            # Query authors table
            author = session.query(Author).filter(Author.phone_number == query_phone_number).first()
            author_zipcode = author.zipcode if author else None
            author_email = author.email if author else None

            # Query conversations_assignees and users tables
            UserAlias = aliased(User)
            assignee_users = session.query(UserAlias.name).join(
                ConversationAssignee, ConversationAssignee.user_id == UserAlias.id
            ).filter(ConversationAssignee.conversation_id == conversation_id).all()
            assignee_user_names = [user.name for user in assignee_users if user.name is not None]

            label_ids = session.query(ConversationLabel.label_id).filter(
                ConversationLabel.conversation_id == conversation_id
            ).distinct().all()
            label_ids = [label_id[0] for label_id in label_ids]

            # Query TwilioMessage table
            messages = session.query(TwilioMessage.preview).filter(
                and_(
                    or_(TwilioMessage.from_field == query_phone_number, TwilioMessage.to_field == query_phone_number),
                    or_(TwilioMessage.references == phone_pair_1, TwilioMessage.references == phone_pair_2)
                )
            ).order_by(TwilioMessage.delivered_at).all()

            first_reply = session.query(TwilioMessage.delivered_at).filter(
                and_(
                    TwilioMessage.from_field == query_phone_number,
                    or_(TwilioMessage.references == phone_pair_1, TwilioMessage.references == phone_pair_2)
                )
            ).order_by(TwilioMessage.delivered_at).first()

            # Query comments table
            comments = session.query(Comments).filter(Comments.conversation_id == conversation_id).all()

            comment_summary = generate_text_summary(comments, "A summary of all comments left in the thread by "
                                                              "reporters over time. Recommendations the reporters "
                                                              "made, handoffs to other reporters, process/case notes, "
                                                              "phone call notes,")
            impact_summary = generate_text_summary(messages, "A short summary of impact/conversation outcomes for "
                                                             "this contact. Detailing whether their issues have "
                                                             "consistently been addressed, or if they were unable to "
                                                             "get the help they needed.")
            message_summary = generate_text_summary(messages, "A summary detailing the contact's general tone and "
                                                              "approach during the conversations. Here we could flag "
                                                              "if a contact has been abusive or rude in their "
                                                              "communications with Outlier staff. Also include "
                                                              "relevant case notes (e.g., this person never follows "
                                                              "up after we provide info), notes from phone calls.")

            # Create a dictionary to store the conversation summary
            conversation_summary = {
                'author_zipcode': author_zipcode,
                'author_email': author_email,
                'assignee_user_name': assignee_user_names,
                'first_reply': first_reply[0] if first_reply else None,
                'labels': label_ids,
                'comments': comment_summary.text,
                'outcome': impact_summary.text,
                'messages': message_summary.text
            }

            return conversation_summary

    except Exception as e:
        # Log the error for debugging purposes
        print(f"Error occurred while retrieving conversation summary: {str(e)}")
        # Re-raise the exception to be handled by the calling code
        raise


def extract_address_messages_from_supabase(phone):
    session = Session()
    messages = (
        session.query(TwilioMessage)
        .filter(TwilioMessage.from_field == phone)
        .order_by(text("delivered_at desc"))
        .limit(30)
        .all()
    )

    return list(map(lambda a: a.preview, messages))


def get_conversation_summary(conversation_id, reference):
    pass
