from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    AGENT = "agent"

    def __str__(self):
        return self.value


class VehicleType(str, Enum):
    SEDAN = "sedan"
    SUV = "suv"
    TRUCK = "truck"

    def __str__(self):
        return self.value


class OrderStatus(str, Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    BOOKED = "booked"
    DELIVERED = "delivered"

    def __str__(self):
        return self.value


class AuditAction(str, Enum):
    CREATE_LEAD = "create_lead"
    UPDATE_LEAD = "update_lead"
    DELETE_LEAD = "delete_lead"
    UPLOAD_ATTACHMENT = "upload_attachment"
    CREATE_ORDER = "create_order"
    UPDATE_ORDER = "update_order"
    DELETE_ORDER = "delete_order"
    REPRICE_ORDER = "reprice_order"
    LOGIN = "login"

    def __str__(self):
        return self.value
