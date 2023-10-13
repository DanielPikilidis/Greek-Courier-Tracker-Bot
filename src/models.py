from dataclasses import dataclass

@dataclass
class Location:
    location: str
    description: str
    datetime: str

@dataclass
class TrackingResult:
    id: str
    found: bool
    delivered: bool
    courier_icon: str
    last_location: Location

@dataclass
class Package:
    tracking_id: str
    courier_name: str
    last_location: str
    description: str