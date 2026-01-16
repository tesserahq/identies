from fastapi import APIRouter
from tessera_sdk.events.nats_healthcheck import NatsHealthcheck

router = APIRouter(prefix="/system", tags=["System"])


@router.post("/nats-healthcheck", operation_id="nats_healthcheck")
async def nats_healthcheck():
    """
    Check the health of the NATS connection.

    Returns a status indicating whether NATS is healthy and operational.
    """
    healthcheck = NatsHealthcheck()
    result = await healthcheck.check()

    return result
