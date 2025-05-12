import uuid

from geoalchemy2 import Geometry
from sqlalchemy import (
    ARRAY,
    TEXT,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    text,
    Text,
    SmallInteger
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class MiWayneDetroit(Base):
    __tablename__ = "mi_wayne_detroit"
    __table_args__ = {"schema": "address_lookup"}

    ogc_fid = Column(
        Integer,
        primary_key=True,
        server_default=text(
            "nextval('address_lookup.mi_wayne_detroit_ogc_fid_seq'::regclass)"
        ),
    )
    wkb_geometry = Column(Geometry(), index=True)
    geoid = Column(String)
    parcelnumb = Column(String)
    parcelnumb_no_formatting = Column(String)
    state_parcelnumb = Column(String)
    account_number = Column(String)
    tax_id = Column(String)
    alt_parcelnumb1 = Column(String)
    alt_parcelnumb2 = Column(String)
    alt_parcelnumb3 = Column(String)
    usecode = Column(String)
    usedesc = Column(String)
    zoning = Column(String)
    zoning_description = Column(String)
    zoning_type = Column(String)
    zoning_subtype = Column(String)
    zoning_code_link = Column(String)
    zoning_id = Column(Integer)
    struct = Column(Boolean)
    structno = Column(Integer)
    yearbuilt = Column(Integer)
    numstories = Column(Float(53))
    numunits = Column(Integer)
    numrooms = Column(Float(53))
    structstyle = Column(String)
    parvaltype = Column(String)
    improvval = Column(Float(53))
    landval = Column(Float(53))
    parval = Column(Float(53))
    agval = Column(Float(53))
    homestead_exemption = Column(String)
    saleprice = Column(Float(53))
    saledate = Column(Date)
    taxamt = Column(Float(53))
    taxyear = Column(String)
    owntype = Column(String)
    owner = Column(String)
    ownfrst = Column(String)
    ownlast = Column(String)
    owner2 = Column(String)
    owner3 = Column(String)
    owner4 = Column(String)
    previous_owner = Column(String)
    mailadd = Column(String)
    mail_address2 = Column(String)
    careof = Column(String)
    mail_addno = Column(String)
    mail_addpref = Column(String)
    mail_addstr = Column(String)
    mail_addsttyp = Column(String)
    mail_addstsuf = Column(String)
    mail_unit = Column(String)
    mail_city = Column(String)
    mail_state2 = Column(String)
    mail_zip = Column(String)
    mail_country = Column(String)
    mail_urbanization = Column(String)
    address = Column(String)
    address2 = Column(String)
    saddno = Column(String)
    saddpref = Column(String)
    saddstr = Column(String)
    saddsttyp = Column(String)
    saddstsuf = Column(String)
    sunit = Column(String)
    scity = Column(String)
    original_address = Column(String)
    city = Column(String)
    county = Column(String)
    state2 = Column(String)
    szip = Column(String)
    szip5 = Column(String)
    urbanization = Column(String)
    ll_address_count = Column(Integer)
    location_name = Column(String)
    address_source = Column(String)
    legaldesc = Column(String)
    plat = Column(String)
    book = Column(String)
    page = Column(String)
    block = Column(String)
    lot = Column(String)
    neighborhood = Column(String)
    subdivision = Column(String)
    lat = Column(String)
    lon = Column(String)
    fema_flood_zone = Column(String)
    fema_flood_zone_subtype = Column(String)
    fema_flood_zone_raw = Column(String)
    fema_flood_zone_data_date = Column(Date)
    qoz = Column(String)
    qoz_tract = Column(String)
    census_tract = Column(String)
    census_block = Column(String)
    census_blockgroup = Column(String)
    census_zcta = Column(String)
    census_elementary_school_district = Column(String)
    census_secondary_school_district = Column(String)
    census_unified_school_district = Column(String)
    ll_last_refresh = Column(Date)
    sourceurl = Column(String)
    recrdareatx = Column(String)
    recrdareano = Column(Integer)
    gisacre = Column(Float(53))
    sqft = Column(Float(53))
    ll_gisacre = Column(Float(53))
    ll_gissqft = Column(BigInteger)
    ll_bldg_footprint_sqft = Column(Integer)
    ll_bldg_count = Column(Integer)
    cdl_raw = Column(String)
    cdl_majority_category = Column(String)
    cdl_majority_percent = Column(Float(53))
    cdl_date = Column(String)
    plss_township = Column(String)
    plss_section = Column(String)
    plss_range = Column(String)
    reviseddate = Column(Date)
    path = Column(String)
    ll_stable_id = Column(String)
    ll_uuid = Column(UUID)
    ll_stack_uuid = Column(String)
    ll_row_parcel = Column(String)
    ll_updated_at = Column(DateTime(True))
    placekey = Column(String)
    dpv_status = Column(String)
    dpv_codes = Column(String)
    dpv_notes = Column(String)
    dpv_type = Column(String)
    cass_errorno = Column(String)
    rdi = Column(String)
    usps_vacancy = Column(String)
    usps_vacancy_date = Column(Date)
    padus_public_access = Column(String)
    lbcs_activity = Column(Float(53))
    lbcs_activity_desc = Column(String)
    lbcs_function = Column(Float(53))
    lbcs_function_desc = Column(String)
    lbcs_structure = Column(Float(53))
    lbcs_structure_desc = Column(String)
    lbcs_site = Column(Float(53))
    lbcs_site_desc = Column(String)
    lbcs_ownership = Column(Float(53))
    lbcs_ownership_desc = Column(String)
    sourceagent = Column(String)
    multistruct = Column(Boolean)
    subsurfown = Column(String)
    subowntype = Column(String)
    sourceref = Column(String)
    sourcedate = Column(Date)
    property_class = Column(String)
    ward = Column(String)
    council_district = Column(String)
    taxable_status = Column(String)
    tax_status = Column(String)
    nez = Column(String)
    frontage = Column(Float(53))
    depth = Column(Float(53))
    taxable_value = Column(Float(53))
    landmap = Column(String)
    related = Column(String)
    vacant_land_program = Column(String)
    vacant_land_program_cluster = Column(String)
    land_bank_inventory_status = Column(String)
    sale_number = Column(Integer)
    grantor = Column(String)
    grantee = Column(String)
    sale_terms = Column(String)
    verified_by = Column(String)
    sale_instrument = Column(String)
    sale_trans = Column(String)
    ecf = Column(String)
    relatedparcel = Column(String)
    tax_due = Column(Float(53))
    tax_details = Column(String)
    tax_payments = Column(String)
    refid_uniq_parcelnumb = Column(Boolean)
    tax_details_bak = Column(String)
    tax_payments_bak = Column(String)


class LookupHistory(Base):
    __tablename__ = "lookup_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String(255), nullable=False)
    zip_code = Column(String(20))
    tax_status = Column(String(50))
    rental_status = Column(String(50))


class ResidentialRentalRegistrations(Base):
    __tablename__ = "residential_rental_registrations"
    __table_args__ = {"schema": "address_lookup"}

    ogc_fid = Column(
        Integer,
        primary_key=True,
        server_default=text(
            "nextval('address_lookup.\"Residential_Rental_Registrations_ogc_fid_seq\"'::regclass)"
        ),
    )
    wkb_geometry = Column(Geometry(), index=True)
    record_id = Column(String)
    date_status = Column(DateTime(True))
    parcel_id = Column(String)
    lon = Column(Float(53))
    lat = Column(Float(53))
    ObjectId = Column(Integer)
    street_num = Column(String)
    street_dir = Column(String)
    street_name = Column(String)
    address_id = Column(String)


class LookupTemplate(Base):
    __tablename__ = "lookup_template"
    __table_args__ = {"schema": "public"}

    id = Column(BigInteger, primary_key=True)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    name = Column(String, unique=True)
    content = Column(String)
    type = Column(String)

    def __repr__(self):
        return f"<LookupTemplate(id={self.id}, name='{self.name}', type='{self.type}')>"


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True)
    created_at = Column(Date, nullable=False)

    conversation_starters_sent = Column(Integer)
    broadcast_replies = Column(Integer)
    text_ins = Column(Integer)
    reporter_conversations = Column(Integer)
    failed_deliveries = Column(Integer)
    unsubscribes = Column(Integer)

    user_satisfaction = Column(Integer)
    problem_addressed = Column(Integer)
    crisis_averted = Column(Integer)
    accountability_gap = Column(Integer)
    source = Column(Integer)
    unsatisfied = Column(Integer)
    future_keyword = Column(Integer)

    status_registered = Column(Integer)
    status_unregistered = Column(Integer)
    status_tax_debt = Column(Integer)
    status_no_tax_debt = Column(Integer)
    status_compliant = Column(Integer)
    status_foreclosed = Column(Integer)

    replies_total = Column(Integer)
    replies_proactive = Column(Integer, default=0)
    replies_receptive = Column(Integer, default=0)
    replies_connected = Column(Integer, default=0)
    replies_passive = Column(Integer, default=0)
    replies_inactive = Column(Integer, default=0)

    unsubscribes_total = Column(Integer)
    unsubscribes_proactive = Column(Integer, default=0)
    unsubscribes_receptive = Column(Integer, default=0)
    unsubscribes_connected = Column(Integer, default=0)
    unsubscribes_passive = Column(Integer, default=0)
    unsubscribes_inactive = Column(Integer, default=0)


class Author(Base):
    __tablename__ = "authors"

    phone_number = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    unsubscribed = Column(Boolean, nullable=False, default=False)
    zipcode = Column(String, nullable=True)
    email = Column(String, nullable=True)

    def __repr__(self):
        return f"<Author(name={self.name}, phone_number={self.phone_number}, unsubscribed={self.unsubscribed})>"


class TwilioMessage(Base):
    __tablename__ = "twilio_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    preview = Column(String, nullable=True)
    type = Column(String, nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    references = Column(ARRAY(TEXT), nullable=True)
    external_id = Column(String, nullable=True)
    attachments = Column(String, nullable=True)
    from_field = Column(String, nullable=True)
    to_field = Column(String, nullable=True)
    is_reply = Column(Boolean, nullable=True, default=False)
    reply_to_broadcast = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<TwilioMessage(id={self.id}, type={self.type}, delivered_at={self.delivered_at})>"


class ConversationLabel(Base):
    __tablename__ = "conversations_labels"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(UUID(as_uuid=True))
    label_id = Column(UUID(as_uuid=True))
    updated_at = Column(DateTime(timezone=True))
    is_archived = Column(Boolean)

    def __repr__(self):
        return f"<ConversationLabel(id={self.id}, conversation_id={self.conversation_id}, label_id={self.label_id})>"


class ConversationAssignee(Base):
    __tablename__ = "conversations_assignees"

    id = Column(Integer, primary_key=True)
    unassigned = Column(Boolean)
    closed = Column(Boolean)
    archived = Column(Boolean)
    trashed = Column(Boolean)
    junked = Column(Boolean)
    assigned = Column(Boolean)
    flagged = Column(Boolean)
    snoozed = Column(Boolean)
    conversation_id = Column(UUID(as_uuid=True))
    user_id = Column(UUID(as_uuid=True))

    def __repr__(self):
        return f"<ConversationAssignee(id={self.id}, conversation_id={self.conversation_id}, user_id={self.user_id})>"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String)
    name = Column(String)
    avatar_url = Column(String)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', name='{self.name}')>"


class Comments(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True)
    created_at = Column(DateTime(timezone=True))
    body = Column(String)
    task_completed_at = Column(DateTime(timezone=True))
    user_id = Column(UUID(as_uuid=True))
    is_task = Column(Boolean)
    conversation_id = Column(UUID(as_uuid=True))
    attachment = Column(JSONB)

    def __repr__(self):
        return f"<Comment(id={self.id}, body='{self.body}', user_id={self.user_id})>"


class CommentsMentions(Base):
    __tablename__ = 'comments_mentions'
    id = Column(Integer, primary_key=True)
    comment_id = Column(UUID)
    user_id = Column(UUID)


class PosibleHomeownerWindfall(Base):
    __tablename__ = 'posible_homeowner_windfalls'
    __table_args__ = {'schema': 'address_lookup', 'comment': 'Likely and Possible Homeowner Windfalls 2015 - 2019'}

    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    status = Column(Text)
    tax_auction_year = Column(SmallInteger)
    parcel_id = Column(Text, primary_key=True)
    street_address = Column(Text)
    city = Column(Text)
    minimum_bid = Column(Float(53))
    auction_sale_price = Column(Float(53))
    windfall_profit = Column(Float(53))
    pre_at_foreclosure = Column(Float(53))
    owner_name_at_foreclosure = Column(Text)
    lat = Column(Text)
    lon = Column(Text)
