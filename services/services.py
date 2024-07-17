import os
import time

from flask import jsonify
from loguru import logger
from sqlalchemy import and_, case, func, or_, text
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import aliased

from configs.cache_template import (
    get_rental_message,
    get_tax_message,
    get_template_content_by_name, cache,
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
    User, LookupTemplate,
)
from utils.address_normalizer import (
    extract_latest_address,
    get_first_valid_normalized_address,
)
from utils.check_property_status import check_property_status
from utils.map_keys_to_result import map_keys_to_result

missive_client = MissiveAPI()
CACHE_TTL = 24 * 60 * 60


def search_service(query, conversation_id, to_phone, owner_query_engine_without_sunit):
    session = Session()

    # Run query engine to get address
    normalized_address = get_first_valid_normalized_address([query])
    if not normalized_address:
        logger.error("Couldn't parse address from query", query)
        return (
            jsonify({"message": "Couldn't parse address from query"}),
            200,
        )
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
            phone_number = os.getenv('PHONE_NUMBER')
            if not phone_number:
                return None
            phone_pair_1 = f"{query_phone_number}{phone_number}"
            phone_pair_2 = f"{query_phone_number}{phone_number[:3]}0{phone_number[3:]}"
            ref = [phone_pair_1, phone_pair_2]
            comments = session.query(Comments.body).filter(Comments.conversation_id == conversation_id).all()

            messages = session.query(TwilioMessage.from_field, TwilioMessage.delivered_at,
                                     TwilioMessage.preview).filter(
                and_(
                    or_(TwilioMessage.from_field == query_phone_number, TwilioMessage.to_field == query_phone_number),
                    or_(TwilioMessage.references == ref)
                )
            ).order_by(TwilioMessage.delivered_at).all()

            author_zipcode, author_email = session.query(
                Author.zipcode, Author.email
            ).filter(Author.phone_number == query_phone_number).first() or (None, None)

            conversation_summary = get_conversation_data_with_cache(
                comments, messages, conversation_id, query_phone_number
            )
            conversation_summary['messages_title'] = get_template_content_by_name("messages_title")
            conversation_summary['comments_title'] = get_template_content_by_name("comments_title")
            conversation_summary['outcome_title'] = get_template_content_by_name("outcome_title")
            if author_zipcode:
                conversation_summary['author_zipcode'] = author_zipcode
            if author_email:
                conversation_summary['author_email'] = author_email
            return conversation_summary

    except Exception as e:
        logger.error(f"Error occurred while retrieving conversation summary: {str(e)}")
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


@cache.memoize(timeout=CACHE_TTL)
def get_conversation_data_with_cache(comments, messages, conversation_id, query_phone_number):
    try:
        with Session() as session:
            phone_number = os.getenv('PHONE_NUMBER')
            if not phone_number:
                return None

            assignee_users = session.query(User.name).join(
                ConversationAssignee, ConversationAssignee.user_id == User.id
            ).filter(ConversationAssignee.conversation_id == conversation_id).all()
            assignee_user_names = [user.name for user in assignee_users if user.name is not None]

            label_ids = session.query(ConversationLabel.label_id).filter(
                ConversationLabel.conversation_id == conversation_id
            ).distinct().all()
            label_ids = [label_id[0] for label_id in label_ids]

            messages_from_query_phone_number = [message for message in messages if
                                                message.from_field == query_phone_number]

            first_message = int(messages_from_query_phone_number[
                0].delivered_at.timestamp()) if messages_from_query_phone_number else None
            last_message = int(messages_from_query_phone_number[
                -1].delivered_at.timestamp()) if messages_from_query_phone_number else None

            template_names = ["comment_summary_prompt", "impact_summary_prompt", "message_summary_prompt"]
            results = session.query(LookupTemplate.name, LookupTemplate.content).filter(
                LookupTemplate.name.in_(template_names)).all()
            content_dict = {result.name: result.content for result in results}

            comment_summary_template = content_dict.get("comment_summary_prompt", "")
            impact_summary_template = content_dict.get("impact_summary_prompt", "")
            message_summary_template = content_dict.get("message_summary_prompt", "")

            comment_summary = generate_text_summary(comments, comment_summary_template)
            impact_summary = generate_text_summary(messages, impact_summary_template)
            message_summary = generate_text_summary(messages, message_summary_template)
            keyword_label_parent_id = get_template_content_by_name("keyword_label_parent_id")
            impact_label_parent_id = get_template_content_by_name("impact_label_parent_id")

            conversation_summary = {
                'assignee_user_name': assignee_user_names,
                'first_reply': first_message,
                'last_reply': last_message,
                'labels': label_ids,
                'comments': comment_summary.text,
                'outcome': impact_summary.text,
                'messages': message_summary.text,
                'keyword_label_parent_id': keyword_label_parent_id,
                'impact_label_parent_id': impact_label_parent_id
            }
            return conversation_summary

    except Exception as e:
        logger.error(f"Error occurred while generating LLM summary: {str(e)}")
        raise


def update_author_and_missive(phone_number, email, zipcode):
    try:
        with Session() as session:
            author = session.query(Author).filter(Author.phone_number == phone_number).one()
            if email is not None:
                author.email = email
            if zipcode is not None:
                author.zipcode = zipcode
            session.commit()
            return {"message": "Author updated successfully"}, 200
    except NoResultFound:
        return {"error": "Author not found"}, 404
    except Exception as e:
        session.rollback()
        error_type = "email" if email else "zipcode"
        error_message = f"Failed to update {error_type}: {str(e)}"
        logger.error(f"Error occurred while updating contact email/zipcode: {str(e)}")
        return {"type": error_type, "msg": error_message}, 500
