from typing import Optional
from app.models.lead import Lead
from app.models.order import Order
from app.schemas.lead import LeadOut
from app.schemas.order import OrderOut


def build_lead_response(lead: Lead) -> LeadOut:
    return LeadOut(
        id=lead.id,
        name=lead.name,
        phone=lead.phone,
        email=lead.email,
        origin_zip=lead.origin_zip,
        dest_zip=lead.dest_zip,
        vehicle_type=lead.vehicle_type,
        operable=lead.operable,
        created_by=lead.created_by,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


def build_order_response(order: Order) -> OrderOut:
    return OrderOut(
        id=order.id,
        lead_id=order.lead_id,
        status=order.status,
        base_price=order.base_price,
        final_price=order.final_price,
        notes=order.notes,
        created_by=order.created_by,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def build_lead_response_list(leads: list) -> list:
    return [build_lead_response(lead) for lead in leads]


def build_order_response_list(orders: list) -> list:
    return [build_order_response(order) for order in orders]
