from enum import Enum


class FollowingMessageType(Enum):
    LAND_BANK = "land_bank"
    UNCONFIRMED_TAX_STATUS = "tax_unconfirmed"
    WINDFALL = "windfall"
    DEFAULT = "match_second_message"
