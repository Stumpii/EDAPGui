from EDMesg.EDMesgBase import EDMesgAction, EDMesgEvent
from EDMesg.EDMesgProvider import EDMesgProvider
from EDMesg.EDMesgClient import EDMesgClient


class LoadWaypointFileAction(EDMesgAction):
    filepath: str


class StartWaypointAssistAction(EDMesgAction):
    pass


class StopAllAssistsAction(EDMesgAction):
    pass


class UndockAction(EDMesgAction):
    pass


class UndockCompleteEvent(EDMesgEvent):
    pass


# Factory methods
provider_name = "EDAP"
actions: list[type[EDMesgAction]] = [
    LoadWaypointFileAction,
    UndockAction,
    StartWaypointAssistAction,
    StopAllAssistsAction,
]
events: list[type[EDMesgEvent]] = [
    UndockCompleteEvent,
]
actions_port = 15560
events_port = 15561


def create_edap_provider() -> EDMesgProvider:
    return EDMesgProvider(
        provider_name=provider_name,
        action_types=actions,
        event_types=events,
        action_port=actions_port,
        event_port=events_port,
    )


def create_edap_client() -> EDMesgClient:
    return EDMesgClient(
        provider_name=provider_name,
        action_types=actions,
        event_types=events,
        action_port=actions_port,
        event_port=events_port,
    )
