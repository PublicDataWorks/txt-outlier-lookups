from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class mi_wayne_detroit(Base):
    __tablename__ = "mi_wayne_detroit"
    __table_args__ = {"schema": "address_lookup"}

    ogc_fid = Column(
        Integer,
        primary_key=True,
        server_default=text("nextval('address_lookup.mi_wayne_detroit_ogc_fid_seq'::regclass)"),
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

    
class lookup_history(Base):
    __tablename__ = "lookup_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String(255), nullable=False)
    zip_code = Column(String(20))
    tax_status = Column(String(50))
    rental_status = Column(String(50))


class residential_rental_registrations(Base):
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
    replies_proactive = Column(Integer)
    replies_receptive = Column(Integer)
    replies_connected = Column(Integer)
    replies_passive = Column(Integer)
    replies_inactive = Column(Integer)

    unsubscribes_total = Column(Integer)
    unsubscribes_proactive = Column(Integer)
    unsubscribes_receptive = Column(Integer)
    unsubscribes_connected = Column(Integer)
    unsubscribes_passive = Column(Integer)
    unsubscribes_inactive = Column(Integer)
