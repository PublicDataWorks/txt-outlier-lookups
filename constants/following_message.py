from enum import Enum


class FollowingMessageType(Enum):
    LAND_BACK = "land_bank"
    UNCONFIRMED_TAX_STATUS = "tax_unconfirmed"
    DEFAULT = "match_second_message"
